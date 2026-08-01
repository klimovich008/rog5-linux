#!/usr/bin/env python3
"""Bind the accepted non-fixture root to the exact diagnostic candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys
from typing import Any, NoReturn


REPO = Path(__file__).resolve().parents[2]
DEPLOYMENT_PATH = (
    REPO / "scripts/host/prepare-headless-ssh-deployment-candidate.py"
)
CANDIDATE_ID = "headless-netroot-early-diag-v1"
EXPECTED_SHA256 = (
    "7081a0c77158ed695e62751e152baff101b18a9b364640c0cbffd6ef8ba1c6e8"
)


class DiagnosticCandidateError(RuntimeError):
    """A stable refusal that does not expose credential material."""


def fail(message: str) -> NoReturn:
    raise DiagnosticCandidateError(message)


def load_deployment_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_diagnostic_deployment_candidate_base",
        DEPLOYMENT_PATH,
    )
    if specification is None or specification.loader is None:
        fail("cannot load the fixed deployment-candidate verifier")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


DEPLOYMENT = load_deployment_module()


def candidate_record(package: dict[str, str]) -> dict[str, Any]:
    record = DEPLOYMENT.CANDIDATE.load_candidate(CANDIDATE_ID)
    for field in DEPLOYMENT.ROOT_FIELDS:
        if record[field] != package[field]:
            fail("diagnostic candidate and deployment package roots differ")
    validated = DEPLOYMENT.CANDIDATE.validate_external_candidate_record(
        record,
        CANDIDATE_ID,
    )
    payload = DEPLOYMENT.canonical_payload(validated)
    if hashlib.sha256(payload).hexdigest() != EXPECTED_SHA256:
        fail("diagnostic deployment candidate identity changed")
    return validated


def prepare(
    package_path: Path,
    output_path: Path,
) -> tuple[dict[str, Any], Path, str]:
    package = DEPLOYMENT.parse_package(package_path)
    record = candidate_record(package)
    payload = DEPLOYMENT.canonical_payload(record)
    output = DEPLOYMENT.write_candidate(output_path, payload)
    return record, output, hashlib.sha256(payload).hexdigest()


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
        record, output, digest = prepare(options.package, options.output)
    except (
        DiagnosticCandidateError,
        DEPLOYMENT.DeploymentCandidateError,
        DEPLOYMENT.HEADLESS.HeadlessRootError,
        DEPLOYMENT.CANDIDATE.CandidateError,
        OSError,
        ValueError,
    ):
        print(
            "FAIL diagnostic deployment candidate preparation refused",
            file=sys.stderr,
        )
        return 1
    print("format=rog5-early-target-diagnostic-deployment-candidate-v1")
    print(f"candidate={record['candidate']}")
    print(f"bundle={record['bundle']}")
    print(f"candidate_record_sha256={digest}")
    print(f"root_tree_sha256={record['root_tree_sha256']}")
    print(f"root_seal_sha256={record['root_seal_sha256']}")
    print(f"root_tree_entries={record['root_tree_entries']}")
    print(f"output={output}")
    print("authority=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
