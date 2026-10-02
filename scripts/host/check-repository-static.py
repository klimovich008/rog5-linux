#!/usr/bin/env python3
"""Static repository checks: context entry points, local Markdown links,
shell/Python syntax of every tracked script (*.py, *.sh and extensionless
files with a sh/bash/python3 shebang), and a private-key/API-key scan that
reports file and line only, never the matched value.

One standalone command (no network, no build, a few seconds):
    python3 scripts/host/check-repository-static.py [--repo DIR] [--skip-syntax]
The repository test runner calls it before any suite.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys

ENTRY_POINTS = ("docs/current-state.md", "docs/active-context.md", "docs/development.md")
SHELL_INTERPRETERS = {
    b"#!/bin/bash": "bash",
    b"#!/usr/bin/bash": "bash",
    b"#!/usr/bin/env bash": "bash",
    b"#!/bin/sh": "sh",
}
ISOLATED_PYTHON_SHEBANG = b"#!/usr/bin/env -S -i /usr/bin/python3 -I -S"
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
# Any PEM/OpenSSH private-key header (PKCS#8 "PRIVATE KEY", "ENCRYPTED
# PRIVATE KEY", RSA/EC/OPENSSH...) and literal provider credentials.
SECRET = (r"BEGIN ([A-Z0-9]+ )*PRIVATE KEY|"
          r"(OPENROUTER|OPENAI|ANTHROPIC)_API_KEY[[:space:]]*=[[:space:]]*['\"]?[A-Za-z0-9_-]{20}|"
          r"(^|[^A-Za-z0-9_-])sk-(ant-|proj-|or-)?[A-Za-z0-9_-]{20,}|"
          r"gh[pousr]_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}")
PYTHON_SHEBANGS = (b"#!/usr/bin/env python3", b"#!/usr/bin/python3")


def tracked(repo, *patterns):
    out = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", *patterns],
                         check=True, stdout=subprocess.PIPE).stdout
    return [name.decode() for name in out.split(b"\0") if name]


def check_entry_points(repo):
    missing = [entry for entry in ENTRY_POINTS if not (repo / entry).is_file()]
    return [f"missing context entry point: {entry}" for entry in missing]


def check_links(repo):
    # Live documents only: docs/history/ and docs/reviews/ keep dated records as they were.
    documents = [repo / "README.md", repo / "ROADMAP.md", *sorted((repo / "docs").glob("*.md")),
                 *(path for folder in ("hardware", "status")
                   for path in sorted((repo / "docs" / folder).glob("*.md")))]
    broken = []
    for document in documents:
        if not document.is_file():
            continue
        fenced = False
        for number, line in enumerate(document.read_text().splitlines(), 1):
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
                continue
            if fenced:
                continue
            for match in LINK.finditer(line):
                target = match.group(1).strip()
                if target.startswith("<") and target.endswith(">"):
                    target = target[1:-1]
                target = target.split("#", 1)[0].split("?", 1)[0]
                if not target or "://" in target or target.startswith(("mailto:", "#")):
                    continue
                candidate = (document.parent / target).resolve()
                try:
                    candidate.relative_to(repo)
                except ValueError:
                    broken.append(f"{document.relative_to(repo)}:{number}: link leaves the repository: {match.group(1)}")
                    continue
                if not candidate.exists():
                    broken.append(f"{document.relative_to(repo)}:{number}: missing local link target {match.group(1)}")
    return broken, len(documents)


def extensionless_scripts(repo):
    """Tracked files without an extension whose shebang names sh, bash or
    python3 (installed helpers such as scripts/device/rog5-desktop-mode)."""
    names = []
    for name in tracked(repo):
        if "." in Path(name).name or name.startswith("third_party/"):
            continue
        path = repo / name
        if path.is_symlink() or not path.is_file():
            continue
        with open(path, "rb") as f:
            first_line = f.readline(200).rstrip(b"\n")
        if first_line in SHELL_INTERPRETERS or first_line in PYTHON_SHEBANGS \
                or first_line == ISOLATED_PYTHON_SHEBANG:
            names.append(name)
    return names


def check_syntax(repo):
    errors = []
    shell_count = 0
    for name in [*tracked(repo, "*.py", "*.sh"), *extensionless_scripts(repo)]:
        path = repo / name
        source = path.read_bytes()
        first_line = source.partition(b"\n")[0]
        if path.suffix == ".py" or first_line == ISOLATED_PYTHON_SHEBANG or first_line in PYTHON_SHEBANGS:
            try:
                compile(source, str(path), "exec")
            except SyntaxError as error:
                errors.append(f"{name}: Python syntax: {error}")
            continue
        shell_count += 1
        interpreter = SHELL_INTERPRETERS.get(first_line)
        if interpreter is None:
            errors.append(f"{name}: unsupported tracked shell shebang {first_line!r}")
            continue
        result = subprocess.run([interpreter, "-n", str(path)], capture_output=True, text=True)
        if result.returncode:
            errors.append(f"{name}: {interpreter} -n: {result.stderr.strip()}")
    if shell_count == 0:
        errors.append("git returned no tracked shell scripts")
    return errors


def check_secrets(repo):
    result = subprocess.run(
        ["git", "-C", str(repo), "grep", "-nE", SECRET, "--",
         ":!scripts/host/check-repository-static.py", ":!scripts/host/test-check-repository-static.py"],
        capture_output=True, text=True)
    if result.returncode == 0:
        # file:line only: a detected secret must not be copied into CI logs
        places = [":".join(line.split(":", 2)[:2]) for line in result.stdout.splitlines()]
        return ["repository contains a private-key header or a literal API key/token at:\n  "
                + "\n  ".join(places)]
    if result.returncode != 1:
        return ["git grep failed: " + result.stderr.strip()]
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--skip-syntax", action="store_true", help="skip the shell/Python syntax pass")
    args = parser.parse_args()
    repo = args.repo.resolve()
    failures = check_entry_points(repo)
    broken, documents = check_links(repo)
    failures += broken
    if not args.skip_syntax:
        failures += check_syntax(repo)
    failures += check_secrets(repo)
    for failure in failures:
        print("FAIL " + failure, file=sys.stderr)
    if failures:
        return 1
    print(f"PASS static: entry points, links in {documents} Markdown files, "
          + ("" if args.skip_syntax else "shell/Python syntax, ") + "secret scan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
