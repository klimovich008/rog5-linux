# Early-target diagnostic successor

## Decision

The next target must be a distinct `diagnostic-initramfs-v1` bundle. It must
not reuse `headless-ssh-network-root-v3-r2`, and it must not be accepted as a
normal headless runtime.

The 2026-08-01 r2 cycle proved recovery transfer, PREPARE, one COMMIT, Linux
7.1 USB-NCM enumeration, watchdog rollback, and signed fallback return. The
target gadget physically disconnected 23 seconds after enumeration, before
SSH host-key acceptance. Every current initramfs failure after USB invokes an
immediate reset, so timing alone cannot distinguish an NFS, seal, overlay,
handoff, `switch_root`, systemd, or gadget failure. No pstore record survived.

The diagnostic successor keeps the accepted Linux 7.1 Image, corrected DTB,
and sealed NFS root. Its only functional delta is a bounded, receive-disabled
ACM progress stream and diagnostic-only failure dwell. This is a measurement
candidate, not a runtime candidate.

## Channel

The target ConfigFS gadget exposes NCM plus ACM under a diagnostic-only USB
product string. The NCM function and `/30` path remain unchanged. The ACM
function has no shell, login, command parser, or request path.

A small statically linked reporter starts before any operation that can block.
It:

- opens `/dev/ttyGS0` raw, without a controlling terminal;
- ignores and never interprets host input;
- emits canonical netstring frames at a fixed 250 ms cadence;
- binds every frame to the diagnostic candidate and current kernel boot ID;
- includes a strictly increasing sequence, monotonic timestamp, current and
  last-good stages, watchdog deadline, and dropped-update counter;
- accepts local stage updates only through a nonblocking abstract Unix
  datagram socket and requires kernel-supplied root peer credentials;
- performs no storage, network, mount, reboot, or gadget mutation; and
- remains alive through `switch_root` without loading files or libraries.

The abstract socket is bound in the initramfs before untrusted userspace can
run, and this reporter instance is never restarted after `switch_root`. A bind
failure therefore fails before `reporter-up` and leaves watchdog rollback
armed. Each receive pass is bounded so rejected local traffic cannot starve
the ACM heartbeat, and any received file descriptors are closed and rejected.

The reporter and initramfs must treat the last received frame as a lower bound
on progress. ACM and NCM share the UDC, PHY, role state, and USB cable, so ACM
cannot prove survival below the gadget layer. Host USB journal timestamps are
part of the evidence and distinguish reporter silence from physical device
departure as far as the shared transport permits.

## Minimal stage vocabulary

Stage codes are monotonic. A later code may never be replaced by an earlier
code. The host classifies by the greatest valid code observed for one boot.

| Code | Name | Boundary proved |
|---:|---|---|
| 10 | `reporter-up` | static reporter and local update socket exist |
| 20 | `gadget-configured` | diagnostic NCM/ACM ConfigFS tree is complete |
| 30 | `udc-bound` | the selected UDC accepted the gadget |
| 40 | `ncm-interface-up` | `usb0` exists and is administratively up |
| 50 | `address-configured` | target owns only `169.254.77.2/30` |
| 60 | `ncm-carrier-up` | host and target observe carrier |
| 70 | `nfs-mount-begin` | the bounded NFSv4.2 mount call is entered |
| 80 | `nfs-mount-ok` | the read-only lower is mounted |
| 90 | `seal-verify-ok` | the complete lower matches the pinned tree |
| 100 | `overlay-ready` | tmpfs upper/work and merged root are ready |
| 110 | `handoff-begin` | retained exitrd and mount moves are starting |
| 120 | `switch-root-exec` | all moves passed and PID 1 will next invoke `switch_root` |
| 130 | `new-init-up` | diagnostic-only early systemd unit ran |
| 140 | `sshd-active` | diagnostic-only post-sshd unit ran |
| 200 | `fault` | a fixed reason code terminated progress |
| 210 | `watchdog-pretimeout` | rollback deadline is imminent |

`fault` carries the last-good code and one enumerated reason. It must not
carry free-form kernel text, paths, credentials, or user data.

