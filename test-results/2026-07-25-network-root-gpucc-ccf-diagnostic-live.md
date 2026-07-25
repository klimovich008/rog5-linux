# Network-root v11 GPUCC generic-CCF diagnostic — live result

Date: 2026-07-25

Result: **bounded diagnostic failure with successful rollback**. V11 narrowed
the SM8350 GPUCC stall from registration of clock index 0 to the call of
`clk_core_reparent_orphans_nolock()` while registering
`gpu_cc_ahb_clk`. The final delivered marker was:

```text
ROG5 CCF diagnostic: phase=orphan-reparent-begin clock=gpu_cc_ahb_clk ret=0
```

Its matching `orphan-reparent-complete` marker never arrived. The immediately
preceding `topology-insert-complete ... ret=1` marker is a state value, not an
error: it confirms that CCF inserted `gpu_cc_ahb_clk` as an orphan because its
parent has not registered yet.

The independent 75-second SysRq watchdog reset the phone to the exact
persistent fallback. Nothing was flashed, Linux 7.1 exposed no physical
storage, standard pstore retained no record, and all temporary host
NFS/firewall/inhibitor state was removed.

## Scope and safety boundary

- Temporary `fastboot boot`, followed by the attended RAM-only kexec path.
- Linux `7.1.4-g7a5cef0db479` with OverlayFS over a read-only NFSv4.2 lower.
- SCSI/UFS absent from the kernel, zero physical block devices, and zero
  block-backed mounts.
- Only `/soc@0/clock-controller@3d90000` changed from `disabled` to `okay`.
- GPU, GMU, Adreno SMMU, display, UFS, RTC, input, and every remote processor
  remained explicitly disabled.
- The GPUCC module was copied only to target tmpfs, root-owned, mode `0400`,
  and pinned to SHA-256
  `3c663bed417bb3bd7438b422ebf3531eca48e53afebc66a4574c7d87f7a8f421`.
- Both diagnostic parameters were read-only, default-off, and enabled exactly
  once only for this exact-compatible boot.
- The trace added logging and a deliberate 100 ms delivery delay. It did not
  add, skip, or modify a clock, register, reset, power-domain, regulator,
  storage, or persistent-state operation.
- The original 900-second network-root rollback watchdog remained armed
  through the complete baseline and payload gate. It was safely disarmed only
  after those checks and immediately replaced by the probe's independent
  process-group watchdog.
- The probe was invoked once. No module-load or `execute` action was retried
  after kexec.
- No firmware, credential, personal data, or private device identifier entered
  this report. The complete 9,223-byte live log remains private outside the
  repository with mode `0600`; its SHA-256 is
  `e5cabd1a1ad1b9ba27e6252bd6d21c45e4bcf025f949101e775b14d02c0f17da`.

## Reproducible candidate

The [v11 offline report](2026-07-25-network-root-gpucc-ccf-diagnostic-offline.md)
records the full source, mutation, duplicate-build, wrapper, package,
transport, and privileged-host gates. The final diagnostic source is commit
`6eef0ab56609f5a5ee6d2de9807178daf1065fa7`, tree
`743a976fd13c1a5c30d93c7dac9b9b4d1cbc3b11`. Its patch SHA-256 is
`5f0be38bf3773f0cc541d7a52f930bc05dc979ee1a086198f3148aa14552dbc9`.

The two clean Linux builds and two ASUS wrapper/package builds matched
byte-for-byte. The live inputs were:

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 Image | `d6bb0a9a7c4d4496aac8593df1727c916f130a10741b2691eebbf28555527021` |
| Linux 7.1.4 Image.gz | `f4138e28b224423eaf0de334344fead6204ac9a0f141dbd8d8f0652d493c73ac` |
| matching module archive | `b1c2bd02d67773e2b213c8aec2e30378580f8bcc638ff378650182a335f6f5d0` |
| external `gpucc-sm8350.ko` | `3c663bed417bb3bd7438b422ebf3531eca48e53afebc66a4574c7d87f7a8f421` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `1d84c11edf9867d59dd473c0a958514e33b1f071a36cdda2f6ac39c2d5d48a7d` |
| ASUS wrapper Image | `1ea673e292447e4f03dceb43f8b1d19dd06c6382b279a950fa990f7a4c5fb7b0` |
| raw boot image | `3974476d879e1fa41296e64390324f959043fcd771bea5e166be93bff0796b95` |
| temporary-boot AVB image | `ed80c46e4d23caa258d3ef07ffddad254d9cba461165751e55476864044fdc42` |

The live probe helper initially still pinned the v10 external module. It was
corrected to the reviewed v11 hash and its executable source contract passed
before the original target watchdog was disarmed. The target copy then
matched that v11 hash, owner, and mode.

## Live baseline and transport

Before watchdog disarm, the target passed:

- exact Linux 7.1.4, PID 1 systemd, and running system state;
- runtime-masked automatic udev and module coldplug;
- both exact trace command-line flags and immutable mode-`0400` `Y` core
  parameters;
- OverlayFS `/`, exact read-only NFSv4.2 lower, and stable USB carrier;
- zero physical block devices and zero block-backed mounts;
- zero failed units and zero fatal kernel signatures;
- GPUCC `okay`, with GPU, GMU, and Adreno SMMU explicitly disabled;
- no loaded GPUCC module and no DRM render node;
- 29 readable thermal zones with a 36.8 C maximum; and
- the original rollback watchdog alive at 258 seconds of its 900-second
  interval.

