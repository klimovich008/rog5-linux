#!/usr/bin/env python3
"""Verify the reviewed recovery responder build record and optional output."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import stat
import sys


REPO = Path(__file__).resolve().parents[2]
VERIFIER = REPO / "scripts/host/verify-retention-cycle-admission.py"
RECOVERY_INIT = REPO / "initramfs/recovery-init"
BUILD_RECORD = REPO / "configs/recovery-control/aarch64-build-v1.json"
SPEC = importlib.util.spec_from_file_location(
    "verify_retention_cycle_admission", VERIFIER
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load retention-cycle admission verifier")
ADMISSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADMISSION)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--emit-build-fields", action="store_true")
    options = parser.parse_args()
    if options.binary is not None and options.emit_build_fields:
        parser.error("--binary and --emit-build-fields are mutually exclusive")
    def current_record(path: Path) -> dict[str, object]:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError(f"reviewed build input is not regular: {path}")
        return {
            "path": path.relative_to(REPO).as_posix(),
            "size": metadata.st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        }

    recovery_inputs = {
        "init": current_record(RECOVERY_INIT),
        "control_build": current_record(BUILD_RECORD),
    }
    (
        _init_payload,
        binary_identity,
        binary_mode,
        init_sha256,
        source_sha256,
        build,
    ) = ADMISSION.verify_recovery_inputs(REPO, recovery_inputs)
    binary_size, binary_sha256 = binary_identity
    source = ADMISSION.require_keys(
        build["source"],
        {"path", "size", "sha256", "mode"},
        "recovery control source",
    )
    builder = ADMISSION.require_keys(
        build["builder"],
        {
            "script_path",
            "script_size",
            "script_sha256",
            "script_mode",
            "image",
            "image_id",
            "image_digest",
            "architecture",
            "compiler_version",
            "source_date_epoch",
        },
        "recovery control builder",
    )
    output = ADMISSION.require_keys(
        build["output"],
        {"size", "sha256", "mode"},
        "recovery control binary",
    )
    if options.emit_build_fields:
        fields = (
            source["path"],
            source["size"],
            source["sha256"],
            source["mode"],
            builder["script_path"],
            builder["script_size"],
            builder["script_sha256"],
            builder["script_mode"],
            builder["image"],
            builder["image_id"],
            builder["image_digest"],
            builder["architecture"],
            builder["compiler_version"],
            builder["source_date_epoch"],
            output["size"],
            output["sha256"],
            output["mode"],
        )
        for value in fields:
            sys.stdout.buffer.write(str(value).encode("utf-8") + b"\0")
        return 0
    if options.binary is not None:
        ADMISSION.read_verified_bytes(
            options.binary.absolute(),
            "built recovery control binary",
            expected_size=binary_size,
            expected_digest=binary_sha256,
            expected_mode=binary_mode,
        )
    print(f"recovery_init_sha256={init_sha256}")
    print(f"recovery_control_source_sha256={source_sha256}")
    print(f"recovery_control_binary_size={binary_size}")
    print(f"recovery_control_binary_sha256={binary_sha256}")
    if options.binary is None:
        print(
            "PASS recovery control build record is repository-bound; "
            "output digest requires clean-build proof"
        )
    else:
        print(
            "PASS recovery control build record and built output are exact"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
