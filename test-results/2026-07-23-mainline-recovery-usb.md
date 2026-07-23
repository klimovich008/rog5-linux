# Linux 7.1 recovery USB result - 2026-07-23

> **CORRECTION — SUPERSEDED V2; DO NOT BOOT**
>
> A later live and artifact audit proved that the v2 first-stage `/` was a
> writable physical UFS filesystem and that its target DTB enabled UFS and
> QMP/SuperSpeed. The storage-free and USB2-only classifications below are
> false. Nothing was flashed. The logs remain historical evidence only; the
> later v6 passed its then-current offline checks but failed live ACM data and
> rollback. Current fixes require a full rebuild; there is no boot candidate.

Result: **PASS** for Linux 7.1.4 kernel/userspace entry and automatic
rollback; **BLOCKED AT HOST USB ENUMERATION**.

## Passing live gates

- The authenticated ASUS 5.4 staging recovery verified the nested payload,
  exposed no storage mount, disabled the single allowlisted Haven watchdog,
  and loaded Linux 7.1.4.
- Linux 7.1.4 reached `/init`, mounted configfs, created NCM and ACM gadget
  functions, bound the expected DWC3 device controller, and created `usb0`.
- The target rollback timer returned the phone to the fallback path.
- Persistent console evidence survived the fallback and was collected through
  the read-only diagnostic path.

## Failure isolation

- Windows did not enumerate a target NCM or ACM device, so target SSH was not
  reachable.
- Reserving TLMM GPIOs 52-59 removed the earlier synchronous external abort.
- Building the Qualcomm FEMTO USB2 PHY into the kernel removed the subsequent
  deterministic deferred probe.
- The recovery DT now uses only the USB2 PHY and ASUS high-speed tuning; UFS,
  QMP/SuperSpeed, and the secondary USB controller remain disabled.
- The next payload adds a bounded wait plus logged UDC state/carrier and a
  conditional soft reconnect. It is built and verified offline but has not
  been exercised because the host currently does not enumerate the phone in
  fastboot or ADB mode.

No partition was flashed, no phone storage was mounted, and no serial number,
private address, complete command line, or private DT data is present in this
report.