The first fixed staging `load-gpucc-diagnostic` marker was again lost during
ACM re-enumeration. The bounded transport recovery rediscovered a stable ACM
endpoint and replayed the exact same idempotent load command once; that replay
passed. The one-shot `execute` action was sent exactly once and was never
retried. This validates the v11 recovery rule while confirming that the
underlying staging marker race still exists.

## Delivered trace

The host captured exactly 7 GPUCC-driver markers, 21 Qualcomm common-clock
markers, and 46 generic CCF markers. The wrapper completed:

```text
clock-regmap-register-begin
regmap-device-lookup-begin
regmap-device-lookup-complete
regmap-device-assign-begin
regmap-device-assign-complete
regmap-lookup-complete
ccf-managed-register-begin
```

For `gpu_cc_ahb_clk`, generic CCF then completed:

- managed-resource allocation and `clk_hw_register`;
- core allocation, name copy, runtime setup, parent-map allocation, and
  consumer allocation/linking;
- prepare-lock acquisition and the `hw->core` link;
- runtime-PM get with return value zero;
- duplicate-name and ops validation;
- the optional driver-init branch;
- initial parent lookup, which returned no registered parent;
- hash/topology insertion with orphan state `1`;
- accuracy, phase, duty-cycle, and rate initialization; and
- the non-critical branch, without invoking a critical-clock prepare.

The final ordered tail was:

```text
phase=rate-begin clock=gpu_cc_ahb_clk ret=0
phase=rate-complete clock=gpu_cc_ahb_clk ret=0
phase=critical-begin clock=gpu_cc_ahb_clk ret=0
phase=critical-complete clock=gpu_cc_ahb_clk ret=0
phase=orphan-reparent-begin clock=gpu_cc_ahb_clk ret=0
```

No `orphan-reparent-complete`, runtime-PM put, core-init completion, managed
registration completion, index-0 registration completion, provider
registration, GPUCC registration completion, `insmod` return, probe PASS, or
probe FAIL marker reached the host.

## Source localization and interpretation

The missing boundary directly brackets this unmodified call in
`__clk_core_init()`:

```c
clk_core_reparent_orphans_nolock();
```

It runs while the global CCF prepare lock is held. The function walks the
entire `clk_orphan_list`, calls `__clk_init_parent()` for each entry, and, when
a parent becomes available, can call parent-migration, accuracy-recalculation,
and rate-recalculation paths for that orphan and its descendants.

Source order places newly registered `gpu_cc_ahb_clk` at the head of the
orphan list immediately before this scan. Its sole parent,
`gpu_cc_hub_ahb_div_clk_src`, has not registered yet. Nevertheless, the live
trace has no per-orphan marker, so it does not prove whether the stall is in
the new clock's repeated parent lookup, a later pre-existing orphan, list
iteration, or a callback reached while reparenting another clock.

This result excludes the earlier allocation, runtime-PM, topology insertion,
phase, duty, rate, and critical-clock steps. It still does **not** prove a
read or write at GPUCC branch register `0x1078`, invocation of
`clk_branch2_ops.enable`, or a GPUCC hardware fault. The generic orphan scan
can invoke code belonging to another clock.

## Rollback and cleanup

The probe did not return during its 30-second stability interval. The
independent 75-second watchdog was the only armed reset path; USB/SSH then
departed and the exact persistent fallback returned. The reset notice could
not traverse the disappearing USB link, so the host log ends at the CCF
boundary rather than the watchdog message.

Final checks passed:

- exact fallback kernel `5.4.134-qgki-perf-00001-g6c308144c23e`, ext4 root,
  and strict key-only SSH;
- zero Fastboot and ADB devices;
- inactive system NFS service and mount daemon;
- zero exports, NFS/mountd listeners, NFS threads, and network-root bind
  mounts;
- restored `ip_nonlocal_bind`, clean temporary firewall state, active
  firewalld, and active ModemManager;
- explicit, non-autoconnecting fallback USB profile restored;
- no temporary host sleep inhibitor;
- 73 readable fallback thermal zones with a 39.5 C maximum; and
- zero current fatal signatures and zero retained pstore records.

## Decision and next gate

GPUCC remains **rejected for normal coldplug**. V11 fulfilled its diagnostic
purpose but does not justify changing clock topology, skipping the orphan
scan, forcing a parent, or touching GPU hardware.

The next candidate, v12, must remain default-off and diagnostic-only:

1. pass the exact triggering core into the orphan-scan trace without changing
   normal behavior;
2. identify each orphan by stable clock name and bracket
   `__clk_init_parent()`;
3. when a parent resolves, separately bracket parent migration, accuracy
   recalculation, rate recalculation, and descendant propagation;
4. preserve exact call counts, lock scope, list mutations, return values, and
   all existing hardware operations under strict source and mutation tests;
5. bound marker volume and watchdog timing from an offline orphan-list test
   fixture before any device run;
6. reproduce two clean kernel/module builds and two wrapper/package builds;
   and
7. repeat the same zero-storage, one-shot probe, independent-watchdog,
   fallback, and complete host-cleanup gates.

No second live v11 probe is justified.
