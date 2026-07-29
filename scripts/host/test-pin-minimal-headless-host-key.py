#!/usr/bin/env python3
"""Hardware-free tests for volatile target SSH host-key pinning."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/host/pin-minimal-headless-host-key.py"
RECOVERY_INIT = REPO / "initramfs/recovery-init"
TARGET_INIT = REPO / "initramfs/network-root-init"
SPEC = importlib.util.spec_from_file_location("rog5_host_key_pin", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load host-key bootstrap")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def ed25519_blob(byte: int = 0x42) -> bytes:
    return (
        b"\x00\x00\x00\x0bssh-ed25519"
        b"\x00\x00\x00\x20"
        + bytes([byte]) * 32
    )


class HostKeyFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-host-key-test-"
        )
        self.root = Path(self.temporary.name)
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        self.sys_devices = self.root / "sys/devices"
        self.sys_bus_usb = self.root / "sys/bus/usb/devices"
        self.sys_tty = self.root / "sys/class/tty"
        self.sys_net = self.root / "sys/class/net"
        self.sys_devices.mkdir(parents=True)
        self.sys_bus_usb.mkdir(parents=True)
        self.sys_tty.mkdir(parents=True)
        self.sys_net.mkdir(parents=True)
        self.host_boot_id = self.root / "boot_id"
        self.host_boot_id.write_text(
            "11111111-2222-3333-4444-555555555555\n",
            encoding="ascii",
        )
        self.usb = self.sys_devices / "pci0000:00/usb1/1-2"
        self.interface = self.usb / "1-2:1.0"
        self.interface.mkdir(parents=True)
        self.set_product(MODULE.RECOVERY_PRODUCT)
        (self.sys_bus_usb / "1-2").symlink_to(self.usb)
        tty = self.interface / "tty/ttyACM0"
        tty.mkdir(parents=True)
        (self.sys_tty / "ttyACM0").symlink_to(tty)
        self.driver_root = self.root / "drivers/cdc_ncm"
        self.driver_root.mkdir(parents=True)
        self.now = 1_800_000_000

    def close(self) -> None:
        self.temporary.cleanup()

    def set_product(self, product: str) -> None:
        (self.usb / "idVendor").write_text("1d6b\n", encoding="ascii")
        (self.usb / "idProduct").write_text("0104\n", encoding="ascii")
        (self.usb / "product").write_text(
            f"{product}\n", encoding="ascii"
        )

    def install_target(self, *, driver: str = "cdc_ncm") -> None:
        self.set_product(MODULE.TARGET_PRODUCT)
        (self.sys_tty / "ttyACM0").unlink(missing_ok=True)
        net_device = self.interface / "netdev"
        net_device.mkdir(exist_ok=True)
        driver_root = self.root / f"drivers/{driver}"
        driver_root.mkdir(parents=True, exist_ok=True)
        device_link = net_device / "device"
        device_link.unlink(missing_ok=True)
        device_link.symlink_to(self.interface)
        driver_link = self.interface / "driver"
        driver_link.unlink(missing_ok=True)
        driver_link.symlink_to(driver_root)
        net_entry = self.sys_net / "enxrog5"
        net_entry.unlink(missing_ok=True)
        net_entry.symlink_to(net_device)

    def patches(self):
        return mock.patch.multiple(
            MODULE,
            SYS_DEVICES=self.sys_devices,
            SYS_BUS_USB=self.sys_bus_usb,
            SYS_CLASS_TTY=self.sys_tty,
            SYS_CLASS_NET=self.sys_net,
            HOST_BOOT_ID=self.host_boot_id,
        )

    def anchor(self, **changes: str) -> Path:
        values = {
            "format": MODULE.FORMAT,
            "host_boot_id": self.host_boot_id.read_text().strip(),
            "created_unix": str(self.now),
            "usb_location": "pci0000:00/usb1/1-2",
            "recovery_vendor": MODULE.USB_VENDOR,
            "recovery_product_id": MODULE.USB_PRODUCT,
            "recovery_product": MODULE.RECOVERY_PRODUCT,
        }
        values.update(changes)
        path = self.private / "anchor"
        path.write_text(
            "".join(f"{name}={values[name]}\n" for name in MODULE.ANCHOR_KEYS),
            encoding="ascii",
        )
        path.chmod(0o600)
        return path


class HostKeyBootstrapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = HostKeyFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_capture_writes_one_private_canonical_anchor(self) -> None:
        output = self.fixture.private / "anchor"
        with (
            self.fixture.patches(),
            mock.patch.object(
                MODULE, "wait_for_recovery",
                return_value="pci0000:00/usb1/1-2",
            ),
            mock.patch.object(MODULE.time, "time", return_value=self.fixture.now),
        ):
            location = MODULE.capture_recovery(output)
        self.assertEqual(location, "pci0000:00/usb1/1-2")
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertEqual(output.stat().st_nlink, 1)
        self.assertEqual(
            output.read_text().splitlines(),
            [
                f"format={MODULE.FORMAT}",
                "host_boot_id=11111111-2222-3333-4444-555555555555",
                f"created_unix={self.fixture.now}",
                "usb_location=pci0000:00/usb1/1-2",
                "recovery_vendor=1d6b",
                "recovery_product_id=0104",
                "recovery_product=ROG5 recovery",
            ],
        )

    def test_raw_sysfs_products_match_the_initramfs_sources(self) -> None:
        recovery = RECOVERY_INIT.read_text()
        target = TARGET_INIT.read_text()
        self.assertEqual(MODULE.RECOVERY_PRODUCT, "ROG5 recovery")
        self.assertEqual(MODULE.TARGET_PRODUCT, "ROG5 network root")
        for source, product in (
            (recovery, MODULE.RECOVERY_PRODUCT),
            (target, MODULE.TARGET_PRODUCT),
        ):
            self.assertIn("echo 0x1d6b", source)
            self.assertIn("echo 0x0104", source)
            self.assertIn(f"echo '{product}'", source)

    def test_recovery_and_target_must_be_unique_exact_usb_devices(self) -> None:
        with self.fixture.patches():
            self.assertEqual(
                MODULE.recovery_observation(),
                "pci0000:00/usb1/1-2",
            )
        self.fixture.install_target()
        with self.fixture.patches():
            self.assertEqual(
                MODULE.target_observation(),
                ("enxrog5", "pci0000:00/usb1/1-2"),
            )
        duplicate = self.fixture.sys_net / "enxduplicate"
        duplicate.symlink_to(self.fixture.interface / "netdev")
        with self.fixture.patches():
            with self.assertRaisesRegex(
                MODULE.BootstrapError, "exactly one"
            ):
                MODULE.target_observation()
        duplicate.unlink()
        duplicate_usb = (
            self.fixture.sys_devices / "pci0000:00/usb1/1-3"
        )
        duplicate_usb.mkdir(parents=True)
        for name, value in (
            ("idVendor", MODULE.USB_VENDOR),
            ("idProduct", MODULE.USB_PRODUCT),
            ("product", MODULE.TARGET_PRODUCT),
        ):
            (duplicate_usb / name).write_text(f"{value}\n", encoding="ascii")
        (self.fixture.sys_bus_usb / "1-3").symlink_to(duplicate_usb)
        with self.fixture.patches():
            with self.assertRaisesRegex(
                MODULE.BootstrapError, "raw ROG5 network root"
            ):
                MODULE.target_observation()

    def test_wrong_product_driver_and_port_are_rejected(self) -> None:
        with self.fixture.patches():
            with self.assertRaisesRegex(
                MODULE.BootstrapError, "raw ROG5 network root"
            ):
                MODULE.target_observation()
        self.fixture.install_target(driver="cdc_ether")
        with self.fixture.patches():
            with self.assertRaises(MODULE.BootstrapError):
                MODULE.target_observation()
        self.fixture.install_target()
        with (
            self.fixture.patches(),
            mock.patch.object(
                MODULE,
                "target_observation",
                return_value=("enxrog5", "pci0000:00/usb1/1-3"),
            ),
        ):
            with self.assertRaisesRegex(
                MODULE.BootstrapError, "different physical USB port"
            ):
                MODULE.wait_for_target("pci0000:00/usb1/1-2")

    def test_anchor_rejects_stale_boot_wrong_order_and_unsafe_metadata(
        self,
    ) -> None:
        path = self.fixture.anchor()
        with (
            self.fixture.patches(),
            mock.patch.object(MODULE.time, "time", return_value=self.fixture.now),
        ):
            self.assertEqual(
                MODULE.read_anchor(path)["usb_location"],
                "pci0000:00/usb1/1-2",
            )
        with (
            self.fixture.patches(),
            mock.patch.object(
                MODULE.time,
                "time",
                return_value=self.fixture.now + 601,
            ),
        ):
            with self.assertRaisesRegex(MODULE.BootstrapError, "stale"):
                MODULE.read_anchor(path)
        self.fixture.host_boot_id.write_text(
            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\n",
            encoding="ascii",
        )
        with (
            self.fixture.patches(),
            mock.patch.object(MODULE.time, "time", return_value=self.fixture.now),
        ):
            with self.assertRaisesRegex(
                MODULE.BootstrapError, "another host boot"
            ):
                MODULE.read_anchor(path)
        self.fixture.host_boot_id.write_text(
            "11111111-2222-3333-4444-555555555555\n",
            encoding="ascii",
        )
        path.write_text(
            path.read_text().replace(
                "format=", "host_boot_id=x\nformat=", 1
            ),
            encoding="ascii",
        )
        with self.fixture.patches():
            with self.assertRaisesRegex(
                MODULE.BootstrapError, "field count"
            ):
                MODULE.read_anchor(path)
        path.unlink()
        path = self.fixture.anchor()
        path.chmod(0o644)
        with self.fixture.patches():
            with self.assertRaisesRegex(MODULE.BootstrapError, "metadata"):
                MODULE.read_anchor(path)

    def test_route_requires_one_exact_direct_usb_path(self) -> None:
        outputs = [
            subprocess.CompletedProcess(
                [], 0, "7: enxrog5 inet 169.254.77.1/30 scope global\n", ""
            ),
            subprocess.CompletedProcess(
                [],
                0,
                "169.254.77.2 dev enxrog5 src 169.254.77.1 uid 1000\n",
                "",
            ),
        ]
        with (
            mock.patch.object(MODULE, "require_fixed_binary"),
            mock.patch.object(
                MODULE.subprocess, "run", side_effect=outputs
            ),
        ):
            MODULE.exact_route("enxrog5")
        outputs[1] = subprocess.CompletedProcess(
            [],
            0,
            "169.254.77.2 via 10.0.0.1 dev eth0 src 10.0.0.2\n",
            "",
        )
        with (
            mock.patch.object(MODULE, "require_fixed_binary"),
            mock.patch.object(
                MODULE.subprocess, "run", side_effect=outputs
            ),
        ):
            with self.assertRaises(MODULE.BootstrapError):
                MODULE.exact_route("enxrog5")

    def test_keyscan_accepts_one_nonzero_ed25519_key(self) -> None:
        blob = ed25519_blob()
        encoded = base64.b64encode(blob).decode()
        result = subprocess.CompletedProcess(
            [], 0, f"{MODULE.TARGET_ADDRESS} ssh-ed25519 {encoded}\n", ""
        )
        with (
            mock.patch.object(MODULE, "require_fixed_binary"),
            mock.patch.object(MODULE.subprocess, "run", return_value=result),
        ):
            record, fingerprint = MODULE.scan_target_key()
        self.assertEqual(
            record,
            f"{MODULE.HOST_ALIAS} ssh-ed25519 {encoded}\n",
        )
        expected = base64.b64encode(hashlib.sha256(blob).digest()).decode(
        ).rstrip("=")
        self.assertEqual(fingerprint, f"SHA256:{expected}")

    def test_keyscan_rejects_absence_multiple_rsa_zero_and_trailing_data(
        self,
    ) -> None:
        valid = base64.b64encode(ed25519_blob()).decode()
        cases = (
            subprocess.CompletedProcess([], 1, "", ""),
            subprocess.CompletedProcess(
                [],
                0,
                (
                    f"{MODULE.TARGET_ADDRESS} ssh-ed25519 {valid}\n"
                    f"{MODULE.TARGET_ADDRESS} ssh-ed25519 {valid}\n"
                ),
                "",
            ),
            subprocess.CompletedProcess(
                [],
                0,
                f"{MODULE.TARGET_ADDRESS} ssh-rsa {valid}\n",
                "",
            ),
            subprocess.CompletedProcess(
                [],
                0,
                (
                    f"{MODULE.TARGET_ADDRESS} ssh-ed25519 "
                    f"{base64.b64encode(ed25519_blob(0)).decode()}\n"
                ),
                "",
            ),
            subprocess.CompletedProcess(
                [],
                0,
                (
                    f"{MODULE.TARGET_ADDRESS} ssh-ed25519 "
                    f"{base64.b64encode(ed25519_blob() + b'x').decode()}\n"
                ),
                "",
            ),
        )
        for result in cases:
            with self.subTest(stdout=result.stdout):
                with (
                    mock.patch.object(MODULE, "require_fixed_binary"),
                    mock.patch.object(
                        MODULE.subprocess, "run", return_value=result
                    ),
                ):
                    with self.assertRaises(MODULE.BootstrapError):
                        MODULE.scan_target_key()

    def test_pin_uses_anchor_then_rechecks_identity_and_route(self) -> None:
        anchor = self.fixture.anchor()
        output = self.fixture.private / "known-hosts"
        with (
            self.fixture.patches(),
            mock.patch.object(MODULE.time, "time", return_value=self.fixture.now),
            mock.patch.object(
                MODULE, "wait_for_target",
                return_value=("enxrog5", "pci0000:00/usb1/1-2"),
            ),
            mock.patch.object(
                MODULE, "target_observation",
                return_value=("enxrog5", "pci0000:00/usb1/1-2"),
            ),
            mock.patch.object(MODULE, "exact_route") as route,
            mock.patch.object(
                MODULE, "scan_target_key",
                side_effect=(
                    MODULE.HostKeyNotReady("not ready"),
                    (
                        f"{MODULE.HOST_ALIAS} ssh-ed25519 "
                        f"{base64.b64encode(ed25519_blob()).decode()}\n",
                        "SHA256:test",
                    ),
                ),
            ),
            mock.patch.object(MODULE.time, "sleep"),
        ):
            fingerprint = MODULE.pin_target(anchor, output)
        self.assertEqual(fingerprint, "SHA256:test")
        self.assertEqual(route.call_count, 3)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertTrue(
            output.read_text().startswith(
                f"{MODULE.HOST_ALIAS} ssh-ed25519 "
            )
        )

    def test_pin_rechecks_anchor_freshness_before_publication(self) -> None:
        anchor = self.fixture.anchor()
        output = self.fixture.private / "known-hosts"
        with (
            self.fixture.patches(),
            mock.patch.object(
                MODULE.time,
                "time",
                side_effect=(self.fixture.now, self.fixture.now + 601),
            ),
            mock.patch.object(
                MODULE, "wait_for_target",
                return_value=("enxrog5", "pci0000:00/usb1/1-2"),
            ),
            mock.patch.object(
                MODULE, "target_observation",
                return_value=("enxrog5", "pci0000:00/usb1/1-2"),
            ),
            mock.patch.object(MODULE, "exact_route"),
            mock.patch.object(
                MODULE,
                "scan_target_key",
                return_value=(
                    f"{MODULE.HOST_ALIAS} ssh-ed25519 "
                    f"{base64.b64encode(ed25519_blob()).decode()}\n",
                    "SHA256:test",
                ),
            ),
        ):
            with self.assertRaisesRegex(MODULE.BootstrapError, "stale"):
                MODULE.pin_target(anchor, output)
        self.assertFalse(output.exists())

    def test_guard_fails_before_any_live_inspection(self) -> None:
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(MODULE, "capture_recovery") as capture,
        ):
            with self.assertRaisesRegex(
                MODULE.BootstrapError,
                "ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP",
            ):
                MODULE.main(["capture-recovery", "/tmp/unused"])
        capture.assert_not_called()

    def test_cli_translates_guard_failure_to_nonzero_exit(self) -> None:
        result = subprocess.run(
            [
                os.fspath(Path(os.sys.executable).resolve()),
                os.fspath(MODULE_PATH),
                "capture-recovery",
                os.fspath(self.fixture.private / "unused"),
            ],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            env={"LC_ALL": "C"},
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(
            "ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP",
            result.stderr,
        )

    def test_outputs_refuse_repo_existing_symlink_and_loose_parent(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            MODULE.BootstrapError, "outside the repository"
        ):
            MODULE.safe_new_output(REPO / "unsafe-host-key")
        existing = self.fixture.private / "existing"
        existing.write_text("x", encoding="ascii")
        with self.assertRaisesRegex(MODULE.BootstrapError, "existing"):
            MODULE.safe_new_output(existing)
        existing.unlink()
        existing.symlink_to("/dev/null")
        with self.assertRaisesRegex(MODULE.BootstrapError, "existing"):
            MODULE.safe_new_output(existing)
        loose = self.fixture.root / "loose"
        loose.mkdir(mode=0o755)
        with self.assertRaisesRegex(MODULE.BootstrapError, "mode 0700"):
            MODULE.safe_new_output(loose / "output")

    def test_failed_atomic_publication_leaves_no_known_hosts_file(self) -> None:
        output = self.fixture.private / "known-hosts"
        with mock.patch.object(
            MODULE.os,
            "fsync",
            side_effect=(None, OSError("directory sync failed")),
        ):
            with self.assertRaisesRegex(
                MODULE.BootstrapError, "publish bootstrap output"
            ):
                MODULE.write_exclusive(output, b"safe-record\n")
        self.assertFalse(output.exists())
        self.assertEqual(
            list(self.fixture.private.glob(".rog5-host-key.*")),
            [],
        )

    def test_source_excludes_enumerated_credential_and_tofu_surfaces(
        self,
    ) -> None:
        source = MODULE_PATH.read_text()
        for forbidden in (
            "StrictHostKeyChecking=no",
            "StrictHostKeyChecking=accept-new",
            "UserKnownHostsFile=/dev/null",
            "IdentityFile",
            "ssh -i",
            "scp ",
            "BEGIN " + "OPENSSH PRIVATE KEY",
            "fastboot",
            "adb ",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
