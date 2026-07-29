#!/usr/bin/env python3
"""Tests for the fixed sealed-snapshot fastboot boundary."""

from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).with_name("verified-fastboot-boot.py")
SPEC = importlib.util.spec_from_file_location("verified_fastboot_boot", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifiedFastbootBootTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.image = self.root / "recovery.avb.img"
        self.payload = b"sealed recovery image\n" * 4
        self.image.write_bytes(self.payload)
        self.image.chmod(0o400)
        self.expected = hashlib.sha256(self.payload).hexdigest()
        self.record = self.root / "record.json"
        self.fake = self.root / "fastboot"
        self.fake.write_text(
            """#!/usr/bin/env python3
import fcntl
import hashlib
import json
import os
import sys
path = sys.argv[-1]
with open(path, "rb") as stream:
    payload = stream.read()
descriptor = int(path.rsplit("/", 1)[1])
record = {
    "argv": sys.argv[1:],
    "sha256": hashlib.sha256(payload).hexdigest(),
    "seals": fcntl.fcntl(descriptor, fcntl.F_GET_SEALS),
}
with open(os.environ["ROG5_TEST_FASTBOOT_RECORD"], "w") as stream:
    json.dump(record, stream)
""",
            encoding="ascii",
        )
        self.fake.chmod(0o500)

    def tearDown(self):
        self.temporary.cleanup()

    def run_boot(self) -> dict[str, object]:
        environment = {
            "ALLOW_TEMPORARY_BOOT": "1",
            "ALLOW_HEADLESS_LIVE_GATE": "1",
            "ROG5_TEST_FASTBOOT_RECORD": str(self.record),
        }
        with (
            mock.patch.dict(os.environ, environment, clear=True),
            mock.patch.object(MODULE, "FASTBOOT", self.fake),
            mock.patch.object(MODULE, "PARTITION_SIZE", len(self.payload)),
            mock.patch.object(MODULE, "validate_fastboot"),
        ):
            MODULE.boot(self.image, self.expected, "SERIAL-1")
        return json.loads(self.record.read_text(encoding="ascii"))

    def test_exactly_one_fixed_boot_receives_the_sealed_snapshot(self):
        record = self.run_boot()
        self.assertEqual(len(record["argv"]), 4)
        self.assertEqual(
            record["argv"][:4],
            ["-s", "SERIAL-1", "boot", record["argv"][3]],
        )
        self.assertRegex(record["argv"][3], r"^/proc/self/fd/[0-9]+$")
        self.assertEqual(record["sha256"], self.expected)
        expected_seals = (
            fcntl.F_SEAL_SEAL
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_WRITE
        )
        self.assertEqual(record["seals"], expected_seals)

    def test_hash_mismatch_never_invokes_fastboot(self):
        with (
            mock.patch.dict(
                os.environ,
                {
                    "ALLOW_TEMPORARY_BOOT": "1",
                    "ALLOW_HEADLESS_LIVE_GATE": "1",
                },
                clear=True,
            ),
            mock.patch.object(MODULE, "PARTITION_SIZE", len(self.payload)),
            mock.patch.object(MODULE, "validate_fastboot"),
            mock.patch.object(MODULE.subprocess, "run") as run,
            self.assertRaisesRegex(RuntimeError, "wrong identity"),
        ):
            MODULE.boot(self.image, "f" * 64, "SERIAL-1")
        run.assert_not_called()

    def test_guards_precede_fastboot_and_image_access(self):
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(MODULE, "validate_fastboot") as validate,
            mock.patch.object(MODULE, "sealed_snapshot") as snapshot,
            self.assertRaisesRegex(RuntimeError, "ALLOW_TEMPORARY_BOOT"),
        ):
            MODULE.boot(self.image, self.expected, "SERIAL-1")
        validate.assert_not_called()
        snapshot.assert_not_called()

    def test_production_fastboot_path_is_fixed(self):
        self.assertEqual(MODULE.FASTBOOT, Path("/usr/bin/fastboot"))
        self.assertNotIn("FASTBOOT", os.environ)
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn('os.environ.get("FASTBOOT"', source)


if __name__ == "__main__":
    unittest.main()
