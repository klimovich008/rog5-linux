#!/usr/bin/env python3
"""Prepare or verify one sealed A660 network-root generation."""

from __future__ import annotations

import argparse
from collections import OrderedDict
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import NoReturn


REPO = Path(__file__).resolve().parents[2]
ROOT_TOOL_PATH = REPO / "scripts/device/persistent-root-tool.py"
HARNESS_SOURCE = REPO / "scripts/device/a660-acceptance.py"
CGROUP_SOURCE = REPO / "tools/a660/rog5-cgroup-exec.c"
VULKAN_SOURCE = REPO / "tools/a660/rog5-vulkan-submit.c"
ROOT_VERIFY_SOURCE = REPO / "tools/persistent-root-verify.c"
BASELINE_SOURCE = REPO / "scripts/device/collect-baseline.sh"
EPOCH = 1681862400
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SAFE_IDENTITY = re.compile(r"[A-Za-z0-9_.:+-]{1,96}\Z")
TOOL_NAMES = (
    "persistent-root-verify",
    "rog5-cgroup-exec",
    "rog5-vulkan-submit",
)
BASE_GENERATIONS = {
    "arch-successor-v3": Path("etc/rog5/arch-successor-v3-export"),
    "a660-gmu-cx-runtime-pm-v10": Path(
        "etc/rog5/a660-gmu-cx-runtime-pm-v10-export"
    ),
}
BASE_VERIFIERS = {
    "arch-successor-v3": REPO
    / "scripts/host/verify-arch-successor-v3-export.sh",
    "a660-gmu-cx-runtime-pm-v10": REPO
    / "scripts/host/verify-a660-gmu-cx-runtime-pm-v10-export.sh",
}
INSTALL_INPUTS = OrderedDict(
    (
        (
            "acceptance",
            (
                HARNESS_SOURCE,
                Path("usr/local/sbin/rog5-a660-acceptance"),
            ),
        ),
        (
            "runner",
            (
                Path("rog5-cgroup-exec"),
                Path("usr/local/libexec/rog5-cgroup-exec"),
            ),
        ),
        (
            "submit",
            (
                Path("rog5-vulkan-submit"),
                Path("usr/local/libexec/rog5-vulkan-submit"),
            ),
        ),
        (
            "root_verify",
            (
                Path("persistent-root-verify"),
                Path("usr/local/sbin/persistent-root-verify"),
            ),
        ),
    )
)
RECORD_PATHS = (
    Path("etc/rog5/a660-command-manifest"),
    Path("etc/rog5/a660-runtime-provenance"),
    Path("etc/rog5/a660-runtime-tools.manifest"),
)
BASELINE_PATH = Path("usr/local/bin/rog5-collect-baseline.sh")
BASE_METADATA_DELTA_PATHS = {
    Path("."),
    Path("etc/rog5"),
    Path("usr/local/libexec"),
    Path("usr/local/sbin"),
}
COMMAND_PATHS = OrderedDict(
    (
        ("runner", Path("usr/local/libexec/rog5-cgroup-exec")),
        ("systemctl", Path("usr/bin/systemctl")),
        ("dmesg", Path("usr/bin/dmesg")),
        ("baseline", Path("usr/local/bin/rog5-collect-baseline.sh")),
        ("vulkaninfo", Path("usr/bin/vulkaninfo")),
        ("eglinfo", Path("usr/bin/eglinfo")),
        ("submit", Path("usr/local/libexec/rog5-vulkan-submit")),
        ("gdbus", Path("usr/bin/gdbus")),
        ("vkcube", Path("usr/bin/vkcube")),
        ("screen", Path("usr/local/bin/rog5-screen-toggle.sh")),
        ("kscreen", Path("usr/bin/kscreen-doctor")),
        ("root_verify", Path("usr/local/sbin/persistent-root-verify")),
    )
)
TOOL_MANIFEST_KEYS = (
    "format",
    "source_date_epoch",
    "static_builder_image_id",
    "vulkan_builder_image_id",
    "builder_packages_sha256",
    "persistent_root_verify_size",
    "persistent_root_verify_sha256",
    "rog5_cgroup_exec_size",
    "rog5_cgroup_exec_sha256",
    "rog5_vulkan_submit_size",
    "rog5_vulkan_submit_sha256",
)
PROVENANCE_KEYS = (
    "format",
    "base_generation",
    "base_export_seal_sha256",
    "base_export_verifier_sha256",
    "base_tree_entries",
    "base_tree_sha256",
    "base_archive_size",
    "base_archive_sha256",
    "kernel_release",
    "a660_acceptance_sha256",
    "cgroup_exec_source_sha256",
    "vulkan_submit_source_sha256",
    "persistent_root_verify_source_sha256",
    "runtime_tools_manifest_sha256",
    "persistent_root_verify_sha256",
    "rog5_cgroup_exec_sha256",
    "rog5_vulkan_submit_sha256",
    "command_manifest_sha256",
)
IDENTITY_KEYS = (
    "format",
    "profile",
    "root_generation",
    "root_subtree",
    "kernel_release",
    "base_generation",
    "base_export_seal_sha256",
    "base_export_verifier_sha256",
    "base_tree_entries",
    "base_tree_sha256",
    "runtime_provenance_sha256",
    "a660_acceptance_sha256",
    "command_manifest_sha256",
    "persistent_root_verify_sha256",
    "rog5_cgroup_exec_sha256",
    "rog5_vulkan_submit_sha256",
    "root_tree_entries",
    "root_tree_sha256",
    "root_seal_sha256",
)


