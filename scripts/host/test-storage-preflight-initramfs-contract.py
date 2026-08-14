#!/usr/bin/env python3
"""Offline contract tests for the sealed storage-preflight initramfs."""

from __future__ import annotations

from pathlib import Path
import stat
import unittest


REPO = Path(__file__).resolve().parents[2]
BUILDER = REPO / "scripts/device/build-storage-preflight-initramfs.sh"
VERIFIER = REPO / "scripts/device/verify-storage-preflight-initramfs.sh"
RUNTIME_VERIFIER = (
    REPO / "scripts/device/verify-storage-preflight-arm64-runtime.sh"
)


class StoragePreflightInitramfsContractTest(unittest.TestCase):
    def source(self, path: Path) -> str:
        self.assertTrue(path.is_file())
        self.assertFalse(path.is_symlink())
        self.assertTrue(path.stat().st_mode & stat.S_IXUSR)
        return path.read_text(encoding="utf-8")

    def test_builder_pins_every_input_and_is_deterministic(self) -> None:
        source = self.source(BUILDER)
        for digest in (
            "da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d",
            "b37f3d8ce629ee38132e308ef0c7e6e6d661e308c02975718a69ceb94136dcb5",
            "5eb2037c453c870f31a1db4f1235f8ac2a27f8d401421cb5662f2ff6f1bea94b",
            "369aaa6e9d099a737bad6dd3e6c2fe7bb1547ca26d22b94ee0411228f709b403",
            "2302e766d4e4926038ec166ecb85837ee884576115236ddb565e3a5fca4a11d7",
            "5e9674b7f41152fe2119093b5cb4c13eaaadb19c2d5422b2d7267913e663ee6e",
            "d2f69552b05184ba205dbc8aa0e79f8a080fcf746ec5e5e25eb89d66fbbe6db6",
        ):
            self.assertEqual(source.count(digest), 1)
        for contract in (
            '[ ! -e "$output" ] && [ ! -L "$output" ]',
            "find . -mindepth 1 -print0 | sort -z",
            "cpio --null -o --quiet --format=newc --owner=0:0 --reproducible",
            "gzip -n",
            "mv -T -- \"$temporary\" \"$output\"",
            "printf '%s\\n' storage-preflight-v2",
            "chmod 0444 \"$stage/etc/rog5/recovery-mode\"",
        ):
            self.assertIn(contract, source)

    def test_builder_removes_control_and_credentials(self) -> None:
        source = self.source(BUILDER)
        for path in (
            "etc/ssh",
            "root/.ssh",
            "usr/sbin/sshd",
            "usr/libexec/rog5-recovery-control",
            "usr/libexec/rog5-bundle-fetch",
            "usr/libexec/rog5-bundle-verify",
            "usr/sbin/kexec",
            "etc/rog5/recovery-bundle-ed25519.pub",
        ):
            self.assertIn(path, source)
        self.assertIn("BEGIN .*PRIVATE KEY", source)
        self.assertIn("-perm /6000", source)

    def test_builder_and_verifier_reject_mutation_contracts(self) -> None:
        for path in (BUILDER, VERIFIER):
            source = self.source(path)
            compact = "".join(source.splitlines())
            for token in (
                "sgdisk[[:space:]].*--(delete|new|zap)",
                "blockdev[[:space:]]+--setrw",
                'resize2fs[[:space:]]+"\\$userdata"',
                'mkfs\\.ext4[[:space:]]+"\\$',
            ):
                self.assertIn(token, compact)

    def test_verifier_requires_exact_mode_tools_and_read_only_commands(self) -> None:
        source = self.source(VERIFIER)
        for contract in (
            "storage-preflight-v2",
            "usr/bin/sgdisk",
            "sbin/e2fsck",
            "usr/sbin/resize2fs",
            "usr/sbin/dumpe2fs",
            "sbin/mkfs.ext4",
            "usr/sbin/partprobe",
            '/usr/bin/sgdisk -v "$disk"',
            '/sbin/e2fsck -fn "$userdata"',
            '/usr/sbin/resize2fs -P "$userdata"',
            "ROG5_STORAGE_PREFLIGHT_V2 status=RUNNING",
            "ROG5_STORAGE_PREFLIGHT_V2 status=FAIL",
            "ROG5_STORAGE_PREFLIGHT_V2 status=PASS",
            "all_read_only=1 block_mounts=0",
        ):
            self.assertIn(contract, source)
        self.assertIn("cmp \"$stage/init\" \"$init\"", source)

    def test_arm64_runtime_verifier_executes_every_sealed_tool(self) -> None:
        source = self.source(RUNTIME_VERIFIER)
        for contract in (
            '"$(id -u)" -eq 0',
            'chroot "$stage" /usr/bin/qemu-aarch64-static',
            "sgdisk --clear --new=1:2048:0 --typecode=1:8300",
            "guest /usr/bin/sgdisk -v /run/fixtures/disk.img",
            "guest /sbin/e2fsck -fn /run/fixtures/ext4.img",
            "guest /usr/sbin/resize2fs -P /run/fixtures/ext4.img",
            "guest /usr/sbin/dumpe2fs -h /run/fixtures/ext4.img",
            "guest /sbin/mkfs.ext4 -V",
            "guest /usr/sbin/partprobe --help",
        ):
            self.assertIn(contract, source)


if __name__ == "__main__":
    unittest.main()
