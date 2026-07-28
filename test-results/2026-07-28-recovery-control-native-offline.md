# Native recovery control responder offline result

Date: 2026-07-28

Result: **PASS OFFLINE; NOT AN IMAGE; NO LIVE AUTHORITY**

The fixed-function native protocol core is implemented in
`tools/recovery_control/rog5-recovery-control.c`. It owns a raw/no-echo TTY,
accepts only the four canonical protocol verbs, persists private immutable
prepare/claim/execution markers, keeps a bounded non-evicting replay ledger,
and invokes only the fixed production `kexec -e` path without a shell.

The production compile deliberately rejects every `PREPARE`. Signed bundle,
payload, DTB, path and structured command-line verification remain mandatory
before the responder can load or execute a production payload.

## Test coverage

The 35 pseudo-terminal tests pass both as a native host build and as a real
static AArch64 binary under `qemu-aarch64-static`. They cover:

- delayed TTY creation, byte-at-a-time request writes, byte-at-a-time response
  reads, coalesced frames, raw/no-echo termios and reconnect after malformed
  input;
- bounded incomplete-prefix/body reads, forced one-byte response writes,
  real PTY output starvation, bounded output drain and fail-closed timeout;
- shell text, bad lengths, oversize frames, bad terminators and non-ASCII
  input without any state transition or execution;
- device-minted session persistence, exact replay, changed-body conflict,
  cross-verb request-ID conflict, stale sessions, same-bundle prepare conflict
  and native/reference differential responses;
- crashes after durable prepare, before claim, after claim, after drained
  response and after the execution-started marker;
- disconnect before a complete commit and after the atomic claim but before
  reply, with no execution;
- a private PID/start-time watchdog lease pinned by pidfd, including stale
  startup identity, watchdog death while ACM is absent or idle, before
  response, and after the execution marker;
- responder restart with retained state, reconstructed authoritative
  transaction replies and no replay-ledger overflow;
- read-only status at ledger capacity, two transaction-reserved ledger slots,
  and immutable decisions rendered with current state after failure;
- crashes around write, file fsync, link, unlink, rename, and directory fsync,
  for prepare, claim, execution, failure, request-decision, and last-error
  publication, with conservative state reconstruction;
- one immutable execution marker, no re-execution after restart and permanent
  `EXEC_FAILED` state when the executor returns;
- private file/directory modes, weak directory rejection, symlinked state-root
  rejection and no-follow handling for state records; and
- source/binary proof that no shell launcher, test hook or path override is
  present in the production compile.

The reference oracle now also persists the prepare fingerprint and covers the
previously unmodeled crash after durable prepare but before replay-record
publication. Its focused suite contains 46 passing tests.

## AArch64 reproducibility

`scripts/host/test-recovery-control-aarch64.sh` builds the production binary
twice in the pinned local Alpine 3.24 ARM64 build image, compares the outputs,
builds the test-only AArch64 variant, and runs the complete PTY suite through
QEMU.

| Item | Identity |
|---|---|
| build image digest | `sha256:750150c51c8b5085d322ecaa5363356bb31ee243d6efab1035bd15f5ffe52355` |
| responder source SHA-256 | `c5ea350f4e86f52e1db8ffe5c3fa520d382d351d9b47e084eb4032620cb8042a` |
| production AArch64 binary SHA-256 | `205bd6cb4a7bc05f7194700512415aae2235ffa19349db1593788015ec717633` |

The two production outputs are byte-identical static-PIE, stripped AArch64
ELF binaries with RELRO, a non-executable stack, no interpreter, no build ID,
and mode `0755`. The runner rejects any build-image ID or digest other than
the committed pair above. The builder accepts only a regular non-symlink
source and compiles inside an exclusive private temporary directory.

## Commands

```text
python3 scripts/host/test-recovery-control-reference.py
python3 scripts/host/test-recovery-control-native.py
scripts/host/test-recovery-control-aarch64.sh
scripts/host/test-repository-linux.sh quick
git diff --check
```

## Boundary

No phone was booted, rebooted or flashed. No initramfs, wrapper, AVB image,
allowlist or signing credential was changed. The accepted v18 image remains
the legacy staging transport, and its interactive shell remains prohibited
for new payload execution.

The next offline gate is signed-manifest, size/hash, DTB, path and structured
command-line mutation testing. Only after that verifier is wired into the
production responder may the three interactive initramfs shells be removed
and one new recovery candidate be reproducibly frozen.

The production `fork`/`execve("/usr/sbin/kexec", ...)` branch is compiled,
checked for a fixed path and absence of shell/test hooks, and monitors the
watchdog before fork, in the child before exec, and while the parent waits.
It cannot be end-to-end exercised while production `PREPARE` always rejects.
Fork, exec, wait and signed-verifier fault injection therefore remain explicit
work for the next offline gate.
