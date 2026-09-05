#!/usr/bin/env python3
"""Atomically publish one path without replacing an existing destination."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys


AT_FDCWD = -100
RENAME_NOREPLACE = 1


def fail(message: str) -> int:
    print(f"FAIL no-replace publication: {message}", file=sys.stderr)
    return 1


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        return fail("expected SOURCE DESTINATION")
    source = Path(arguments[0])
    destination = Path(arguments[1])
    if (
        not source.is_absolute()
        or not destination.is_absolute()
        or source == Path("/")
        or destination == Path("/")
        or source == destination
    ):
        return fail("paths are unsafe")

    library = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = library.renameat2
    except AttributeError:
        return fail("host libc lacks renameat2")
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        AT_FDCWD,
        os.fsencode(source),
        AT_FDCWD,
        os.fsencode(destination),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        return fail(os.strerror(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
