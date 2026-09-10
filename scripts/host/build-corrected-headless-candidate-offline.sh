#!/usr/bin/env -S -i /usr/bin/python3 -I -S
"""Launch one credential-free corrected-candidate build in a fixed environment."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


DEFAULT_DTB = "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root")
    parser.add_argument("--candidate", default="headless-network-root-v1")
    parser.add_argument("--expected-dtb", default=DEFAULT_DTB)
    parser.add_argument("--expected-target", default="headless-network-root")
    parser.add_argument("--wrapper-jobs", default="8")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    implementation = Path(__file__).resolve().with_name(
        "build-corrected-headless-candidate-offline-impl.sh"
    )
    environment = {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "ROG5_DEPLOYMENT_BUILD": "0",
        "ROG5_OFFLINE_CANDIDATE": arguments.candidate,
        "ROG5_OFFLINE_EXPECTED_DTB": arguments.expected_dtb,
        "ROG5_OFFLINE_EXPECTED_TARGET": arguments.expected_target,
        "ROG5_OFFLINE_WRAPPER_JOBS": arguments.wrapper_jobs,
    }
    os.execve(
        "/usr/bin/bash",
        [
            "/usr/bin/bash",
            "--noprofile",
            "--norc",
            str(implementation),
            arguments.output_root,
        ],
        environment,
    )


if __name__ == "__main__":
    main()
