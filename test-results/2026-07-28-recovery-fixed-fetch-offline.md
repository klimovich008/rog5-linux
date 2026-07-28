# Fixed recovery bundle fetch offline result

Date: 2026-07-28

Result: **PASS OFFLINE; RESPONDER-INTEGRATED; NO LIVE AUTHORITY**

The recovery-side helper now acquires one requested signed-bundle candidate
from a fixed USB-NCM peer without HTTP, DNS, redirects, a shell, or a
caller-provided path. The recovery responder now invokes it as the first
`PREPARE` stage under a fixed outer deadline and the rollback watchdog. A
production host server and initramfs integration remain absent. This
checkpoint did not connect to, boot, reboot, flash, or otherwise act on the
phone. It did not create or use a production signing key.

## Boundary implemented

The privileged parent:

1. opens and nonblockingly locks the fixed RAM-only bundle root;
2. rejects unknown, linked, unsafe, or over-quota root inventory;
3. safely removes only recognized stale staging files;
4. binds `usb0` and source `169.254.77.2`, then connects only to
   `169.254.77.1:8080`;
5. creates one staging directory and forks one worker;
6. kills and definitively reaps a failed or timed-out worker while retaining
   the root lock;
7. independently checks the exact inventory, canonical manifest, requested
   manifest hash, sizes, and all three artifact hashes;
8. locks the directory to root-owned mode `0500`, changes the five files to
   root-owned mode `0400`, then reopens and revalidates the complete normalized
   tree; and
9. publishes with `renameat2(RENAME_NOREPLACE)` plus directory sync.

The worker receives only the connected socket as descriptor 3 and staging
directory as descriptor 4. It captures the parent PID before `fork`, installs
and re-installs `PR_SET_PDEATHSIG=SIGKILL` around the credential transition,
closes every other descriptor, chroots into staging, clears supplementary
groups and all capability sets, changes to UID/GID 65534, enables
`no_new_privs`, and installs a classic-BPF syscall allowlist before parsing
network bytes.

The one-connection stream uses a four-byte big-endian length and exact
canonical ASCII request/response records. The response then contains
`manifest`, `manifest.sig`, `Image`, `board.dtb`, and
`initramfs.cpio.gz` in that order, followed by required EOF. Every object is
streamed to an `O_EXCL|O_NOFOLLOW|O_CLOEXEC` file under one absolute
deadline. The compressed allocation is bounded to approximately 386 MiB; the
later fetched-plus-sealed boundary remains approximately 772 MiB.

The responder directly executes the fixed fetcher path with only the bundle
ID and manifest hash. Its 65-second outer deadline exceeds the helper's
60-second data-path deadline and is checked together with the pinned rollback
watchdog. Only fetcher exit zero reaches the verifier. Exit 42 becomes the
immutable `BUNDLE_ID_CONFLICT` response; every other exit, signal, or timeout
becomes `FETCH_FAILED`. The fetcher, verifier, and descriptor-only kexec
loader execute in that exact order.

## Offline tests

| Suite | Result |
|---|---:|
| native host suite | 28 passed |
| network-disabled root-container suite | 28 passed |
| static AArch64/QEMU suite | 23 passed, 5 intentionally skipped |
| reproducible AArch64 production builds | 2 byte-identical builds |
| responder reference model | 48 passed |
| native responder pipeline | 53 passed |
| static AArch64/QEMU responder pipeline | 53 passed |
| reproducible AArch64 responder builds | 2 byte-identical builds |

QEMU user mode cannot safely apply an AArch64 seccomp filter to the
x86-64 emulator syscall stream. Therefore QEMU skips seccomp and
process-introspection cases; both native suites exercise the real filter, and
the root suite additionally exercises chroot, UID/GID 65534, zero effective,
permitted, bounding, and ambient capabilities, and parent death after the
credential drop.

Coverage includes:

- exact fragmented request/response framing and every canonical-header
  mutation;
- overflow and all artifact size/hash mismatches;
- truncation in the frame prefix, header, and every body;
- body reordering, trailing bytes, second frames, reset, timeout, and
  slowloris behavior;
- simulated `ENOSPC` after the first partial write of every artifact;
- fixed manifest identity and timeout-schema boundaries;
- atomic invisibility until complete publication;
- crash/retry at every parent validation, normalization, directory-sync, and
  rename boundary;
