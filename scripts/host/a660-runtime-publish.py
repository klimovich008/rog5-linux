#!/usr/bin/env python3
"""Atomically publish one prepared A660 artifact directory."""

from __future__ import annotations

import argparse
import ctypes
import os
from pathlib import Path
import stat
import sys
from typing import Callable, NoReturn


RENAME_NOREPLACE = 1


class PublicationError(RuntimeError):
    """An A660 publication contract was not met."""


def fail(message: str) -> NoReturn:
    raise PublicationError(message)


def file_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
    )


def canonical_child(path: Path) -> tuple[Path, str]:
    if not path.is_absolute() or path.name in ("", ".", ".."):
        fail("publication path is not absolute and canonical")
    try:
        parent = path.parent.resolve(strict=True)
        metadata = parent.lstat()
    except OSError as error:
        raise PublicationError("publication parent is unavailable") from error
    if (
        path.parent != parent
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        fail("publication parent metadata is unsafe")
    return parent, path.name


def atomic_publish(
    stage_path: Path,
    output_path: Path,
    *,
    before_rename: Callable[[], None] | None = None,
    after_rename: Callable[[], None] | None = None,
) -> None:
    stage_parent, stage_name = canonical_child(stage_path)
    output_parent, output_name = canonical_child(output_path)
    if stage_parent != output_parent or stage_name == output_name:
        fail("publication paths are not distinct siblings")
    if output_path.exists() or output_path.is_symlink():
        fail("publication output already exists")

    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    parent_descriptor = os.open(stage_parent, flags)
    stage_descriptor = -1
    published_descriptor = -1
    try:
        parent_before = os.fstat(parent_descriptor)
        if file_identity(parent_before) != file_identity(stage_parent.lstat()):
            fail("publication parent identity changed")
        try:
            stage_descriptor = os.open(
                stage_name,
                flags,
                dir_fd=parent_descriptor,
            )
        except OSError as error:
            raise PublicationError("publication stage is unavailable") from error
        stage_before = os.fstat(stage_descriptor)
        if (
            not stat.S_ISDIR(stage_before.st_mode)
            or stage_before.st_uid != os.geteuid()
            or stat.S_IMODE(stage_before.st_mode) & 0o022
        ):
            fail("publication stage metadata is unsafe")
        library = ctypes.CDLL(None, use_errno=True)
        try:
            renameat2 = library.renameat2
        except AttributeError as error:
            raise PublicationError(
                "atomic no-replace rename is unavailable"
            ) from error
        renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameat2.restype = ctypes.c_int
        if before_rename is not None:
            before_rename()
        result = renameat2(
            parent_descriptor,
            os.fsencode(stage_name),
            parent_descriptor,
            os.fsencode(output_name),
            RENAME_NOREPLACE,
        )
        if result != 0:
            error_number = ctypes.get_errno()
            raise PublicationError(
                "atomic no-replace publication failed"
            ) from OSError(error_number, os.strerror(error_number))
        if after_rename is not None:
            after_rename()
        os.fsync(parent_descriptor)
        try:
            os.stat(
                stage_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            fail("publication stage name survived the rename")
        try:
            published_descriptor = os.open(
                output_name,
                flags,
                dir_fd=parent_descriptor,
            )
        except OSError as error:
            raise PublicationError("published output is unavailable") from error
        published = os.fstat(published_descriptor)
        if (
            file_identity(stage_before)
            != file_identity(os.fstat(stage_descriptor))
            or file_identity(stage_before) != file_identity(published)
        ):
            fail("published directory identity changed")
    finally:
        if published_descriptor >= 0:
            os.close(published_descriptor)
        if stage_descriptor >= 0:
            os.close(stage_descriptor)
        os.close(parent_descriptor)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    result.add_argument("--stage", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def main(arguments: list[str] | None = None) -> int:
    values = parser().parse_args(arguments)
    try:
        atomic_publish(values.stage, values.output)
        print("format=rog5-a660-atomic-publication-v1")
        print(f"output={values.output}")
        return 0
    except PublicationError as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    except OSError:
        print("FAIL publication filesystem operation failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
