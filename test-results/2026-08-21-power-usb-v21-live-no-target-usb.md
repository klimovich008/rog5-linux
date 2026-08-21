# V21 live rejection: diagnostic-token parser mismatch

Primary question: can the early-initramfs observer keep side-port NCM stable
while reporting battery/UCSI telemetry before NFS?

Result: rejected and consumed; never retry or flash. Exact stock slot-A
fallback, host cleanup, and `FALLBACK_RETURNED` intent resolution passed.

Earliest observed stage:

- recovery boot, NCM peer reachability, complete 62,555,197-byte signed-bundle
  transfer, verification, kexec load, PREPARE, and COMMIT passed;
- recovery USB disconnected;
- no target ACM or NCM identity enumerated;
- stock Android USB returned about 26.1 seconds later;
- the bounded collector retained zero frames and zero power records.

Root cause: proven R2 target composition/parser defect. V21 correctly changed
to `diagnostic-initramfs-v1`, whose verified command line adds
`rog5.diagnostic=1`. The active early-power branch in
`network-root-init` still accepted power candidates only when the diagnostic
token count was zero. PID1 therefore rejected the command line and rolled back
before USB configuration. This exactly explains zero target USB evidence.

A separate R1 identity defect was also found: the collector parsed V21 using
the supplied candidate but wrote the historical diagnostic candidate into its
JSON document. That did not cause the absent USB device, but would have
rejected a successful V21 stream later.

Phone storage modified: no. UFS remains disabled in the target kernel and DT.

Regression:

- early power candidates require exactly one `rog5.diagnostic=1`;
- post-SSH power candidates require zero diagnostic tokens;
- missing, duplicate, and wrong-mode combinations fail;
- collector evidence publishes the exact requested candidate.

Successor: V22 changes only target initramfs/collector bytes and identity.
Kernel, DTB, firmware, signed recovery transport, and charging controls remain
unchanged. One future live cycle must not reuse V21.
