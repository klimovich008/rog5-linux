#!/usr/bin/env python3
"""Hostile tests for the ROG5 buttons and indicator source contract."""

from __future__ import annotations

import importlib.util
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


REPO = Path(__file__).resolve().parents[2]
VERIFIER = REPO / "scripts/host/verify-buttons-indicator-source-contract.py"
SOURCE = (
    Path(os.environ["ROG5_LINUX_SOURCE"])
    if "ROG5_LINUX_SOURCE" in os.environ
    else None
)
CONFIG = REPO / "artifacts/network-root-v3/config-7.1.4-network-root"
MODULES = (
    Path(os.environ["ROG5_ACCEPTED_MODULES"])
    if "ROG5_ACCEPTED_MODULES" in os.environ
    else (
        REPO
        / "artifacts/network-root-v3/"
        "modules-7.1.4-network-root.tar.gz"
    )
)
MODULE_FIXTURE = REPO / "artifacts/buttons-indicator-v1/leds-qcom-lpg.ko"
MANIFEST = REPO / "manifests/artifacts.tsv"


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


def require_tracked_artifact(
    path: Path, expected_size: int, expected_hash: str
) -> None:
    relative = path.relative_to(REPO).as_posix()
    completed = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--error-unmatch", "--", relative],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if completed.returncode:
        raise AssertionError(f"clean-checkout fixture is not tracked: {relative}")
    if path.is_symlink() or not path.is_file():
        raise AssertionError(f"clean-checkout fixture is not ordinary: {relative}")
    data = path.read_bytes()
    if len(data) != expected_size or sha256(data).hexdigest() != expected_hash:
        raise AssertionError(f"clean-checkout fixture identity changed: {relative}")
    rows = [
        line.split("\t")
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.split("\t", 1)[0] == relative
    ]
    if (
        len(rows) != 1
        or len(rows[0]) != 5
        or rows[0][1] != str(expected_size)
        or rows[0][2] != expected_hash
        or rows[0][4] != "yes"
    ):
        raise AssertionError(
            f"clean-checkout fixture manifest row is not exact: {relative}"
        )


def run_integration() -> None:
    if SOURCE is None:
        print(
            "SKIP retained source integration; set ROG5_LINUX_SOURCE and "
            "ROG5_ACCEPTED_MODULES to run it"
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
    require_tracked_artifact(
        CONFIG, verifier.ACCEPTED_CONFIG_SIZE, verifier.ACCEPTED_CONFIG_SHA256
    )
    require_tracked_artifact(
        MODULE_FIXTURE,
        verifier.ACCEPTED_MODULE_FIXTURE_SIZE,
        verifier.ACCEPTED_MODULE_FIXTURE_SHA256,
    )

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

    verifier.verify_config(CONFIG)
    verifier.verify_module_fixture(MODULE_FIXTURE)
    if MODULES.is_file() and not MODULES.is_symlink():
        verifier.verify_modules(MODULES)
        print("PASS retained module archive projects to exact CI fixture")
    else:
        print("SKIP retained module archive projection")
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

        altered_module = stage / "altered-module.ko"
        altered_module.write_bytes(MODULE_FIXTURE.read_bytes() + b"\0")
        expect_failure(
            lambda: verifier.verify_module_fixture(altered_module),
            "accepted LPG module size is wrong:",
        )

        linked_module = stage / "linked-module.ko"
        linked_module.symlink_to(MODULE_FIXTURE)
        expect_failure(
            lambda: verifier.verify_module_fixture(linked_module),
            "input is not an ordinary file:",
        )

        accepted_member = tarfile.TarInfo(verifier.EXPECTED_MODULE)
        accepted_member.type = tarfile.REGTYPE
        verifier.check_module_members([accepted_member])

        irregular_member = tarfile.TarInfo(verifier.EXPECTED_MODULE)
        irregular_member.type = tarfile.DIRTYPE
        expect_failure(
            lambda: verifier.check_module_members([irregular_member]),
            "accepted LPG module archive member is not a regular file",
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
