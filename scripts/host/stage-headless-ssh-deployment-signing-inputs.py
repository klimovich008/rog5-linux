#!/usr/bin/env -S -i /usr/bin/python3 -I -S
"""Compatibility entry point for the neutral recovery deployment stager."""

from __future__ import annotations

import os
from pathlib import Path
import sys


TARGET = Path(__file__).with_name(
    "stage-recovery-deployment-signing-inputs.py"
)


if __name__ == "__main__":
    os.execve(
        "/usr/bin/python3",
        [
            "/usr/bin/python3",
            "-I",
            "-S",
            str(TARGET),
            *sys.argv[1:],
        ],
        {
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
        },
    )
