# Generation-11 progress-listener scope mismatch — offline reproduction

Date: 2026-08-04

Result: **A SUFFICIENT FAILURE CAUSE WAS REPRODUCED AND FIXED OFFLINE — the
exact installed receive-only collector creates one PID-owned IPv4 listener,
but root `ss`
renders its `SO_BINDTODEVICE` endpoint as
`169.254.77.1%enp4s0f3u1u2:8081`. The production controller required the
unscoped substring `169.254.77.1:8081`, so it rejected the correct listener.
The controller now requires the exact host-IP plus USB-interface scope and
retains the one-line, sole exact PID/fd owner, live-process, and
no-IPv6-conflict gates.**

## Reproduction boundary

The installed collector and repository source were byte-identical at SHA-256
`8b15aaac28d54ac0acf93411dc2dbb77d9a9b7b5dfc8e2cc591609f7a23ed20a`.
The verified Alpine fallback interface already held `169.254.77.1/30`; no
recovery image, bundle server, recovery control request, NFS export, target,
or SSH probe was started.

SteamOS normally owns `[::]:8081` through
`steam-web-debug-portforward.socket`, whose unit uses `ReusePort=yes`. A
privileged read-only inspection identified its listener as systemd PID 1. The
bounded reproducer recorded the socket's active state, stopped the socket and
inactive service, verified both IPv4 and IPv6 port inventories were empty,
and restored the socket from an EXIT trap.

The first direct `sudo` reproduction failed safely before opening a listener.
SteamOS `sudo` supplied inheritable `CAP_WAKE_ALARM`, while the production
PolicyKit controller context used by Generation 11 had no inheritable
capabilities and reached the collector's ready marker. The reproducer therefore
cleared only the inherited and ambient sets before invoking the unchanged
collector; the collector still performed and verified its own complete
root-to-operator capability, UID, GID, group, and no-new-privileges drop.

## Exact observation

With the production privilege shape, the exact collector emitted its ready
marker. Root `ss -H -lntp4` reported one listener in this canonical shape:

```text
LISTEN 0 1 169.254.77.1%enp4s0f3u1u2:8081 0.0.0.0:* users:(("python3",pid=<exact-collector-pid>,fd=3))
```

The observed PID equalled the launched collector PID and the matching IPv6
inventory was empty. Termination produced a private 0600
`PARTIAL/NO_ADMISSION` capture with zero records and `authority=NONE`. Steam's
socket returned to active/listening afterward. The private PID and raw
reproduction directory remain outside Git.

This reproduces a sufficient cause consistent with the Generation-11 host
confinement rejection; the live record did not retain the contemporaneous
`ss` inventory, so it does not prove this was the unique cause. It also does
not prove that recovery control, PREPARE, transfer, COMMIT, NFS, or a target
ran during that consumed lifecycle; the live evidence proves none of those
stages started.

## Regression and fix

The controller now parses the sole `ss` record and requires exact `LISTEN`
state, numeric queues, local endpoint `169.254.77.1%$interface:8081`, wildcard
IPv4 peer, no trailing field, the launched collector PID, a live process, and
an empty IPv6 inventory. The hardware-free host-controller oracle uses that
production shape and adds hostile cases for:

- an unscoped `169.254.77.1:8081` lookalike;
- an interface with the expected interface only as a suffix;
- an address with the expected address only as a suffix;
- pre-existing and post-start Steam-shaped `[::]:8081` systemd listeners; and
- scoped foreign-PID, shared-owner, duplicate-record, absent, delayed, and
  post-exit cases.

`python3 scripts/host/test-recovery-host-controller.py` reports `Ran 38 tests`
and `OK`. The exact scoped rendering is a fail-closed prerequisite of this
host surface: another host or iproute2 version that emits a different local
endpoint must run and document the production-faithful reproducer before its
controller is installed; it is not silently accepted. Broader review,
complete local CI, and installed-host replacement passed. Publication and
exact-head GitHub CI then passed at implementation commit `1f3cc66` in run
`30931511061` (recovery-core 4m02s; QEMU 37s). This host fix can now support
offline issuance and preflight of a distinct diagnostic successor; it does not
authorize that successor's phone boot.
This result grants no Generation-11 retry and no phone-boot authority.

## Validation and installed host

Independent spec and standards reviews found shared-owner acceptance,
production-infaithful abbreviated `ss` filters, and overstated live causation.
The implementation now requires one exact owner tuple; the fixtures use full
production filters and cover scoped foreign/shared owners and duplicate
records; and this record limits its conclusion to a sufficient cause
consistent with the live failure. A constrained Claude Opus review's useful
pre-start IPv6 coverage suggestion was also added. Its contrary endpoint and
mock-escaping concerns were resolved by the real root `ss` capture, explicit
fixture tracing, and healthy-path tests.

`scripts/host/test-repository-linux.sh ci` passed the complete local Linux
tier. The reviewed installer atomically replaced the root-owned controller;
source, installed file, and the dynamic `control.conf` pin now share SHA-256
`9692265ae8bd60687d6f76736e65a048930f43eee441c56c0e56fcf2626548e0`.
The controller is root-owned mode 0555, its configuration is root-owned mode
0444, and the operator-only host socket is active and enabled. The installed
broker proved the NFS export table exactly empty. Steam's port-8081 socket is
active and enabled again, and SteamOS read-only mode is enabled.

## Effects

No flash, erase, wipe, slot operation, factory reset, phone-storage mount, or
phone write occurred. The reproduction temporarily replaced Steam's TCP 8081
listener with one receive-only host listener on the existing fallback USB
interface, accepted no connection, and restored Steam automatically. It
created only a private host evidence directory and capture outside Git.