## Failure and rollback behavior

Normal network-root behavior remains fail-fast. Only the signed diagnostic
profile may replace a post-reporter failure with:

1. publish one terminal `fault` update;
2. continue heartbeat frames for five seconds; and
3. force rollback while the independent recovery watchdog remains armed.

The five-second dwell is bounded and never disarms or extends the watchdog.
An internal pretimeout update is emitted five seconds before the fixed
deadline. Failure to emit or capture diagnostics never permits a retry.

The diagnostic bundle is consumed after one COMMIT regardless of outcome.
Host-side bundle admission is the expiry mechanism; the phone stores no boot
counter or diagnostic state.

## Systemd handoff

Before `switch_root`, the initramfs adds two units only to the volatile
OverlayFS upper:

- an early unit sends `new-init-up`; and
- a unit ordered after `sshd.service` sends `sshd-active`.

Both invoke the same static helper from the retained exitrd and send one
nonblocking datagram. They do not alter the sealed NFS lower. The reporter
holds its abstract socket and ACM descriptor open across the handoff and
requires no path lookup after startup.

## Host capture

The host collector starts before target enumeration and:

- binds the recovery anchor's exact physical USB port;
- accepts exactly one diagnostic product, ACM interface, and boot ID;
- opens the tty exclusively in raw/no-echo/no-HUPCL mode;
- parses fragmented and coalesced netstrings under fixed memory and time
  limits;
- rejects malformed, noncanonical, regressing, duplicate-sequence,
  wrong-candidate, and mixed-boot records;
- timestamps each frame on host receipt and captures bounded matching kernel
  USB events;
- writes one mode-`0600` evidence record outside Git; and
- sends zero bytes to the phone.

The ordinary host-key/runtime acceptance path must reject the diagnostic USB
product, profile, candidate, and ACM function.

The implemented collector is:

```sh
scripts/host/collect-early-target-diagnostics.py \
  /absolute/private/recovery-anchor \
  /absolute/private/early-target-evidence.json \
  60 900
```

Both parent directories must resolve to caller-owned mode `0700` directories;
the anchor must be the existing canonical mode-`0600` recovery anchor and the
output must not exist. The optional final arguments bound target enumeration
and stream capture in seconds. The collector starts a read-only kernel-journal
tail before target enumeration, filters only the anchor port's USB, `cdc_acm`,
and `cdc_ncm` messages, and excludes serial-number lines. It then admits one
literal `ROG5 diagnostic network root` product and its interface `02`
`cdc_acm` character device on that port.

After the journal subprocess starts successfully and before target
enumeration begins, the collector emits and flushes exactly one supervisor
handshake line:

```text
READY receive-only early-target diagnostic collector
```

A diagnostic lifecycle must observe that complete line before exposing the
NFS handoff marker that releases the recovery controller's non-retryable
COMMIT. Anchor, output, or journal-startup failure emits no readiness line.
The final PASS/FAIL result is separate and cannot be mistaken for readiness.

The tty is opened `O_RDONLY|O_NOCTTY|O_NONBLOCK`, locked with `flock` and
`TIOCEXCL`, and configured raw with echo and `HUPCL` disabled. The opened
file's device number is checked before parsing; the descriptor remains bound
to that character device even when USB sysfs entries disappear during
disconnect. No phone-facing write method exists. At most 4,096 validated
frames and 64 sanitized USB events are retained. A valid timeout or disconnect
and every post-anchor capture rejection produce exactly one canonical JSON
record via exclusive mode-`0600` creation outside Git. Rejected evidence
contains only records accepted before the violation and a bounded reason,
never the raw untrusted stream.

## Hardware-free gate

No diagnostic bundle may be signed or booted until tests prove:

1. every stage and fault reason round-trips through the native emitter and
   host parser;
2. every byte split and bounded coalescing pattern parses identically;
3. truncation, malformed lengths, oversize frames, duplicate fields, mixed
   boots, sequence reuse/regression, stage regression, and unknown values fail
   closed;
