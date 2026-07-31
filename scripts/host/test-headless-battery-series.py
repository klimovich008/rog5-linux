#!/usr/bin/env python3
"""Hostile hardware-free tests for sustained battery telemetry."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
VERIFIER_PATH = REPO / "scripts/host/verify-headless-battery-series.py"
COLLECTOR = REPO / "scripts/device/collect-headless-battery-series.sh"
BOOT_ID = "7d9a6f34-0e4a-4d4e-9d24-0b1f6c7215a8"


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


VERIFIER = load_module("rog5_test_battery_series", VERIFIER_PATH)


def golden_values(
    phase: str,
    *,
    boot_id: str = BOOT_ID,
    execution_mode: str = "live",
    sample_count: int = VERIFIER.LIVE_SAMPLE_COUNT,
    interval_seconds: int = VERIFIER.LIVE_INTERVAL_SECONDS,
) -> dict[str, str]:
    values = dict(VERIFIER.EXACT_HEADER)
    values.update(
        {
            "execution_mode": execution_mode,
            "collector_sha256": hashlib.sha256(
                COLLECTOR.read_bytes()
            ).hexdigest(),
            "boot_id": boot_id,
            "phase": phase,
            "interval_seconds": str(interval_seconds),
            "sample_count": str(sample_count),
        }
    )
    if set(values) != set(VERIFIER.HEADER_FIELDS):
        raise AssertionError("golden battery header does not cover the schema")
    return values


def golden_samples(
    phase: str,
    *,
    sample_count: int = VERIFIER.LIVE_SAMPLE_COUNT,
    interval_seconds: int = VERIFIER.LIVE_INTERVAL_SECONDS,
    current_ua: int | None = None,
    status: str | None = None,
) -> list[VERIFIER.Sample]:
    usb_online, wireless_online = VERIFIER.PHASE_ONLINE[phase]
    if current_ua is None:
        current_ua = 100_000 if phase == "unplugged" else -120_000
    if status is None:
        status = "Discharging" if phase == "unplugged" else "Charging"
    return [
        VERIFIER.Sample(
            elapsed_seconds=index * interval_seconds,
            capacity_percent=84,
            voltage_uv=8_255_000,
            current_ua=current_ua,
            temp_dc=303,
            status=status,
            usb_online=usb_online,
            wireless_online=wireless_online,
        )
        for index in range(sample_count)
    ]


def render(
    values: dict[str, str],
    samples: list[VERIFIER.Sample],
) -> bytes:
    lines = [f"{field}={values[field]}" for field in VERIFIER.HEADER_FIELDS]
    for index, sample in enumerate(samples):
        lines.append(
            f"sample_{index:03d}="
            f"{sample.elapsed_seconds},{sample.capacity_percent},"
            f"{sample.voltage_uv},{sample.current_ua},{sample.temp_dc},"
            f"{sample.status},{sample.usb_online},"
            f"{sample.wireless_online}"
        )
    lines.append("result=OBSERVED")
    return ("\n".join(lines) + "\n").encode("ascii")


class HeadlessBatterySeriesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-battery-series-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.record = self.directory / "series.record"
        self.write("unplugged")

    def write(
        self,
        phase: str,
        *,
        values: dict[str, str] | None = None,
        samples: list[VERIFIER.Sample] | None = None,
        data: bytes | None = None,
        path: Path | None = None,
    ) -> Path:
        destination = self.record if path is None else path
        selected_values = golden_values(phase) if values is None else values
        selected_samples = (
            golden_samples(phase) if samples is None else samples
        )
        destination.write_bytes(
            render(selected_values, selected_samples)
            if data is None
            else data
        )
        destination.chmod(0o600)
        return destination

    def verify(
        self,
        path: Path | None = None,
        *,
        boot_id: str = BOOT_ID,
        mode: str = "live",
        sample_count: int = VERIFIER.LIVE_SAMPLE_COUNT,
        interval_seconds: int = VERIFIER.LIVE_INTERVAL_SECONDS,
    ) -> VERIFIER.Series:
        return VERIFIER.verify_record(
            self.record if path is None else path,
            boot_id,
            expected_mode=mode,
            expected_sample_count=sample_count,
            expected_interval_seconds=interval_seconds,
        )

    def test_canonical_single_and_usb_pair_pass(self) -> None:
        unplugged = self.verify()
        usb_record = self.directory / "usb.record"
        self.write("usb-online", path=usb_record)
        usb = self.verify(usb_record)
        self.assertEqual(
            VERIFIER.verify_usb_pair(unplugged, usb),
            "positive-discharge",
        )
        self.assertEqual(len(unplugged.samples), 21)

    def test_pair_accepts_the_opposite_driver_sign_convention(self) -> None:
        self.write(
            "unplugged",
            samples=golden_samples("unplugged", current_ua=-100_000),
        )
        usb_record = self.directory / "usb.record"
        self.write(
            "usb-online",
            samples=golden_samples("usb-online", current_ua=120_000),
            path=usb_record,
        )
        self.assertEqual(
            VERIFIER.verify_usb_pair(
                self.verify(),
                self.verify(usb_record),
            ),
            "positive-charge",
        )

    def test_pair_rejects_ambiguous_current_and_status(self) -> None:
        unplugged = self.verify()
        cases = (
            (100_000, "Charging", "direction"),
            (1_000, "Charging", "direction"),
            (-120_000, "Discharging", "Charging or Full"),
        )
        for current, status, message in cases:
            with self.subTest(current=current, status=status):
                usb_record = self.directory / "usb.record"
                self.write(
                    "usb-online",
                    samples=golden_samples(
                        "usb-online",
                        current_ua=current,
                        status=status,
                    ),
                    path=usb_record,
                )
                with self.assertRaisesRegex(
                    VERIFIER.BatterySeriesError,
                    message,
                ):
                    VERIFIER.verify_usb_pair(
                        unplugged,
                        self.verify(usb_record),
                    )

    def test_pair_requires_one_boot_candidate_and_capacity_window(self) -> None:
        unplugged = self.verify()
        usb_record = self.directory / "usb.record"
        values = golden_values(
            "usb-online",
            boot_id="8d9a6f34-0e4a-4d4e-9d24-0b1f6c7215a8",
        )
        self.write("usb-online", values=values, path=usb_record)
        other_boot = self.verify(
            usb_record,
            boot_id=values["boot_id"],
        )
        with self.assertRaisesRegex(
            VERIFIER.BatterySeriesError,
            "comparison identity",
        ):
            VERIFIER.verify_usb_pair(unplugged, other_boot)

        samples = [
            VERIFIER.Sample(
                **{
                    **sample.__dict__,
                    "capacity_percent": 60,
                }
            )
            for sample in golden_samples("usb-online")
        ]
        self.write("usb-online", samples=samples, path=usb_record)
        with self.assertRaisesRegex(
            VERIFIER.BatterySeriesError,
            "capacity state",
        ):
            VERIFIER.verify_usb_pair(
                unplugged,
                self.verify(usb_record),
            )

    def test_every_header_identity_is_exact(self) -> None:
        replacements = {
            "format": "rog5-headless-battery-series-v2",
            "profile": "battery-write-v1",
            "execution_mode": "test",
            "collector_sha256": "a" * 64,
            "candidate": "headless-network-root-v1",
            "boot_id": "8d9a6f34-0e4a-4d4e-9d24-0b1f6c7215a8",
            "kernel_release": "7.1.5",
            "interval_seconds": "31",
            "sample_count": "20",
            "battery_supply": "battery",
            "usb_supply": "usb",
            "wireless_supply": "wireless",
            "battery_property_modes": "capacity:644",
            "usb_input_current_limit_mode": "644",
            "charge_control_surface_count": "1",
            "typec_device_count": "1",
        }
        for field, replacement in replacements.items():
            with self.subTest(field=field):
                values = golden_values("unplugged")
                values[field] = replacement
                self.write("unplugged", values=values)
                with self.assertRaises(VERIFIER.BatterySeriesError):
                    self.verify()

    def test_phase_and_sample_online_state_are_bound(self) -> None:
        values = golden_values("unplugged")
        values["phase"] = "invalid"
        self.write("unplugged", values=values)
        with self.assertRaisesRegex(
            VERIFIER.BatterySeriesError,
            "phase",
        ):
            self.verify()

        sample = golden_samples("unplugged")
        sample[10] = VERIFIER.Sample(
            **{
                **sample[10].__dict__,
                "usb_online": 1,
            }
        )
        self.write("unplugged", samples=sample)
        with self.assertRaisesRegex(
            VERIFIER.BatterySeriesError,
            "contradicts",
        ):
            self.verify()

    def test_sample_schedule_width_and_ranges_are_strict(self) -> None:
        cases = (
            ("elapsed_seconds", 1, "schedule"),
            ("capacity_percent", 101, "capacity"),
            ("voltage_uv", 2_499_999, "voltage"),
            ("current_ua", 20_000_001, "current"),
            ("temp_dc", 1_001, "temperature"),
            ("status", "charge", "status"),
        )
        for field, replacement, message in cases:
            with self.subTest(field=field):
                samples = golden_samples("unplugged")
                samples[0] = VERIFIER.Sample(
                    **{
                        **samples[0].__dict__,
                        field: replacement,
                    }
                )
                self.write("unplugged", samples=samples)
                with self.assertRaisesRegex(
                    VERIFIER.BatterySeriesError,
                    message,
                ):
                    self.verify()

    def test_framing_duplicate_truncation_and_encoding_refuse(self) -> None:
        canonical = self.record.read_bytes()
        cases = (
            canonical[:-1],
            canonical.replace(b"\n", b"\r\n", 1),
            canonical + b"extra=1\n",
            canonical.replace(b"sample_001=", b"sample_000=", 1),
            canonical.replace(b"capacity:444", b"capacity:\xff", 1),
        )
        for index, payload in enumerate(cases):
            with self.subTest(index=index):
                self.write("unplugged", data=payload)
                with self.assertRaises(VERIFIER.BatterySeriesError):
                    self.verify()

    def test_record_metadata_and_path_replacement_refuse(self) -> None:
        linked = self.directory / "linked.record"
        linked.symlink_to(self.record.name)
        with self.assertRaisesRegex(
            VERIFIER.BatterySeriesError,
            "metadata",
        ):
            self.verify(linked)
        linked.unlink()

        linked.hardlink_to(self.record)
        with self.assertRaisesRegex(
            VERIFIER.BatterySeriesError,
            "metadata",
        ):
            self.verify()
        linked.unlink()
        self.write("unplugged")

        self.record.chmod(0o644)
        with self.assertRaisesRegex(
            VERIFIER.BatterySeriesError,
            "metadata",
        ):
            self.verify()
        self.record.chmod(0o600)

        real_read = os.read
        original = self.directory / "opened.record"
        replaced = False

        def replace_path(descriptor: int, count: int) -> bytes:
            nonlocal replaced
            if not replaced:
                self.record.rename(original)
                self.record.write_bytes(b"replacement\n")
                self.record.chmod(0o600)
                replaced = True
            return real_read(descriptor, count)

        with (
            mock.patch.object(
                VERIFIER.os,
                "read",
                side_effect=replace_path,
            ),
            self.assertRaisesRegex(
                VERIFIER.BatterySeriesError,
                "changed",
            ),
        ):
            self.verify()

    def prepare_collector_fixture(self) -> Path:
        root = self.directory / "fixture"
        (root / "proc/sys/kernel/random").mkdir(parents=True)
        (root / "proc/sys/kernel/random/boot_id").write_text(
            f"{BOOT_ID}\n",
            encoding="ascii",
        )
        class_root = root / "sys/class/power_supply"
        device_root = root / "sys/devices/mock"
        class_root.mkdir(parents=True)
        device_root.mkdir(parents=True)
        supplies = {
            "qcom-battmgr-bat": {
                "capacity": "84\n",
                "voltage_now": "8255000\n",
                "current_now": "100000\n",
                "temp": "303\n",
                "status": "Discharging\n",
            },
            "qcom-battmgr-usb": {
                "online": "0\n",
                "input_current_limit": "3000000\n",
            },
            "qcom-battmgr-wls": {
                "online": "0\n",
            },
        }
        for name, properties in supplies.items():
            target = device_root / name
            target.mkdir()
            for property_name, value in properties.items():
                path = target / property_name
                path.write_text(value, encoding="ascii")
                path.chmod(0o444)
            (class_root / name).symlink_to(
                Path("../../devices/mock") / name
            )
        return root

    def test_collector_fixture_emits_a_verifiable_read_only_record(
        self,
    ) -> None:
        root = self.prepare_collector_fixture()
        environment = {
            "PATH": os.environ["PATH"],
            "ALLOW_HEADLESS_BATTERY_SERIES": "1",
            "ROG5_BATTERY_TEST_MODE": "1",
            "ROG5_BATTERY_RUNTIME_ROOT": str(root),
            "ROG5_BATTERY_TEST_KERNEL_RELEASE": (
                VERIFIER.KERNEL_RELEASE
            ),
            "ROG5_BATTERY_TEST_SAMPLE_COUNT": "3",
            "ROG5_BATTERY_TEST_INTERVAL_SECONDS": "0",
        }
        result = subprocess.run(
            [str(COLLECTOR), "unplugged"],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(
            result.returncode,
            0,
            result.stderr.decode("utf-8", errors="replace"),
        )
        self.record.write_bytes(result.stdout)
        self.record.chmod(0o600)
        series = self.verify(
            mode="test",
            sample_count=3,
            interval_seconds=0,
        )
        self.assertEqual(len(series.samples), 3)
        self.assertEqual(series.values["phase"], "unplugged")

    def test_collector_guards_and_source_exclude_mutation_surfaces(
        self,
    ) -> None:
        source = COLLECTOR.read_text(encoding="utf-8")
        for forbidden in (
            "fastboot",
            "adb ",
            "flash",
            "modprobe",
            "insmod",
            "rmmod",
            "systemctl",
            "tee ",
            "/proc/sysrq-trigger",
            "charge_control_start_threshold\" >",
            "charge_control_end_threshold\" >",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("ALLOW_HEADLESS_BATTERY_SERIES", source)
        self.assertIn("result=OBSERVED", source)

        result = subprocess.run(
            [str(COLLECTOR), "unplugged"],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": os.environ["PATH"]},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"ALLOW_HEADLESS_BATTERY_SERIES",
            result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
