#!/usr/bin/env python3
"""check-repository-static.py fails on a broken link, bad syntax or a key header, and passes a clean tree."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("check-repository-static.py")


def run(repo, *extra):
    return subprocess.run([sys.executable, str(CHECK), "--repo", str(repo), *extra],
                          capture_output=True, text=True)


class StaticCheck(unittest.TestCase):
    def make(self, root):
        (root / "docs").mkdir()
        for name in ("current-state.md", "active-context.md", "development.md"):
            (root / "docs" / name).write_text("# x\n")
        (root / "README.md").write_text("[state](docs/current-state.md)\n```\n[not a link](nowhere)\n```\n")
        (root / "ROADMAP.md").write_text("[web](https://example.org)\n")
        (root / "ok.sh").write_text("#!/bin/sh\necho ok\n")
        (root / "ok.py").write_text("print('ok')\n")
        (root / 'configs').mkdir()
        (root / 'input.txt').write_text('tracked fixture\n')
        (root / 'configs/repository-tests.json').write_text(json.dumps({
            'tests': [{'path': 'ok.py', 'required_inputs': ['input.txt']}]}))
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        self.add(root)

    def add(self, root):
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)

    def test_clean_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make(root)
            result = run(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PASS static", result.stdout)

    def test_each_failure_is_reported(self):
        cases = {
            "broken link": ("docs/development.md", "[gone](missing.md)\n", "missing local link target"),
            "python syntax": ("bad.py", "def (:\n", "Python syntax"),
            "shell syntax": ("bad.sh", "#!/bin/sh\nif then\n", "sh -n"),
            "shebang": ("noshebang.sh", "set -eu\n", "unsupported tracked shell shebang"),
            "key": ("key.txt", "-----BEGIN OPENSSH " + "PRIVATE KEY-----\n", "private-key header"),
            "pkcs8 key": ("key.pem", "-----BEGIN " + "PRIVATE KEY-----\n", "private-key header"),
            "encrypted key": ("key.pem", "-----BEGIN ENCRYPTED " + "PRIVATE KEY-----\n", "private-key header"),
            "dsa key": ("key.pem", "-----BEGIN DSA " + "PRIVATE KEY-----\n", "private-key header"),
            "entry point": ("docs/active-context.md", None, "missing context entry point"),
        }
        for label, (name, content, message) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.make(root)
                if content is None:
                    (root / name).unlink()
                else:
                    (root / name).write_text(content)
                self.add(root)
                result = run(root)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(message, result.stderr)

    def test_skip_syntax_skips_only_syntax(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make(root)
            (root / "bad.py").write_text("def (:\n")
            self.add(root)
            self.assertEqual(run(root, "--skip-syntax").returncode, 0)
            (root / "README.md").write_text("[gone](missing.md)\n")
            self.assertEqual(run(root, "--skip-syntax").returncode, 1)

    def test_publication_cannot_drop_a_suite_or_required_input(self):
        for name in ('ok.py', 'input.txt', 'configs/repository-tests.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.make(root)
                (root / name).unlink()
                self.add(root)
                result = run(root, '--skip-syntax')
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(name, result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_ignored_local_input_cannot_mask_a_missing_tracked_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make(root)
            subprocess.run(['git', '-C', str(root), 'rm', '--cached', 'input.txt'], check=True,
                           capture_output=True)
            (root / '.gitignore').write_text('input.txt\n')
            result = run(root)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn('untracked repository test input: input.txt', result.stderr)

    def test_missing_tracked_script_is_reported_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make(root)
            (root / 'ok.py').unlink()
            result = run(root)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn('missing or unsafe repository test input: ok.py', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_linked_input_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make(root)
            (root / 'input.txt').unlink()
            (root / 'input.txt').symlink_to('ok.py')
            self.add(root)
            result = run(root)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn('missing or unsafe repository test input: input.txt', result.stderr)


if __name__ == "__main__":
    unittest.main()
