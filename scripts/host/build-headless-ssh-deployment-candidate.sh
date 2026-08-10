#!/usr/bin/env -S -i /usr/bin/python3 -I -S
"""Launch one exact SSH deployment build across a clean credential boundary."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile


GIT_ENV = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_OPTIONAL_LOCKS": "0",
}
F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
REQUIRED_SEALS = (
    getattr(fcntl, "F_SEAL_SEAL", 0x0001)
    | getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
    | getattr(fcntl, "F_SEAL_GROW", 0x0004)
    | getattr(fcntl, "F_SEAL_WRITE", 0x0008)
)
IMPLEMENTATION_REPOSITORY_PATH = (
    "scripts/host/build-corrected-headless-candidate-offline-impl.sh"
)
CHECKPOINT_INPUTS = (
    (
        "artifacts/network-root-v1/Image-7.1.4-network-root",
        40049152,
        0o755,
        "349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf",
    ),
    (
        "artifacts/headless-network-root-v1/rog5-headless-network-root-initramfs.cpio.gz",
        5978369,
        0o644,
        "819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5",
    ),
    (
        "artifacts/recovery-inputs-v18r/rog5-recovery-base-v18r.cpio.gz",
        5838975,
        0o644,
        "da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d",
    ),
    (
        "artifacts/recovery-inputs/kexec-tools-2.0.32-r2.apk",
        80911,
        0o644,
        "bd8b6951f862af1123972b521c355c655b7a2f40c2bf9cfe700edd590a101c94",
    ),
    (
        "artifacts/recovery-inputs/xz-libs-5.8.3-r0.apk",
        118819,
        0o644,
        "76dce86852903fef7adba0285d816e5ce9ffbe9fb3ca86bbb349b97afaba1f63",
    ),
    (
        "artifacts/recovery-inputs/zstd-libs-1.5.7-r2.apk",
        365383,
        0o644,
        "2bb5136c89f5b0bbe1554c8915a3b520d5aa63ae2a51d4d821eb81698db5a818",
    ),
    (
        "artifacts/host-tools/qemu-aarch64-static",
        6245816,
        0o755,
        "bfcd46c842441912baed36158569ac29a7fb656684ca73c1b3b2f0f3971e9bec",
    ),
    (
        "artifacts/android-boot-tools-v1/mkbootimg.py",
        27333,
        0o755,
        "d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a",
    ),
    (
        "artifacts/android-boot-tools-v1/unpack_bootimg.py",
        23786,
        0o755,
        "7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef",
    ),
    (
        "artifacts/android-boot-tools-v1/avbtool.py",
        247851,
        0o755,
        "6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff",
    ),
    (
        "artifacts/recovery-wrapper-inputs-v1/rog5-canonical-boot-v3-template.raw.img",
        12288,
        0o644,
        "95be17d48ec61d00a4e8c92be754c8a8345f93685ce05d412a6d3a6aceba6e02",
    ),
)


def git_output(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        [
            "/usr/bin/git",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(repository),
            *arguments,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=GIT_ENV,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit("FAIL cannot verify the deployment-launcher checkpoint")
    return result.stdout.strip()


def git_bytes(repository: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        [
            "/usr/bin/git",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(repository),
            *arguments,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=GIT_ENV,
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit("FAIL cannot read the deployment implementation blob")
    return result.stdout


def sealed_implementation(
    repository: Path,
    implementation: Path,
    checkpoint: str,
) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    source = os.open(implementation, flags)
    sealed = -1
    try:
        before = os.fstat(source)
        expected = git_bytes(
            repository,
            "show",
            f"{checkpoint}:{IMPLEMENTATION_REPOSITORY_PATH}",
        )
        payload = bytearray()
        while True:
            block = os.read(source, 1024 * 1024)
            if not block:
                break
            payload.extend(block)
        after = os.fstat(source)
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or bytes(payload) != expected
        ):
            raise SystemExit(
                "FAIL deployment implementation differs from reviewed checkpoint"
            )
        sealed = os.memfd_create(
            "rog5-deployment-builder",
            os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
        view = memoryview(payload)
        while view:
            written = os.write(sealed, view)
            if written <= 0:
                raise SystemExit("FAIL deployment implementation snapshot stalled")
            view = view[written:]
        os.fchmod(sealed, 0o555)
        fcntl.fcntl(sealed, F_ADD_SEALS, REQUIRED_SEALS)
        if fcntl.fcntl(sealed, F_GET_SEALS) & REQUIRED_SEALS != REQUIRED_SEALS:
            raise SystemExit("FAIL deployment implementation snapshot is unsealed")
        os.set_inheritable(sealed, True)
        return sealed
    except BaseException:
        if sealed >= 0:
            os.close(sealed)
        raise
    finally:
        os.close(source)


def metadata_identity(metadata: os.stat_result) -> tuple[int, ...]:
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


def stage_checkpoint_inputs(
    repository: Path,
    snapshot: Path,
    contracts=CHECKPOINT_INPUTS,
) -> None:
    reviewed: list[tuple[Path, int, int, str]] = []
    names: set[str] = set()
    for contract in contracts:
        if not isinstance(contract, tuple) or len(contract) != 4:
            raise SystemExit("FAIL deployment checkpoint input contract is invalid")
        relative, size, mode, digest = contract
        if not isinstance(relative, str):
            raise SystemExit("FAIL deployment checkpoint input path is invalid")
        relative_path = Path(relative)
        if (
            not relative
            or relative_path.is_absolute()
            or relative_path.as_posix() != relative
            or any(part in ("", ".", "..") for part in relative_path.parts)
            or relative in names
        ):
            raise SystemExit("FAIL deployment checkpoint input path is invalid")
        if (
            not isinstance(size, int)
            or isinstance(size, bool)
            or size < 1
            or size > 512 * 1024 * 1024
            or mode not in (0o644, 0o755)
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise SystemExit("FAIL deployment checkpoint input identity is invalid")
        names.add(relative)
        reviewed.append((relative_path, size, mode, digest))

    for relative, size, mode, digest in reviewed:
        source = repository / relative
        destination = snapshot / relative
        try:
            if source.resolve(strict=True) != source:
                raise SystemExit(
                    f"FAIL deployment checkpoint input is aliased: {relative}"
                )
        except OSError as error:
            raise SystemExit(
                f"FAIL deployment checkpoint input is unavailable: {relative}"
            ) from error

        parent = snapshot
        for part in relative.parent.parts:
            parent /= part
            try:
                parent.mkdir(mode=0o755)
            except FileExistsError:
                pass
            metadata = parent.lstat()
            if (
                parent.resolve(strict=True) != parent
                or stat.S_ISLNK(metadata.st_mode)
                or not stat.S_ISDIR(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or metadata.st_gid != os.getegid()
                or stat.S_IMODE(metadata.st_mode) & 0o022
            ):
                raise SystemExit(
                    "FAIL deployment checkpoint input parent is unsafe"
                )
        git_output(snapshot, "check-ignore", "-q", str(destination))

        source_flags = os.O_RDONLY | os.O_CLOEXEC
        destination_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            source_flags |= os.O_NOFOLLOW
            destination_flags |= os.O_NOFOLLOW
        try:
            source_fd = os.open(source, source_flags)
        except OSError as error:
            raise SystemExit(
                f"FAIL deployment checkpoint input is unavailable: {relative}"
            ) from error
        destination_fd = -1
        created: os.stat_result | None = None
        try:
            before = os.fstat(source_fd)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.geteuid()
                or before.st_gid != os.getegid()
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) != mode
                or before.st_size != size
            ):
                raise SystemExit(
                    f"FAIL deployment checkpoint input metadata changed: {relative}"
                )
            try:
                destination_fd = os.open(destination, destination_flags, mode)
            except OSError as error:
                raise SystemExit(
                    "FAIL deployment checkpoint input output is occupied"
                ) from error
            created = os.fstat(destination_fd)
            hasher = hashlib.sha256()
            copied = 0
            while True:
                block = os.read(source_fd, 1024 * 1024)
                if not block:
                    break
                copied += len(block)
                if copied > size:
                    raise SystemExit(
                        f"FAIL deployment checkpoint input size changed: {relative}"
                    )
                hasher.update(block)
                view = memoryview(block)
                while view:
                    written = os.write(destination_fd, view)
                    if written <= 0:
                        raise SystemExit(
                            "FAIL deployment checkpoint input copy stalled"
                        )
                    view = view[written:]
            after = os.fstat(source_fd)
            if (
                copied != size
                or hasher.hexdigest() != digest
                or metadata_identity(before) != metadata_identity(after)
            ):
                raise SystemExit(
                    f"FAIL deployment checkpoint input identity changed: {relative}"
                )
            os.fchmod(destination_fd, mode)
            os.fsync(destination_fd)
            output = os.fstat(destination_fd)
            named = destination.lstat()
            if (
                metadata_identity(output) != metadata_identity(named)
                or not stat.S_ISREG(output.st_mode)
                or output.st_uid != os.geteuid()
                or output.st_gid != os.getegid()
                or output.st_nlink != 1
                or stat.S_IMODE(output.st_mode) != mode
                or output.st_size != size
            ):
                raise SystemExit(
                    "FAIL deployment checkpoint input output is unsafe"
                )
        except BaseException:
            if destination_fd >= 0:
                os.close(destination_fd)
                destination_fd = -1
            if created is not None:
                try:
                    named = destination.lstat()
                    if (
                        named.st_dev == created.st_dev
                        and named.st_ino == created.st_ino
                        and stat.S_ISREG(named.st_mode)
                    ):
                        destination.unlink()
                except FileNotFoundError:
                    pass
            raise
        finally:
            os.close(source_fd)
            if destination_fd >= 0:
                os.close(destination_fd)

    if git_output(snapshot, "status", "--porcelain", "--untracked-files=all"):
        raise SystemExit("FAIL checkpoint inputs changed reviewed Git state")


def remove_checkpoint_worktree(repository: Path, snapshot: Path) -> None:
    subprocess.run(
        [
            "/usr/bin/git",
            "-C",
            str(repository),
            "worktree",
            "remove",
            "--force",
            str(snapshot),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=GIT_ENV,
        timeout=15,
        check=False,
    )


def checkpoint_worktree(repository: Path, checkpoint: str) -> Path:
    build_root = repository / "build"
    build_root.mkdir(mode=0o700, exist_ok=True)
    metadata = build_root.lstat()
    if (
        build_root.resolve(strict=True) != build_root
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or metadata.st_gid != os.getegid()
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        raise SystemExit("FAIL deployment checkpoint parent is unsafe")
    git_output(repository, "check-ignore", "-q", str(build_root))
    reserved = Path(
        tempfile.mkdtemp(prefix=".rog5-reviewed-checkpoint-", dir=build_root)
    )
    reserved.rmdir()
    try:
        git_output(
            repository,
            "worktree",
            "add",
            "--detach",
            str(reserved),
            checkpoint,
        )
        reserved.chmod(0o700)
        if (
            git_output(reserved, "rev-parse", "HEAD") != checkpoint
            or git_output(
                reserved,
                "status",
                "--porcelain",
                "--untracked-files=all",
            )
        ):
            raise SystemExit("FAIL deployment checkpoint worktree is not exact")
        return reserved
    except BaseException:
        remove_checkpoint_worktree(repository, reserved)
        raise


def verified_implementation(
    stage_inputs: bool = False,
) -> tuple[Path, Path, str, int]:
    lexical = Path(os.path.abspath(__file__))
    resolved = lexical.resolve(strict=True)
    repository = resolved.parents[2]
    implementation = resolved.with_name(
        "build-corrected-headless-candidate-offline-impl.sh"
    )
    for path, expected_type in (
        (repository, stat.S_ISDIR),
        (repository / "scripts", stat.S_ISDIR),
        (resolved.parent, stat.S_ISDIR),
        (resolved, stat.S_ISREG),
        (implementation, stat.S_ISREG),
    ):
        metadata = path.lstat()
        if (
            path.resolve(strict=True) != path
            or stat.S_ISLNK(metadata.st_mode)
            or not expected_type(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_gid != os.getegid()
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            raise SystemExit("FAIL deployment-launcher filesystem metadata is unsafe")
    if git_output(repository, "status", "--porcelain", "--untracked-files=all"):
        raise SystemExit("FAIL repository must be clean before deployment signing")
    branch = git_output(repository, "branch", "--show-current")
    upstream = git_output(
        repository,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    )
    if not branch or upstream != f"origin/{branch}":
        raise SystemExit("FAIL deployment-signing branch has no exact origin peer")
    git_output(
        repository,
        "fetch",
        "--no-tags",
        "--prune",
        "origin",
        f"refs/heads/{branch}:refs/remotes/origin/{branch}",
    )
    checkpoint = git_output(repository, "rev-parse", "HEAD")
    if checkpoint != git_output(repository, "rev-parse", upstream):
        raise SystemExit("FAIL deployment-signing checkpoint differs from origin")
    implementation_fd = sealed_implementation(
        repository,
        implementation,
        checkpoint,
    )
    try:
        snapshot = checkpoint_worktree(repository, checkpoint)
        if stage_inputs:
            stage_checkpoint_inputs(repository, snapshot)
    except BaseException:
        os.close(implementation_fd)
        if "snapshot" in locals():
            remove_checkpoint_worktree(repository, snapshot)
        raise
    return repository, snapshot, checkpoint, implementation_fd


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorize-recovery-deployment-build", action="store_true")
    parser.add_argument("--authorize-phone-credential-use", action="store_true")
    parser.add_argument("--candidate-record", required=True)
    parser.add_argument("--signing-key", required=True)
    parser.add_argument("--signing-input-preflight", action="store_true")
    parser.add_argument("output_root")
    arguments = parser.parse_args()
    if not arguments.authorize_recovery_deployment_build:
        parser.error(
            "set --authorize-recovery-deployment-build for one signed recovery build"
        )
    if not arguments.authorize_phone_credential_use:
        parser.error("set --authorize-phone-credential-use before using the signing key")
    return arguments


def main() -> None:
    arguments = parse_arguments()
    repository, snapshot, checkpoint, implementation_fd = verified_implementation(
        stage_inputs=not arguments.signing_input_preflight,
    )
    environment = {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "ROG5_INTERNAL_REPOSITORY_ROOT": str(snapshot),
        "ROG5_INTERNAL_CHECKPOINT_REPOSITORY_ROOT": str(repository),
        "ROG5_INTERNAL_REPOSITORY_COMMIT": checkpoint,
        "ROG5_INTERNAL_IMPLEMENTATION_SEALED": "1",
        "ALLOW_RECOVERY_DEPLOYMENT_BUILD": "1",
        "ALLOW_PHONE_CREDENTIAL_USE": "1",
        "ROG5_DEPLOYMENT_CANDIDATE_RECORD": arguments.candidate_record,
        "ROG5_DEPLOYMENT_SIGNING_KEY": arguments.signing_key,
        "ROG5_DEPLOYMENT_BUILD": "1",
        "ROG5_DEPLOYMENT_SIGNING_INPUT_PREFLIGHT": (
            "1" if arguments.signing_input_preflight else "0"
        ),
        "ROG5_OFFLINE_CANDIDATE": "headless-ssh-network-root-v3",
        "ROG5_OFFLINE_EXPECTED_DTB": (
            "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46"
        ),
        "ROG5_OFFLINE_EXPECTED_TARGET": "headless-ssh-network-root",
    }
    try:
        os.execve(
            "/usr/bin/bash",
            [
                "/usr/bin/bash",
                "--noprofile",
                "--norc",
                f"/proc/self/fd/{implementation_fd}",
                arguments.output_root,
            ],
            environment,
        )
    except BaseException:
        os.close(implementation_fd)
        remove_checkpoint_worktree(repository, snapshot)
        raise


if __name__ == "__main__":
    main()
