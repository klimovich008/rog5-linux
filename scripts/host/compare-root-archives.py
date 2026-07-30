#!/usr/bin/env python3
"""Compare archive structure and inode flags across a dense re-encoding.

The caller separately compares complete extracted-tree seals for content,
mode, ownership, timestamps, xattrs, and symlink targets.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path, PurePosixPath
import tarfile
from typing import NoReturn


class ArchiveComparisonError(RuntimeError):
    """The archives do not describe the same filesystem inventory."""


def fail(message: str) -> NoReturn:
    raise ArchiveComparisonError(message)


def clean_path(name: str) -> str:
    while name.startswith("./"):
        name = name[2:]
    if name in ("", "."):
        return "."
    if "\0" in name or name.startswith("/"):
        fail("archive contains an unsafe path")
    path = PurePosixPath(name)
    if any(part in ("", ".", "..") for part in path.parts):
        fail("archive contains an unsafe path")
    return path.as_posix()


def member_kind(member: tarfile.TarInfo) -> str:
    if member.isfile() or member.islnk():
        return "file"
    if member.isdir():
        return "directory"
    if member.issym():
        return "symlink"
    fail("archive contains an unsupported entry")


def load_archive(path: Path) -> dict[str, tarfile.TarInfo]:
    if path.is_symlink() or not path.is_file():
        fail("archive is not a regular, non-linked file")
    members: dict[str, tarfile.TarInfo] = {}
    try:
        with tarfile.open(path, mode="r:*") as archive:
            for member in archive:
                name = clean_path(member.name)
                if name in members:
                    fail("archive contains a duplicate path")
                member_kind(member)
                members[name] = member
    except (OSError, tarfile.TarError) as error:
        raise ArchiveComparisonError("cannot inspect archive") from error
    if not members:
        fail("archive is empty")
    return members


def resolve_hardlink(
    name: str,
    members: dict[str, tarfile.TarInfo],
    seen: frozenset[str] = frozenset(),
) -> str:
    if name in seen:
        fail("archive contains a hard-link cycle")
    member = members.get(name)
    if member is None or member_kind(member) != "file":
        fail("archive hard link has no regular-file target")
    if not member.islnk():
        return name
    target = clean_path(member.linkname)
    return resolve_hardlink(target, members, seen | {name})


def hardlink_groups(
    members: dict[str, tarfile.TarInfo],
) -> tuple[tuple[str, ...], ...]:
    groups: dict[str, list[str]] = defaultdict(list)
    for name, member in members.items():
        if member_kind(member) == "file":
            groups[resolve_hardlink(name, members)].append(name)
    return tuple(
        sorted(tuple(sorted(group)) for group in groups.values() if len(group) > 1)
    )


def fflags(
    members: dict[str, tarfile.TarInfo],
) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    file_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for name, member in members.items():
        value = member.pax_headers.get("SCHILY.fflags", "")
        if "\0" in value or "\n" in value:
            fail("archive contains malformed inode flags")
        if member_kind(member) == "file":
            representative = resolve_hardlink(name, members)
            file_groups[representative].append((name, value))
        elif value:
            result.append((name, value))
    for group in file_groups.values():
        values = {value for _, value in group if value}
        if len(values) > 1:
            fail("hard-linked archive entries disagree on inode flags")
        if values:
            result.append(("|".join(sorted(name for name, _ in group)), values.pop()))
    return tuple(sorted(result))


def compare(source: Path, normalized: Path) -> None:
    source_members = load_archive(source)
    normalized_members = load_archive(normalized)
    source_kinds = {
        name: member_kind(member) for name, member in source_members.items()
    }
    normalized_kinds = {
        name: member_kind(member)
        for name, member in normalized_members.items()
    }
    if source_kinds != normalized_kinds:
        fail("archive path inventory or entry kind changed")
    if hardlink_groups(source_members) != hardlink_groups(normalized_members):
        fail("archive hard-link topology changed")
    if fflags(source_members) != fflags(normalized_members):
        fail("archive inode flags changed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("normalized", type=Path)
    arguments = parser.parse_args()
    try:
        compare(arguments.source, arguments.normalized)
    except ArchiveComparisonError as error:
        parser.error(str(error))
    print("PASS archive paths, kinds, hard links, and inode flags match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
