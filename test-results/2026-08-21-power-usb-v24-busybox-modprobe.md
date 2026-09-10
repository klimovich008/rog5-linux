# V24 live result: typed observer passed, BusyBox modprobe failed

Primary question: can the early-initramfs observer keep side-port NCM stable
while reporting battery/UCSI telemetry before NFS?

Result: transport and typed observation passed; charging telemetry remained
unavailable. V24 is consumed and must never be retried or flashed. Exact stock
slot-A fallback, host cleanup, and `FALLBACK_RETURNED` intent resolution passed.

Evidence:

- valid stream with 170 progress frames and 177 typed power records;
- NCM remained stable for about 41 seconds with zero dropped USB events or
  transport snapshots;
- observer identity, kernel release, firmware path, and final completion
  record passed;
- every `modprobe --first-time` call returned BusyBox's unsupported-option
  error;
- the PDR override then failed on unresolved symbols;
- remoteproc, PMIC GLINK, power_supply, and Type-C classes remained absent;
- voltage trend and net-positive current were therefore correctly reported as
  `error=telemetry-unavailable`, not treated as fatal;
- no phone-storage access occurred.

Root cause: proven R3 exact-artifact capability mismatch. The sealed target
uses BusyBox 1.37 `modprobe`, which supports ordinary module loading but not
kmod's `--first-time` option.

Regression: active tests reject `modprobe --first-time`. The observer first
checks `/sys/module`, invokes plain BusyBox `modprobe MODULE`, then verifies the
module became observable before reporting success.

Successor: V25 changes target initramfs and identity only. Kernel, DTB,
firmware, stable recovery, charging controls, and UFS exclusion remain
unchanged.
