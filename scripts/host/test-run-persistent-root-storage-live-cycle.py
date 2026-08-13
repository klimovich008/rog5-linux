#!/usr/bin/env python3
"""Hardware-free tests for the read-only persistent-root live runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/host/run-persistent-root-storage-live-cycle.py"
SPEC = importlib.util.spec_from_file_location("persistent_root_live", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load persistent-root live runner")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class PersistentRootLiveCycleTest(unittest.TestCase):
    def test_profile_and_artifact_identities_are_exact(self) -> None:
        self.assertEqual(
            MODULE.PROFILE_ID,
            "persistent-root-qmp-third-clock-runtime-pm-stage-v23-live-v1",
        )
        self.assertEqual(MODULE.PROFILE.candidate, MODULE.BUNDLE)
        self.assertEqual(MODULE.PROFILE.bundle, MODULE.BUNDLE)
        self.assertEqual(MODULE.PROFILE.bundle_profile, "persistent-root-ro-v1")
        self.assertEqual(MODULE.PROFILE.recovery_profile, MODULE.PROFILE_ID)
        self.assertFalse(MODULE.PROFILE.diagnostic)
        self.assertEqual(MODULE.TARGET_PRODUCT, "ROG5 persistent root")
        self.assertEqual(MODULE.TARGET_UDEV_MODEL, "ROG5_persistent_root")
        self.assertTrue(MODULE.USB_CONTROL_ONLY)
        self.assertEqual(
            MODULE.QMP_COMPLETED_GATE,
            "second and third fixed-rate clock registrations",
        )
        self.assertEqual(
            MODULE.QMP_NEXT_GATE,
            "qmp-ufs-of-clock-provider-publication",
        )
        for digest in (
            MODULE.MANIFEST_SHA256,
            MODULE.RECOVERY_SHA256,
            MODULE.TRUST_KEY_SHA256,
            MODULE.HOST_VERIFIER_SHA256,
        ):
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertNotEqual(digest, "0" * 64)

    def test_runtime_evidence_accepts_dynamic_device_letter(self) -> None:
        payload = "\n".join(
            (
                "format=rog5-persistent-root-live-evidence-v1",
                "boot_id=11111111-2222-3333-4444-555555555555",
                "uptime_seconds=21.00",
                "status=PASS",
                f"kernel={MODULE.TARGET_RELEASE}",
                "physical_blocks=116",
                "block_backed_mounts=1",
                "userdata_mount=ro-noload",
                "root=overlay-tmpfs",
                "blocked_device_queries=0",
                "blocked_scsi_commands=0",
                "journal_recovery_events=0",
                "ufs_error_events=0",
                "backlights=0",
                "ssh=strict-key-only",
                "userdata_device=/dev/sdg23",
                "result=PASS",
                "",
            )
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "runtime.log"
            path.write_text(payload)
            self.assertEqual(
                MODULE.parse_runtime_evidence(path),
                "11111111-2222-3333-4444-555555555555",
            )

    def test_runtime_evidence_rejects_missing_duplicate_and_wrong_storage(self) -> None:
        baseline = [
            "format=rog5-persistent-root-live-evidence-v1",
            "boot_id=11111111-2222-3333-4444-555555555555",
            "status=PASS",
            f"kernel={MODULE.TARGET_RELEASE}",
            "physical_blocks=116",
            "block_backed_mounts=1",
            "userdata_mount=ro-noload",
            "root=overlay-tmpfs",
            "blocked_device_queries=0",
            "blocked_scsi_commands=0",
            "journal_recovery_events=0",
            "ufs_error_events=0",
            "ssh=strict-key-only",
            "userdata_device=/dev/sda23",
            "result=PASS",
        ]
        hostile = (
            baseline[:-2] + ["userdata_device=/dev/mmcblk0p23", "result=PASS"],
            baseline + ["boot_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"],
            [line for line in baseline if line != "physical_blocks=116"],
            baseline + ["blocked_scsi_commands=0"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "runtime.log"
            for payload in hostile:
                with self.subTest(payload=payload[-2:]):
                    path.write_text("\n".join(payload) + "\n")
                    with self.assertRaises(MODULE.PersistentCycleError):
                        MODULE.parse_runtime_evidence(path)

    def test_ssh_is_key_only_and_pins_the_bootstrap_alias(self) -> None:
        inputs = SimpleNamespace(ssh_key=Path("/private/key"))
        arguments = MODULE.ssh_arguments(inputs, Path("/private/known-hosts"))
        joined = " ".join(arguments)
        self.assertIn("BatchMode=yes", joined)
        self.assertIn("IdentitiesOnly=yes", joined)
        self.assertIn("PasswordAuthentication=no", joined)
        self.assertIn("StrictHostKeyChecking=yes", joined)
        self.assertIn("HostKeyAlias=rog5-minimal-headless-v1", joined)
        self.assertNotIn("StrictHostKeyChecking=no", joined)

    def test_nmcli_has_one_unprivileged_then_noninteractive_sudo_path(self) -> None:
        results = (
            SimpleNamespace(returncode=1, stdout="not authorized\n"),
            SimpleNamespace(returncode=0, stdout="ok\n"),
        )
        with mock.patch.object(
            MODULE.CYCLE,
            "run_capture",
            side_effect=results,
        ) as runner:
            MODULE.privileged_nmcli(["device", "set", "enxrog5", "managed", "yes"])
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(runner.call_args_list[0].args[0][0], "/usr/bin/nmcli")
        self.assertEqual(
            runner.call_args_list[1].args[0][:3],
            ["/usr/bin/sudo", "-n", "/usr/bin/nmcli"],
        )

    def test_post_commit_cleanup_allows_recovery_usb_to_reenumerate(self) -> None:
        cycle = SimpleNamespace(wait_host_clean=mock.Mock())
        MODULE.wait_post_commit_host_cleanup(cycle)
        cycle.wait_host_clean.assert_called_once_with()

    def test_fallback_transition_uses_usb_identity_not_nm_state(self) -> None:
        with mock.patch.object(
            MODULE.PIN,
            "fallback_returned",
            return_value=True,
        ) as fallback:
            self.assertTrue(
                MODULE.alpine_fallback_is_present("pci0000:00/usb1/1-1")
            )
        fallback.assert_called_once_with("pci0000:00/usb1/1-1")

    def test_module_load_control_requires_exact_ncm_for_the_whole_window(self) -> None:
        snapshot = MODULE.CYCLE.InterfaceSnapshot(
            name="enxrog5",
            product=MODULE.TARGET_UDEV_MODEL,
            addresses=("169.254.77.1/30",),
            firewall_zone="trusted",
            network_manager_managed="yes",
        )
        cycle = SimpleNamespace(
            dependencies=object(),
            poll=0.25,
            rog5_ncm_interfaces=mock.Mock(return_value=(snapshot,)),
        )
        clock = FakeClock()
        with (
            mock.patch.object(
                MODULE.CYCLE,
                "read_recovery_anchor_location",
                return_value="pci0000:00/usb1/1-1",
            ),
            mock.patch.object(
                MODULE.PIN,
                "target_observation",
                return_value=("enxrog5", "pci0000:00/usb1/1-1"),
            ),
            mock.patch.object(MODULE.PIN, "exact_route"),
        ):
            elapsed = MODULE.require_post_module_ncm(
                cycle,
                Path("/private/anchor"),
                "enxrog5",
                duration=1.0,
                clock=clock,
            )
        self.assertEqual(elapsed, 1.0)
        self.assertEqual(cycle.rog5_ncm_interfaces.call_count, 4)

    def test_module_proof_requires_exact_target_record_and_addresses(self) -> None:
        expected = (
            "format=rog5-deferred-ufs-module-proof-v1\n"
            f"target_release={MODULE.TARGET_RELEASE}\n"
            "module=phy_qcom_qmp_ufs\n"
            "result=PASS\n"
        ).encode()

        class Connection:
            def __init__(self, payload: bytes) -> None:
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def settimeout(self, _timeout: float) -> None:
                return None

            def recv(self, _size: int) -> bytes:
                payload, self.payload = self.payload, b""
                return payload

            def getsockname(self):
                return ("169.254.77.1", MODULE.MODULE_PROOF_PORT)

        class Listener:
            def __init__(self, payload: bytes, peer: str) -> None:
                self.payload = payload
                self.peer = peer

            def settimeout(self, _timeout: float) -> None:
                return None

            def bind(self, address) -> None:
                self.bound = address

            def listen(self, _backlog: int) -> None:
                return None

            def accept(self):
                return Connection(self.payload), (self.peer, 40000)

            def close(self) -> None:
                return None

        class SocketModule:
            AF_INET = 2
            SOCK_STREAM = 1

            def __init__(self, payload: bytes, peer="169.254.77.2") -> None:
                self.listener = Listener(payload, peer)

            def socket(self, *_args):
                return self.listener

        with tempfile.TemporaryDirectory() as temporary:
            cycle = SimpleNamespace(
                output=lambda name: Path(temporary) / name,
            )
            with mock.patch.object(MODULE.CYCLE, "write_record") as writer:
                MODULE.receive_module_proof(
                    cycle,
                    "enxrog5",
                    socket_module=SocketModule(expected),
                )
            writer.assert_called_once()
            for payload, peer in (
                (expected.replace(b"result=PASS", b"result=FAIL"), "169.254.77.2"),
                (expected, "169.254.77.3"),
            ):
                with self.subTest(peer=peer, payload=payload[-12:]):
                    with self.assertRaises(MODULE.PersistentCycleError):
                        MODULE.receive_module_proof(
                            cycle,
                            "enxrog5",
                            socket_module=SocketModule(payload, peer),
                        )

    def test_module_load_control_rejects_early_usb_loss(self) -> None:
        cycle = SimpleNamespace(
            dependencies=object(),
            poll=0.25,
            rog5_ncm_interfaces=mock.Mock(return_value=()),
        )
        with (
            mock.patch.object(
                MODULE.CYCLE,
                "read_recovery_anchor_location",
                return_value="pci0000:00/usb1/1-1",
            ),
            mock.patch.object(
                MODULE.PIN,
                "target_observation",
                side_effect=MODULE.PIN.BootstrapError("gone"),
            ),
            self.assertRaises(MODULE.PersistentCycleError),
        ):
            MODULE.require_post_module_ncm(
                cycle,
                Path("/private/anchor"),
                "enxrog5",
                duration=1.0,
                clock=FakeClock(),
            )

    def test_network_inspection_race_reclassifies_disappeared_usb(self) -> None:
        cycle = SimpleNamespace(
            dependencies=object(),
            poll=0.25,
            rog5_ncm_interfaces=mock.Mock(
                side_effect=MODULE.CYCLE.CycleError(
                    "cannot inspect NetworkManager ownership of ROG5 link"
                )
            ),
        )
        with (
            mock.patch.object(
                MODULE.CYCLE,
                "read_recovery_anchor_location",
                return_value="pci0000:00/usb1/1-1",
            ),
            mock.patch.object(
                MODULE.PIN,
                "target_observation",
                side_effect=[
                    ("enxrog5", "pci0000:00/usb1/1-1"),
                    MODULE.PIN.BootstrapError("gone"),
                ],
            ),
            mock.patch.object(MODULE.PIN, "exact_route"),
            self.assertRaisesRegex(
                MODULE.PersistentCycleError,
                "target NCM vanished during the module-load control window",
            ),
        ):
            MODULE.require_post_module_ncm(
                cycle,
                Path("/private/anchor"),
                "enxrog5",
                duration=1.0,
                clock=FakeClock(),
            )

    def test_runner_contains_no_phone_storage_mutation_surface(self) -> None:
        source = MODULE_PATH.read_text()
        for forbidden in (
            "fastboot flash",
            "fastboot erase",
            "mkfs.",
            "sgdisk",
            "parted",
            "blockdev --setrw",
            "ALLOW_NETWORK_ROOT_NFS_HANDOFF",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('"prepare-commit",', source)
        self.assertIn('"/usr/bin/systemctl reboot"', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
