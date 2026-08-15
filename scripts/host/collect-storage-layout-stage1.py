#!/usr/bin/env python3
"""Durably collect the fresh stage-1 GPT backup before acknowledging mutation."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import stat
import sys
import termios
import time
import tty
from typing import Callable, NoReturn, Protocol


PREFIX = "ROG5_LAYOUT_STAGE1_V1"
FILE_ORDER = ("sgdisk.gpt", "primary.raw", "secondary.raw")
FILE_SIZE_POLICY = {
    "sgdisk.gpt": (4096, 65536),
    "primary.raw": (24576, 24576),
    "secondary.raw": (20480, 20480),
}
MAX_LINE = 1024
MAX_LEADING_LINES = 64
HEX32 = re.compile(r"^[0-9a-f]{32}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class LayoutProtocolError(RuntimeError):
    """The target did not provide one exact, safely acknowledged backup set."""


class Transport(Protocol):
    def readline(self, maximum: int, timeout: float) -> bytes: ...
    def read_exact(self, size: int, timeout: float) -> bytes: ...
    def write_all(self, payload: bytes, timeout: float) -> None: ...


def fail(message: str) -> NoReturn:
    raise LayoutProtocolError(message)


def ascii_line(payload: bytes) -> list[str]:
    if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        fail("line framing is not exact")
    try:
        line = payload[:-1].decode("ascii")
    except UnicodeDecodeError as error:
        raise LayoutProtocolError("protocol line is not ASCII") from error
    tokens = line.split(" ")
    if not tokens or tokens[0] != PREFIX or "" in tokens:
        fail("protocol prefix or spacing changed")
    return tokens


def exact_fields(tokens: list[str], names: tuple[str, ...]) -> dict[str, str]:
    if len(tokens) != len(names) + 1:
        fail("protocol field count changed")
    result: dict[str, str] = {}
    for token, name in zip(tokens[1:], names, strict=True):
        observed, separator, value = token.partition("=")
        if separator != "=" or observed != name or not value:
            fail("protocol field order changed")
        result[name] = value
    return result


def validate_operation(value: str) -> None:
    if HEX32.fullmatch(value) is None:
        fail("operation identity is not canonical")


def validate_hash(value: str) -> None:
    if HEX64.fullmatch(value) is None:
        fail("SHA-256 is not canonical")


def backup_set_digest(files: dict[str, dict[str, object]]) -> str:
    records = "".join(
        f"{name}:{files[name]['sha256']}:{files[name]['size']}\n"
        for name in FILE_ORDER
    ).encode("ascii")
    return hashlib.sha256(records).hexdigest()


def write_exact(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail("host backup write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_raw_gpt(files: dict[str, bytes]) -> None:
    primary = files["primary.raw"]
    secondary = files["secondary.raw"]
    if primary[510:512] != b"\x55\xaa" or primary[4096:4104] != b"EFI PART":
        fail("primary GPT/PMBR signature is invalid")
    if secondary[-4096:-4088] != b"EFI PART":
        fail("secondary GPT signature is invalid")


def receive_backup_set(
    transport: Transport,
    output: Path,
    expected_operation: str,
    timeout: float,
    before_ack: Callable[[], None] | None = None,
) -> dict[str, object]:
    validate_operation(expected_operation)
    if output.exists() or output.is_symlink():
        fail("backup output already exists")
    if not output.is_absolute():
        fail("backup output must be absolute")
    parent = output.parent
    if not parent.is_dir() or parent.is_symlink():
        fail("backup output parent is unsafe")
    parent_mode = parent.stat().st_mode
    if parent.stat().st_uid != os.getuid() or parent_mode & 0o022:
        fail("backup output parent ownership or mode is unsafe")

    begin: dict[str, str] | None = None
    for _ in range(MAX_LEADING_LINES):
        tokens = ascii_line(transport.readline(MAX_LINE, timeout))
        if len(tokens) > 1 and tokens[1] == "status=BACKUP_BEGIN":
            begin = exact_fields(
                tokens,
                ("status", "operation_id", "nonce", "files", "backup_set_sha256"),
            )
            break
        running = exact_fields(tokens, ("status", "stage", "reason"))
        if running["status"] != "RUNNING" or running["reason"] != "none":
            fail("unexpected record before backup begin")
    if begin is None:
        fail("backup begin was not received within the record bound")
    if begin["status"] != "BACKUP_BEGIN" or begin["operation_id"] != expected_operation:
        fail("backup operation identity changed")
    if HEX32.fullmatch(begin["nonce"]) is None:
        fail("backup nonce is not canonical")
    if begin["files"] != str(len(FILE_ORDER)):
        fail("backup file count changed")
    validate_hash(begin["backup_set_sha256"])

    output.mkdir(mode=0o700)
    if stat.S_IMODE(output.stat().st_mode) != 0o700 or output.stat().st_uid != os.getuid():
        fail("backup output directory mode is unsafe")
    write_exact(output / ".incomplete", b"no mutation ACK has been sent\n")

    payloads: dict[str, bytes] = {}
    metadata: dict[str, dict[str, object]] = {}
    for expected_name in FILE_ORDER:
        fields = exact_fields(
            ascii_line(transport.readline(MAX_LINE, timeout)),
            ("status", "name", "size", "sha256"),
        )
        if fields["status"] != "BACKUP_FILE" or fields["name"] != expected_name:
            fail("backup file header or order changed")
        if not fields["size"].isascii() or not fields["size"].isdecimal():
            fail("backup file size is not canonical")
        size = int(fields["size"])
        minimum, maximum = FILE_SIZE_POLICY[expected_name]
        if not minimum <= size <= maximum:
            fail("backup file size is outside policy")
        validate_hash(fields["sha256"])
        payload = transport.read_exact(size, timeout)
        if hashlib.sha256(payload).hexdigest() != fields["sha256"]:
            fail("backup payload hash mismatch")
        if transport.read_exact(1, timeout) != b"\n":
            fail("backup payload terminator changed")
        end = exact_fields(
            ascii_line(transport.readline(MAX_LINE, timeout)), ("status", "name")
        )
        if end != {"status": "BACKUP_FILE_END", "name": expected_name}:
            fail("backup file end marker changed")
        payloads[expected_name] = payload
        metadata[expected_name] = {"size": size, "sha256": fields["sha256"]}

    end = exact_fields(
        ascii_line(transport.readline(MAX_LINE, timeout)),
        ("status", "operation_id", "nonce", "backup_set_sha256"),
    )
    if end != {
        "status": "BACKUP_END",
        "operation_id": expected_operation,
        "nonce": begin["nonce"],
        "backup_set_sha256": begin["backup_set_sha256"],
    }:
        fail("backup end identity changed")
    observed_set = backup_set_digest(metadata)
    if observed_set != begin["backup_set_sha256"]:
        fail("backup set hash mismatch")
    validate_raw_gpt(payloads)

    for name in FILE_ORDER:
        write_exact(output / name, payloads[name])
    manifest: dict[str, object] = {
        "format": "rog5-storage-layout-stage1-backup-v1",
        "operation_id": expected_operation,
        "nonce": begin["nonce"],
        "backup_set_sha256": observed_set,
        "files": metadata,
        "ack_prepared": True,
    }
    manifest_payload = (
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")
    write_exact(output / "manifest.json", manifest_payload)
    fsync_directory(output)
    (output / ".incomplete").unlink()
    fsync_directory(output)
    fsync_directory(parent)

    if before_ack is not None:
        before_ack()
    ack = (
        f"{PREFIX} status=BACKUP_ACK operation_id={expected_operation} "
        f"nonce={begin['nonce']} backup_set_sha256={observed_set}\n"
    ).encode("ascii")
    transport.write_all(ack, timeout)
    write_exact(output / "ack-sent.txt", ack)
    fsync_directory(output)
    return manifest


class RawSerial:
    def __init__(self, path: str) -> None:
        flags = os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW
        self.fd = os.open(path, flags)
        self.buffer = bytearray()
        metadata = os.fstat(self.fd)
        if not stat.S_ISCHR(metadata.st_mode):
            os.close(self.fd)
            fail("ACM path is not a character device")
        fcntl.ioctl(self.fd, termios.TIOCEXCL)
        tty.setraw(self.fd, termios.TCSANOW)
        attributes = termios.tcgetattr(self.fd)
        attributes[2] = (attributes[2] | termios.CLOCAL | termios.CREAD) & ~termios.HUPCL
        attributes[4] = termios.B115200
        attributes[5] = termios.B115200
        attributes[6][termios.VMIN] = 0
        attributes[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSANOW, attributes)

    def close(self) -> None:
        os.close(self.fd)

    def __enter__(self) -> "RawSerial":
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()

    def _read_more(self, deadline: float) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            fail("ACM receive deadline expired")
        readable, _, _ = select.select([self.fd], [], [], remaining)
        if not readable:
            fail("ACM receive deadline expired")
        try:
            chunk = os.read(self.fd, 65536)
        except BlockingIOError:
            return
        if not chunk:
            fail("ACM disconnected during stage-1 protocol")
        self.buffer.extend(chunk)

    def readline(self, maximum: int, timeout: float) -> bytes:
        deadline = time.monotonic() + timeout
        while True:
            newline = self.buffer.find(b"\n")
            if newline >= 0:
                if newline + 1 > maximum:
                    fail("ACM line exceeded its byte bound")
                result = bytes(self.buffer[: newline + 1])
                del self.buffer[: newline + 1]
                return result
            if len(self.buffer) >= maximum:
                fail("ACM line exceeded its byte bound")
            self._read_more(deadline)

    def read_exact(self, size: int, timeout: float) -> bytes:
        deadline = time.monotonic() + timeout
        while len(self.buffer) < size:
            self._read_more(deadline)
        result = bytes(self.buffer[:size])
        del self.buffer[:size]
        return result

    def write_all(self, payload: bytes, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        view = memoryview(payload)
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                fail("ACM ACK deadline expired")
            _, writable, _ = select.select([], [self.fd], [], remaining)
            if not writable:
                fail("ACM ACK deadline expired")
            try:
                written = os.write(self.fd, view)
            except BlockingIOError:
                continue
            if written <= 0:
                fail("ACM ACK write made no progress")
            view = view[written:]
        termios.tcdrain(self.fd)


def load_preflight_module():
    path = Path(__file__).with_name("collect-storage-preflight-report.py")
    spec = importlib.util.spec_from_file_location("rog5_stage1_usb_identity", path)
    if spec is None or spec.loader is None:
        fail("cannot load exact recovery USB identity helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def capture_terminal(
    transport: Transport,
    operation: str,
    backup_set_sha256: str,
    timeout: float,
) -> bytes:
    running_stages = {
        "S31_BACKUP_ACK",
        "S32_WATCHDOG_DISARM",
        "S40_FILESYSTEM_CHECK",
        "S50_SHRINK",
        "S60_GPT_TRANSACTION",
        "S70_POSTVERIFY",
        "S80_LOCK",
    }
    deadline = time.monotonic() + timeout
    for _ in range(128):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            fail("stage-1 terminal record deadline expired")
        payload = transport.readline(MAX_LINE, remaining)
        tokens = ascii_line(payload)
        status = tokens[1] if len(tokens) > 1 else ""
        if status == "status=PASS":
            fields = exact_fields(
                tokens,
                (
                    "status",
                    "stage",
                    "reason",
                    "operation_id",
                    "userdata_last_lba",
                    "arch_root_first_lba",
                    "arch_root_last_lba",
                    "filesystem_blocks",
                    "backup_set_sha256",
                    "all_read_only",
                    "block_mounts",
                ),
            )
            if fields != {
                "status": "PASS",
                "stage": "S99_COMPLETE",
                "reason": "none",
                "operation_id": operation,
                "userdata_last_lba": "53477375",
                "arch_root_first_lba": "53477376",
                "arch_root_last_lba": "61865978",
                "filesystem_blocks": "51124000",
                "backup_set_sha256": backup_set_sha256,
                "all_read_only": "1",
                "block_mounts": "0",
            }:
                fail("stage-1 PASS identity changed")
            return payload
        if status == "status=FAIL":
            fields = exact_fields(tokens, ("status", "stage", "reason", "gpt_restored"))
            if fields["stage"] == "S99_COMPLETE" or fields["reason"] == "none":
                fail("stage-1 failure classification changed")
            if fields["gpt_restored"] not in {"yes", "no", "not_needed"}:
                fail("stage-1 GPT restoration classification changed")
            return payload
        fields = exact_fields(tokens, ("status", "stage", "reason"))
        if (
            fields["status"] != "RUNNING"
            or fields["stage"] not in running_stages
            or fields["reason"] != "none"
        ):
            fail("unexpected stage-1 record after backup ACK")
    fail("stage-1 terminal record exceeded its record bound")


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--usb-location", required=True)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enumeration-timeout", type=int, default=120)
    parser.add_argument("--operation-timeout", type=int, default=600)
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    validate_operation(options.operation_id)
    if not options.output.is_absolute():
        fail("backup output must be absolute")
    preflight = load_preflight_module()
    identity = preflight.wait_storage_acm(options.usb_location, options.enumeration_timeout)
    with RawSerial(identity.path) as transport:
        manifest = receive_backup_set(
            transport,
            options.output,
            options.operation_id,
            options.operation_timeout,
            before_ack=lambda: preflight.revalidate_storage_acm(identity),
        )
        terminal = capture_terminal(
            transport,
            options.operation_id,
            str(manifest["backup_set_sha256"]),
            options.operation_timeout,
        )
    write_exact(options.output / "terminal.txt", terminal)
    fsync_directory(options.output)
    fields = ascii_line(terminal)
    status = fields[1].partition("=")[2]
    print(
        f"STORAGE_LAYOUT_STAGE1 status={status} "
        f"backup_set_sha256={manifest['backup_set_sha256']}"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except LayoutProtocolError as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