4. the emitter remains write-only on ACM and cannot execute input;
5. local stage updates are nonblocking, monotonic, bounded, and abstract-
   socket-only;
6. heartbeat cadence, watchdog deadline, pretimeout, five-second failure
   dwell, and total runtime are deterministic under a fake clock;
7. reporter death or blocked ACM cannot delay initramfs progress or rollback;
8. diagnostic mode preserves zero physical storage, one COMMIT, one target
   execution, and automatic fallback;
9. normal mode contains no ACM reporter, dwell, or injected units;
10. the diagnostic initramfs and signed bundle twin-build byte-identically;
11. QEMU proves reporter continuity across the board-neutral root handoff and
    then executes both transient stage updates under real AArch64 systemd; and
12. the normal runtime verifier rejects every diagnostic identity; and
13. the host collector starts before enumeration, binds the exact anchor port,
    remains receive-only, distinguishes timeout from disconnect, bounds and
    sanitizes kernel events, and publishes one private evidence record.

## Promotion sequence

1. Implement and hostile-test the frame codec and host parser.
2. Implement and test the static reporter with fake tty/socket/clock inputs.
3. Integrate diagnostic mode into the shared network-root init without
   duplicating the normal init script.
4. Add the volatile systemd units and QEMU handoff test.
5. Build the diagnostic initramfs twice and compare complete bytes.
6. Package with disposable signing authority and pass the native verifier.
7. Obtain independent code review and green local/GitHub CI.
8. Create a new externally held candidate and signed bundle identity.
9. Run all connected preflights, then at most one temporary boot.

Steps 1 through 6 and the receive-only host collector are implemented. The
complete disposable-key promotion path now includes two clean ASUS 5.4 wrapper
builds, byte comparison, native verification, and the temporary-identity
artifact-preflight fixture. Independent review and local CI for step 7 are
closed; GitHub CI remains pending. Step 4 now crosses the root handoff and
executes both generated milestone units under real AArch64 systemd. The native
reporter uses write-only,
exclusive, raw ACM access; a credential-checked abstract datagram socket;
nonblocking partial-frame writes; fixed-cadence heartbeats; immutable terminal
state; and automatic watchdog pretimeout. The hardware-free suite exercises
blocked ACM output, host-to-target bytes that remain unread, descriptor-bearing
and oversized local updates, post-deadline watchdog heartbeats, deterministic
clock behavior, and byte equality with the host oracle. Production binaries
are also checked to contain no test-hook strings.

The credential-free half of promotion step 8 now has an exact no-replace
preparer that binds the admitted non-fixture Arch package to candidate record
SHA-256 `7081a0c7…c6e8`. The guarded production builder accepts only that
diagnostic tuple or the existing normal SSH tuple, validates the candidate
and reserves every output before opening the recovery signing key, scrubs the
original path environment before the first helper and the guards before later
children, and requires the diagnostic manifest to remain `4eacb90f…e76`. The
neutral stager retains the old SSH-named path only as a compatibility entry
point. A disposable-key wrapper-to-stager preflight and diagnostic-only,
exact-output recovery-policy preflight cover the complete guarded input wiring
and exact diagnostic profile record without a production credential. A second
full-path execution at clean checkpoint `0375e97a` proves the guarded wrapper,
two clean builds, native verifier, and artifact gate compose through final
`authority=none` output.
Actual production signing, installation, and phone execution remain pending
after green GitHub CI.

Twenty-three collector tests cover canonical private anchor/output handling,
duplicate or wrong-port USB identities, interface/driver binding, character-
device replacement, rejection of a pre-existing foreign holder, read-only
raw/no-`HUPCL` tty behavior, timeout versus disconnect, fragmented valid
frames, malformed and truncated rejection, chunk-invariant retention of a
valid prefix before rejection, bounded redacted kernel events, burst-safe line
buffering, pre-enumeration and final-disconnect event retention, canonical
mode-`0600` evidence, successful and rejected frame-prefix retention across a
failed final drain, start-before-enumeration ordering, immediate journal-child
exit rejection, an exact flushed readiness handshake that is absent on
journal-startup failure, and absence of a serial write or shell surface. A
deterministic test executes the real subprocess/nonblocking-buffer/termination
path, and a local smoke starts and stops `/usr/bin/journalctl` as the
unprivileged user. The complete repository `ci` tier passes with this collector
test in sequence.

