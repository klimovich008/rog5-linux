"""Harmless child probe for the offline held-descriptor executor fixture."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import sys
import time


FORMAT = "rog5-retention-descriptor-exec-v1"
PROGRAM_FD = 198
EXPECTED_MODES = frozenset(
    {"success", "timeout", "descendant", "overflow", "exit"}
)
BASE_ENVIRONMENT = {
    "HOME": "/nonexistent",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONNOUSERSITE": "1",
    "TZ": "UTC",
}


def fail(message: str) -> None:
    os.write(2, f"descriptor-probe-failure:{message}\n".encode("ascii"))
    os._exit(125)


def read_descriptor(descriptor: int) -> bytes:
    metadata = os.fstat(descriptor)
    os.lseek(descriptor, 0, os.SEEK_SET)
    payload = bytearray()
    while len(payload) <= metadata.st_size:
        block = os.read(descriptor, min(65536, metadata.st_size + 1 - len(payload)))
        if not block:
            break
        payload.extend(block)
    os.lseek(descriptor, 0, os.SEEK_SET)
    if len(payload) != metadata.st_size:
        fail("descriptor-read")
    return bytes(payload)


def active_descriptors() -> tuple[int, ...]:
    values: list[int] = []
    try:
        names = os.listdir("/proc/self/fd")
    except OSError:
        fail("fd-inventory")
    for name in names:
        if not name.isdigit():
            fail("fd-name")
        descriptor = int(name)
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        values.append(descriptor)
    return tuple(sorted(values))


def run() -> None:
    if len(sys.argv) != 4 or sys.argv[1] != "probe":
        fail("argv-shape")
    mode = sys.argv[2]
    nonce = sys.argv[3]
    if mode not in EXPECTED_MODES:
        fail("mode")
    if len(nonce) != 64 or any(value not in "0123456789abcdef" for value in nonce):
        fail("nonce")

    expected_environment = dict(BASE_ENVIRONMENT)
    expected_environment.update(
        {
            "ROG5_DESCRIPTOR_FIXTURE_FORMAT": FORMAT,
            "ROG5_DESCRIPTOR_FIXTURE_MODE": mode,
            "ROG5_DESCRIPTOR_FIXTURE_NONCE": nonce,
            "ROG5_DESCRIPTOR_FIXTURE_REPO": os.getcwd(),
        }
    )
    if dict(os.environ) != expected_environment:
        fail("environment")

    if mode == "timeout":
        time.sleep(10)
        fail("timeout-returned")
    if mode == "descendant":
        child = os.fork()
        if child == 0:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            time.sleep(10)
            os._exit(0)
        os.write(2, f"descendant-pid:{child}\n".encode("ascii"))
        time.sleep(10)
        fail("descendant-returned")
    if mode == "overflow":
        os.write(1, b"x" * 4097)
        os._exit(0)
    if mode == "exit":
        os._exit(7)

    program_metadata = os.fstat(PROGRAM_FD)
    program_payload = read_descriptor(PROGRAM_FD)
    executable_path = Path("/proc/self/exe").resolve(strict=True)
    executable_metadata = executable_path.stat()
    interpreter_payload = executable_path.read_bytes()
    stdin_metadata = os.fstat(0)
    stdout_metadata = os.fstat(1)
    stderr_metadata = os.fstat(2)
    devnull_metadata = os.stat("/dev/null")
    previous_umask = os.umask(0o077)
    os.umask(previous_umask)
    process_id = os.getpid()
    process_group = os.getpgrp()
    session_id = os.getsid(0)
    descriptors = active_descriptors()
    environment_payload = json.dumps(
        sorted(expected_environment.items()),
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    exec_argv_payload = Path("/proc/self/cmdline").read_bytes()
    argv_payload = json.dumps(
        sys.argv,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    evidence = {
        "argv_sha256": hashlib.sha256(argv_payload).hexdigest(),
        "cwd": os.getcwd(),
        "environment_sha256": hashlib.sha256(environment_payload).hexdigest(),
        "exec_argv_sha256": hashlib.sha256(exec_argv_payload).hexdigest(),
        "format": FORMAT,
        "interpreter_device": executable_metadata.st_dev,
        "interpreter_inode": executable_metadata.st_ino,
        "interpreter_path": str(executable_path),
        "interpreter_sha256": hashlib.sha256(interpreter_payload).hexdigest(),
        "mode": mode,
        "nonce": nonce,
        "open_fds": ",".join(str(value) for value in descriptors),
        "process_group_leader": process_group == process_id,
        "program_device": program_metadata.st_dev,
        "program_fd": PROGRAM_FD,
        "program_inode": program_metadata.st_ino,
        "program_sha256": hashlib.sha256(program_payload).hexdigest(),
        "session_leader": session_id == process_id,
        "stderr_pipe": stat.S_ISFIFO(stderr_metadata.st_mode),
        "stdin_devnull": (
            stat.S_ISCHR(stdin_metadata.st_mode)
            and stdin_metadata.st_rdev == devnull_metadata.st_rdev
        ),
        "stdout_pipe": stat.S_ISFIFO(stdout_metadata.st_mode),
        "umask": f"{previous_umask:04o}",
    }
    payload = (
        json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")
    os.write(1, payload)


run()
