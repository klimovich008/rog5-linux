"""Fixed, read-only host server for one ROG5 recovery bundle.

The production CLI deliberately has no path, address, port, URL, key, or
protocol override. Tests import the descriptor-oriented core and supply
already-created sockets and temporary directory descriptors.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import re
import socket
import stat
import struct
import time
from typing import Callable, Iterator, Sequence


BUNDLE_ROOT = Path("/var/lib/rog5-recovery-bundles")
HOST_ADDRESS = "169.254.77.1"
DEVICE_ADDRESS = "169.254.77.2"
HOST_PORT = 8080
REQUEST_MAX = 256
HEADER_MAX = 1024
TRANSFER_TIMEOUT_SECONDS = 195
MAX_REJECTED_PEERS = 8
HASH_LENGTH = 64
BUNDLE_MAX = 64
MANIFEST_MAX = 4096
ARTIFACTS = (
    ("manifest", 1, MANIFEST_MAX),
    ("manifest.sig", 64, 64),
    ("Image", 64, 128 * 1024 * 1024),
    ("board.dtb", 40, 2 * 1024 * 1024),
    ("initramfs.cpio.gz", 2, 256 * 1024 * 1024),
)
MANIFEST_FIELDS = (
    "format",
    "bundle",
    "profile",
    "kernel_size",
    "kernel_sha256",
    "dtb_size",
    "dtb_sha256",
    "initramfs_size",
    "initramfs_sha256",
    "target_id",
    "target_release",
    "rollback_timeout",
    "target_timeout",
    "a660_command_manifest_sha256",
    "root_generation",
    "root_tree_sha256",
    "root_seal_sha256",
    "root_tree_entries",
    "root_subtree",
)
REQUEST_FIELDS = (
    "format",
    "bundle",
    "manifest_sha256",
)
PROFILES = {
    "diagnostic-initramfs-v1",
    "network-root-v1",
    "persistent-root-ro-v1",
}
HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
BUNDLE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
IDENTITY = re.compile(r"[A-Za-z0-9_+.-]{1,96}\Z")


class ServerRefusal(RuntimeError):
    """Fail-closed rejection with a stable, non-sensitive reason."""


def valid_bundle(value: str) -> bool:
    return (
        bool(BUNDLE_ID.fullmatch(value))
        and ".." not in value
        and value != "none"
    )


def valid_hash(value: str) -> bool:
    return bool(HEX_SHA256.fullmatch(value)) and value != "0" * HASH_LENGTH


def parse_decimal(value: str, minimum: int, maximum: int) -> int:
    if (
        not value
        or not value.isascii()
        or not value.isdecimal()
        or (value.startswith("0") and value != "0")
    ):
        raise ServerRefusal("noncanonical decimal")
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise ServerRefusal("decimal outside policy")
    return parsed


def parse_record(payload: bytes, fields: Sequence[str]) -> dict[str, str]:
    if (
        not payload
        or not payload.endswith(b"\n")
        or b"\x00" in payload
        or b"\r" in payload
    ):
        raise ServerRefusal("noncanonical record")
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise ServerRefusal("non-ASCII record") from error
    lines = text.splitlines()
    if len(lines) != len(fields):
        raise ServerRefusal("wrong record field count")
    result: dict[str, str] = {}
    for expected, line in zip(fields, lines, strict=True):
        name, separator, value = line.partition("=")
        if separator != "=" or name != expected or not value:
            raise ServerRefusal("wrong record field")
        if any(ord(byte) < 0x21 or ord(byte) > 0x7E for byte in value):
            raise ServerRefusal("unsafe record value")
        result[name] = value
    return result


def hash_descriptor(descriptor: int, maximum: int) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    os.lseek(descriptor, 0, os.SEEK_SET)
    while True:
        block = os.read(descriptor, 1024 * 1024)
        if not block:
            break
        size += len(block)
        if size > maximum:
            raise ServerRefusal("artifact exceeds allocation policy")
        digest.update(block)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return size, digest.hexdigest()


def safe_directory(
    descriptor: int, owner: int, mode: int, label: str
) -> None:
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != owner
        or stat.S_IMODE(metadata.st_mode) != mode
    ):
        raise ServerRefusal(f"unsafe {label} metadata")


def open_regular(
    directory: int,
    name: str,
    owner: int,
    minimum: int,
    maximum: int,
) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NOATIME"):
        flags |= os.O_NOATIME
    try:
        descriptor = os.open(name, flags, dir_fd=directory)
    except OSError as error:
        raise ServerRefusal("cannot open fixed bundle artifact") from error
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != owner
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or metadata.st_nlink != 1
        or metadata.st_size < minimum
        or metadata.st_size > maximum
    ):
        os.close(descriptor)
        raise ServerRefusal("unsafe fixed bundle artifact")
    return descriptor


def validate_identity(value: str, maximum: int) -> bool:
    return (
        len(value) <= maximum
        and bool(IDENTITY.fullmatch(value))
        and not value.startswith(".")
        and ".." not in value
    )


def validate_manifest(
    payload: bytes,
    bundle: str,
    manifest_hash: str,
    observed: dict[str, tuple[int, str]],
) -> None:
    fields = parse_record(payload, MANIFEST_FIELDS)
    if (
        fields["format"] != "rog5-recovery-bundle-v2"
        or fields["bundle"] != bundle
        or fields["profile"] not in PROFILES
        or hashlib.sha256(payload).hexdigest() != manifest_hash
        or not validate_identity(fields["target_id"], 64)
        or not validate_identity(fields["target_release"], 96)
    ):
        raise ServerRefusal("manifest identity mismatch")
    rollback = parse_decimal(fields["rollback_timeout"], 60, 900)
    target = parse_decimal(fields["target_timeout"], 30, 600)
    if target > rollback - 30:
        raise ServerRefusal("manifest timeout margin is unsafe")
    if fields["profile"] == "persistent-root-ro-v1" and rollback < 300:
        raise ServerRefusal("persistent profile rollback is too short")
    if fields["profile"] in {
        "diagnostic-initramfs-v1",
        "network-root-v1",
    }:
        if (
            not valid_hash(fields["a660_command_manifest_sha256"])
            or fields["root_generation"] != "arch-a"
            or not valid_hash(fields["root_tree_sha256"])
            or not valid_hash(fields["root_seal_sha256"])
            or fields["root_subtree"] != "/"
        ):
            raise ServerRefusal("network-root trust identity is invalid")
        parse_decimal(fields["root_tree_entries"], 1, (1 << 63) - 1)
    elif (
        fields["a660_command_manifest_sha256"] != "0" * HASH_LENGTH
        or fields["root_generation"] != "none"
        or fields["root_tree_sha256"] != "0" * HASH_LENGTH
        or fields["root_seal_sha256"] != "0" * HASH_LENGTH
        or fields["root_tree_entries"] != "0"
        or fields["root_subtree"] != "none"
    ):
        raise ServerRefusal(
            "non-network profile carries root trust identity"
        )
    bindings = (
        ("Image", "kernel_size", "kernel_sha256"),
        ("board.dtb", "dtb_size", "dtb_sha256"),
        (
            "initramfs.cpio.gz",
            "initramfs_size",
            "initramfs_sha256",
        ),
    )
    for artifact, size_field, hash_field in bindings:
        size, digest = observed[artifact]
        if (
            parse_decimal(fields[size_field], 1, 256 * 1024 * 1024)
            != size
            or fields[hash_field] != digest
            or not valid_hash(fields[hash_field])
        ):
            raise ServerRefusal("manifest artifact binding mismatch")


@dataclass
class PreparedBundle:
    descriptors: tuple[int, ...]
    sizes: tuple[int, ...]
    bundle: str
    manifest_hash: str

    def close(self) -> None:
        for descriptor in self.descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass

    def __enter__(self) -> PreparedBundle:
        return self

    def __exit__(self, *_arguments: object) -> None:
        self.close()


def prepare_bundle(
    root: int, bundle: str, manifest_hash: str, owner: int
) -> PreparedBundle:
    if not valid_bundle(bundle) or not valid_hash(manifest_hash):
        raise ServerRefusal("invalid requested bundle identity")
    safe_directory(root, owner, 0o700, "bundle root")
    try:
        fcntl.flock(root, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except OSError as error:
        raise ServerRefusal("bundle root is busy") from error
    root_inventory = sorted(os.listdir(root))
    if root_inventory != [bundle]:
        raise ServerRefusal("unexpected bundle-root inventory")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NOATIME"):
        flags |= os.O_NOATIME
    try:
        directory = os.open(bundle, flags, dir_fd=root)
    except OSError as error:
        raise ServerRefusal("cannot open fixed bundle directory") from error
    descriptors: list[int] = []
    try:
        safe_directory(directory, owner, 0o500, "bundle directory")
        if sorted(os.listdir(directory)) != sorted(
            name for name, _minimum, _maximum in ARTIFACTS
        ):
            raise ServerRefusal("unexpected bundle inventory")
        observed: dict[str, tuple[int, str]] = {}
        inode_identities: set[tuple[int, int]] = set()
        for name, minimum, maximum in ARTIFACTS:
            descriptor = open_regular(
                directory, name, owner, minimum, maximum
            )
            descriptors.append(descriptor)
            metadata = os.fstat(descriptor)
            identity = (metadata.st_dev, metadata.st_ino)
            if identity in inode_identities:
                raise ServerRefusal("aliased bundle artifacts")
            inode_identities.add(identity)
            observed[name] = hash_descriptor(descriptor, maximum)
        manifest_descriptor = descriptors[0]
        manifest_size = observed["manifest"][0]
        manifest = os.read(manifest_descriptor, manifest_size + 1)
        os.lseek(manifest_descriptor, 0, os.SEEK_SET)
        if len(manifest) != manifest_size:
            raise ServerRefusal("manifest changed while opening")
        validate_manifest(
            manifest, bundle, manifest_hash, observed
        )
        return PreparedBundle(
            descriptors=tuple(descriptors),
            sizes=tuple(observed[name][0] for name, *_limits in ARTIFACTS),
            bundle=bundle,
            manifest_hash=manifest_hash,
        )
    except BaseException:
        for descriptor in descriptors:
            os.close(descriptor)
        raise
    finally:
        os.close(directory)


def remaining_timeout(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ServerRefusal("transfer deadline expired")
    return remaining


def receive_exact(connection: socket.socket, size: int, deadline: float) -> bytes:
    output = bytearray()
    while len(output) < size:
        connection.settimeout(remaining_timeout(deadline))
        try:
            block = connection.recv(size - len(output))
        except (TimeoutError, socket.timeout, OSError) as error:
            raise ServerRefusal("request receive failed") from error
        if not block:
            raise ServerRefusal("request truncated")
        output.extend(block)
    return bytes(output)


def receive_request(
    connection: socket.socket, prepared: PreparedBundle, deadline: float
) -> None:
    prefix = receive_exact(connection, 4, deadline)
    length = struct.unpack(">I", prefix)[0]
    if length < 1 or length > REQUEST_MAX:
        raise ServerRefusal("request frame length is invalid")
    payload = receive_exact(connection, length, deadline)
    fields = parse_record(payload, REQUEST_FIELDS)
    if (
        fields["format"] != "rog5-fetch-request-v1"
        or fields["bundle"] != prepared.bundle
        or fields["manifest_sha256"] != prepared.manifest_hash
    ):
        raise ServerRefusal("request identity mismatch")
    connection.settimeout(remaining_timeout(deadline))
    try:
        trailing = connection.recv(1)
    except (TimeoutError, socket.timeout, OSError) as error:
        raise ServerRefusal("request completion failed") from error
    if trailing:
        raise ServerRefusal("request contains trailing bytes")


def send_all(
    connection: socket.socket, payload: bytes, deadline: float
) -> None:
    offset = 0
    while offset < len(payload):
        connection.settimeout(remaining_timeout(deadline))
        try:
            count = connection.send(payload[offset:])
        except (TimeoutError, socket.timeout, OSError) as error:
            raise ServerRefusal("response send failed") from error
        if count <= 0:
            raise ServerRefusal("response send made no progress")
        offset += count


def serve_connection(
    connection: socket.socket,
    prepared: PreparedBundle,
    deadline: float,
    *,
    progress: Callable[[str, int, int], None] | None = None,
) -> None:
    def report(phase: str, sent: int, total: int) -> None:
        if progress is None:
            return
        try:
            progress(phase, sent, total)
        except Exception:
            # Evidence must never become part of transfer correctness.
            pass

    receive_request(connection, prepared, deadline)
    total = sum(prepared.sizes)
    sent = 0
    report("request-accepted", sent, total)
    manifest_size, signature_size, kernel_size, dtb_size, initramfs_size = (
        prepared.sizes
    )
    header = (
        "format=rog5-fetch-response-v1\n"
        f"bundle={prepared.bundle}\n"
        f"manifest_sha256={prepared.manifest_hash}\n"
        f"manifest_size={manifest_size}\n"
        f"signature_size={signature_size}\n"
        f"kernel_size={kernel_size}\n"
        f"dtb_size={dtb_size}\n"
        f"initramfs_size={initramfs_size}\n"
    ).encode("ascii")
    if len(header) > HEADER_MAX:
        raise ServerRefusal("response header exceeds policy")
    send_all(connection, struct.pack(">I", len(header)), deadline)
    send_all(connection, header, deadline)
    for (name, _minimum, _maximum), descriptor, expected in zip(
        ARTIFACTS,
        prepared.descriptors,
        prepared.sizes,
        strict=True,
    ):
        os.lseek(descriptor, 0, os.SEEK_SET)
        remaining = expected
        while remaining:
            block = os.read(descriptor, min(1024 * 1024, remaining))
            if not block:
                raise ServerRefusal("opened artifact became short")
            send_all(connection, block, deadline)
            remaining -= len(block)
        if os.read(descriptor, 1):
            raise ServerRefusal("opened artifact became oversized")
        sent += expected
        report(name, sent, total)


def serve_listener(
    listener: socket.socket,
    prepared: PreparedBundle,
    peer_allowed: Callable[[object], bool],
    timeout_seconds: int = TRANSFER_TIMEOUT_SECONDS,
    *,
    progress: Callable[[str, int, int], None] | None = None,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    rejected = 0
    while True:
        listener.settimeout(remaining_timeout(deadline))
        try:
            connection, peer = listener.accept()
        except (TimeoutError, socket.timeout, OSError) as error:
            raise ServerRefusal("listener accept failed") from error
        with connection:
            if not peer_allowed(peer):
                rejected += 1
                if rejected >= MAX_REJECTED_PEERS:
                    raise ServerRefusal("too many rejected peers")
                continue
            serve_connection(
                connection,
                prepared,
                deadline,
                progress=progress,
            )
            try:
                connection.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            return


def production_peer(peer: object) -> bool:
    return (
        isinstance(peer, tuple)
        and len(peer) >= 2
        and peer[0] == DEVICE_ADDRESS
    )


@contextmanager
def prepare_production(
    bundle: str, manifest_hash: str
) -> Iterator[PreparedBundle]:
    if os.geteuid() == 0:
        raise ServerRefusal("bundle server must run unprivileged")
    if not valid_bundle(bundle) or not valid_hash(manifest_hash):
        raise ServerRefusal("invalid requested bundle identity")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NOATIME"):
        flags |= os.O_NOATIME
    try:
        root = os.open(BUNDLE_ROOT, flags)
    except OSError as error:
        raise ServerRefusal("cannot open fixed host bundle root") from error
    try:
        with prepare_bundle(
            root, bundle, manifest_hash, os.geteuid()
        ) as prepared:
            yield prepared
    finally:
        os.close(root)


def run_preflight(bundle: str, manifest_hash: str) -> None:
    with prepare_production(bundle, manifest_hash):
        pass


def run_production(bundle: str, manifest_hash: str) -> None:
    def report_progress(phase: str, sent: int, total: int) -> None:
        # The fixed broker merges child stderr into stdout and relays complete
        # lines, so stdout is the intentional live evidence channel here.
        print(
            "INFO recovery bundle transfer "
            f"phase={phase} bytes_sent={sent} bytes_total={total}",
            flush=True,
        )

    with prepare_production(bundle, manifest_hash) as prepared:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind((HOST_ADDRESS, HOST_PORT))
            listener.listen(1)
            serve_listener(
                listener,
                prepared,
                production_peer,
                progress=report_progress,
            )


def main(arguments: Sequence[str]) -> int:
    if len(arguments) == 4 and arguments[1] == "--preflight":
        run_preflight(arguments[2], arguments[3])
        print("PASS fixed recovery bundle inventory and manifest verified")
        return 0
    if len(arguments) != 3 or arguments[1] == "--preflight":
        raise ServerRefusal(
            "usage: serve-recovery-bundle.py "
            "[--preflight] BUNDLE MANIFEST_SHA256"
        )
    run_production(arguments[1], arguments[2])
    return 0


if __name__ == "__main__":
    import sys

    try:
        raise SystemExit(main(sys.argv))
    except ServerRefusal as error:
        print(f"serve-recovery-bundle: {error}", file=sys.stderr)
        raise SystemExit(1) from None
