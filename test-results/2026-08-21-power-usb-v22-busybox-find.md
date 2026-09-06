# V22 live rejection: unsupported BusyBox `find -printf`

Primary question: can the early-initramfs observer keep side-port NCM stable
while reporting battery/UCSI telemetry before NFS?

Result: rejected and consumed; never retry or flash. Exact stock slot-A
fallback, host cleanup, and `FALLBACK_RETURNED` intent resolution passed.

Earliest evidence:

- signed recovery transfer, verification, PREPARE, and COMMIT passed;
- the mainline target enumerated exact NCM and ACM on USB path `1-1.2`;
- target USB disconnected about 268 ms after enumeration;
- no ACM frame became stable; stock Android returned about 24 seconds later;
- phone storage remained inaccessible because UFS is disabled in kernel/DT.

Root cause: proven R3 exact-artifact capability defect. The observer's first
transport check invoked GNU `find -printf`. The sealed target contains BusyBox
1.37.0, whose exact `find` applet returns `find: unrecognized: -printf`. The
failed exact-UDC check is fatal by design and therefore immediately requested
rollback. This matches the observed ordering and lifetime without requiring a
kernel, DT, recovery, or charging-stack change.

Why tests missed it: archive verification compared source bytes and ran shell
syntax checks, while host tests executed with GNU find instead of the exact
initramfs utility capability.

Regression: the observer now selects exactly one fixed `a600000.usb` UDC with
POSIX shell globbing. Fixtures reject zero, multiple, wrong, and renamed UDCs,
and the active test rejects reintroduction of GNU `find -printf`.

Successor: V23 changes target initramfs and identity only. Kernel, DTB,
firmware, stable recovery transport, charging controls, and storage exclusion
remain unchanged.
