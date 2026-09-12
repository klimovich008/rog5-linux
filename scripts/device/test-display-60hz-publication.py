#!/usr/bin/env python3
"""Exercise actual atomic publication independently of mocked schema tools."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('builder', Path(__file__).with_name('build-display-60hz-candidate-dtb.py'))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


class Publication(unittest.TestCase):
    def bundle(self, path, payload):
        path.mkdir()
        (path / 'candidate.dtb').write_bytes(payload)
        (path / 'provenance.json').write_text(json.dumps({
            'format': B.FORMAT, 'dtb_sha256': hashlib.sha256(payload).hexdigest()}))

    def test_new_replace_and_old_pair_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage, output = root / 'stage', root / 'output'
            self.bundle(stage, b'first')
            B.publish(stage, output, False)
            B.existing_bundle(output)
            self.bundle(stage, b'second')
            with self.assertRaises(ValueError):
                B.publish(stage, output, False)
            B.publish(stage, output, True)
            B.existing_bundle(output)
            B.existing_bundle(stage)
            self.assertEqual((stage / 'candidate.dtb').read_bytes(), b'first')
            self.assertEqual((output / 'candidate.dtb').read_bytes(), b'second')

    def test_refuse_unowned_mismatched_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage, output = root / 'stage', root / 'output'
            self.bundle(stage, b'new')
            self.bundle(output, b'old')
            (output / 'candidate.dtb').write_bytes(b'mutant')
            with self.assertRaises(ValueError):
                B.publish(stage, output, True)
            (output / 'extra').write_text('unrelated')
            with self.assertRaises(ValueError):
                B.publish(stage, output, True)
            link = root / 'link'
            link.symlink_to(output)
            with self.assertRaises(ValueError):
                B.publish(stage, link, True)
            self.assertEqual((output / 'candidate.dtb').read_bytes(), b'mutant')

    def test_incomplete_staging_does_not_change_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'output'
            self.bundle(output, b'old')
            # An interrupted producer has not reached its single commit.
            partial = root / 'stage'
            partial.mkdir()
            (partial / 'candidate.dtb').write_bytes(b'partial')
            with self.assertRaises(ValueError):
                B.publish(partial, output, True)
            B.existing_bundle(output)
            self.assertEqual((output / 'candidate.dtb').read_bytes(), b'old')


if __name__ == '__main__':
    unittest.main()
