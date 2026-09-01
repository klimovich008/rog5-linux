#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/collect-display-post-switch.py"


def load_module():
    spec = importlib.util.spec_from_file_location("rog5_display_report", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load display collector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def payload(**overrides: str) -> bytes:
    dmesg = b"drm: ready\n"
    values = {
        "format": "rog5-display-post-switch-v1",
        "candidate": "persistent-native-root-display60-v6",
        "target_release": "7.1.4-rog5-display60-v1",
        "boot_id": "11111111-2222-3333-4444-555555555555",
        "sample_seconds": "20",
        "refgen_status": "present",
        "refgen_hex": "71636f6d2d72656667656e2d726567756c61746f72",
        "dsi_status": "present",
        "dsi_hex": "6d736d5f647369",
        "drm_status": "present",
        "drm_hex": "6361726430",
        "fb_status": "present",
        "fb_hex": "666230",
        "backlight_status": "present",
        "backlight_hex": "70616e656c302d6261636b6c696768743a313032333a30",
        "status_screen_status": "present",
        "status_screen_hex": "696e7374616c6c6564",
        "dmesg_status": "present",
        "dmesg_sha256": hashlib.sha256(dmesg).hexdigest(),
        "dmesg_tail_hex": dmesg.hex(),
        "result": "PASS",
    }
    values.update(overrides)
    fields = (
        "format", "candidate", "target_release", "boot_id", "sample_seconds",
        "refgen_status", "refgen_hex", "dsi_status", "dsi_hex",
        "drm_status", "drm_hex", "fb_status", "fb_hex",
        "backlight_status", "backlight_hex", "status_screen_status",
        "status_screen_hex", "dmesg_status", "dmesg_sha256",
        "dmesg_tail_hex", "result",
    )
    return "".join(f"{name}={values[name]}\n" for name in fields).encode("ascii")


class DisplayCollectorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_valid_record_preserves_optional_absence(self) -> None:
        parsed = self.module.parse_record(
            payload(
                fb_status="absent",
                fb_hex="",
                backlight_status="unsupported",
                backlight_hex="",
            ),
            "persistent-native-root-display60-v6",
            "7.1.4-rog5-display60-v1",
        )
        self.assertEqual(parsed["fb_status"], "absent")
        self.assertEqual(parsed["backlight_status"], "unsupported")

    def test_wrong_identity_and_hostile_framing_fail_closed(self) -> None:
        for hostile in (
            payload(candidate="other"),
            payload(target_release="7.1.4-wrong"),
            payload(boot_id="0" * 36),
            payload() + b"extra=1\n",
            payload().rstrip(b"\n"),
            payload(dmesg_tail_hex="GG"),
            payload(refgen_status="fatal"),
            b"x" * 20000,
        ):
            with self.subTest(tail=hostile[-24:]):
                with self.assertRaises(self.module.DisplayReportError):
                    self.module.parse_record(
                        hostile,
                        "persistent-native-root-display60-v6",
                        "7.1.4-rog5-display60-v1",
                    )

    def test_output_is_exclusive_and_mode_0600(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "record"
            self.module.write_record(path, payload())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                self.module.write_record(path, payload())

    def test_receive_requires_the_exact_ncm_endpoints(self) -> None:
        class Connection:
            def __init__(self, raw: bytes, local: str) -> None:
                self.raw = raw
                self.local = local

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def settimeout(self, _timeout: float) -> None:
                pass

            def recv(self, _maximum: int) -> bytes:
                raw, self.raw = self.raw, b""
                return raw

            def getsockname(self):
                return (self.local, self.module.PORT)

        class Listener:
            def __init__(
                self, outer, raw: bytes, peer: str, local: str
            ) -> None:
                self.outer = outer
                self.raw = raw
                self.peer = peer
                self.local = local

            def accept(self):
                connection = Connection(self.raw, self.local)
                connection.module = self.outer.module
                return connection, (self.peer, 42000)

        good = Listener(
            self,
            payload(),
            self.module.TARGET_ADDRESS,
            self.module.HOST_ADDRESS,
        )
        self.assertEqual(self.module.receive(good), payload())
        for peer, local in (
            ("169.254.77.3", self.module.HOST_ADDRESS),
            (self.module.TARGET_ADDRESS, "0.0.0.0"),
        ):
            with self.subTest(peer=peer, local=local):
                with self.assertRaises(self.module.DisplayReportError):
                    self.module.receive(Listener(self, payload(), peer, local))


if __name__ == "__main__":
    unittest.main()
