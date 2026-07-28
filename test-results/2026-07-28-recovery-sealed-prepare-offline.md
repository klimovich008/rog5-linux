# Sealed recovery PREPARE offline result

Date: 2026-07-28

Result: **PASS OFFLINE; NOT IN AN IMAGE; NO LIVE AUTHORITY**

The recovery responder now connects signed-bundle verification to a bounded
load-only `PREPARE` path without reopening an artifact pathname. The verifier
copies the kernel, DTB, and compressed initramfs into private write-sealed
`memfd` snapshots, verifies those exact immutable bytes, and transfers their
descriptors with one canonical plan over a private Unix `SOCK_SEQPACKET`
channel. The responder validates the plan and all three descriptors, then a
bounded watchdog-supervised child directly executes the fixed equivalent of:

```text
/usr/sbin/kexec -c -l /proc/self/fd/<kernel-fd>
    --initrd=/proc/self/fd/<initramfs-fd>
    --dtb=/proc/self/fd/<dtb-fd>
    --command-line=<verified-generated-command-line>
```

`PREPARED` is persisted only after the loader exits zero. Every failed,
timed-out, or returned load path and every non-prepared startup runs fixed
`kexec -c -u` before continuing. This checkpoint does not execute a loaded
kernel. It did not connect to, reboot, boot, or flash the phone; create or use
a production signing key; modify an initramfs or AVB wrapper; or change a live
allowlist.

## Exact-object boundary

The production verifier's only mode switch is `--handoff-fd3`. Descriptor 3
must be a same-UID/GID Unix `SOCK_SEQPACKET` peer. For each artifact the
verifier:

1. opens the fixed bundle basename under the already constrained bundle
   directory;
2. copies exactly the signed size and requires EOF;
3. removes write mode bits from the private snapshot;
4. applies and rechecks `F_SEAL_SEAL`, `F_SEAL_SHRINK`, `F_SEAL_GROW`, and
   `F_SEAL_WRITE`;
5. proves a write is rejected;
6. verifies the signed hash and the Image, FDT, or gzip/newc policy against
   that sealed descriptor; and
7. rewinds it before handoff.

The source descriptors close before authorization. Source-path replacement
after the copy cannot change the snapshot. In-place mutation during or before
the copy changes the bytes authorized by the signed hash and fails
verification. The maximum compressed snapshot allocation is bounded by the
three signed role limits: 128 MiB kernel + 2 MiB DTB + 256 MiB initramfs =
386 MiB. The accepted stage configuration already records
`CONFIG_MEMFD_CREATE=y` in
`artifacts/recovery-stage-v18/config-5.4.210-kexec-stage-builtin-recovery`;
image construction must reassert that prerequisite.

One atomic packet carries the canonical plan and exactly three
`SCM_RIGHTS` descriptors in kernel/DTB/initramfs order. The responder receives
with `MSG_CMSG_CLOEXEC` and rejects truncated data or control records,
additional ancillary records, any descriptor count other than three,
non-regular or linked files, writable mode bits, missing or extra seals,
aliased files, unsafe ownership, nonzero offsets, role-size violations,
verifier failure, and any plan/request mismatch. Its ancillary buffer holds
Linux's full 253-descriptor `SCM_RIGHTS` maximum so it can close every
descriptor the kernel installs for malformed zero-data, short, or over-count
packets.

Only the loader child clears close-on-exec. `-c` selects legacy
`kexec_load`, matching the accepted ASUS 5.4 staging kernel and preserving the
separately supplied DTB. The parent never reopens a bundle pathname, monitors
the verifier and loader under fixed deadlines, and kills and boundedly reaps a
child before any watchdog-fatal exit.

## Replay and crash policy

Three replay-ledger slots are protected while the responder is idle. This
leaves room to persist one failed `PREPARE` decision exactly once, or to
persist a successful `PREPARE` and its exact `COMMIT_EXEC`. At the boundary:

- a failed first `PREPARE` records `VERIFY_FAILED`;
- exact replay returns that decision without rerunning the verifier;
- a different new mutation returns `LEDGER_FULL` without running the
  verifier; and
- after preparation, only the matching commit may consume the remaining
  transaction capacity.

A crash after a successful load but before `PREPARED` publication leaves the
transaction idle. Startup first unloads any kernel-side image, then exact
retry may load the same immutable, signed content again but cannot execute it.
A crash after durable `PREPARED` reconstructs the transaction and does not
rerun verification or loading. `COMMIT_EXEC` remains the sole non-retryable
execution boundary.

## Offline tests

All tests passed on the x86-64 host. The verifier and responder suites also
passed as real static AArch64 binaries under `qemu-aarch64-static`.

| Suite | Result |
|---|---:|
| protocol/ledger reference model | 47 passed |
| native signed-bundle verifier | 21 passed |
| native responder/PTTY/PREPARE boundary | 49 passed |
| AArch64/QEMU verifier | 21 passed |
| AArch64/QEMU responder/PTTY/PREPARE boundary | 49 passed |

Coverage added by this checkpoint includes:

- source pathname replacement and in-place overwrite without changing the
  received sealed snapshot;
- exact snapshot seals, private unlinked identity, mode, offset, order, and
  close-on-exec state;
