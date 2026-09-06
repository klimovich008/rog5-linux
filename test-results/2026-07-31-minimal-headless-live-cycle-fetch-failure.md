# Minimal-headless live cycle: pre-PREPARE fetch timeout

Date: 2026-07-31

Result: **safe rejection; no target commit or kexec occurred**.

## Accepted boundaries

- The repository checkpoint was clean, pushed, and synchronized.
- Local deployment-key admission, fixed-host preflight, sealed export
  verification, recovery artifact verification, exact `lahaina` fastboot
  identity, and signed Alpine fallback host preflight passed.
- `fastboot boot` accepted the pinned 100,663,296-byte recovery image. No
  partition was flashed or mounted.
- Recovery appeared on the anchored physical USB path and the fixed bundle
  server completed exactly one transfer of
  `headless-ssh-network-root-v3`.

## Rejection

The host control process began at 12:59:44, while the one-shot bundle server
finished at 12:59:50. Recovery returned at 13:00:46 with:

```text
result=FETCH_FAILED state=IDLE
```

The responder remained healthy, but the old fetch helper exposed only one
generic failure and used one 60-second monotonic deadline for connection,
transfer, sandboxed receipt, parent revalidation, normalization, final
revalidation, and publication. The response arrived at that exact boundary.
The retained evidence cannot identify which post-transfer stage consumed the
remaining time, so this result does not justify a blind retry.

Because PREPARE never succeeded:

- no `COMMIT_EXEC` request was sent;
- no durable host intent was armed;
- no kexec image was loaded;
- the target NFS root was never mounted by the phone; and
- the recovery watchdog remained armed.

## Cleanup defect and remediation

The lifecycle had already started the restricted NFS handoff while waiting
for PREPARE. Its exception path attempted to signal the root-owned PolicyKit
child from the unprivileged parent and received `EPERM`. The exact supervised
PID was terminated once with root authority. Its trap removed the export,
NFS workers, mount daemon, bind mount, listener, firewall rules, temporary
address, handoff marker, and nonlocal-bind change. Direct inspection then
showed no listener on TCP 8080/2049 or TCP/UDP 32767, no export, and zero NFS
workers.

The temporary narrowly scoped PolicyKit rule used for this attended cycle was
removed immediately afterward.

## Rollback proof

Recovery disconnected from the anchored port at 13:02:29. The same port
re-enumerated at 13:02:47 as Alpine's `ROG Phone 5 Linux Server` gadget. One
fresh nonce-bound signed ACM preflight then passed, including the strict
thermal policy. Its mode-`0600` proof remains outside Git.

## Required change before another boot

1. Preserve a bounded fetch-stage failure in the framed response instead of
   collapsing every helper exit into `FETCH_FAILED`.
2. Use coherent nested monotonic budgets for the measured 46 MiB bundle.
3. Give the fixed privileged NFS server an authenticated `cancel` action and
   root-owned PID/start-time identity, then require verified cleanup on every
   pre-commit exception.
4. Rebuild and re-pin the changed recovery before a new temporary boot.

This is live failure evidence, not acceptance of the minimal-headless target.
