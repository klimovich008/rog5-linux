#!/usr/bin/env python3
"""Static repository checks: context entry points, local Markdown links,
shell/Python syntax of every tracked script, and a private-key/API-key scan.

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
# PKCS#8 ("BEGIN PRIVATE KEY", the Ed25519 signing key's format) and encrypted
# PKCS#8 headers have no algorithm word.
SECRET = (r"BEGIN ((RSA|OPENSSH|EC|DSA|ENCRYPTED) )?PRIVATE KEY|"
          r"OPENROUTER_API_KEY[[:space:]]*=[[:space:]]*['\"]?[A-Za-z0-9_-]{20}")


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


def check_syntax(repo):
    errors = []
    shell_count = 0
    for name in tracked(repo, "*.py", "*.sh"):
        path = repo / name
        source = path.read_bytes()
        first_line = source.partition(b"\n")[0]
        if path.suffix == ".py" or first_line == ISOLATED_PYTHON_SHEBANG:
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
        return ["repository contains a private-key header or literal OpenRouter key:\n" + result.stdout]
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
