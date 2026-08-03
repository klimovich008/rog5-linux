# Generation-5 signal-mask choreography correction — offline

Date: 2026-08-03

Result: **PASS complete local CI; no phone action**. The Generation-5
transfer did not fail because 46,163,787 bytes needed more time. The
privileged host broker started the controller with `SIGHUP`, `SIGINT`, and
`SIGTERM` blocked. That mask survived `exec` and propagated to the controller,
its hard watchdog, and cleanup descendants. The successful transfer process
therefore could not terminate its watchdog, so the controller waited for the
watchdog's full 205-second sleep and never published the independent
completion receipt needed to start NFS before the control gate closed.

## Evidence boundary

Private Generation-5 evidence is retained outside Git. Its filesystem
timestamps establish this order:

- bundle output began at `10:59:58` and its last progress update was
  `11:00:10.675`;
- recovery control began at `11:00:07.210`;
- the final progress line reported
  `phase=initramfs.cpio.gz bytes_sent=46163787 bytes_total=46163787` about
  3.5 seconds after control began; and
- control rejected at `11:00:56.880` because the exact NFSv4.2 listener was
  not ready before COMMIT.

The bytes were therefore sent roughly 46 seconds before the NFS-readiness
failure. Increasing the 45-second NFS gate would hide the process-lifecycle
defect and is not an accepted correction.

## Test-first correction

The first regression inspected `/proc/self/status` in the broker child. Before
the correction, all three managed bits were present in `SigBlk`; after the
correction they are clear while an unrelated mask bit deliberately inherited
from the caller remains set. This proves restoration of the caller's exact
mask rather than an indiscriminate unblock.

A second regression starts a watchdog-like grandchild, sends `SIGTERM` to the
broker, and requires the complete child process group to stop, protocol status
`143` to be framed, and the broker to finish within two seconds. It completes
in about 0.1 seconds. Failure cleanups kill and reap the fixture processes.

## Implementation

The broker now:

1. blocks the three managed signals while installing forwarding handlers;
2. restores the caller's original mask before `Popen`, preventing inherited
   blocked signals in the controller and every descendant;
3. retains signals from the narrow pre-spawn window and forwards them after
   `start_new_session=True` establishes the child process group;
4. ignores a vanished process group without falling back to a potentially
   reused direct PID;
5. converts a retained signal during spawn failure into the framed
   `128 + signal` status; and
6. restores the broker's original handlers and mask on every normal or
   exceptional exit.

The corrected broker source SHA-256 is
`fbafce24e9c11eea0c79d99f18cb2fb8c849d8b0180883cd8a0a562c8c8cc42c`.
It is not yet claimed as installed by this offline result.

## Review and verification

The initial failing mask test reproduced the defect. After the final
hardening, these suites pass:

- 13 recovery-host socket/broker tests;
- 25 privileged recovery-host controller tests; and
- 47 minimal-headless lifecycle tests.

Complete `scripts/host/test-repository-linux.sh ci` also passes, including
documentation/policy, recovery protocol, source/DT, generated runtime,
native-fetch/server integration, and QEMU stages.

A constrained, tool-free Claude Opus review returned useful stale-PID and test
cleanup concerns, alongside an invalid simulated tool transcript and an unsafe
`preexec_fn` recommendation. Each item was checked against the actual source;
the direct-PID fallback and fixture cleanup were corrected, while unconditional
success-path restoration was already present. This review is advisory, not
independent execution evidence.

No credential, signing key, server, fastboot command, or phone interface was
used. Generation 5 remains consumed and must never be retried or flashed. A
distinct successor remains forbidden until the exact corrected broker is
installed and hash-verified through a separate host-only checkpoint.