The shared init admits diagnostic mode only when both `rog5.diagnostic=1` and
the fixed `headless-netroot-early-diag-v1` bundle identity are present. That
branch alone adds ACM, starts the reporter after the independent watchdog is
attested, emits stages 10 through 120, retains the helper across
`switch_root`, injects the two volatile systemd units, and dwells exactly five
seconds after a terminal fault. Normal mode creates no ACM function, reporter,
dwell, or units. Isolated shell tests execute the command-line gate, rollback
dwell, unit generation, handoff rollback, and failed-`switch_root` path.

The archive builder optionally accepts only the sealed 67,288-byte reporter
with SHA-256
`f0a9a52b42385a5c963230d5c48f152bed2e24e382c22de09acdba529082a1fd`.
Two qualified diagnostic archive builds were byte-identical at 6,010,870 bytes,
SHA-256
`10cc407e2bb5a9c9b63fd7eb30c7fc785d78b587e0c7c0b32346f7b1a50ce35c`;
normal mode separately reconstructs its frozen 5,978,369-byte archive,
SHA-256
`819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5`,
from the five required files at historical source commit
`27a270f2955c57f61e2cb8aeae0be23b31223499`. This prevents diagnostic
changes in the shared current init source from silently redefining the normal
candidate's historical bytes.
The native signed-bundle verifier requires an executable reporter for the
diagnostic profile and rejects one in every normal profile.

The QEMU harness compiles the same production reporter source without test
hooks, routes its write-only stream over a separate virtio console, performs
the root-move/chroot/exec sequence, and requires one canonical boot stream to
cross stages 10, 120, 130, and 140 in order. The retained reporter crosses into
the sealed Arch runtime, where real AArch64 `systemd 260.2-2-arch` loads and
executes the exact units generated by `network-root-init`. The test
`sshd.service` is an ordering stub, so stage 140 proves systemd ordering and
execution but not a real SSH connection. The corrected Linux 7.1.4 QEMU
profile explicitly verifies FUTEX, MEMFD_CREATE, SHMEM, and TMPFS; the clean
local full-system gate and complete repository CI pass. See the
[systemd QEMU result](../test-results/2026-08-01-arm64-systemd-qemu-gate.md).
The [host collector result](../test-results/2026-08-01-early-target-host-collector-offline.md)
records its hardware-free acceptance. Promotion steps 1 through 6 now pass:
the [offline candidate result](../test-results/2026-08-01-early-target-diagnostic-candidate-offline.md)
records byte-identical disposable-signed bundles, stable-recovery wrappers,
raw/AVB images, native verification, and private-key destruction. The complete
local `ci` tier passes. Independent final review reports no actionable
standards/safety or objective-fidelity findings. GitHub CI, production signing,
and every phone action remain pending.

The diagnostic admission and one-shot supervisor are now implemented
hardware-free. `diagnostic-run` captures the recovery USB anchor, starts the
collector and requires its flushed readiness marker before starting either the
bundle server or recovery control, then performs at most one existing
prepare/commit transaction. It waits for canonical private diagnostic
evidence instead of target host-key/SSH acceptance, preserves rejected
evidence, verifies fallback and final cleanup, and resolves the intent only as
`FALLBACK_RETURNED`. Sixteen admission tests and thirty-four lifecycle methods
pass;
see the
[offline lifecycle result](../test-results/2026-08-01-early-target-diagnostic-lifecycle-offline.md).
The first independent review's readiness-liveness, evidence-binding, and
mutable-policy findings are fixed with hostile regressions. Independent
closure review reports no remaining actionable findings, and the complete
local `ci` tier passes. GitHub CI remains pending.

No step above authorizes flashing, phone-storage writes, a second r2 execute,
or promotion of diagnostic output as normal runtime acceptance.