class RuntimeRootError(RuntimeError):
    """A versioned A660 runtime-root contract was not met."""


def fail(message: str) -> NoReturn:
    raise RuntimeRootError(message)


def load_root_tool():
    specification = importlib.util.spec_from_file_location(
        "rog5_persistent_root_tool",
        ROOT_TOOL_PATH,
    )
    if specification is None or specification.loader is None:
        fail("cannot load the persistent-root tool")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def file_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def safe_root(path: Path) -> tuple[Path, int]:
    if not path.is_absolute():
        fail("runtime root must be absolute")
    try:
        before = path.lstat()
        resolved = path.resolve(strict=True)
        after = resolved.lstat()
    except OSError as error:
        raise RuntimeRootError("runtime root is unavailable") from error
    if (
        resolved == Path("/")
        or path != resolved
        or file_identity(before) != file_identity(after)
        or not stat.S_ISDIR(after.st_mode)
        or stat.S_IMODE(after.st_mode) & 0o022
    ):
        fail("runtime root path or metadata is unsafe")
    if after.st_uid != os.geteuid():
        fail("runtime root is not owned by the caller")
    return resolved, after.st_uid


def safe_parent(path: Path, owner: int) -> Path:
    if not path.is_absolute():
        fail("identity path must be absolute")
    parent = path.parent
    try:
        resolved = parent.resolve(strict=True)
        metadata = resolved.lstat()
    except OSError as error:
        raise RuntimeRootError("identity parent is unavailable") from error
    if (
        parent != resolved
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != owner
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        fail("identity parent metadata is unsafe")
    return resolved


def ensure_ancestors(root: Path, relative: Path, owner: int) -> None:
    if relative.is_absolute() or ".." in relative.parts:
        fail("runtime-root relative path is unsafe")
    current = root
    for part in relative.parent.parts:
        current /= part
        try:
            metadata = current.lstat()
        except OSError as error:
            raise RuntimeRootError(
                "runtime-root ancestor is unavailable"
            ) from error
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != owner
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            fail("runtime-root ancestor metadata is unsafe")


def open_regular(
    path: Path,
    *,
    owner: int | None = None,
    mode: int | None = None,
    executable: bool | None = None,
) -> tuple[int, os.stat_result]:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        before = path.lstat()
        descriptor = os.open(path, flags)
        observed = os.fstat(descriptor)
    except OSError as error:
        raise RuntimeRootError("required regular file is unavailable") from error
    if (
        file_identity(before) != file_identity(observed)
        or not stat.S_ISREG(observed.st_mode)
        or observed.st_nlink != 1
        or stat.S_IMODE(observed.st_mode) & 0o022
        or (owner is not None and observed.st_uid != owner)
        or (mode is not None and stat.S_IMODE(observed.st_mode) != mode)
        or (
            executable is not None
            and bool(observed.st_mode & 0o111) != executable
        )
    ):
        os.close(descriptor)
        fail("required regular-file metadata is unsafe")
    return descriptor, observed


def read_descriptor(descriptor: int, maximum: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    payload = bytearray()
    while len(payload) <= maximum:
        chunk = os.read(descriptor, maximum + 1 - len(payload))
        if not chunk:
            break
        payload.extend(chunk)
    if len(payload) > maximum:
        fail("regular file exceeds size policy")
    return bytes(payload)


def sha256_descriptor(descriptor: int) -> str:
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            return digest.hexdigest()
        digest.update(chunk)


def sha256_file(path: Path, *, owner: int | None = None) -> str:
    descriptor, before = open_regular(path, owner=owner)
    try:
        digest = sha256_descriptor(descriptor)
        after = os.fstat(descriptor)
        named = path.lstat()
        if (
            file_identity(before) != file_identity(after)
            or file_identity(before) != file_identity(named)
        ):
            fail("regular file changed while being hashed")
        return digest
    finally:
        os.close(descriptor)


def parse_canonical(
    path: Path,
    keys: tuple[str, ...],
    *,
    owner: int,
    mode: int,
    maximum: int = 16384,
) -> OrderedDict[str, str]:
    descriptor, before = open_regular(path, owner=owner, mode=mode)
    try:
        payload = read_descriptor(descriptor, maximum)
        after = os.fstat(descriptor)
        named = path.lstat()
        if (
            file_identity(before) != file_identity(after)
            or file_identity(before) != file_identity(named)
        ):
            fail("canonical record changed while being read")
    finally:
        os.close(descriptor)
    if not payload.endswith(b"\n") or b"\0" in payload or b"\r" in payload:
        fail("canonical record framing changed")
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise RuntimeRootError("canonical record is not ASCII") from error
    if len(lines) != len(keys):
        fail("canonical record field count changed")
    result: OrderedDict[str, str] = OrderedDict()
    for expected, line in zip(keys, lines, strict=True):
        name, separator, value = line.partition("=")
        if separator != "=" or name != expected or not value:
            fail("canonical record fields or ordering changed")
        result[name] = value
    return result


def canonical_bytes(values: OrderedDict[str, str]) -> bytes:
    return "".join(f"{name}={value}\n" for name, value in values.items()).encode(
        "ascii"
    )


def validate_hash(value: str, label: str) -> None:
    if not SHA256.fullmatch(value) or value == "0" * 64:
        fail(f"{label} is not a nonzero SHA-256")


def validate_positive(value: str, label: str) -> None:
    if not value.isascii() or not value.isdecimal() or value.startswith("0"):
        fail(f"{label} is not a canonical positive integer")
    if int(value) <= 0 or int(value) >= 1 << 63:
        fail(f"{label} is outside policy")


def validate_tool_manifest(
    tools: Path,
    owner: int,
    approved_sha256: str,
) -> tuple[OrderedDict[str, str], str]:
    validate_hash(approved_sha256, "approved runtime-tools manifest hash")
    try:
        metadata = tools.lstat()
    except OSError as error:
        raise RuntimeRootError("runtime-tools directory is unavailable") from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != owner
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        fail("runtime-tools directory metadata changed")
    inventory = sorted(entry.name for entry in tools.iterdir())
    if inventory != ["manifest", *sorted(TOOL_NAMES)]:
        fail("runtime-tools directory inventory changed")
    manifest_sha256 = sha256_file(tools / "manifest", owner=owner)
    if manifest_sha256 != approved_sha256:
        fail("runtime-tools manifest is not the approved build")
    values = parse_canonical(
        tools / "manifest",
        TOOL_MANIFEST_KEYS,
        owner=owner,
        mode=0o400,
    )
    if (
        values["format"] != "rog5-a660-runtime-tools-v1"
        or values["source_date_epoch"] != str(EPOCH)
    ):
        fail("runtime-tools manifest identity changed")
    for name in (
        "static_builder_image_id",
        "vulkan_builder_image_id",
        "builder_packages_sha256",
    ):
        validate_hash(values[name], name)
    for filename in TOOL_NAMES:
        prefix = filename.replace("-", "_")
        validate_positive(values[f"{prefix}_size"], f"{filename} size")
        validate_hash(values[f"{prefix}_sha256"], f"{filename} hash")
        descriptor, metadata = open_regular(
            tools / filename,
            owner=owner,
            mode=0o755,
            executable=True,
        )
        try:
            if metadata.st_size != int(values[f"{prefix}_size"]):
                fail(f"{filename} size differs from its build manifest")
            if sha256_descriptor(descriptor) != values[f"{prefix}_sha256"]:
                fail(f"{filename} hash differs from its build manifest")
        finally:
            os.close(descriptor)
    if sha256_file(tools / "manifest", owner=owner) != manifest_sha256:
        fail("runtime-tools manifest changed during validation")
    return values, manifest_sha256


def create_from_descriptor(
    source: int,
    destination: Path,
    *,
    mode: int,
) -> str:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        output = os.open(destination, flags, mode)
    except OSError as error:
        raise RuntimeRootError("runtime-root output already exists") from error
    digest = hashlib.sha256()
    try:
        os.lseek(source, 0, os.SEEK_SET)
        while True:
            payload = os.read(source, 1024 * 1024)
            if not payload:
                break
            digest.update(payload)
            view = memoryview(payload)
            while view:
                written = os.write(output, view)
                if written <= 0:
                    fail("runtime-root copy made no progress")
                view = view[written:]
        os.fchmod(output, mode)
        os.fsync(output)
    finally:
        os.close(output)
    os.utime(destination, ns=(EPOCH * 1_000_000_000,) * 2)
    return digest.hexdigest()


def create_bytes(destination: Path, payload: bytes, mode: int) -> str:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(destination, flags, mode)
    except OSError as error:
        raise RuntimeRootError("runtime-root record already exists") from error
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail("runtime-root record write made no progress")
            view = view[written:]
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.utime(destination, ns=(EPOCH * 1_000_000_000,) * 2)
    return hashlib.sha256(payload).hexdigest()


def verify_base_preservation(
    base_path: Path,
    runtime_path: Path,
    *,
    owner: int,
    root_tool=None,
) -> OrderedDict[str, str]:
    base, base_owner = safe_root(base_path)
    runtime, runtime_owner = safe_root(runtime_path)
    if (
        base_owner != owner
        or runtime_owner != owner
        or base == runtime
        or base.is_relative_to(runtime)
        or runtime.is_relative_to(base)
    ):
        fail("base-preservation roots are unsafe or aliased")
    if root_tool is None:
        root_tool = load_root_tool()

    base_tree = OrderedDict(root_tool.seal_tree(base))
    base_entries = {
        relative: (path, metadata)
        for relative, path, metadata in root_tool.walk_tree(os.fsencode(base))
    }
    runtime_entries = {
        relative: (path, metadata)
        for relative, path, metadata in root_tool.walk_tree(
            os.fsencode(runtime)
        )
    }
    additions = {
        os.fsencode(path.as_posix())
        for _name, (_source, path) in INSTALL_INPUTS.items()
    }
    additions.update(os.fsencode(path.as_posix()) for path in RECORD_PATHS)
    if os.fsencode(BASELINE_PATH.as_posix()) not in base_entries:
        additions.add(os.fsencode(BASELINE_PATH.as_posix()))
    if set(runtime_entries) != set(base_entries) | additions:
        fail("runtime integration changed the base path inventory")

    metadata_delta = {
        os.fsencode(path.as_posix()) for path in BASE_METADATA_DELTA_PATHS
    }
    if os.fsencode(BASELINE_PATH.as_posix()) in additions:
        metadata_delta.add(os.fsencode(BASELINE_PATH.parent.as_posix()))

    for relative, (base_entry, before) in base_entries.items():
        runtime_entry, after = runtime_entries[relative]
        if (
            stat.S_IFMT(before.st_mode) != stat.S_IFMT(after.st_mode)
            or stat.S_IMODE(before.st_mode) != stat.S_IMODE(after.st_mode)
            or before.st_uid != after.st_uid
            or before.st_gid != after.st_gid
            or before.st_nlink != after.st_nlink
            or root_tool.entry_xattrs(base_entry)
            != root_tool.entry_xattrs(runtime_entry)
        ):
            fail("runtime integration changed base entry metadata")
        if relative not in metadata_delta and (
            before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
        ):
            fail("runtime integration changed base entry identity")
        if stat.S_ISREG(before.st_mode):
            if (
                root_tool.file_digest(base_entry, before)
                != root_tool.file_digest(runtime_entry, after)
            ):
                fail("runtime integration changed base file content")
        elif stat.S_ISLNK(before.st_mode):
            if os.readlink(base_entry) != os.readlink(runtime_entry):
                fail("runtime integration changed a base symbolic link")
        elif not stat.S_ISDIR(before.st_mode):
            fail("base tree contains an unsupported entry")
    return base_tree


def command_manifest(root: Path, owner: int) -> tuple[bytes, OrderedDict[str, str]]:
    values: OrderedDict[str, str] = OrderedDict(
        (("format", "rog5-a660-command-manifest-v1"),)
    )
    for name, relative in COMMAND_PATHS.items():
        ensure_ancestors(root, relative, owner)
        descriptor, _metadata = open_regular(
            root / relative,
            owner=owner,
            executable=True,
        )
        try:
            values[f"{name}_sha256"] = sha256_descriptor(descriptor)
        finally:
            os.close(descriptor)
    return canonical_bytes(values), values


def expected_provenance(
    *,
    base_generation: str,
    base_seal_sha256: str,
    base_verifier_sha256: str,
    base_tree_entries: str,
    base_tree_sha256: str,
    base_archive_size: str,
    base_archive_sha256: str,
    kernel_release: str,
    tools_manifest_sha256: str,
    tool_values: OrderedDict[str, str],
    acceptance_sha256: str,
    command_manifest_sha256: str,
) -> OrderedDict[str, str]:
    return OrderedDict(
        (
            ("format", "rog5-a660-runtime-provenance-v1"),
            ("base_generation", base_generation),
            ("base_export_seal_sha256", base_seal_sha256),
            ("base_export_verifier_sha256", base_verifier_sha256),
            ("base_tree_entries", base_tree_entries),
            ("base_tree_sha256", base_tree_sha256),
            ("base_archive_size", base_archive_size),
            ("base_archive_sha256", base_archive_sha256),
            ("kernel_release", kernel_release),
            ("a660_acceptance_sha256", acceptance_sha256),
            ("cgroup_exec_source_sha256", sha256_file(CGROUP_SOURCE)),
            ("vulkan_submit_source_sha256", sha256_file(VULKAN_SOURCE)),
            (
                "persistent_root_verify_source_sha256",
                sha256_file(ROOT_VERIFY_SOURCE),
            ),
            ("runtime_tools_manifest_sha256", tools_manifest_sha256),
            (
                "persistent_root_verify_sha256",
                tool_values["persistent_root_verify_sha256"],
            ),
            (
                "rog5_cgroup_exec_sha256",
                tool_values["rog5_cgroup_exec_sha256"],
            ),
            (
                "rog5_vulkan_submit_sha256",
                tool_values["rog5_vulkan_submit_sha256"],
            ),
            ("command_manifest_sha256", command_manifest_sha256),
        )
    )


def prepare_runtime_root(
    root_path: Path,
    base_path: Path,
    tools_path: Path,
    identity_path: Path,
    *,
    base_generation: str,
    base_seal_sha256: str,
    base_verifier_sha256: str,
    base_archive_size: str,
    base_archive_sha256: str,
    kernel_release: str,
    approved_tools_manifest_sha256: str,
) -> OrderedDict[str, str]:
    validate_hash(base_seal_sha256, "base export seal hash")
    validate_hash(base_verifier_sha256, "base export verifier hash")
    validate_hash(base_archive_sha256, "base archive hash")
    validate_positive(base_archive_size, "base archive size")
    if not SAFE_IDENTITY.fullmatch(kernel_release):
        fail("kernel release is not canonical")
    if base_generation not in BASE_GENERATIONS:
        fail("base generation is outside policy")
    if (
        sha256_file(BASE_VERIFIERS[base_generation])
        != base_verifier_sha256
    ):
        fail("base export verifier identity changed")
    root, owner = safe_root(root_path)
    base, base_owner = safe_root(base_path)
    if (
        base_owner != owner
        or base == root
        or base.is_relative_to(root)
        or root.is_relative_to(base)
    ):
        fail("runtime base root is unsafe or aliased")
    identity_parent = safe_parent(identity_path, owner)
    if identity_path.parent != identity_parent or identity_path.exists():
        fail("identity output path is unsafe or already exists")
    if identity_path.is_relative_to(root):
        fail("identity output cannot be inside the sealed root")

    base_seal_relative = BASE_GENERATIONS[base_generation]
    base_seal = root / base_seal_relative
    ensure_ancestors(root, base_seal_relative, owner)
    if sha256_file(base_seal, owner=owner) != base_seal_sha256:
        fail("base export seal identity changed")
    if (root / ".rog5-persistent-seal").exists():
        fail("runtime root already contains a persistent seal")
    for _name, (_source, relative) in INSTALL_INPUTS.items():
        if (root / relative).exists():
            fail("runtime-root installation target already exists")
        ensure_ancestors(root, relative, owner)
    for relative in RECORD_PATHS:
        if (root / relative).exists():
            fail("runtime-root record target already exists")
        ensure_ancestors(root, relative, owner)
    baseline_relative = BASELINE_PATH
    ensure_ancestors(root, baseline_relative, owner)

    tool_values, tools_manifest_sha256 = validate_tool_manifest(
        tools_path,
        tools_path.lstat().st_uid,
        approved_tools_manifest_sha256,
    )
    root_tool = load_root_tool()
    base_tree = OrderedDict(root_tool.seal_tree(base))
    os.chmod(root, 0o755)
    created_hashes: dict[str, str] = {}
    for name, (source_name, relative) in INSTALL_INPUTS.items():
        source = source_name if name == "acceptance" else tools_path / source_name
        descriptor, before = open_regular(source, executable=True)
        try:
            created_hashes[name] = create_from_descriptor(
                descriptor,
                root / relative,
                mode=0o755,
            )
            after = os.fstat(descriptor)
            named = source.lstat()
            if (
                file_identity(before) != file_identity(after)
                or file_identity(before) != file_identity(named)
            ):
                fail("runtime-root source changed while being copied")
        finally:
            os.close(descriptor)

    if created_hashes["acceptance"] != sha256_file(HARNESS_SOURCE):
        fail("installed A660 acceptance harness changed")
    for name, manifest_name in (
        ("runner", "rog5_cgroup_exec_sha256"),
        ("submit", "rog5_vulkan_submit_sha256"),
        ("root_verify", "persistent_root_verify_sha256"),
    ):
        if created_hashes[name] != tool_values[manifest_name]:
            fail("installed A660 runtime tool changed")
    baseline_source_sha256 = sha256_file(BASELINE_SOURCE)
    baseline_target = root / baseline_relative
    baseline_added = False
    if baseline_target.exists():
        if sha256_file(baseline_target, owner=owner) != baseline_source_sha256:
            fail("existing baseline collector differs from the reviewed source")
    else:
        baseline_added = True
        descriptor, before = open_regular(
            BASELINE_SOURCE,
            executable=True,
        )
        try:
            if (
                create_from_descriptor(
                    descriptor,
                    baseline_target,
                    mode=0o755,
                )
                != baseline_source_sha256
            ):
                fail("installed baseline collector changed")
            if file_identity(before) != file_identity(os.fstat(descriptor)):
                fail("baseline collector changed while being copied")
        finally:
            os.close(descriptor)

    tools_manifest_payload = (tools_path / "manifest").read_bytes()
    installed_tools_manifest_sha256 = create_bytes(
        root / "etc/rog5/a660-runtime-tools.manifest",
        tools_manifest_payload,
        0o444,
    )
    if installed_tools_manifest_sha256 != tools_manifest_sha256:
        fail("installed runtime-tools manifest changed")

    command_payload, _command_values = command_manifest(root, owner)
    command_manifest_sha256 = create_bytes(
        root / "etc/rog5/a660-command-manifest",
        command_payload,
        0o400,
    )
    provenance_values = expected_provenance(
        base_generation=base_generation,
        base_seal_sha256=base_seal_sha256,
        base_verifier_sha256=base_verifier_sha256,
        base_tree_entries=base_tree["tree_entries"],
        base_tree_sha256=base_tree["tree_sha256"],
        base_archive_size=base_archive_size,
        base_archive_sha256=base_archive_sha256,
        kernel_release=kernel_release,
        tools_manifest_sha256=tools_manifest_sha256,
        tool_values=tool_values,
        acceptance_sha256=created_hashes["acceptance"],
        command_manifest_sha256=command_manifest_sha256,
    )
    provenance_payload = canonical_bytes(provenance_values)
    provenance_sha256 = create_bytes(
        root / "etc/rog5/a660-runtime-provenance",
        provenance_payload,
        0o444,
    )

    seal = root / ".rog5-persistent-seal"
    create_bytes(seal, b"", 0o600)
    touched_directories = {
        root,
        root / "etc/rog5",
        root / "usr/local/libexec",
        root / "usr/local/sbin",
    }
    if baseline_added:
        touched_directories.add(root / BASELINE_PATH.parent)
    os.chmod(root, 0o555)
    for directory in touched_directories:
        os.utime(directory, ns=(EPOCH * 1_000_000_000,) * 2)

    preserved_tree = verify_base_preservation(
        base,
        root,
        owner=owner,
        root_tool=root_tool,
    )
    if preserved_tree != base_tree:
        fail("base tree changed during runtime integration")
    tree = root_tool.seal_tree(root)
    seal_values = OrderedDict(
        (
            ("seal_format", "rog5-persistent-root-v1"),
            ("generation", "arch-a"),
            ("source_archive_size", base_archive_size),
            ("source_archive_sha256", base_archive_sha256),
            ("promotion_state", "UNBOOTED"),
            *((name, tree[name]) for name in root_tool.TREE_KEYS),
        )
    )
    seal_payload = canonical_bytes(seal_values)
    descriptor = os.open(seal, os.O_WRONLY | os.O_TRUNC | os.O_CLOEXEC)
    try:
        view = memoryview(seal_payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail("persistent-seal write made no progress")
            view = view[written:]
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.utime(seal, ns=(EPOCH * 1_000_000_000,) * 2)
    root_tool.verify_tree(root, seal)
    seal_sha256 = hashlib.sha256(seal_payload).hexdigest()

    identity_values = OrderedDict(
        (
            ("format", "rog5-a660-runtime-root-v1"),
            ("profile", "network-root-v1"),
            ("root_generation", "arch-a"),
            ("root_subtree", "/"),
            ("kernel_release", kernel_release),
            ("base_generation", base_generation),
            ("base_export_seal_sha256", base_seal_sha256),
            ("base_export_verifier_sha256", base_verifier_sha256),
            ("base_tree_entries", base_tree["tree_entries"]),
            ("base_tree_sha256", base_tree["tree_sha256"]),
            ("runtime_provenance_sha256", provenance_sha256),
            ("a660_acceptance_sha256", created_hashes["acceptance"]),
            ("command_manifest_sha256", command_manifest_sha256),
            (
                "persistent_root_verify_sha256",
                created_hashes["root_verify"],
            ),
            ("rog5_cgroup_exec_sha256", created_hashes["runner"]),
            ("rog5_vulkan_submit_sha256", created_hashes["submit"]),
            ("root_tree_entries", tree["tree_entries"]),
            ("root_tree_sha256", tree["tree_sha256"]),
            ("root_seal_sha256", seal_sha256),
        )
    )
    create_bytes(identity_path, canonical_bytes(identity_values), 0o444)
    return identity_values


def inspect_elf(path: Path, kind: str) -> None:
    try:
        header = subprocess.run(
            ["readelf", "-h", str(path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout
        program = subprocess.run(
            ["readelf", "-l", str(path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout
        dynamic = subprocess.run(
            ["readelf", "-d", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeRootError("cannot inspect A660 runtime ELF") from error
    if not re.search(r"Machine:\s+AArch64\s*$", header, re.MULTILINE):
        fail(f"{kind} is not AArch64")
    if kind in {"runner", "root verifier"}:
        if "Requesting program interpreter" in program or "Shared library:" in dynamic:
            fail(f"{kind} is not static")
    else:
        if (
            "Requesting program interpreter: /lib/ld-linux-aarch64.so.1"
            not in program
            or "Shared library: [libvulkan.so.1]" not in dynamic
            or "(RPATH)" in dynamic
            or "(RUNPATH)" in dynamic
        ):
            fail("Vulkan submit helper dynamic contract changed")


def run_independent_verifier(
    root: Path,
    verifier: Path,
    seal: Path,
    seal_sha256: str,
    entries: str,
    tree_sha256: str,
) -> None:
    try:
        result = subprocess.run(
            [
                "qemu-aarch64-static",
                str(verifier),
                str(root),
                str(seal),
                seal_sha256,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeRootError(
            "cannot execute the independent AArch64 root verifier"
        ) from error
    expected = (
        "PASS persistent root matches anchored seal "
        f"entries={entries} tree_sha256={tree_sha256}\n"
    )
    if result.returncode != 0 or result.stdout != expected or result.stderr:
        fail("independent AArch64 root verification failed")


def verify_runtime_root(
    root_path: Path,
    identity_path: Path,
    *,
    inspect_elf_files: bool = True,
    independent_verification: bool = True,
) -> OrderedDict[str, str]:
    root, owner = safe_root(root_path)
    if stat.S_IMODE(root.lstat().st_mode) != 0o555:
        fail("sealed runtime-root mode changed")
    identity = parse_canonical(
        identity_path,
        IDENTITY_KEYS,
        owner=owner,
        mode=0o444,
    )
    if (
        identity["format"] != "rog5-a660-runtime-root-v1"
        or identity["profile"] != "network-root-v1"
        or identity["root_generation"] != "arch-a"
        or identity["root_subtree"] != "/"
        or not SAFE_IDENTITY.fullmatch(identity["kernel_release"])
        or identity["base_generation"] not in BASE_GENERATIONS
    ):
        fail("runtime-root identity changed")
    for name in IDENTITY_KEYS:
        if name.endswith("_sha256"):
            validate_hash(identity[name], name)
    validate_positive(identity["root_tree_entries"], "root tree entries")
    validate_positive(identity["base_tree_entries"], "base tree entries")

    base_seal = root / BASE_GENERATIONS[identity["base_generation"]]
    if sha256_file(base_seal, owner=owner) != identity["base_export_seal_sha256"]:
        fail("runtime-root base export seal changed")
    tools_manifest = parse_canonical(
        root / "etc/rog5/a660-runtime-tools.manifest",
        TOOL_MANIFEST_KEYS,
        owner=owner,
        mode=0o444,
    )
    if tools_manifest["format"] != "rog5-a660-runtime-tools-v1":
        fail("installed runtime-tools manifest identity changed")
    command_payload, command_values = command_manifest(root, owner)
    if (
        hashlib.sha256(command_payload).hexdigest()
        != identity["command_manifest_sha256"]
    ):
        fail("runtime command-manifest identity changed")
    installed_command = root / "etc/rog5/a660-command-manifest"
    descriptor, before = open_regular(
        installed_command,
        owner=owner,
        mode=0o400,
    )
    try:
        if read_descriptor(descriptor, 4096) != command_payload:
            fail("runtime command manifest is not canonical")
        if file_identity(before) != file_identity(os.fstat(descriptor)):
            fail("runtime command manifest changed while being read")
    finally:
        os.close(descriptor)

    installed_hashes = {
        "acceptance": sha256_file(
            root / "usr/local/sbin/rog5-a660-acceptance",
            owner=owner,
        ),
        "persistent_root_verify": sha256_file(
            root / "usr/local/sbin/persistent-root-verify",
            owner=owner,
        ),
        "rog5_cgroup_exec": sha256_file(
            root / "usr/local/libexec/rog5-cgroup-exec",
            owner=owner,
        ),
        "rog5_vulkan_submit": sha256_file(
            root / "usr/local/libexec/rog5-vulkan-submit",
            owner=owner,
        ),
    }
    for identity_name, installed_name in (
        ("a660_acceptance_sha256", "acceptance"),
        ("persistent_root_verify_sha256", "persistent_root_verify"),
        ("rog5_cgroup_exec_sha256", "rog5_cgroup_exec"),
        ("rog5_vulkan_submit_sha256", "rog5_vulkan_submit"),
    ):
        if identity[identity_name] != installed_hashes[installed_name]:
            fail("installed A660 runtime file changed")
    if installed_hashes["acceptance"] != sha256_file(HARNESS_SOURCE):
        fail("installed A660 acceptance source differs from the repository")
    for manifest_name in (
        "persistent_root_verify_sha256",
        "rog5_cgroup_exec_sha256",
        "rog5_vulkan_submit_sha256",
    ):
        if tools_manifest[manifest_name] != identity[manifest_name]:
            fail("runtime-tools manifest and root identity disagree")
    if command_values["runner_sha256"] != identity["rog5_cgroup_exec_sha256"]:
        fail("command manifest does not bind the cgroup executor")
    if command_values["submit_sha256"] != identity["rog5_vulkan_submit_sha256"]:
        fail("command manifest does not bind the Vulkan helper")
    if (
        command_values["root_verify_sha256"]
        != identity["persistent_root_verify_sha256"]
    ):
        fail("command manifest does not bind the root verifier")

    provenance = parse_canonical(
        root / "etc/rog5/a660-runtime-provenance",
        PROVENANCE_KEYS,
        owner=owner,
        mode=0o444,
    )
    provenance_payload = canonical_bytes(provenance)
    if (
        hashlib.sha256(provenance_payload).hexdigest()
        != identity["runtime_provenance_sha256"]
        or provenance["format"] != "rog5-a660-runtime-provenance-v1"
        or provenance["base_generation"] != identity["base_generation"]
        or provenance["base_export_seal_sha256"]
        != identity["base_export_seal_sha256"]
        or provenance["base_export_verifier_sha256"]
        != identity["base_export_verifier_sha256"]
        or provenance["base_tree_entries"] != identity["base_tree_entries"]
        or provenance["base_tree_sha256"] != identity["base_tree_sha256"]
        or provenance["kernel_release"] != identity["kernel_release"]
        or provenance["a660_acceptance_sha256"]
        != identity["a660_acceptance_sha256"]
        or provenance["command_manifest_sha256"]
        != identity["command_manifest_sha256"]
    ):
        fail("runtime provenance and root identity disagree")
    for name in (
        "persistent_root_verify_sha256",
        "rog5_cgroup_exec_sha256",
        "rog5_vulkan_submit_sha256",
    ):
        if provenance[name] != identity[name]:
            fail("runtime provenance tool identity changed")
    for name in (
        "cgroup_exec_source_sha256",
        "vulkan_submit_source_sha256",
        "persistent_root_verify_source_sha256",
        "runtime_tools_manifest_sha256",
    ):
        validate_hash(provenance[name], name)
    if (
        provenance["cgroup_exec_source_sha256"] != sha256_file(CGROUP_SOURCE)
        or provenance["vulkan_submit_source_sha256"] != sha256_file(VULKAN_SOURCE)
        or provenance["persistent_root_verify_source_sha256"]
        != sha256_file(ROOT_VERIFY_SOURCE)
        or provenance["base_export_verifier_sha256"]
        != sha256_file(BASE_VERIFIERS[identity["base_generation"]])
        or provenance["runtime_tools_manifest_sha256"]
        != hashlib.sha256(canonical_bytes(tools_manifest)).hexdigest()
    ):
        fail("runtime provenance source identity changed")

    seal = root / ".rog5-persistent-seal"
    if sha256_file(seal, owner=owner) != identity["root_seal_sha256"]:
        fail("runtime-root seal identity changed")
    root_tool = load_root_tool()
    seal_values = root_tool.read_seal(seal)
    if (
        seal_values["generation"] != "arch-a"
        or seal_values["promotion_state"] != "UNBOOTED"
        or seal_values["tree_entries"] != identity["root_tree_entries"]
        or seal_values["tree_sha256"] != identity["root_tree_sha256"]
    ):
        fail("runtime-root seal and identity disagree")
    root_tool.verify_tree(root, seal)

    if inspect_elf_files:
        inspect_elf(root / "usr/local/libexec/rog5-cgroup-exec", "runner")
        inspect_elf(
            root / "usr/local/sbin/persistent-root-verify",
            "root verifier",
        )
        inspect_elf(
            root / "usr/local/libexec/rog5-vulkan-submit",
            "Vulkan helper",
        )
    if independent_verification:
        run_independent_verifier(
            root,
            root / "usr/local/sbin/persistent-root-verify",
            seal,
            identity["root_seal_sha256"],
            identity["root_tree_entries"],
            identity["root_tree_sha256"],
        )
    return identity


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
    )
    subparsers = result.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", allow_abbrev=False)
    prepare.add_argument("--root", required=True, type=Path)
    prepare.add_argument("--base-root", required=True, type=Path)
    prepare.add_argument("--tools", required=True, type=Path)
    prepare.add_argument("--identity", required=True, type=Path)
    prepare.add_argument("--base-seal-sha256", required=True)
    prepare.add_argument("--base-verifier-sha256", required=True)
    prepare.add_argument("--base-archive-size", required=True)
    prepare.add_argument("--base-archive-sha256", required=True)
    prepare.add_argument("--kernel-release", required=True)
    prepare.add_argument("--approved-tools-manifest-sha256", required=True)
    prepare.add_argument(
        "--base-generation",
        required=True,
        choices=tuple(BASE_GENERATIONS),
    )
    verify = subparsers.add_parser("verify", allow_abbrev=False)
    verify.add_argument("--root", required=True, type=Path)
    verify.add_argument("--identity", required=True, type=Path)
    return result


def main(arguments: list[str] | None = None) -> int:
    os.umask(0o077)
    values = parser().parse_args(arguments)
    try:
        if values.command == "prepare":
            identity = prepare_runtime_root(
                values.root,
                values.base_root,
                values.tools,
                values.identity,
                base_generation=values.base_generation,
                base_seal_sha256=values.base_seal_sha256,
                base_verifier_sha256=values.base_verifier_sha256,
                base_archive_size=values.base_archive_size,
                base_archive_sha256=values.base_archive_sha256,
                kernel_release=values.kernel_release,
                approved_tools_manifest_sha256=(
                    values.approved_tools_manifest_sha256
                ),
            )
            print("format=rog5-a660-runtime-root-preparation-v1")
        else:
            identity = verify_runtime_root(values.root, values.identity)
            print("format=rog5-a660-runtime-root-verification-v1")
        print(f"root_generation={identity['root_generation']}")
        print(
            "command_manifest_sha256="
            f"{identity['command_manifest_sha256']}"
        )
        print(f"root_tree_entries={identity['root_tree_entries']}")
        print(f"root_tree_sha256={identity['root_tree_sha256']}")
        print(f"root_seal_sha256={identity['root_seal_sha256']}")
        return 0
    except RuntimeRootError as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    except OSError:
        print("FAIL runtime-root filesystem operation failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
