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
| 120 | `switch-root-exec` | all moves passed and PID 1 is executing pivot |
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
11. QEMU proves reporter continuity across `switch_root` and both transient
    systemd stage updates; and
12. the normal runtime verifier rejects every diagnostic identity.

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

Steps 1 and 2 are implemented. The native reporter uses write-only,
exclusive, raw ACM access; a credential-checked abstract datagram socket;
nonblocking partial-frame writes; fixed-cadence heartbeats; immutable terminal
state; and automatic watchdog pretimeout. The hardware-free suite exercises
blocked ACM output, host-to-target bytes that remain unread, descriptor-bearing
and oversized local updates, post-deadline watchdog heartbeats, deterministic
clock behavior, and byte equality with the host oracle. Production binaries
are also checked to contain no test-hook strings. Initramfs integration begins
at step 3.

No step above authorizes flashing, phone-storage writes, a second r2 execute,
or promotion of diagnostic output as normal runtime acceptance.
