#!/usr/bin/env python3
"""Hostile tests for the two-identity retention-cycle admission review."""

from __future__ import annotations

import copy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
VERIFIER = REPO / "scripts/host/verify-retention-cycle-admission.py"
PROFILE = REPO / "configs/retention-cycles/host-rendezvous-v3-observer-v1.json"
CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"
SEQUENCE_REFERENCE = REPO / "scripts/host/retention-cycle-sequence-reference.py"
TRANSACTION_FIXTURE = REPO / "scripts/host/retention-cycle-transaction.py"
ADAPTER_FIXTURE = REPO / "scripts/host/retention-cycle-adapter.py"
EXECUTOR_CONTRACT = (
    REPO / "scripts/host/retention-cycle-executor-contract.py"
)
EXECUTOR_BOUNDARY = (
    REPO / "scripts/host/retention-cycle-executor-boundary.py"
)
EXECUTOR_RUNTIME = (
    REPO / "scripts/host/retention-cycle-runtime-closure.py"
)
EXECUTOR_DESCRIPTOR_RUNNER = (
    REPO / "scripts/host/retention-cycle-descriptor-execution.py"
)
EXECUTOR_DESCRIPTOR_PROBE = (
    REPO / "scripts/host/retention-cycle-descriptor-probe.py"
)
SPEC = importlib.util.spec_from_file_location(
    "verify_retention_cycle_admission", VERIFIER
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load retention-cycle admission verifier")
ADMISSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADMISSION)
RECOVERY_CMDLINE = ADMISSION.EXPECTED_RECOVERY_CMDLINE


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def align4(payload: bytearray) -> None:
    payload.extend(b"\0" * ((-len(payload)) & 3))


def newc(entries: dict[str, tuple[int, bytes]]) -> bytes:
    archive = bytearray()
    inode = 1
    for name, (mode, payload) in entries.items():
        encoded = name.encode("utf-8") + b"\0"
        fields = (
            inode,
            mode,
            0,
            0,
            1,
            0,
            len(payload),
            0,
            0,
            0,
            0,
            len(encoded),
            0,
        )
        archive.extend(b"070701" + b"".join(f"{value:08x}".encode() for value in fields))
        archive.extend(encoded)
        align4(archive)
        archive.extend(payload)
        align4(archive)
        inode += 1
    trailer = b"TRAILER!!!\0"
    fields = (inode, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, len(trailer), 0)
    archive.extend(b"070701" + b"".join(f"{value:08x}".encode() for value in fields))
    archive.extend(trailer)
    align4(archive)
    return gzip.compress(bytes(archive), compresslevel=9, mtime=0)


def recovery_archive(
    mode: str,
    *,
    inject_kexec: bool = False,
    init_payload: bytes = b"init\n",
    control_payload: bytes = b"control\n",
) -> bytes:
    entries = {
        "init": (stat.S_IFREG | 0o755, init_payload),
        "usr/libexec/rog5-recovery-control": (
            stat.S_IFREG | 0o755,
            control_payload,
        ),
        "etc/rog5/recovery-mode": (
            stat.S_IFREG | 0o444,
            f"{mode}\n".encode("ascii"),
        ),
        "etc/rog5/shared-contract": (
            stat.S_IFREG | 0o444,
            b"shared\n",
        ),
    }
    if mode == "full-v1" or inject_kexec:
        entries.update(
            {
                "usr/libexec/rog5-bundle-fetch": (
                    stat.S_IFREG | 0o755,
                    b"fetch\n",
                ),
                "usr/libexec/rog5-bundle-verify": (
                    stat.S_IFREG | 0o755,
                    b"verify\n",
                ),
                "etc/rog5/recovery-bundle-ed25519.pub": (
                    stat.S_IFREG | 0o444,
                    b"K" * 32,
                ),
                "usr/sbin/kexec": (stat.S_IFREG | 0o755, b"kexec\n"),
            }
        )
    return newc(entries)


def fake_avb(raw: bytes, *, algorithm: int = 0) -> bytes:
    salt = hashlib.sha256(raw).digest()
    recorded_digest = hashlib.sha256(salt + raw).digest()
    descriptor = struct.pack(
        "!QQQ32sLLLL60s",
        2,
        184,
        len(raw),
        b"sha256",
        4,
        32,
        32,
        0,
        b"\0" * 60,
    ) + b"boot" + salt + recorded_digest
    auxiliary = descriptor + b"\0" * (256 - len(descriptor))
    header = bytearray(256)
    header[:4] = b"AVB0"
    struct.pack_into("!2I", header, 4, 1, 0)
    struct.pack_into("!2Q", header, 12, 0, len(auxiliary))
    struct.pack_into("!I", header, 28, algorithm)
    struct.pack_into("!2Q", header, 64, len(descriptor), 0)
    struct.pack_into("!2Q", header, 80, len(descriptor), 0)
    struct.pack_into("!2Q", header, 96, 0, len(descriptor))
    header[128 : 128 + len(b"avbtool 1.4.0")] = b"avbtool 1.4.0"
    vbmeta = bytes(header) + auxiliary
    footer = struct.pack(
        "!4s2I3Q28x",
        b"AVBf",
        1,
        0,
        len(raw),
        len(raw),
        len(vbmeta),
    )
    return raw + vbmeta + footer


def fake_boot_v3(kernel: bytes, ramdisk: bytes) -> bytes:
    page = 4096
    header = bytearray(page)
    header[:8] = b"ANDROID!"
    struct.pack_into("<4I", header, 8, len(kernel), len(ramdisk), 0, 1580)
    struct.pack_into("<I", header, 40, 3)
    command_line = RECOVERY_CMDLINE.encode("ascii")
    header[44 : 44 + len(command_line)] = command_line
    payload = bytearray(header)
    payload.extend(kernel)
    payload.extend(b"\0" * ((-len(kernel)) & (page - 1)))
    payload.extend(ramdisk)
    payload.extend(b"\0" * ((-len(ramdisk)) & (page - 1)))
    return bytes(payload)


class RetentionCycleAdmissionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.reset_fixture()

    def reset_fixture(self) -> None:
        self.repo = self.base / "repo"
        self.execution = self.base / "execution"
        self.observer = self.base / "observer"
        for directory in (self.repo, self.execution, self.observer):
            shutil.rmtree(directory, ignore_errors=True)
        for directory in (self.repo, self.execution, self.observer):
            directory.mkdir(mode=0o700)
        self.profile = copy.deepcopy(
            json.loads(PROFILE.read_text(encoding="utf-8"))
        )
        self.profile_path = self.base / "profile.json"
        self.artifacts_path = self.repo / "manifests/artifacts.tsv"
        self.policy_path = self.repo / "manifests/temporary-boot-images.tsv"
        self.consumer = self.repo / "scripts/host/consume-exact-boot-claim.py"
        self.consumer.parent.mkdir(parents=True)
        self.consumer.write_bytes(CONSUMER.read_bytes())
        self.consumer.chmod(0o755)
        sequence_reference_record = self.profile["claims"]["sequence_reference"]
        assert isinstance(sequence_reference_record, dict)
        self.sequence_reference = self.repo / str(
            sequence_reference_record["path"]
        )
        self.sequence_reference.parent.mkdir(parents=True, exist_ok=True)
        self.sequence_reference.write_bytes(SEQUENCE_REFERENCE.read_bytes())
        self.sequence_reference.chmod(0o755)
        transaction_record = self.profile["claims"]["transaction_fixture"]
        assert isinstance(transaction_record, dict)
        self.transaction_fixture = self.repo / str(
            transaction_record["path"]
        )
        self.transaction_fixture.parent.mkdir(parents=True, exist_ok=True)
        self.transaction_fixture.write_bytes(TRANSACTION_FIXTURE.read_bytes())
        self.transaction_fixture.chmod(0o644)
        adapter_record = self.profile["claims"]["adapter_fixture"]
        assert isinstance(adapter_record, dict)
        self.adapter_fixture = self.repo / str(adapter_record["path"])
        self.adapter_fixture.parent.mkdir(parents=True, exist_ok=True)
        self.adapter_fixture.write_bytes(ADAPTER_FIXTURE.read_bytes())
        self.adapter_fixture.chmod(0o644)
        executor_record = self.profile["claims"]["executor_contract"]
        assert isinstance(executor_record, dict)
        self.executor_contract = self.repo / str(executor_record["path"])
        self.executor_contract.parent.mkdir(parents=True, exist_ok=True)
        self.executor_contract.write_bytes(EXECUTOR_CONTRACT.read_bytes())
        self.executor_contract.chmod(0o644)
        boundary_record = self.profile["claims"]["executor_boundary"]
        assert isinstance(boundary_record, dict)
        self.executor_boundary = self.repo / str(boundary_record["path"])
        self.executor_boundary.parent.mkdir(parents=True, exist_ok=True)
        self.executor_boundary.write_bytes(EXECUTOR_BOUNDARY.read_bytes())
        self.executor_boundary.chmod(0o644)
        runtime_record = self.profile["claims"]["executor_runtime"]
        assert isinstance(runtime_record, dict)
        self.executor_runtime = self.repo / str(runtime_record["path"])
        self.executor_runtime.parent.mkdir(parents=True, exist_ok=True)
        self.executor_runtime.write_bytes(EXECUTOR_RUNTIME.read_bytes())
        self.executor_runtime.chmod(0o644)
        descriptor_record = self.profile["claims"][
            "executor_descriptor_fixture"
        ]
        assert isinstance(descriptor_record, dict)
        self.executor_descriptor_runner = self.repo / str(
            descriptor_record["runner_path"]
        )
        self.executor_descriptor_runner.parent.mkdir(
            parents=True, exist_ok=True
        )
        self.executor_descriptor_runner.write_bytes(
            EXECUTOR_DESCRIPTOR_RUNNER.read_bytes()
        )
        self.executor_descriptor_runner.chmod(0o644)
        self.executor_descriptor_probe = self.repo / str(
            descriptor_record["probe_path"]
        )
        self.executor_descriptor_probe.parent.mkdir(
            parents=True, exist_ok=True
        )
        self.executor_descriptor_probe.write_bytes(
            EXECUTOR_DESCRIPTOR_PROBE.read_bytes()
        )
        self.executor_descriptor_probe.chmod(0o644)
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        claims["consumer_size"] = self.consumer.stat().st_size
        claims["consumer_sha256"] = digest(self.consumer.read_bytes())
        claims["consumer_mode"] = "0755"
        recovery_inputs = self.profile["recovery_inputs"]
        assert isinstance(recovery_inputs, dict)
        init_record = recovery_inputs["init"]
        control_build_record = recovery_inputs["control_build"]
        assert isinstance(init_record, dict)
        assert isinstance(control_build_record, dict)
        init_source = self.write(
            self.repo,
            str(init_record["path"]),
            b"init\n",
        )
        init_source.chmod(0o755)
        init_record["size"] = init_source.stat().st_size
        init_record["sha256"] = digest(init_source.read_bytes())
        init_record["mode"] = "0755"

        control_source = self.write(
            self.repo,
            ADMISSION.EXPECTED_RECOVERY_CONTROL_SOURCE,
            b"control-source\n",
        )
        control_source.chmod(0o644)
        control_builder = self.write(
            self.repo,
            ADMISSION.EXPECTED_RECOVERY_CONTROL_BUILDER,
            b"builder\n",
        )
        control_builder.chmod(0o755)
        self.control_build = {
            "format": "rog5-recovery-control-build-v1",
            "source": {
                "path": ADMISSION.EXPECTED_RECOVERY_CONTROL_SOURCE,
                "size": control_source.stat().st_size,
                "sha256": digest(control_source.read_bytes()),
                "mode": "0644",
            },
            "builder": {
                "script_path": ADMISSION.EXPECTED_RECOVERY_CONTROL_BUILDER,
                "script_size": control_builder.stat().st_size,
                "script_sha256": digest(control_builder.read_bytes()),
                "script_mode": "0755",
                "image": "localhost/rog5-persistent-root-verifier:alpine-3.24-deck-v1",
                "image_id": ADMISSION.EXPECTED_RECOVERY_CONTROL_IMAGE_ID,
                "image_digest": (
                    ADMISSION.EXPECTED_RECOVERY_CONTROL_IMAGE_DIGEST
                ),
                "architecture": "arm64",
                "compiler_version": "15.2.0",
                "source_date_epoch": 1681862400,
            },
            "output": {
                "size": len(b"control\n"),
                "sha256": digest(b"control\n"),
                "mode": "0755",
            },
        }
        self.control_build_path = self.repo / str(control_build_record["path"])
        self.save_control_build()
        self.build_fixture()

    def write(self, root: Path, relative: str, payload: bytes) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.chmod(0o600)
        return path

    def set_single(self, section: dict[str, object], key: str, root: Path, payload: bytes) -> Path:
        record = section[key]
        assert isinstance(record, dict)
        path = self.write(root, str(record["path"]), payload)
        record["size"] = len(payload)
        record["sha256"] = digest(payload)
        record["mode"] = "0600"
        return path

    def set_pair(self, section: dict[str, object], key: str, root: Path, payload: bytes) -> tuple[Path, Path]:
        record = section[key]
        assert isinstance(record, dict)
        first = self.write(root, str(record["path_a"]), payload)
        second = self.write(root, str(record["path_b"]), payload)
        record["size"] = len(payload)
        record["sha256"] = digest(payload)
        record["mode"] = "0600"
        return first, second

    def build_fixture(self) -> None:
        execution = self.profile["execution"]
        observer = self.profile["observer"]
        assert isinstance(execution, dict)
        assert isinstance(observer, dict)

        candidate_id = str(execution["candidate"])
        artifact_payloads = {
            "Image": b"target-kernel",
            "board.dtb": b"target-dtb",
            "initramfs.cpio.gz": b"target-initramfs",
        }
        candidate = {
            "format": "rog5-recovery-candidate-v1",
            "candidate": candidate_id,
            "status": "offline",
            "authority": "none",
            "bundle": candidate_id,
            "profile": "diagnostic-initramfs-v1",
            "target_id": candidate_id,
            "target_release": "7.1.4-test",
            "rollback_timeout": "600",
            "target_timeout": "480",
            "a660_command_manifest_sha256": "a" * 64,
            "root_generation": "arch-a",
            "root_tree_sha256": "b" * 64,
            "root_seal_sha256": "c" * 64,
            "root_tree_entries": "3",
            "root_subtree": "/",
            "artifacts": {
                name: {
                    "path": f"artifacts/{name}",
                    "size": len(payload),
                    "sha256": digest(payload),
                }
                for name, payload in artifact_payloads.items()
            },
        }
        candidate_path = self.write(
            self.repo,
            str(execution["candidate_path"]),
            (json.dumps(candidate, indent=2) + "\n").encode(),
        )
        execution["candidate_size"] = candidate_path.stat().st_size
        execution["candidate_sha256"] = digest(candidate_path.read_bytes())
        execution["candidate_mode"] = "0600"

        self.artifacts_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts_path.write_text(
            "name\tsize\tsha256\trole\ttracked\n"
            f"{execution['candidate_path']}\t{execution['candidate_size']}\t"
            f"{execution['candidate_sha256']}\ttracked current diagnostic identity\tyes\n"
        )
        self.artifacts_path.chmod(0o600)
        execution["artifact_inventory_mode"] = "0600"
        self.policy_path.write_text(
            "name\tstatus\tbasis\n"
            "build/observation-recovery-mainline-udc-v11-generation10-"
            "20260811-r1/repack/stable-recovery-a.avb.img\tallow\t"
            "one exact NFS-xattr retention observation recovery; RAM-only; "
            "externally consumed exact claim required; never flash or retry "
            "after entry\n"
            "build/headless-core-v21-generation21-20260812-r1/"
            "repack/stable-recovery-a.avb.img\tallow\t"
            "one exact headless-core Arch SSH recovery with power-key "
            "indicator; RAM-only; externally consumed exact claim required; "
            "never flash or retry after entry\n"
            "build/persistent-root-local-image-write-roclass-v40-generation62-"
            "20260814-r1/repack/stable-recovery-a.avb.img\tallow\t"
            "one exact bounded SM8350 UFS local-image effective-readonly "
            "discriminator with fixed selected/unrelated disk/partition and "
            "blockdev/sysfs terminal classes; the mutation "
            "remains one fixed marker inside the existing 16 GiB image followed "
            "by all-116-node relock and read-only Arch SSH; RAM-only kernel/"
            "recovery; externally consumed exact claim required; never flash or "
            "retry after entry\n"
            "build/persistent-root-storage-read-v4-generation25-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 25 RAM-only cycle; exact Alpine "
            "fallback returned; never retry or flash\n"
            "build/persistent-root-storage-read-v5-generation26-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 26 RAM-only cycle; no target USB "
            "appeared and exact Alpine returned after 25.333 seconds; never "
            "retry or flash\n"
            "build/persistent-root-usb-control-v6-generation27-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 27 RAM-only cycle; stable target "
            "NCM passed before exact Alpine fallback; never retry or flash\n"
            "build/persistent-root-dtb-control-v7-generation28-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 28 RAM-only cycle; stable target "
            "NCM passed before exact Alpine fallback; never retry or flash\n"
            "build/persistent-root-image-control-v8-generation29-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 29 RAM-only cycle; stable target "
            "NCM passed before exact Alpine fallback; never retry or flash\n"
            "build/persistent-root-accepted-image-v9-generation30-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 30 RAM-only cycle; no target USB "
            "appeared before exact Alpine fallback; never retry or flash\n"
            "build/persistent-root-deferred-ufs-v10-generation31-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 31 RAM-only cycle; no target USB "
            "appeared before exact Alpine fallback; never retry or flash\n"
            "build/persistent-root-deferred-qmp-ufs-v11-generation32-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 32 RAM-only cycle; stable target "
            "NCM appeared before the module chain and exact Alpine fallback; "
            "never retry or flash\n"
            "build/persistent-root-qmp-ufs-phy-control-v12-generation33-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 33 RAM-only cycle; target NCM "
            "disappeared during the PHY-only control window; never retry or flash\n"
            "build/persistent-root-qmp-module-load-control-v13-generation34-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 34 RAM-only cycle; QMP-UFS module "
            "registration passed the exact NCM window and Alpine returned; "
            "never retry or flash\n"
            "build/persistent-root-qmp-regulator-stage-v14-generation35-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 35 RAM-only cycle; "
            "clock/regulator probe stage passed the exact NCM window and "
            "Alpine returned; never retry or flash\n"
            "build/persistent-root-qmp-mmio-stage-v15-generation36-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 36 RAM-only cycle; "
            "DT/MMIO probe stage passed the exact NCM window and Alpine "
            "returned; never retry or flash\n"
            "build/persistent-root-qmp-clock-provider-stage-v16-generation37-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 37 RAM-only cycle; target NCM "
            "disappeared inside qmp_ufs_register_clocks and exact Alpine "
            "returned; never retry or flash\n"
            "build/persistent-root-qmp-fixed-clocks-stage-v17-generation38-20260812-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 38 RAM-only cycle; target NCM "
            "disappeared during allocation or one of three fixed-rate clock "
            "registrations and exact Alpine returned; no phone-storage access; "
            "never retry or flash\n"
            "build/persistent-root-qmp-first-fixed-clock-stage-v18-generation39-20260813-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 39 RAM-only cycle; target NCM "
            "disappeared during allocation or first fixed-rate clock registration "
            "and exact Alpine returned; no phone-storage access; never retry or "
            "flash\n"
            "build/persistent-root-qmp-allocation-stage-v19-generation40-20260813-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 40 RAM-only cycle; clock-data "
            "allocation completed, stable target NCM passed, and exact Alpine "
            "returned; no phone-storage access; never retry or flash\n"
            "build/persistent-root-qmp-first-clock-name-stage-v20-generation41-20260813-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 41 RAM-only cycle; first-symbol-clock "
            "name construction and stable NCM passed before exact Alpine fallback; "
            "no phone-storage access; never retry or flash\n"
            "build/persistent-root-qmp-first-clock-runtime-pm-stage-v21-generation42-20260813-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 42 RAM-only cycle; first fixed-rate "
            "clock registration and stable NCM passed before exact Alpine "
            "fallback; no phone-storage access; never retry or flash\n"
            "build/persistent-root-qmp-second-clock-runtime-pm-stage-v22-generation43-20260813-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 43 RAM-only cycle; stable target "
            "NCM and exact Alpine fallback passed, but stale initramfs release "
            "identity stopped before QMP-UFS module load; no phone-storage "
            "access; never retry or flash\n"
            "build/persistent-root-qmp-third-clock-runtime-pm-stage-v23-generation44-20260813-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 44 RAM-only cycle; exact target "
            "proof crossed all three fixed-rate clocks, stable NCM and exact "
            "Alpine fallback passed, and no phone-storage access occurred; "
            "never retry or flash\n"
            "build/persistent-root-qmp-clock-provider-cleanup-stage-v25-generation46-20260813-r1/"
            "repack/stable-recovery-a.avb.img\trevoked\t"
            "consumed by the sole Generation 46 RAM-only cycle; OF clock-provider "
            "publication and paired cleanup completed, stable target NCM passed, "
            "exact Alpine fallback returned, and no phone-storage access occurred; "
            "never retry or flash\n"
            "build/persistent-root-qmp-ufs-phy-creation-stage-v26-generation47-20260813-r1/"
			"repack/stable-recovery-a.avb.img\trevoked\t"
			"consumed by the sole Generation 47 RAM-only cycle; PHY creation "
			"completed, stable target NCM passed, exact Alpine fallback returned, "
			"and no phone-storage access occurred; never retry or flash\n"
			"build/persistent-root-qmp-ufs-phy-provider-stage-v27-generation48-20260813-r1/"
			"repack/stable-recovery-a.avb.img\trevoked\t"
			"consumed by the sole Generation 48 RAM-only cycle; QMP-UFS OF "
			"PHY-provider registration completed, stable target NCM passed, exact "
			"Alpine fallback returned, and no phone-storage access occurred; never "
			"retry or flash\n"
			"build/persistent-root-ufs-readonly-enumeration-v28-generation49-20260813-r1/"
			"repack/stable-recovery-a.avb.img\trevoked\t"
			"consumed by the sole Generation 49 RAM-only cycle; exact 116-node "
			"read-only UFS enumeration, stable NCM, and exact Alpine fallback "
			"passed with zero mounts and writes; never retry or flash\n"
			"build/persistent-root-ufs-local-root-v29-generation50-20260813-r1/"
			"repack/stable-recovery-a.avb.img\trevoked\t"
			"consumed by the sole Generation 50 RAM-only cycle; target NCM remained "
			"stable for approximately 599 seconds, key-only SSH never appeared, the "
			"bounded target watchdog reset, and exact Alpine fallback returned; no "
			"persistent phone writes; never retry or flash\n"
			"build/persistent-root-ufs-local-root-stage-v30-generation51-20260813-r1/"
			"repack/stable-recovery-a.avb.img\trevoked\t"
			"consumed by the sole Generation 51 RAM-only cycle; exact read-only UFS, "
			"116-node storage lock, dynamic userdata resolution, and ro,noload mount "
			"passed; complete 181242-entry root verification exceeded the 600-second "
			"rollback window while NCM remained stable; exact Alpine fallback returned; "
			"no persistent phone writes; never retry or flash\n"
			"build/persistent-root-ufs-fast-admission-v31-generation52-20260813-r1/"
			"repack/stable-recovery-a.avb.img\trevoked\t"
			"consumed by the sole Generation 52 RAM-only cycle; read-only UFS, exact "
			"userdata, bounded root admission, and switch-root entry passed, key-only "
			"SSH did not appear, and exact Alpine fallback returned; never retry or "
			"flash\n"
			"build/persistent-root-local-image-v32-generation53-20260813-r1/"
			"repack/stable-recovery-a.avb.img\trevoked\t"
			"consumed by the sole Generation 53 RAM-only cycle; local-image Arch reached "
			"strict key-only SSH at target uptime 298.62 seconds with both ext4 layers "
			"ro,noload, tmpfs OverlayFS, clean UFS checks, normal systemd reboot, and exact "
			"Alpine fallback; host parser rejected only a stale root marker after success; "
			"never retry or flash\n"
            "historical/recovery.img\trevoked\thistorical only\n"
        )
        self.policy_path.chmod(0o600)
        policy = self.profile["policy"]
        assert isinstance(policy, dict)
        policy["mode"] = "0600"

        for prefix_key in ("bundle_a", "bundle_b"):
            prefix = str(execution[prefix_key])
            for name, payload in artifact_payloads.items():
                self.write(self.execution, f"{prefix}/{name}", payload).chmod(0o400)

        manifest = (
            "format=rog5-recovery-bundle-v2\n"
            f"bundle={candidate_id}\n"
            "profile=diagnostic-initramfs-v1\n"
            f"kernel_size={len(artifact_payloads['Image'])}\n"
            f"kernel_sha256={digest(artifact_payloads['Image'])}\n"
            f"dtb_size={len(artifact_payloads['board.dtb'])}\n"
            f"dtb_sha256={digest(artifact_payloads['board.dtb'])}\n"
            f"initramfs_size={len(artifact_payloads['initramfs.cpio.gz'])}\n"
            f"initramfs_sha256={digest(artifact_payloads['initramfs.cpio.gz'])}\n"
            f"target_id={candidate_id}\n"
            "target_release=7.1.4-test\n"
            "rollback_timeout=600\n"
            "target_timeout=480\n"
            f"a660_command_manifest_sha256={'a' * 64}\n"
            "root_generation=arch-a\n"
            f"root_tree_sha256={'b' * 64}\n"
            f"root_seal_sha256={'c' * 64}\n"
            "root_tree_entries=3\n"
            "root_subtree=/\n"
        ).encode("ascii")
        manifest_a, manifest_b = self.set_pair(
            execution,
            "runtime_manifest",
            self.execution,
            manifest,
        )

        signing_key = self.base / "signing-key.pem"
        subprocess.run(
            ["/usr/bin/openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(signing_key)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        public_der = subprocess.run(
            ["/usr/bin/openssl", "pkey", "-in", str(signing_key), "-pubout", "-outform", "DER"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout
        trust_key = self.set_single(
            execution,
            "trust_key",
            self.execution,
            public_der[-32:],
        )
        signature = self.base / "manifest.sig"
        subprocess.run(
            [
                "/usr/bin/openssl",
                "pkeyutl",
                "-sign",
                "-inkey",
                str(signing_key),
                "-rawin",
                "-in",
                str(manifest_a),
                "-out",
                str(signature),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.set_pair(
            execution,
            "runtime_signature",
            self.execution,
            signature.read_bytes(),
        )
        candidate_record = (
            "format=rog5-prepared-candidate-v1\n"
            f"candidate={candidate_id}\n"
            "status=offline\n"
            "authority=none\n"
            f"bundle={candidate_id}\n"
            f"manifest_sha256={digest(manifest)}\n"
            f"trust_key_sha256={digest(trust_key.read_bytes())}\n"
        ).encode("ascii")
        self.set_pair(
            execution,
            "candidate_record",
            self.execution,
            candidate_record,
        )

        execution_archive = recovery_archive("full-v1")
        self.set_pair(
            execution,
            "recovery_initramfs",
            self.execution,
            execution_archive,
        )
        shared_config = (
            b"CONFIG_PSTORE=y\n"
            b"CONFIG_PSTORE_CONSOLE=y\n"
            b"CONFIG_PSTORE_PMSG=y\n"
            b"CONFIG_PSTORE_RAM=y\n"
        )
        self.set_pair(execution, "wrapper_config", self.execution, shared_config)
        execution_image = b"execution-image"
        self.set_pair(execution, "wrapper_image", self.execution, execution_image)
        execution_raw = fake_boot_v3(execution_image, execution_archive)
        self.set_pair(execution, "raw_boot", self.execution, execution_raw)
        self.set_pair(
            execution,
            "unsigned_avb",
            self.execution,
            fake_avb(execution_raw),
        )

        observer_archive = recovery_archive("observation-only-v1")
        self.set_pair(observer, "recovery_initramfs", self.observer, observer_archive)
        self.set_pair(observer, "wrapper_config", self.observer, shared_config)
        observer_image = b"observer-image"
        self.set_pair(observer, "wrapper_image", self.observer, observer_image)
        observer_raw = fake_boot_v3(observer_image, observer_archive)
        self.set_pair(observer, "raw_boot", self.observer, observer_raw)
        self.set_pair(
            observer,
            "unsigned_avb",
            self.observer,
            fake_avb(observer_raw),
        )
        self.refresh_observer_evidence()
        self.refresh_root_inventories()
        self.save_profile()

    def refresh_root_inventories(self) -> None:
        inventories = self.profile["root_inventory"]
        assert isinstance(inventories, dict)
        for key, root in (("execution", self.execution), ("observer", self.observer)):
            entries = []
            for entry in root.iterdir():
                if entry.is_file():
                    kind = "file"
                elif entry.is_dir():
                    kind = "directory"
                else:
                    raise AssertionError(f"unsafe fixture entry: {entry}")
                entries.append(f"{entry.name}:{kind}")
            inventories[key] = sorted(entries)

    def refresh_observer_evidence(self) -> None:
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        evidence = (
            "format=rog5-observation-recovery-wrapper-evidence-v1\n"
            f"observer_initramfs_size={observer['recovery_initramfs']['size']}\n"
            f"observer_initramfs_sha256={observer['recovery_initramfs']['sha256']}\n"
            f"wrapper_config_size={observer['wrapper_config']['size']}\n"
            f"wrapper_config_sha256={observer['wrapper_config']['sha256']}\n"
            f"wrapper_image_size={observer['wrapper_image']['size']}\n"
            f"wrapper_image_sha256={observer['wrapper_image']['sha256']}\n"
            f"raw_boot_size={observer['raw_boot']['size']}\n"
            f"raw_boot_sha256={observer['raw_boot']['sha256']}\n"
            f"unsigned_avb_size={observer['unsigned_avb']['size']}\n"
            f"unsigned_avb_sha256={observer['unsigned_avb']['sha256']}\n"
            "ramoops_mem_address=0x9b800000\n"
            "ramoops_mem_size=0x400000\n"
            "authority=none\n"
            "candidate=none\n"
            "boot_authority=none\n"
            "retention=unproven\n"
            "PASS observation-only clean-twin wrapper evidence is exact and offline-only\n"
        ).encode("ascii")
        self.set_single(
            observer,
            "wrapper_evidence",
            self.observer,
            evidence,
        )

    def save_profile(self) -> None:
        self.profile_path.write_text(json.dumps(self.profile, indent=2) + "\n")
        self.profile_path.chmod(0o600)

    def save_control_build(self) -> None:
        payload = (json.dumps(self.control_build, indent=2) + "\n").encode()
        self.write(
            self.repo,
            str(self.control_build_path.relative_to(self.repo)),
            payload,
        ).chmod(0o644)
        recovery_inputs = self.profile["recovery_inputs"]
        assert isinstance(recovery_inputs, dict)
        record = recovery_inputs["control_build"]
        assert isinstance(record, dict)
        record["size"] = len(payload)
        record["sha256"] = digest(payload)
        record["mode"] = "0644"

    def replace_recovery_archives(
        self,
        *,
        init_payload: bytes = b"init\n",
        control_payload: bytes = b"control\n",
    ) -> None:
        execution = self.profile["execution"]
        observer = self.profile["observer"]
        assert isinstance(execution, dict)
        assert isinstance(observer, dict)
        for section, root, mode in (
            (execution, self.execution, "full-v1"),
            (observer, self.observer, "observation-only-v1"),
        ):
            archive = recovery_archive(
                mode,
                init_payload=init_payload,
                control_payload=control_payload,
            )
            self.set_pair(section, "recovery_initramfs", root, archive)
            image_record = section["wrapper_image"]
            assert isinstance(image_record, dict)
            image = (root / str(image_record["path_a"])).read_bytes()
            raw = fake_boot_v3(image, archive)
            self.set_pair(section, "raw_boot", root, raw)
            self.set_pair(section, "unsigned_avb", root, fake_avb(raw))
        self.refresh_observer_evidence()
        self.save_profile()

    def verify(self) -> str:
        return ADMISSION.verify(
            self.profile_path,
            self.repo,
            self.execution,
            self.observer,
            self.artifacts_path,
            self.policy_path,
            enforce_repository_layout=False,
        )

    def assert_rejected(self, message: str) -> None:
        with self.assertRaisesRegex(ADMISSION.AdmissionError, message):
            self.verify()

    def test_exact_distinct_authority_free_pair_passes(self) -> None:
        report = self.verify()
        self.assertIn("temporary_boot_allow_rows=3", report)
        self.assertIn("execution_claim=not-defined", report)
        self.assertIn("observer_claim=not-defined", report)
        self.assertIn("missing_pstore=inconclusive", report)
        self.assertIn("recovery_init_sha256=", report)
        self.assertIn("recovery_control_source_sha256=", report)
        self.assertIn("recovery_control_binary_sha256=", report)
        self.assertIn("sequence_reference_sha256=", report)
        self.assertIn("transaction_fixture_sha256=", report)
        self.assertIn("transaction_fixture=offline-only", report)
        self.assertIn("adapter_fixture_sha256=", report)
        self.assertIn("adapter_fixture=callback-only", report)
        self.assertIn("executor_contract_sha256=", report)
        self.assertIn("executor_contract=pure-offline-only", report)
        self.assertIn("executor_boundary_sha256=", report)
        self.assertIn(
            "executor_boundary=six-decodable-two-hold-gates", report
        )
        self.assertIn("executor_runtime_sha256=", report)
        self.assertIn(
            "executor_runtime=offline-fresh-pipe-adapter-ineligible",
            report,
        )
        self.assertIn("executor_descriptor_runner_sha256=", report)
        self.assertIn("executor_descriptor_probe_sha256=", report)
        self.assertIn(
            "fixture_descriptor_execution=held-fd-proven-adapter-ineligible",
            report,
        )
        self.assertIn("production_descriptor_execution=unproven", report)
        self.assertIn("fallback_boot_result=guarded-producer-defined", report)
        self.assertIn("draft_claims=unregistered", report)
        self.assertIn("recommendation=HOLD", report)

    def test_execution_requires_the_project_trust_class(self) -> None:
        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        self.assertEqual(execution["trust_class"], "production-project")

        execution["trust_class"] = "disposable-offline"
        self.save_profile()
        self.assert_rejected("execution and observation roles are not fail-closed")

    def test_recovery_sources_and_embedded_control_are_exact(self) -> None:
        recovery_inputs = self.profile["recovery_inputs"]
        assert isinstance(recovery_inputs, dict)
        init_record = recovery_inputs["init"]
        assert isinstance(init_record, dict)
        init_path = self.repo / str(init_record["path"])
        init_path.write_bytes(b"inIt\n")
        self.assert_rejected("recovery init source")

        self.reset_fixture()
        control_source_path = (
            self.repo / ADMISSION.EXPECTED_RECOVERY_CONTROL_SOURCE
        )
        control_source_path.write_bytes(b"control-Source\n")
        self.assert_rejected("recovery control source")

        self.reset_fixture()
        recovery_inputs = self.profile["recovery_inputs"]
        assert isinstance(recovery_inputs, dict)
        init_record = recovery_inputs["init"]
        assert isinstance(init_record, dict)
        init_payload = (
            self.repo / str(init_record["path"])
        ).read_bytes()
        alternate = self.write(
            self.repo,
            "alternate/recovery-init",
            init_payload,
        )
        init_record["path"] = str(alternate.relative_to(self.repo))
        self.save_profile()
        self.assert_rejected("recovery init source repository path is not exact")

        self.reset_fixture()
        recovery_inputs = self.profile["recovery_inputs"]
        assert isinstance(recovery_inputs, dict)
        build_record = recovery_inputs["control_build"]
        assert isinstance(build_record, dict)
        alternate = self.write(
            self.repo,
            "alternate/aarch64-build-v1.json",
            self.control_build_path.read_bytes(),
        )
        alternate.chmod(0o644)
        build_record["path"] = str(alternate.relative_to(self.repo))
        self.save_profile()
        self.assert_rejected(
            "recovery control build record repository path is not exact"
        )

        self.reset_fixture()
        source = self.control_build["source"]
        assert isinstance(source, dict)
        source["path"] = "alternate/rog5-recovery-control.c"
        alternate = self.write(
            self.repo,
            str(source["path"]),
            b"control-source\n",
        )
        alternate.chmod(0o644)
        self.save_control_build()
        self.save_profile()
        self.assert_rejected(
            "recovery control source repository path is not exact"
        )

        self.reset_fixture()
        self.replace_recovery_archives(init_payload=b"inIt\n")
        self.assert_rejected(
            "embedded recovery init does not match its repository source"
        )

        self.reset_fixture()
        self.replace_recovery_archives(control_payload=b"contrOl\n")
        self.assert_rejected("embedded recovery control binary identity changed")

    def test_recovery_control_build_record_is_fail_closed(self) -> None:
        self.control_build["extra"] = "rejected"
        self.save_control_build()
        self.save_profile()
        self.assert_rejected("recovery control build record fields are not exact")

        self.reset_fixture()
        self.control_build["format"] = "wrong-format"
        self.save_control_build()
        self.save_profile()
        self.assert_rejected("recovery control build record format changed")

        self.reset_fixture()
        payload = self.control_build_path.read_bytes()
        source = self.control_build["source"]
        assert isinstance(source, dict)
        source_digest = str(source["sha256"])
        digest_line = f'    "sha256": "{source_digest}",\n'.encode()
        self.assertEqual(payload.count(digest_line), 1)
        payload = payload.replace(digest_line, digest_line * 2, 1)
        self.control_build_path.write_bytes(payload)
        recovery_inputs = self.profile["recovery_inputs"]
        assert isinstance(recovery_inputs, dict)
        build_record = recovery_inputs["control_build"]
        assert isinstance(build_record, dict)
        build_record["size"] = len(payload)
        build_record["sha256"] = digest(payload)
        self.save_profile()
        self.assert_rejected("JSON contains duplicate key: sha256")

        self.reset_fixture()
        builder = self.control_build["builder"]
        assert isinstance(builder, dict)
        builder["script_path"] = "alternate/build-recovery-control.sh"
        alternate = self.write(
            self.repo,
            str(builder["script_path"]),
            b"builder\n",
        )
        alternate.chmod(0o755)
        self.save_control_build()
        self.save_profile()
        self.assert_rejected(
            "recovery control builder repository path is not exact"
        )

        self.reset_fixture()
        builder_path = (
            self.repo / ADMISSION.EXPECTED_RECOVERY_CONTROL_BUILDER
        )
        builder_path.write_bytes(b"buildEr\n")
        self.assert_rejected("recovery control builder identity changed")

        self.reset_fixture()
        builder = self.control_build["builder"]
        assert isinstance(builder, dict)
        builder["image_id"] = "3" * 64
        self.save_control_build()
        self.save_profile()
        self.assert_rejected("recovery control builder identity changed")

        self.reset_fixture()
        source_path = self.repo / ADMISSION.EXPECTED_RECOVERY_CONTROL_SOURCE
        source_path.chmod(0o600)
        self.assert_rejected("recovery control source mode changed")

        self.reset_fixture()
        output = self.control_build["output"]
        assert isinstance(output, dict)
        output["size"] = True
        self.save_control_build()
        self.save_profile()
        self.assert_rejected("recovery control binary size is invalid")

        self.reset_fixture()
        output = self.control_build["output"]
        assert isinstance(output, dict)
        output["sha256"] = "not-a-digest"
        self.save_control_build()
        self.save_profile()
        self.assert_rejected("recovery control binary SHA-256")

    def test_profile_authority_role_sequence_and_claim_mutations_fail(self) -> None:
        cases = (
            ("authority", "live", "weakens the HOLD boundary"),
            ("boot_authority", "one-shot", "weakens the HOLD boundary"),
            ("missing_pstore", "no-crash", "weakens the HOLD boundary"),
            ("sequence", list(reversed(self.profile["sequence"])), "weakens the HOLD boundary"),
            ("execution.role", "observation-only-v1", "roles are not fail-closed"),
            ("observer.role", "target-execution-v1", "roles are not fail-closed"),
            ("claims.execution", "issued", "claim policy is not exact"),
            ("claims.reuse", "allowed", "claim policy is not exact"),
            (
                "claims.sequence_reference.execution_identifier",
                "replacement",
                "sequence reference contract is not exact",
            ),
            (
                "claims.transaction_fixture.live_entrypoint",
                "run",
                "transaction fixture contract is not exact",
            ),
            (
                "claims.adapter_fixture.builtin_executor",
                "subprocess",
                "adapter fixture contract is not exact",
            ),
            (
                "claims.executor_contract.builtin_executor",
                "subprocess",
                "executor contract is not exact",
            ),
            (
                "claims.executor_boundary.live_entrypoint",
                "run",
                "executor boundary is not exact",
            ),
            (
                "claims.executor_runtime.adapter_wiring",
                "live",
                "executor runtime closure is not exact",
            ),
            (
                "claims.executor_descriptor_fixture.adapter_wiring",
                "live",
                "executor descriptor fixture is not exact",
            ),
        )
        baseline = copy.deepcopy(self.profile)
        for dotted, value, message in cases:
            with self.subTest(field=dotted):
                self.profile = copy.deepcopy(baseline)
                target: dict[str, object] = self.profile
                parts = dotted.split(".")
                for part in parts[:-1]:
                    child = target[part]
                    assert isinstance(child, dict)
                    target = child
                target[parts[-1]] = value
                self.save_profile()
                self.assert_rejected(message)

    def test_sequence_reference_is_exact_and_nonconsumable(self) -> None:
        self.sequence_reference.write_bytes(
            self.sequence_reference.read_bytes().replace(
                b"reference-only", b"reference-ONLY", 1
            )
        )
        self.assert_rejected("sequence reference")

        self.reset_fixture()
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        reference = claims["sequence_reference"]
        assert isinstance(reference, dict)
        reference["size"] = True
        self.save_profile()
        self.assert_rejected("sequence reference contract is not exact")

    def test_transaction_fixture_is_exact_and_offline_only(self) -> None:
        self.transaction_fixture.write_bytes(
            self.transaction_fixture.read_bytes().replace(
                b"append-only", b"append_ONLY", 1
            )
        )
        self.assert_rejected("transaction fixture")

        self.reset_fixture()
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        fixture = claims["transaction_fixture"]
        assert isinstance(fixture, dict)
        fixture["policy_allow_rows"] = 1
        self.save_profile()
        self.assert_rejected("transaction fixture contract is not exact")

    def test_adapter_fixture_is_exact_and_callback_only(self) -> None:
        self.adapter_fixture.write_bytes(
            self.adapter_fixture.read_bytes().replace(
                b"Callback-only", b"Callback_ONLY", 1
            )
        )
        self.assert_rejected("adapter fixture")

        self.reset_fixture()
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        fixture = claims["adapter_fixture"]
        assert isinstance(fixture, dict)
        fixture["journal_sha256"] = "f" * 64
        self.save_profile()
        self.assert_rejected("adapter fixture contract is not exact")

    def test_executor_contract_is_exact_and_has_no_executor(self) -> None:
        self.executor_contract.write_bytes(
            self.executor_contract.read_bytes().replace(
                b"Pure process", b"PURE process", 1
            )
        )
        self.assert_rejected("executor contract")

        self.reset_fixture()
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        contract = claims["executor_contract"]
        assert isinstance(contract, dict)
        contract["adapter_sha256"] = "f" * 64
        self.save_profile()
        self.assert_rejected("executor contract is not exact")

    def test_executor_boundary_is_exact_and_tracks_live_producers(self) -> None:
        self.executor_boundary.write_bytes(
            self.executor_boundary.read_bytes().replace(
                b"guarded-producer-defined", b"guarded-producer-defineD", 1
            )
        )
        self.assert_rejected("executor boundary")

        self.reset_fixture()
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        boundary = claims["executor_boundary"]
        assert isinstance(boundary, dict)
        producers = boundary["live_producer_state"]
        assert isinstance(producers, dict)
        producers["fallback-reboot"] = "unreviewed"
        self.save_profile()
        self.assert_rejected("executor boundary is not exact")

    def test_executor_runtime_is_exact_and_adapter_ineligible(self) -> None:
        self.executor_runtime.write_bytes(
            self.executor_runtime.read_bytes().replace(
                b"fresh-intent/fresh-pipe", b"fresh-intent/fresh_pipe", 1
            )
        )
        self.assert_rejected("executor runtime closure")

        self.reset_fixture()
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        runtime = claims["executor_runtime"]
        assert isinstance(runtime, dict)
        runtime["transaction_sha256"] = "f" * 64
        self.save_profile()
        self.assert_rejected("executor runtime closure is not exact")

    def test_executor_descriptor_fixture_is_exact_and_offline_only(self) -> None:
        self.executor_descriptor_runner.write_bytes(
            self.executor_descriptor_runner.read_bytes().replace(
                b"held file descriptors", b"held file descriptorS", 1
            )
        )
        self.assert_rejected("executor descriptor runner")

        self.reset_fixture()
        self.executor_descriptor_probe.write_bytes(
            self.executor_descriptor_probe.read_bytes().replace(
                b"Harmless child probe", b"Harmless child probE", 1
            )
        )
        self.assert_rejected("executor descriptor probe")

        self.reset_fixture()
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        descriptor = claims["executor_descriptor_fixture"]
        assert isinstance(descriptor, dict)
        descriptor["production_descriptor_execution"] = "proven"
        self.save_profile()
        self.assert_rejected("executor descriptor fixture is not exact")

    def test_policy_allow_or_malformed_row_fails_closed(self) -> None:
        for payload, message in (
            (
                "name\tstatus\tbasis\nfuture.img\tallow\tone boot\n",
                "does not contain exact retention admissions",
            ),
            (
                "name\tstatus\tbasis\nfuture.img\tpending\tunknown\n",
                "status is unknown",
            ),
            ("name\tstatus\tbasis\nbroken\n", "row is malformed"),
        ):
            with self.subTest(message=message):
                self.policy_path.write_text(payload)
                self.assert_rejected(message)

    def test_candidate_semantics_inventory_and_bundle_mutations_fail(self) -> None:
        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        candidate_path = self.repo / str(execution["candidate_path"])
        candidate = json.loads(candidate_path.read_text())
        candidate["authority"] = "live"
        candidate_path.write_text(json.dumps(candidate) + "\n")
        execution["candidate_size"] = candidate_path.stat().st_size
        execution["candidate_sha256"] = digest(candidate_path.read_bytes())
        rows = self.artifacts_path.read_text().splitlines()
        fields = rows[1].split("\t")
        fields[1] = str(execution["candidate_size"])
        fields[2] = str(execution["candidate_sha256"])
        self.artifacts_path.write_text(rows[0] + "\n" + "\t".join(fields) + "\n")
        self.save_profile()
        self.assert_rejected("not authority-free and exact")

        self.reset_fixture()
        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        bundle = self.execution / str(execution["bundle_b"]) / "board.dtb"
        bundle.chmod(0o600)
        bundle.write_bytes(b"mutated")
        bundle.chmod(0o400)
        self.assert_rejected("bundle B board.dtb size changed")

        self.reset_fixture()
        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        self.write(
            self.execution,
            f"{execution['bundle_a']}/unmanifested",
            b"extra",
        )
        self.assert_rejected("bundle A inventory is not exact")

        self.reset_fixture()
        self.write(self.execution, "unexpected-top-level", b"extra")
        self.assert_rejected("execution evidence-root inventory is not exact")

    def test_manifest_and_signature_paths_must_belong_to_each_bundle(self) -> None:
        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        manifest = execution["runtime_manifest"]
        signature = execution["runtime_signature"]
        assert isinstance(manifest, dict)
        assert isinstance(signature, dict)
        manifest_payload = (
            self.execution / str(manifest["path_a"])
        ).read_bytes()
        signature_payload = (
            self.execution / str(signature["path_a"])
        ).read_bytes()
        manifest["path_a"] = "detached/manifest-a"
        manifest["path_b"] = "detached/manifest-b"
        signature["path_a"] = "detached/manifest-a.sig"
        signature["path_b"] = "detached/manifest-b.sig"
        self.set_pair(execution, "runtime_manifest", self.execution, manifest_payload)
        self.set_pair(execution, "runtime_signature", self.execution, signature_payload)
        self.refresh_root_inventories()
        self.save_profile()
        self.assert_rejected("manifest and signature paths are not bundle-owned")

    def test_candidate_and_manifest_fields_are_exact(self) -> None:
        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        candidate_path = self.repo / str(execution["candidate_path"])
        candidate = json.loads(candidate_path.read_text())
        candidate.pop("root_tree_sha256")
        candidate_path.write_text(json.dumps(candidate) + "\n")
        execution["candidate_size"] = candidate_path.stat().st_size
        execution["candidate_sha256"] = digest(candidate_path.read_bytes())
        fields = self.artifacts_path.read_text().splitlines()[1].split("\t")
        fields[1] = str(execution["candidate_size"])
        fields[2] = str(execution["candidate_sha256"])
        self.artifacts_path.write_text(
            "name\tsize\tsha256\trole\ttracked\n" + "\t".join(fields) + "\n"
        )
        self.save_profile()
        self.assert_rejected("candidate fields are not exact")

        self.reset_fixture()
        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        manifest_record = execution["runtime_manifest"]
        assert isinstance(manifest_record, dict)
        manifest = (
            self.execution / str(manifest_record["path_a"])
        ).read_bytes() + b"extra_directive=1\n"
        manifest_a, _manifest_b = self.set_pair(
            execution,
            "runtime_manifest",
            self.execution,
            manifest,
        )
        signature = self.base / "mutated-manifest.sig"
        subprocess.run(
            [
                "/usr/bin/openssl",
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.base / "signing-key.pem"),
                "-rawin",
                "-in",
                str(manifest_a),
                "-out",
                str(signature),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.set_pair(
            execution,
            "runtime_signature",
            self.execution,
            signature.read_bytes(),
        )
        candidate_record = execution["candidate_record"]
        assert isinstance(candidate_record, dict)
        record_path = self.execution / str(candidate_record["path_a"])
        record = record_path.read_text().replace(
            next(
                line
                for line in record_path.read_text().splitlines()
                if line.startswith("manifest_sha256=")
            ),
            f"manifest_sha256={digest(manifest)}",
        ).encode("ascii")
        self.set_pair(
            execution,
            "candidate_record",
            self.execution,
            record,
        )
        self.save_profile()
        self.assert_rejected("manifest fields are not exact")

    def test_signature_and_private_key_fail_closed(self) -> None:
        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        signature = execution["runtime_signature"]
        assert isinstance(signature, dict)
        payload = b"X" * 64
        self.set_pair(execution, "runtime_signature", self.execution, payload)
        self.save_profile()
        self.assert_rejected("runtime signature is invalid")

        self.reset_fixture()
        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        self.write(self.execution, str(execution["private_key_path"]), b"private")
        self.assert_rejected("private signing key must be absent")

    def test_observer_execution_path_and_wrong_mode_fail_closed(self) -> None:
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        self.set_pair(
            observer,
            "recovery_initramfs",
            self.observer,
            recovery_archive("observation-only-v1", inject_kexec=True),
        )
        self.refresh_observer_evidence()
        self.save_profile()
        self.assert_rejected("retains a payload execution path")

        self.reset_fixture()
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        self.set_pair(
            observer,
            "recovery_initramfs",
            self.observer,
            recovery_archive("full-v1"),
        )
        self.refresh_observer_evidence()
        self.save_profile()
        self.assert_rejected("mode is not exact")

    def test_noncanonical_archive_path_is_rejected_before_role_checks(self) -> None:
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        archive = newc(
            {
                "init": (stat.S_IFREG | 0o755, b"init\n"),
                "usr/libexec/rog5-recovery-control": (
                    stat.S_IFREG | 0o755,
                    b"control\n",
                ),
                "etc/rog5/recovery-mode": (
                    stat.S_IFREG | 0o444,
                    b"observation-only-v1\n",
                ),
                "usr/./libexec/rog5-bundle-fetch": (
                    stat.S_IFREG | 0o755,
                    b"fetch\n",
                ),
            }
        )
        self.set_pair(observer, "recovery_initramfs", self.observer, archive)
        self.refresh_observer_evidence()
        self.save_profile()
        self.assert_rejected("unsafe or duplicate path")

        self.reset_fixture()
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        first = recovery_archive("observation-only-v1")
        second = recovery_archive("full-v1")
        concatenated = gzip.compress(
            gzip.decompress(first) + gzip.decompress(second),
            compresslevel=9,
            mtime=0,
        )
        self.set_pair(
            observer,
            "recovery_initramfs",
            self.observer,
            concatenated,
        )
        self.refresh_observer_evidence()
        self.save_profile()
        self.assert_rejected("trailing archive member")

        self.reset_fixture()
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        embedded_nul = newc(
            {
                "init": (stat.S_IFREG | 0o755, b"init\n"),
                "usr/libexec/rog5-recovery-control": (
                    stat.S_IFREG | 0o755,
                    b"control\n",
                ),
                "etc/rog5/recovery-mode": (
                    stat.S_IFREG | 0o444,
                    b"observation-only-v1\n",
                ),
                "usr/sbin/kexec\0hidden": (
                    stat.S_IFREG | 0o755,
                    b"hidden-execution-path\n",
                ),
            }
        )
        self.set_pair(observer, "recovery_initramfs", self.observer, embedded_nul)
        self.refresh_observer_evidence()
        self.save_profile()
        self.assert_rejected("truncated entry name")

    def test_observer_is_exact_execution_free_derivation(self) -> None:
        execution = self.profile["execution"]
        observer = self.profile["observer"]
        assert isinstance(execution, dict)
        assert isinstance(observer, dict)
        entries = {
            "init": (stat.S_IFREG | 0o755, b"init\n"),
            "usr/libexec/rog5-recovery-control": (
                stat.S_IFREG | 0o755,
                b"control\n",
            ),
            "etc/rog5/recovery-mode": (
                stat.S_IFREG | 0o444,
                b"observation-only-v1\n",
            ),
            "etc/rog5/shared-contract": (
                stat.S_IFREG | 0o444,
                b"different-shared-contract\n",
            ),
        }
        archive = newc(entries)
        self.set_pair(observer, "recovery_initramfs", self.observer, archive)
        image_record = observer["wrapper_image"]
        assert isinstance(image_record, dict)
        image = (self.observer / str(image_record["path_a"])).read_bytes()
        raw = fake_boot_v3(image, archive)
        self.set_pair(observer, "raw_boot", self.observer, raw)
        self.set_pair(observer, "unsigned_avb", self.observer, fake_avb(raw))
        self.refresh_observer_evidence()
        self.save_profile()
        self.assert_rejected("changed a shared base entry")

    def test_signed_avb_payload_mismatch_and_identity_crossover_fail(self) -> None:
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        raw_record = observer["raw_boot"]
        assert isinstance(raw_record, dict)
        raw = (self.observer / str(raw_record["path_a"])).read_bytes()
        self.set_pair(observer, "unsigned_avb", self.observer, fake_avb(raw, algorithm=1))
        self.save_profile()
        self.assert_rejected("algorithm is not NONE")

        self.reset_fixture()
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        avb_record = observer["unsigned_avb"]
        assert isinstance(avb_record, dict)
        first = self.observer / str(avb_record["path_a"])
        payload = bytearray(first.read_bytes())
        payload[0] ^= 1
        self.set_pair(observer, "unsigned_avb", self.observer, bytes(payload))
        self.save_profile()
        self.assert_rejected("payload differs")

        self.reset_fixture()
        execution = self.profile["execution"]
        observer = self.profile["observer"]
        assert isinstance(execution, dict)
        assert isinstance(observer, dict)
        execution_raw = execution["raw_boot"]
        assert isinstance(execution_raw, dict)
        raw = (self.execution / str(execution_raw["path_a"])).read_bytes()
        self.set_pair(observer, "raw_boot", self.observer, raw)
        self.set_pair(observer, "unsigned_avb", self.observer, fake_avb(raw))
        self.refresh_observer_evidence()
        self.save_profile()
        self.assert_rejected("boot-v3 header is not exact")

    def test_boot_embedding_and_avb_geometry_are_bound(self) -> None:
        execution = self.profile["execution"]
        observer = self.profile["observer"]
        assert isinstance(execution, dict)
        assert isinstance(observer, dict)
        observer_image_record = observer["wrapper_image"]
        execution_initramfs_record = execution["recovery_initramfs"]
        assert isinstance(observer_image_record, dict)
        assert isinstance(execution_initramfs_record, dict)
        observer_image = (
            self.observer / str(observer_image_record["path_a"])
        ).read_bytes()
        full_initramfs = (
            self.execution / str(execution_initramfs_record["path_a"])
        ).read_bytes()
        hostile_raw = fake_boot_v3(observer_image, full_initramfs)
        self.set_pair(observer, "raw_boot", self.observer, hostile_raw)
        self.set_pair(observer, "unsigned_avb", self.observer, fake_avb(hostile_raw))
        self.refresh_observer_evidence()
        self.save_profile()
        self.assert_rejected("boot-v3 header is not exact")

        self.reset_fixture()
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        avb_record = observer["unsigned_avb"]
        assert isinstance(avb_record, dict)
        avb_path = self.observer / str(avb_record["path_a"])
        avb = bytearray(avb_path.read_bytes())
        raw_record = observer["raw_boot"]
        assert isinstance(raw_record, dict)
        raw_size = int(raw_record["size"])
        struct.pack_into("!Q", avb, len(avb) - 64 + 20, raw_size + 1)
        self.set_pair(observer, "unsigned_avb", self.observer, bytes(avb))
        self.save_profile()
        self.assert_rejected("AVB footer is not exact")

        self.reset_fixture()
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        avb_record = observer["unsigned_avb"]
        raw_record = observer["raw_boot"]
        assert isinstance(avb_record, dict)
        assert isinstance(raw_record, dict)
        avb_path = self.observer / str(avb_record["path_a"])
        avb = bytearray(avb_path.read_bytes())
        struct.pack_into("!Q", avb, int(raw_record["size"]) + 12, 1)
        self.set_pair(observer, "unsigned_avb", self.observer, bytes(avb))
        self.save_profile()
        self.assert_rejected("algorithm is not NONE")

        self.reset_fixture()
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        image_record = observer["wrapper_image"]
        initramfs_record = observer["recovery_initramfs"]
        assert isinstance(image_record, dict)
        assert isinstance(initramfs_record, dict)
        image = (self.observer / str(image_record["path_a"])).read_bytes()
        initramfs = (
            self.observer / str(initramfs_record["path_a"])
        ).read_bytes()
        raw = bytearray(fake_boot_v3(image, initramfs))
        raw[44] ^= 1
        self.set_pair(observer, "raw_boot", self.observer, bytes(raw))
        self.set_pair(observer, "unsigned_avb", self.observer, fake_avb(bytes(raw)))
        self.refresh_observer_evidence()
        self.save_profile()
        self.assert_rejected("command line is not exact")

    def test_descriptor_pinning_detects_content_and_pathname_races(self) -> None:
        path = self.base / "racy-input"
        expected = b"expected"
        path.write_bytes(expected)
        path.chmod(0o600)
        with self.assertRaisesRegex(
            ADMISSION.AdmissionError,
            "changed during verification",
        ):
            with ADMISSION.verified_descriptor(
                path,
                "racy input",
                expected_size=len(expected),
                expected_digest=digest(expected),
            ):
                path.write_bytes(b"mutated!")

        path.write_bytes(expected)
        detached = self.base / "detached-input"
        with self.assertRaisesRegex(
            ADMISSION.AdmissionError,
            "changed during verification",
        ):
            with ADMISSION.verified_descriptor(
                path,
                "racy input",
                expected_size=len(expected),
                expected_digest=digest(expected),
            ):
                path.rename(detached)
                path.write_bytes(expected)
                path.chmod(0o600)

        parent = self.base / "racy-parent"
        parent.mkdir()
        path = parent / "input"
        path.write_bytes(expected)
        path.chmod(0o600)
        detached_parent = self.base / "detached-parent"
        outside_parent = self.base / "outside-parent"
        outside_parent.mkdir()
        (outside_parent / "input").write_bytes(expected)
        (outside_parent / "input").chmod(0o600)
        with self.assertRaisesRegex(
            ADMISSION.AdmissionError,
            "ancestry changed during verification",
        ):
            with ADMISSION.verified_descriptor(
                path,
                "ancestor-racy input",
                expected_size=len(expected),
                expected_digest=digest(expected),
                expected_mode=0o600,
            ):
                parent.rename(detached_parent)
                parent.symlink_to(outside_parent, target_is_directory=True)

    def test_exact_modes_and_buffer_limits_fail_closed(self) -> None:
        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        record = execution["candidate_record"]
        assert isinstance(record, dict)
        (self.execution / str(record["path_b"])).chmod(0o400)
        self.assert_rejected("execution candidate record B mode changed")

        oversized = self.base / "oversized-buffered-input"
        with oversized.open("wb") as stream:
            stream.truncate(ADMISSION.MAX_BUFFERED_INPUT_BYTES + 1)
        oversized.chmod(0o600)
        with self.assertRaisesRegex(
            ADMISSION.AdmissionError,
            "buffered input exceeds its fixed limit",
        ):
            ADMISSION.read_safe_file(oversized, "oversized buffered input")

    def test_symlink_evidence_and_preissued_consumer_fail_closed(self) -> None:
        def insert_claim(profile: str) -> None:
            source = self.consumer.read_text(encoding="utf-8")
            marker = "\n}\n\n\nclass ClaimError"
            replacement = (
                f'\n    "{profile}": b"issued",' + marker
            )
            self.assertIn(marker, source)
            self.consumer.write_text(
                source.replace(marker, replacement, 1),
                encoding="utf-8",
            )

        execution = self.profile["execution"]
        assert isinstance(execution, dict)
        record = execution["wrapper_image"]
        assert isinstance(record, dict)
        path = self.execution / str(record["path_b"])
        target = self.base / "outside-image"
        path.replace(target)
        path.symlink_to(target)
        self.assert_rejected("unsafe or missing execution wrapper Image B")

        self.reset_fixture()
        insert_claim("host-rendezvous-v3-observer-v1")
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        claims["consumer_size"] = self.consumer.stat().st_size
        claims["consumer_sha256"] = digest(self.consumer.read_bytes())
        self.save_profile()
        self.assert_rejected("registry is not exact")

        self.reset_fixture()
        self.consumer.write_text(
            self.consumer.read_text() + "CLAIMS['late-profile'] = b'issued'\n"
        )
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        claims["consumer_size"] = self.consumer.stat().st_size
        claims["consumer_sha256"] = digest(self.consumer.read_bytes())
        self.save_profile()
        self.assert_rejected("registry is mutated after definition")

        self.reset_fixture()
        self.consumer.write_text(
            self.consumer.read_text(encoding="utf-8").replace(
                "\n\n\nclass ClaimError",
                "\n\nCLAIMS_ALIAS = CLAIMS\n\nclass ClaimError",
                1,
            ),
            encoding="utf-8",
        )
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        claims["consumer_size"] = self.consumer.stat().st_size
        claims["consumer_sha256"] = digest(self.consumer.read_bytes())
        self.save_profile()
        self.assert_rejected("registry is aliased or rebound")

        self.reset_fixture()
        insert_claim("unreviewed-live-v1")
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        claims["consumer_size"] = self.consumer.stat().st_size
        claims["consumer_sha256"] = digest(self.consumer.read_bytes())
        self.save_profile()
        self.assert_rejected("registry is not exact")

        self.reset_fixture()
        insert_claim("headless-diagnostic-generation11-live-v1")
        claims = self.profile["claims"]
        assert isinstance(claims, dict)
        claims["consumer_size"] = self.consumer.stat().st_size
        claims["consumer_sha256"] = digest(self.consumer.read_bytes())
        self.save_profile()
        self.assert_rejected("registry is not exact")

    def test_observer_evidence_fields_are_exact(self) -> None:
        observer = self.profile["observer"]
        assert isinstance(observer, dict)
        evidence_record = observer["wrapper_evidence"]
        assert isinstance(evidence_record, dict)
        evidence_path = self.observer / str(evidence_record["path"])
        lines = evidence_path.read_text().splitlines()
        lines.insert(-1, "extra=unreviewed")
        self.set_single(
            observer,
            "wrapper_evidence",
            self.observer,
            ("\n".join(lines) + "\n").encode("ascii"),
        )
        self.save_profile()
        self.assert_rejected("does not bind the offline role")

    def test_repository_profile_and_verifier_are_registered_but_not_live(self) -> None:
        self.assertTrue(VERIFIER.is_file())
        self.assertTrue(PROFILE.is_file())
        source = VERIFIER.read_text(encoding="utf-8")
        self.assertNotIn("ALLOW_TEMPORARY_BOOT", source)
        self.assertNotIn("/usr/bin/fastboot", source)
        self.assertNotIn("subprocess.Popen", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("os.exec", source)
        self.assertNotIn("generation13", source.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