- safe stale-stage cleanup and unsafe extra, symlink, hardlink, subdirectory,
  owner/mode, final, and root mutations;
- existing-final exact reuse, same-ID/hash conflict, another-bundle quota,
  and concurrent-helper exclusion;
- worker UID/GID, descriptors, capabilities, `no_new_privs`, seccomp, and a
  forbidden-syscall kill;
- parent death while blocked in the header and every response body, followed
  by safe stale-stage recovery; and
- repeated reset failure without live process or descriptor growth;
- exact fetch-before-verifier-before-loader ordering;
- immutable replay of fetch failure and permanent bundle-ID conflict without
  a second acquisition attempt, including a changed request ID;
- proof that fetch failure never invokes verifier, loader, unload, or
  executor;
- outer timeout of a fetch helper blocked while reaping its own
  `PDEATHSIG`-bound worker;
- rollback-watchdog death during that same nested fetch lifecycle; and
- abrupt responder `SIGKILL` propagation through the fetcher to the nested
  worker.

Both production and test C builds pass `-Wall -Wextra -Werror -Wpedantic`;
the production translation unit passes GCC `-fanalyzer`. Shell entry points
pass syntax validation, ShellCheck, and `git diff --check`. The production
builder rejects endpoint/path/timeout/identity/crash/write/seccomp test
overrides, dynamic interpreters, executable stacks, shell paths, and HTTP
tokens.

## Independent security review

The first independent review returned `DO-NOT-COMMIT` for three publication
and lifecycle defects, plus two hardening recommendations. The implementation
now:

- makes the staging directory root-owned and non-writable before final
  normalization, then reopens, rehashes, and revalidates the complete
  publication tree under its final ownership and modes;
- treats an unprovable descriptor closure or any unexpected close failure as
  fatal;
- sends `SIGKILL` and definitively reaps the worker while retaining the root
  lock;
- arms and checks `PDEATHSIG` as the child's first operation and re-arms it
  after the credential transition; and
- drops the runtime kernel capability bounding set until the kernel reports
  the end of the supported capability range.

The second review confirmed four findings closed but correctly rejected an
unbounded blocking reap as the helper's only deadline. The responder
integration resolves that process-boundary problem: the helper retains the
root lock until normal definitive reap, while the responder independently
bounds the entire helper and its `PDEATHSIG`-bound worker under the rollback
watchdog. A final focused reinspection confirmed both abrupt parent-death
cleanup and changed-request-ID refetch refusal, found no remaining must-fix
issue in this scope, and returned `COMMIT`.

## Reproducible identities

| Item | Identity |
|---|---|
| AArch64 builder ID | `d5fb16636fadea937b74dc3e062617d74a12577fd3fcc3f61fec24d0f7364495` |
| AArch64 builder digest | `sha256:750150c51c8b5085d322ecaa5363356bb31ee243d6efab1035bd15f5ffe52355` |
| fetcher source SHA-256 | `4e4f5eef9c9587bf2d2957f62677a0f883c24fbc1a3d14141935dd7b34b71c58` |
| fetcher AArch64 binary SHA-256 | `ca8c9fcef9153de850d3476383c13fe5e3441e2fb95e7acd07041e42f7cc052f` |
| responder source SHA-256 | `fa28285ffda05915f9f73f418f26a6ec557270767011fce77aef1fdd43fd37a4` |
| responder AArch64 binary SHA-256 | `479ac6c7e0269a0ebb67e6c07745216ae37e79c61da60a3a862c51194a3b67ea` |
| root-test image ID | `34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941` |
| root-test image digest | `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c` |

These are offline checkpoint identities, not a live allowlist.

## Remaining gates

1. Add a fixed read-only host-serving command for the canonical stream.
2. Include the fetcher, verifier, responder, pinned kexec-tools, runtime
   libraries, and separately approved public key in one shell-free initramfs.
3. Re-run the complete offline image suite, then perform the separately
   authorized staging-only promotion sequence.

## Commands

```text
python3 scripts/host/test-recovery-fetch-native.py
scripts/host/test-recovery-fetch-root.sh
scripts/host/test-recovery-fetch-aarch64.sh
python3 scripts/host/test-recovery-control-reference.py
python3 scripts/host/test-recovery-control-native.py
scripts/host/test-recovery-control-aarch64.sh
scripts/host/test-repository-linux.sh quick
git diff --check
```
