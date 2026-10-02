#!/usr/bin/env python3
"""check-repository-static.py fails on a broken link, bad syntax or a key header, and passes a clean tree."""
from pathlib import Path
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
            "pkcs8 key": ("k8.pem", "-----BEGIN " + "PRIVATE KEY-----\n", "private-key header"),
            "encrypted key": ("k9.pem", "-----BEGIN ENCRYPTED " + "PRIVATE KEY-----\n", "private-key header"),
            "openai key": ("env", "OPENAI_API_KEY" + "=abcdefghijklmnopqrstuvwxyz\n", "API key"),
            "sk token": ("conf", "token: s" + "k-proj-ABCDEFGHIJKLMNOPQRSTUV0123\n", "API key"),
            "github token": ("gh", "g" + "hp_" + "a" * 36 + "\n", "API key"),
            "extensionless shell": ("tool", "#!/bin/sh\nif then\n", "sh -n"),
            "extensionless python": ("pytool", "#!/usr/bin/env python3\ndef (:\n", "Python syntax"),
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

    def test_secret_values_are_not_printed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make(root)
            value = "s" + "k-or-v1-" + "Z" * 40
            (root / "leak.txt").write_text("x\nkey = " + value + "\n")
            self.add(root)
            result = run(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("leak.txt:2", result.stderr)
            self.assertNotIn(value, result.stderr + result.stdout)

    def test_words_ending_in_sk_are_not_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make(root)
            (root / "series").write_text("0115-ASoC-cs35l45-ROG5-mask-unused-IRQ-sources-and-the-PLL\n")
            self.add(root)
            self.assertEqual(run(root).returncode, 0)

    def test_skip_syntax_skips_only_syntax(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make(root)
            (root / "bad.py").write_text("def (:\n")
            self.add(root)
            self.assertEqual(run(root, "--skip-syntax").returncode, 0)
            (root / "README.md").write_text("[gone](missing.md)\n")
            self.assertEqual(run(root, "--skip-syntax").returncode, 1)


if __name__ == "__main__":
    unittest.main()
