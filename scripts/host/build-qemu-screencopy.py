#!/usr/bin/env python3
"""Build the small diagnostic client, natively or with an explicit CC executable.

The exact, license-preserving XML is copied from wayland-protocols-wlr 0.3.12,
wlr-protocols/unstable/wlr-screencopy-unstable-v1.xml (retained Cargo source).
Its immutable SHA256 below is checked before wayland-scanner runs. This is
protocol generation, not a kernel, Denial or candidate-image build.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
XML = ROOT / "tools/qemu-virtio-drm/wlr-screencopy-unstable-v1.xml"
SOURCE = ROOT / "tools/qemu-virtio-drm/screencopy.c"
XML_SHA256 = "131b8f9b4aad0c8a9cf705e90d2a1511a5ca0c477637fd3400cf1cc4fa963fb8"


class Blocked(RuntimeError):
    pass


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def executable(name):
    # CC is one executable, never shell syntax or a flags string.
    result = shutil.which(name)
    if not result:
        raise Blocked(f"mandatory executable missing: {name}")
    return str(Path(result).resolve())


def build(output):
    output = output.resolve()
    output.mkdir(mode=0o700)  # Existing directories are never overwritten.
    started = time.monotonic()
    report = {"status": "FAIL", "started": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "diagnostic Wayland client build; no VM or phone qualification",
              "commands": [], "tools": {}, "inputs": {}, "outputs": {}}

    def run(command, *, check=True):
        report["commands"].append(command)
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if check and result.returncode:
            raise RuntimeError(f"command failed ({result.returncode}): {command!r}\n{result.stderr[-8192:]}")
        return result

    def tool(name, version_args=("--version",)):
        path = executable(name)
        result = run([path, *version_args])
        report["tools"][name] = {"path": path, "sha256": digest(path),
                                  "version": (result.stdout + result.stderr).strip()[:4096]}
        return path

    code = 1
    try:
        report["inputs"] = {str(SOURCE): digest(SOURCE), str(XML): digest(XML)}
        if report["inputs"][str(XML)] != XML_SHA256:
            raise RuntimeError("pinned screencopy XML identity mismatch")
        cc = tool(os.environ.get("CC", "cc"))
        scanner = tool(os.environ.get("WAYLAND_SCANNER", "wayland-scanner"))
        pkg_config = tool(os.environ.get("PKG_CONFIG", "pkg-config"))
        pkg = run([pkg_config, "--cflags", "--libs", "wayland-client"], check=False)
        if pkg.returncode:
            include = os.environ.get("ROG5_WAYLAND_INCLUDE")
            if not include:
                raise Blocked("wayland-client development inputs missing; install libwayland-dev or provide ROG5_WAYLAND_INCLUDE")
            # Copy just architecture-independent Wayland headers, not an ARM
            # sysroot's entire include tree into the native compiler's search.
            headers = Path(include).resolve()
            required = ["wayland-client.h", "wayland-client-core.h",
                        "wayland-client-protocol.h", "wayland-util.h", "wayland-version.h"]
            if any(not (headers / name).is_file() for name in required):
                raise Blocked("ROG5_WAYLAND_INCLUDE lacks required Wayland headers")
            isolated = output / "include"
            isolated.mkdir()
            for name in required:
                source = headers / name
                report["inputs"][str(source)] = digest(source)
                shutil.copyfile(source, isolated / name)
            flags = ["-I" + str(isolated), "-l:libwayland-client.so.0"]
            report["wayland_development_source"] = "explicit retained headers and system runtime library"
        else:
            flags = shlex.split(pkg.stdout)
            report["wayland_development_source"] = "pkg-config wayland-client"
            report["wayland_client_version"] = run([pkg_config, "--modversion", "wayland-client"]).stdout.strip()
        linker_name = run([cc, "-print-prog-name=ld"]).stdout.strip()
        tool(linker_name)
        header = output / "wlr-screencopy-client-protocol.h"
        protocol = output / "wlr-screencopy-protocol.c"
        binary = output / "screencopy"
        run([scanner, "client-header", str(XML), str(header)])
        run([scanner, "private-code", str(XML), str(protocol)])
        run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-I" + str(output),
             str(SOURCE), str(protocol), *flags, "-o", str(binary)])
        for path in (header, protocol, binary):
            report["outputs"][path.name] = digest(path)
        report["status"] = "PASS"
        code = 0
    except Blocked as error:
        report["status"] = "BLOCKED"
        report["error"] = str(error)
        code = 2
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
    finally:
        report["duration_seconds"] = time.monotonic() - started
        report["ended"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        report["exit_status"] = code
        (output / "provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new directory in an existing parent")
    arguments = parser.parse_args()
    try:
        sys.exit(build(arguments.output))
    except OSError as error:
        parser.exit(1, f"FAIL: cannot create fresh build output: {error}\n")
