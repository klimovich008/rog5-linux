#!/usr/bin/env python3
"""Hostile tests for the ROG5 buttons and indicator source contract."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile


REPO = Path(__file__).resolve().parents[2]
VERIFIER = REPO / "scripts/host/verify-buttons-indicator-source-contract.py"
SOURCE = (
    Path(os.environ["ROG5_LINUX_SOURCE"])
    if "ROG5_LINUX_SOURCE" in os.environ
    else None
)
CONFIG = REPO / "artifacts/network-root-v3/config-7.1.4-network-root"
MODULES = REPO / "artifacts/network-root-v3/modules-7.1.4-network-root.tar.gz"


def load_verifier():
    specification = importlib.util.spec_from_file_location(
        "buttons_indicator_source_contract", VERIFIER
    )
    if specification is None or specification.loader is None:
        raise AssertionError("cannot load source verifier")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def expect_failure(action, expected: str) -> None:
    try:
        action()
    except ValueError as error:
        if expected not in str(error):
            raise AssertionError(
                f"wrong failure: expected {expected!r}, got {str(error)!r}"
            ) from error
    else:
        raise AssertionError(f"unexpected pass: {expected}")


def run_integration() -> None:
    if SOURCE is None:
        print(
            "SKIP retained source integration; set ROG5_LINUX_SOURCE "
            "to run it"
        )
        return
    completed = subprocess.run(
        [str(VERIFIER), str(SOURCE), str(CONFIG), str(MODULES)],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode:
        raise AssertionError(completed.stderr)
    if "PASS accepted kernel source" not in completed.stdout:
        raise AssertionError("integration verifier emitted no PASS")


def main() -> int:
    verifier = load_verifier()
    run_integration()

    texts = (
        verifier.load_source_texts(SOURCE)
        if SOURCE is not None
        else {
            relative: "\n".join(fragments)
            for relative, fragments in verifier.SOURCE_FRAGMENTS.items()
        }
    )
    verifier.check_source_fragments(texts)
    for relative, fragments in verifier.SOURCE_FRAGMENTS.items():
        for marker in fragments:
            mutant = dict(texts)
            source_text = mutant[relative]
            normalized_marker = verifier.normalize(marker)
            if normalized_marker in source_text:
                mutant[relative] = source_text.replace(normalized_marker, "")
            else:
                words = normalized_marker.split()
                position = 0
                for word in words:
                    position = source_text.find(word, position)
                    if position < 0:
                        raise AssertionError(
                            f"cannot mutate marker: {relative}: {marker}"
                        )
                    source_text = (
                        source_text[:position]
                        + ("_" * len(word))
                        + source_text[position + len(word) :]
                    )
                    position += len(word)
                mutant[relative] = source_text
            expect_failure(
                lambda mutant=mutant: verifier.check_source_fragments(mutant),
                f"source contract marker is missing: {relative}:",
            )

    config_values = verifier.parse_config(CONFIG.read_bytes())
    verifier.check_required_config(config_values)
    for name in verifier.REQUIRED_CONFIG:
        mutant = dict(config_values)
        mutant[name] = "n"
        expect_failure(
            lambda mutant=mutant: verifier.check_required_config(mutant),
            f"kernel config value is wrong: {name}=",
        )

    duplicate = b"CONFIG_INPUT=y\nCONFIG_INPUT=m\n"
    expect_failure(
        lambda: verifier.parse_config(duplicate),
        "kernel config contains a duplicate symbol: CONFIG_INPUT",
    )

    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary)
        altered_config = stage / "config"
        altered_config.write_bytes(CONFIG.read_bytes() + b"\n# drift\n")
        expect_failure(
            lambda: verifier.verify_config(altered_config),
            "kernel config hash is not accepted:",
        )

        linked_config = stage / "linked-config"
        linked_config.symlink_to(CONFIG)
        expect_failure(
            lambda: verifier.verify_config(linked_config),
            "input is not an ordinary file:",
        )

        wrong_members: list = []
        expect_failure(
            lambda: verifier.check_module_members(wrong_members),
            "modules archive has 0 accepted LPG module members",
        )

        wrong_source = REPO
        expect_failure(
            lambda: verifier.verify_source(wrong_source),
            "source commit is not accepted:",
        )

    print("PASS hostile buttons and indicator source/config/module contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
