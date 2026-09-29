#!/usr/bin/env python3
"""docs/current-state.md's generated block matches docs/status/components.json, and the renderer is strict."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).with_name('render-current-state.py')
SPEC = importlib.util.spec_from_file_location('render_current_state', SOURCE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

DATA = {
    'as_of': '2026-09-29 (fixture)',
    'bundles': {
        'default': {'bundle': 'b-default', 'kernel': 'k1', 'dtb': 'd1', 'installed': '2026-09-29'},
        'fallback': {'bundle': 'b-fallback', 'kernel': 'k0', 'dtb': 'd0', 'installed': 'kept'},
    },
    'areas': [
        {'name': 'A', 'components': [
            {'name': 'one', 'status': 'ready', 'weight': 1},
            {'name': 'two', 'status': 'partial', 'weight': 1, 'note': 'half'},
            {'name': 'three', 'status': 'missing', 'weight': 1}]},
        {'name': 'B', 'components': [{'name': 'four', 'status': 'untested', 'weight': 1, 'note': 'needs hands'}]},
    ],
}


class Render(unittest.TestCase):
    def test_repository_block_is_current(self):
        result = subprocess.run([sys.executable, str(SOURCE), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_block_lists_bundles_counts_and_open_items(self):
        block = M.render(DATA)
        self.assertTrue(block.startswith(M.BEGIN) and block.rstrip().endswith(M.END))
        self.assertIn('| Default | `b-default` | k1 | d1 | 2026-09-29 |', block)
        self.assertIn('| Fallback | `b-fallback` | k0 | d0 | kept |', block)
        self.assertIn('Components: 1 ready, 1 partial, 1 needs a test, 1 missing.', block)
        self.assertIn('- A / two: half', block)
        self.assertIn('- B / four: needs hands', block)
        self.assertIn('- A / three', block)
        self.assertNotIn('- A / one', block)

    def test_unknown_status_and_missing_markers_fail(self):
        bad = json.loads(json.dumps(DATA))
        bad['areas'][0]['components'][0]['status'] = 'done'
        with self.assertRaises(ValueError):
            M.render(bad)
        with self.assertRaises(ValueError):
            M.splice('no markers\n', M.render(DATA))

    def test_check_detects_stale_block_and_write_fixes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            components, state = Path(tmp) / 'c.json', Path(tmp) / 's.md'
            components.write_text(json.dumps(DATA))
            state.write_text('# t\n\n' + M.BEGIN + '\nold\n' + M.END + '\n\ntail\n')
            args = [sys.executable, str(SOURCE), '--components', str(components), '--state', str(state)]
            self.assertEqual(subprocess.run(args + ['--check'], capture_output=True).returncode, 1)
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(args + ['--check'], capture_output=True).returncode, 0)
            text = state.read_text()
            self.assertTrue(text.startswith('# t\n\n') and text.endswith('\n\ntail\n'))


if __name__ == '__main__':
    unittest.main()
