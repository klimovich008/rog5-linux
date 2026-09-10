#!/usr/bin/env python3
"""Compile real driver fragments; optionally check/apply against retained source."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "scripts/device/fixtures/qcom-battmgr-charge-units.c"
PATCH = REPO / "patches/linux-7.1.4/0038-power-supply-qcom-battmgr-fix-charge-units.patch"
DRIVER = Path("drivers/power/supply/qcom_battmgr.c")
FRAGMENTS = re.compile(r"/\* source: ([\w-]+) \*/\n(.*?)/\* end: \1 \*/", re.S)


def apply_patch(directory, source):
    target = directory / DRIVER
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)
    subprocess.run(["git", "apply", "--check", str(PATCH)], cwd=directory, check=True)
    subprocess.run(["git", "apply", str(PATCH)], cwd=directory, check=True)
    return target.read_text()


class ChargeUnits(unittest.TestCase):
    def compile_run(self, directory, source):
        c = directory / "test.c"
        exe = directory / "test"
        c.write_text(source)
        subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-O2", str(c), "-o", str(exe)], check=True)
        return subprocess.run([str(exe)], capture_output=True, text=True)

    def test_unfixed_driver_reproduces_enodata(self):
        with tempfile.TemporaryDirectory(prefix="rog5-charge-unit-") as tmp:
            result = self.compile_run(Path(tmp), FIXTURE.read_text())
        self.assertEqual(result.returncode, 1)
        for variant in (1, 2):
            for prop in (0, 1):
                self.assertIn(f"variant={variant} initial=0 prop={prop} unit=0 rc=-61",
                              result.stderr)
        self.assertNotIn("variant=0", result.stderr)
        self.assertNotIn("variant=3", result.stderr)

    def test_fixed_phone_capacity_and_unchanged_laptop_units(self):
        with tempfile.TemporaryDirectory(prefix="rog5-charge-unit-") as tmp:
            patched = apply_patch(Path(tmp), FIXTURE.read_text())
            result = self.compile_run(Path(tmp), patched)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_patch_changes_only_phone_unit_initialization(self):
        lines = PATCH.read_text().splitlines()
        self.assertEqual([line for line in lines if line.startswith("+++ ")],
                         ["+++ b/" + str(DRIVER)])
        self.assertFalse(any(line.startswith("-") and not line.startswith("--- ")
                             for line in lines))
        added = "\n".join(line[1:] for line in lines
                          if line.startswith("+") and not line.startswith("+++ "))
        # No charging-control hook, firmware message, scaling or policy change.
        code = re.sub(r"/\*.*?\*/", "", added, flags=re.S).strip()
        self.assertEqual(code, "battmgr->unit = QCOM_BATTMGR_UNIT_mAh;")


def check_retained_source(path):
    original = path.read_text()
    fixture = FIXTURE.read_text()
    fragments = FRAGMENTS.findall(fixture)
    if len(fragments) != 6:
        raise ValueError("fixture fragments missing")
    for name, fragment in fragments:
        if original.count(fragment) != 1:
            raise ValueError(f"retained source mismatch: {name}")
    with tempfile.TemporaryDirectory(prefix="rog5-charge-unit-source-") as tmp:
        directory = Path(tmp)
        patched_source = apply_patch(directory / "source", original)
        patched_fixture = apply_patch(directory / "fixture", fixture)
        for name, fragment in FRAGMENTS.findall(patched_fixture):
            if patched_source.count(fragment) != 1:
                raise ValueError(f"patched source mismatch: {name}")
    print("PASS retained source excerpts and actual driver patch application (no source modification)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="retained qcom_battmgr.c; read only")
    args, remaining = parser.parse_known_args()
    if args.source:
        check_retained_source(args.source)
    unittest.main(argv=[__file__, *remaining])
