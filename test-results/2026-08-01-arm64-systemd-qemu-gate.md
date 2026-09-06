# ARM64 systemd QEMU gate

Date: 2026-08-01

Status: local hardware-free acceptance passed; GitHub rerun pending

Successor note (2026-08-08): the ordering-stub limitation recorded below is
closed by the real OpenSSH loopback gate. The current harness requires a
disposable Ed25519 key login, authenticated command execution, and rejection
of a keyless login before accepting stage 140. The text below remains the
historical result of the original 2026-08-01 run.

## Result

The pinned upstream Linux 7.1.4 QEMU kernel now boots the sealed AArch64
runtime, enters Arch `systemd 260.2-2-arch` as PID 1, loads the exact
production-generated diagnostic units, and executes their stage 130 and stage
140 commands. The canonical write-only reporter stream crossed stages 10, 120,
130, and 140 in order.

This closes the hardware-free systemd execution gap. It does not prove the
ROG Phone DTB, Qualcomm hardware, USB/NCM, real OpenSSH, credentials, or phone
rollback. The test `sshd.service` is an ordering stub; it proves that the
post-sshd diagnostic unit is ordered and executed by systemd, not that an SSH
daemon accepted a connection.

## Root cause and correction

The original `tinyconfig` image omitted three systemd runtime primitives:

- `CONFIG_FUTEX`: without it, glibc aborted during systemd's first
  `pthread_once()`;
- `CONFIG_MEMFD_CREATE`: without it, systemd could not create its executor
  serialization stream; and
- `CONFIG_SHMEM` plus `CONFIG_TMPFS`: without shmem, the requested TMPFS option
  resolved off and memfd sealing returned `EINVAL`.

The kernel builder now enables and verifies all four resolved symbols after
`olddefconfig`. The QEMU cache key already includes the builder hash, so the
corrected profile cannot reuse the preceding kernel image.

## Evidence

- Linux source: tag `v7.1.4`, commit
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`.
- Corrected local QEMU `Image` SHA-256:
  `cf318b26245fffd95a5661646c3c9111085ffd9ee4893ea2152b54310b9b4d98`.
- Sealed ARM64 systemd runtime: 9,628,993 bytes, SHA-256
  `5011267029d8da251c20e66f232cce2f36530e09d18a36e0a492018255f178f7`.
- Runtime closure: 17 AArch64 ELF files with recursive `DT_NEEDED` closure and
  the required `libmount.so.1` dlopen dependency.
- Clean local handoff result:
  `PASS canonical reporter stream crossed real systemd units` followed by
  `PASS generated diagnostic units executed under ARM64 systemd`.
- `scripts/host/test-qemu-system-smoke-contract.sh`, the kernel-to-initramfs
  smoke, the clean systemd handoff, and `scripts/host/test-repository-linux.sh
  ci` all passed.

No phone was contacted. No credential, signing key, fastboot operation,
storage write, or boot authority was used.
