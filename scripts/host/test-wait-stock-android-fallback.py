#!/usr/bin/env python3
"""Focused tests for the stock-WW33 fallback proof."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/wait-stock-android-fallback.py"
SPEC = importlib.util.spec_from_file_location("rog5_stock_fallback", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load stock fallback verifier")
FALLBACK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FALLBACK
SPEC.loader.exec_module(FALLBACK)


class StockFallbackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_adb = FALLBACK.adb
        self.properties = {
            "ro.boot.slot_suffix": "_a",
            "ro.build.fingerprint": FALLBACK.FINGERPRINT,
            "ro.boot.vbmeta.digest": FALLBACK.VBMETA_DIGEST,
            "ro.boot.verifiedbootstate": "orange",
            "sys.boot_completed": "1",
            "sys.usb.config": "adb",
        }

        def fake_adb(*arguments: str, timeout: int = 10) -> str:
            del timeout
            if arguments == ("devices", "-l"):
                return (
                    "List of devices attached\n"
                    f"{FALLBACK.SERIAL} device usb:1-1.2 "
                    f"product:{FALLBACK.PRODUCT} model:{FALLBACK.MODEL} "
                    f"device:{FALLBACK.DEVICE} transport_id:7\n"
                )
            if arguments[:4] == ("-s", FALLBACK.SERIAL, "shell", "getprop"):
                return self.properties[arguments[4]] + "\n"
            if arguments == (
                "-s",
                FALLBACK.SERIAL,
                "shell",
                "cat",
                "/proc/sys/kernel/random/boot_id",
            ):
                return "11111111-2222-3333-4444-555555555555\n"
            raise AssertionError(arguments)

        FALLBACK.adb = fake_adb

    def tearDown(self) -> None:
        FALLBACK.adb = self.original_adb

    def test_exact_stock_slot_a_identity_passes(self) -> None:
        self.assertTrue(FALLBACK.exact_device("1-1.2"))
        values = FALLBACK.verify_stock("1-1.2")
        self.assertEqual(values["result"], "PASS")
        self.assertEqual(values["usb_config"], "adb")

    def test_wrong_slot_fingerprint_digest_and_usb_path_refuse(self) -> None:
        self.assertFalse(FALLBACK.exact_device("1-1.3"))
        for name, value in (
            ("ro.boot.slot_suffix", "_b"),
            ("ro.build.fingerprint", "wrong"),
            ("ro.boot.vbmeta.digest", "0" * 64),
            ("ro.boot.verifiedbootstate", "red"),
            ("sys.boot_completed", "0"),
        ):
            original = self.properties[name]
            self.properties[name] = value
            with self.assertRaises(FALLBACK.FallbackError):
                FALLBACK.verify_stock("1-1.2")
            self.properties[name] = original

    def test_evidence_publication_is_private_and_no_replace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rog5-stock-fallback-") as raw:
            root = Path(raw)
            root.chmod(0o700)
            output = root / "fallback.record"
            values = FALLBACK.verify_stock("1-1.2")
            FALLBACK.publish(output, values)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FALLBACK.FallbackError):
                FALLBACK.publish(output, values)


if __name__ == "__main__":
    unittest.main(verbosity=2)
