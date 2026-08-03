# Generation-4 NFS-readiness lifecycle — live

Date: 2026-08-03

Result: **REJECTED safely and consumed**. The sole admitted Generation-4
RAM-only recovery boot reached verified ACM/NCM with rollback armed. The
one-transfer bundle service became ready, but it never emitted its independent
completion marker before recovery control's 45-second NFS-readiness deadline.
NFS did not start, `COMMIT_EXEC` was never sent, and the target did not run.

## Exact candidate

- profile: `headless-diagnostic-generation4-live-v1`
- AVB image SHA-256:
  `220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d`
- unchanged raw recovery SHA-256:
  `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`
- signed diagnostic manifest SHA-256:
  `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`
- recovery trust-root SHA-256:
  `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b`
- host verifier SHA-256:
  `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621`
- fastboot serial: retained only in private evidence
- physical USB anchor:
  `pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2`

The connected lifecycle preflight passed against one exact `lahaina` fastboot
device and the installed root-owned bundle/controller boundary. It performed
no phone boot, payload transfer, SSH connection, or privileged server start.

## Live sequence

The guarded lifecycle executed exactly once, with no retry:

1. The strict signed-SSH fallback preflight passed on Alpine.
2. The guarded fallback helper requested bootloader mode and verified one exact
   `lahaina` fastboot device.
3. The AVB footer and `NONE` vbmeta structure passed verification, as did the
   boot descriptor over exactly `58101760` bytes.
4. `fastboot boot` accepted the 100663296-byte RAM-only image. Recovery exposed
   `/dev/ttyACM1`, the lifecycle captured the exact physical USB anchor, and
   rollback remained armed.
5. The receive-only diagnostic collector emitted `READY`. The bundle service
   emitted its ready line for `169.254.77.1:8080` and announced one exact serve
   of `headless-netroot-early-diag-v1`.
6. The service never emitted its independent completion marker. Recovery
   control terminated with `FAIL exact network-root NFSv4.2 listener was not
   ready before COMMIT` at its 45-second readiness boundary.

That 45-second boundary is the separate post-PREPARE, pre-COMMIT NFS-listener
gate in `stable-recovery-control.py`; it is not one of the
180/190/195/205/220/260/320-second fetch-worker-to-control process deadlines.
The process lattice can remain valid while this later choreography still fails
because NFS startup is deliberately conditional on the transfer service's
independent completion receipt.

There is no NFS server log, diagnostic JSON, target frame, durable new intent,
or commit record. The evidence therefore supports only recovery transport and
pre-commit failure. It does not support target execution or normal
minimal-headless acceptance.

## Rollback and host cleanup

The phone returned automatically to the exact Alpine fallback gadget. The
first lifecycle cleanup proof failed because the shared ROG5 `/30` remained
outside the exact managed fallback profile while the root-owned controller was
still inside its 205-second hard watchdog. A later process check corrected an
initial monitoring mistake: an unprivileged `kill -0` returned `EPERM`, which
had been misread as process exit; `/proc/<pid>` showed that the controller was
still alive until its watchdog terminated it with failure.

After the controller exited, one fixed `restore-fallback` operation using the
captured USB anchor restored the exact `rog5-fallback-usb-ssh` NetworkManager
profile. Strict fallback preflight then passed. Final inspection found the
expected `169.254.77.1/30` host interface and no project NFS export, NFS
listener, bundle server, diagnostic collector, or project process residue. An
unrelated Steam loopback listener on `127.0.0.1:8080` remained
outside the ROG5 USB path.

No image was flashed; no partition was erased, formatted, mounted, or written;
no slot changed; and no target-side action ran.

## Verification

The focused compatibility, source/DT, recovery-policy, and stable-recovery
live-gate suites pass after the consumption transition. Complete
`scripts/host/test-repository-linux.sh ci` also passes, including all 41 local
Markdown targets, 39 compatibility tests, 74 source/DT tests with one optional
retained-input skip, 42 lifecycle tests, and the recovery/host-controller
regressions.

The first constrained, tool-free Claude Opus review found four documentation
consistency issues: one wrong primary evidence link, an omitted generation-zero
count, dropped historical links, and no explicit relation between the
45-second NFS gate and the process deadline lattice. All four were corrected.
A smaller follow-up review returned `NO FINDINGS`.

## Disposition

Generation 4 is single-use and consumed regardless of this pre-commit result.
Its central-policy `allow` row is removed, its artifact inventory role is
consumed/offline-only/never-retry-or-flash, both recovery-policy tests require
its absence, and both downstream compatibility hashes are repinned. The exact
image must not be retried or flashed.

The next candidate must be a distinct generation. Before issuing it, add
hardware-free tests for the PREPARE/completion-receipt/NFS startup choreography
and make every early control failure execute fixed fallback-profile restoration
after the anchored Alpine gadget returns. Extending another timeout without
proving this ordering is not an adequate fix.
