#!/usr/bin/env python3
"""Run one applet from an extracted initramfs in a private, host-free root.

Offline only: no network, host /lib, device nodes, mount actions or admission.
The QEMU executable is the sole host file mounted into the extracted root.
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
import time

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "rog5_archive", REPO / "scripts/device/build-native-wifi-boot-initramfs.py")
ARCHIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARCHIVE)


def extract(members, root):
    """Never follow archive links on the host, including a linked parent."""
    for name, (fields, data) in members.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or ".." in path.parts or str(path) != name
                or name in {".", "", "rog5-qemu"}):
            raise ValueError("noncanonical archive path")
        for parent in path.parents:
            if str(parent) == ".":
                continue
            if str(parent) not in members or not stat.S_ISDIR(members[str(parent)][0][1]):
                raise ValueError("archive parent is not a directory")
        mode = fields[1]
        if fields[2:4] != [0, 0] or mode & 0o6000:
            raise ValueError("non-root ownership or set-ID metadata is unsupported")
        if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
            raise ValueError("device or special file in offline root")
        if stat.S_ISREG(mode) and fields[4] != 1:
            raise ValueError("hardlinked archive file requires explicit support")
    # Validate the complete inventory before writing, then parents before children.
    for name in sorted(members, key=lambda name: (name.count("/"), name)):
        fields, data = members[name]
        destination = root / name
        mode = fields[1]
        if stat.S_ISDIR(mode):
            destination.mkdir()
        elif stat.S_ISREG(mode):
            destination.write_bytes(data)
            destination.chmod(stat.S_IMODE(mode) & 0o777)  # never set-ID on host
        else:
            destination.symlink_to(data.decode())
    for name, (fields, _) in members.items():
        if stat.S_ISDIR(fields[1]):
            (root / name).chmod(stat.S_IMODE(fields[1]))


def run(archive, release, applet, *, qemu, empty_module_index=False):
    if not re.fullmatch(r"[A-Za-z0-9._+-]+", release):
        raise ValueError("invalid target release")
    if not applet or applet[0].startswith("-"):
        raise ValueError("supply an explicit BusyBox applet")
    bwrap = shutil.which("bwrap")
    if not bwrap or not qemu.is_file():
        raise ValueError("requires bubblewrap and a static qemu-aarch64 executable")
    started = time.monotonic()
    with archive.open("rb") as source:
        compressed = source.read(256 * 1024 * 1024 + 1)
    if len(compressed) > 256 * 1024 * 1024:
        raise ValueError("compressed initramfs exceeds 256 MiB")
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as source:
        payload = source.read(512 * 1024 * 1024 + 1)
    if len(payload) > 512 * 1024 * 1024:
        raise ValueError("expanded initramfs exceeds 512 MiB")
    members = ARCHIVE.entries(payload)
    with tempfile.TemporaryDirectory(prefix="rog5-sealed-") as scratch:
        root = Path(scratch)
        extract(members, root)
        # This is an explicit simulation of the trusted pre-switch runtime's
        # empty index. Default execution leaves the archive filesystem unchanged.
        if empty_module_index:
            index = root / "lib" / "modules" / release / "modules.dep"
            for directory in (root / "lib", index.parent.parent, index.parent):
                if directory.is_symlink():
                    raise ValueError("linked module directory")
                directory.mkdir(exist_ok=True)
            with index.open("xb"):
                pass
            index.chmod(0o444)
        (root / "rog5-qemu").touch()
        result = subprocess.run([
            bwrap, "--unshare-all", "--die-with-parent", "--new-session",
            "--ro-bind", str(root), "/", "--ro-bind", str(qemu.resolve()), "/rog5-qemu",
            "--clearenv", "--setenv", "PATH", "/bin:/sbin:/usr/bin:/usr/sbin",
            "--setenv", "LC_ALL", "C", "--chdir", "/",
            "/rog5-qemu", "-r", release, "/bin/busybox", *applet,
        ], capture_output=True, timeout=30)
    return result, {
        "format": "rog5-sealed-busybox-result-v1",
        "archive_sha256": hashlib.sha256(compressed).hexdigest(),
        "qemu_sha256": hashlib.sha256(qemu.read_bytes()).hexdigest(),
        "target_release": release, "applet": applet,
        "empty_runtime_module_index": empty_module_index,
        "returncode": result.returncode,
        "seconds": round(time.monotonic() - started, 3),
        "authority": "none",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("--qemu", type=Path, default=Path(
        shutil.which("qemu-aarch64-static") or "/missing/qemu-aarch64-static"))
    parser.add_argument("--empty-module-index", action="store_true")
    parser.add_argument("archive", type=Path)
    parser.add_argument("applet", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    applet = args.applet[1:] if args.applet[:1] == ["--"] else args.applet
    result, record = run(args.archive, args.release, applet, qemu=args.qemu,
                         empty_module_index=args.empty_module_index)
    print(result.stdout.decode(errors="replace"), end="")
    print(result.stderr.decode(errors="replace"), end="")
    print(json.dumps(record, sort_keys=True))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