- wrong descriptor count, a fourth rights descriptor, zero-data rights,
  16- and 253-descriptor rights packets, unsafe directory descriptors,
  aliases, unsealed memory files, nonzero offsets, malformed plans, and
  nonzero verifier exit;
- repeated malformed-rights requests and a successful PREPARE with a stable
  responder descriptor count;
- verifier/loader failure and timeout, watchdog death during either child,
  and proof that recorded child PIDs no longer exist;
- `PREPARED` publication only after a successful load;
- loaded-then-timeout unload, crash-after-load startup reconciliation, and
  safe exact retry;
- fixed-executor return unload plus bounded kill/reap on watchdog death; and
- the three-slot ledger boundary, one recorded failure, and verifier-free
  replay/full rejection.

Both C translation units pass GCC `-Wall -Wextra -Werror -fanalyzer`. The
modified shell entry points pass ShellCheck and syntax validation.
`git diff --check` passes. Production builders reject test hooks, path
overrides, dynamic interpreters, executable stacks, shell paths, and
shell-style execution strings.

## Reproducible AArch64 identities

Each production binary was built twice in its pinned Alpine 3.24 arm64
builder and compared byte for byte before QEMU execution.

| Item | Identity |
|---|---|
| verifier builder ID | `e2e90f8ad3cfc4f9b7660ee8828fcae008792f05567fb9b4efd3ab0102063d8e` |
| verifier builder digest | `sha256:b4946b74324785d005aa3067dd18788f90cc65215a519c8735dce03aa01d1268` |
| verifier source SHA-256 | `6fc8afd4d67204b28923916041a33133fa88d2b9eef65fab872bf748ede5c6ae` |
| verifier binary SHA-256 | `ce0f2d997c0243b43e417a41fb5daadd89dfde7b2738ce3bb2e33783ba403b4c` |
| responder builder ID | `d5fb16636fadea937b74dc3e062617d74a12577fd3fcc3f61fec24d0f7364495` |
| responder builder digest | `sha256:750150c51c8b5085d322ecaa5363356bb31ee243d6efab1035bd15f5ffe52355` |
| responder source SHA-256 | `d8d380cbe88798c7b898bbbbb04f099a2d29a13a7f6269731004b1b4805d620c` |
| responder binary SHA-256 | `26e0b5d291738548ed095ad9e71f75dcc607d0873cc5a231f1987e0d0363b1d5` |

These are offline checkpoint identities, not a live allowlist.

## Independent review

Independent security and kexec-path reviews found four must-fix issues in the
first implementation: mutable regular-file descriptors, descriptor leaks on
malformed `SCM_RIGHTS`, potentially orphaned or blocking child cleanup, and a
ledger boundary that could repeatedly perform an expensive failed
verification. The sealed snapshots, full ancillary drain/close path, bounded
kill/reap path, and three-slot ledger rule above close those findings. The
kexec-path review also confirmed that this project's accepted stage and
pinned kexec-tools require `-c` for custom-DTB legacy loading and that
`/proc/self/fd` paths remain valid across the loader `execve`.

A subsequent full-source Opus review confirmed those four fixes and found two
remaining state/cleanup gaps: the production `kexec -e` child still used an
unbounded blocking reap, and a load that won a timeout/crash race could remain
present while persistent state was idle or consumed. The production executor
now shares the fixed-path behavioral test seam and bounded kill/reap helper.
Failed/timed-out loads, returned execution, and non-prepared startup all run
fixed bounded unload reconciliation. Host and AArch64/QEMU tests exercise
loaded-then-timeout, crash/restart, returned-executor, and watchdog-death
paths. A focused Opus re-review found no remaining must-fix issue and
recommended commit; its small descriptor-initialization, bounded-copy, and
additional cleanup-test suggestions are included here.

## Remaining gates

This is not ready for recovery-image integration or live execution. The next
required work is:

1. add the production host-serving command; fixed acquisition and atomic
   publication are integrated with `PREPARE` in the later
   [fixed-fetch result](2026-07-28-recovery-fixed-fetch-offline.md);
2. integrate the pinned fetcher, verifier, responder, Alpine arm64
   `kexec-tools 2.0.32-r2`, its runtime libraries, and a separately approved
   public key into one initramfs;
3. prove `/proc`, `/proc/self/fd`, `/sys/kernel/kexec_loaded`, the watchdog,
   and loader dependencies are ready before USB bind;
4. in a separately authorized staging-only load gate, prove the real pinned
   AArch64 loader changes `kexec_loaded` from 0 to 1 through the procfd
   invocation, repeat the same load, then prove `kexec -c -u` returns it from
   1 to 0 without executing either target;
5. repeat that gate with a loaded-then-timeout and crash/restart to prove the
   offline unload/reconciliation policy against the real kernel;
6. remove all interactive recovery/network-root/persistent-root shells in the
   same image change and update the image verifiers;
7. reproducibly freeze one candidate and use the existing staging-only
   promotion sequence; and
8. request confirmation before creating or using any production signing
   credential.

## Commands

```text
python3 scripts/host/test-recovery-control-reference.py
python3 scripts/host/test-recovery-bundle-native.py
python3 scripts/host/test-recovery-control-native.py
scripts/host/test-recovery-bundle-aarch64.sh
scripts/host/test-recovery-control-aarch64.sh
scripts/host/test-repository-linux.sh quick
git diff --check
```
