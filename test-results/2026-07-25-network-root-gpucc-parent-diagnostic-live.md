# Network-root v13 GPUCC inner-parent diagnostic — live result

Date: 2026-07-25

Result: **bounded diagnostic failure with successful rollback**. V13 proved
that the global CCF orphan scan entered the display clock's existing
`get_parent()` callback while its provider was runtime-suspended. The final
marker was:

```text
phase=orphan-get-parent-begin clock=disp_cc_mdss_pclk0_clk_src ret=0
```

The matching callback-complete marker never arrived, and neither parent-cache
marker appeared. This excludes CCF's later cached-parent lookup from the
non-returning boundary. It does **not** yet prove that the callback reached its
regmap read or that a particular register access caused the stall.

The independent 75-second SysRq watchdog reset the phone to the exact
persistent fallback. Nothing was flashed, Linux 7.1 exposed no physical
storage, standard pstore retained no target-kernel fatal record, and all
temporary host NFS, firewall, inhibitor, and network state was removed.

## Scope and safety boundary

- Temporary `fastboot boot`, followed by the attended RAM-only kexec path.
- Linux `7.1.4-g7a5cef0db479` with OverlayFS over a read-only NFSv4.2 lower.
- SCSI/UFS absent from the kernel, zero physical block devices, and zero
  block-backed mounts.
- Only `/soc@0/clock-controller@3d90000` changed from `disabled` to `okay`.
- GPU, GMU, Adreno SMMU, display consumers, UFS, RTC, input, and every remote
  processor remained explicitly disabled.
- The GPUCC module was copied only to target tmpfs, root-owned, mode `0400`,
  and pinned to SHA-256
  `574fefd282fbff6577c921a116a5485546e788ca338802b960b26b9ad9fc6d9c`.
- Both diagnostic parameters were read-only, default-off, and enabled exactly
  once only for this exact-compatible boot.
- The trace added logging and deliberate 100 ms delivery delays. It did not
  add, skip, or modify a clock, parent, register, reset, power domain,
  regulator, storage, or persistent-state operation.
- The original 900-second network-root rollback watchdog remained armed
  through the baseline and payload gate. It was disarmed only when the
  independent 75-second process-group watchdog was ready to replace it.
- The probe was invoked once. No module-load or `execute` action was retried
  after kexec.
- No firmware, credential, personal data, full command line, or private device
  identifier entered this report. The complete 11,066-byte probe log remains
  private outside the repository with mode `0600`; its SHA-256 is
  `204e9cd4d52a06797104ab38b2c9b3a29412d498fd29fb982f550e8f0410ebe3`.

## Reproducible candidate

The
[v13 offline report](2026-07-25-network-root-gpucc-parent-diagnostic-offline.md)
records the complete source, mutation, duplicate-build, wrapper, package,
transport, and privileged-host gates. The final diagnostic source is commit
`f7c0a9d067db77f05a40a5bc242c1e14ac297ac5`, tree
`adec6b40ce25145e3e18cd82a788aa458514017d`. Its patch SHA-256 is
`6531645c80d9e07e40baf7d8af8ba6732f5ddfc75a3255a6dd75c8c3b8f7b5b5`.

The two clean Linux builds and two ASUS wrapper/package builds matched
byte-for-byte. The live inputs were:

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 Image | `1c5c1bd3841c6fdc2f0ebc29fb19f43099e4d5e70d63d9a183cd9646f6c35c28` |
| Linux 7.1.4 Image.gz | `217f66c1370600542fe6a6b1349ae7e449bceade5ee64d56504e259ee76e0049` |
| matching module archive | `22d069c6d8bea928f5fac6ab3107bb007b2cb76fd95fc85541780cb5d315f199` |
| external `gpucc-sm8350.ko` | `574fefd282fbff6577c921a116a5485546e788ca338802b960b26b9ad9fc6d9c` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `0f311f92113f443df395e249f04109539038569e472c1379002a934e5aca8770` |
| ASUS wrapper Image | `99f197cd36a55dce7ae37670ec390cae83e16164ba4b8cac93ee672842b74e38` |
| raw boot image | `c5ebd75037a4099ba396fb7ea98d84824461c6379986845c5c8b5acf684c9ca2` |
| temporary-boot AVB image | `8433036e89733427b53e33dba8e26b1999b11ef12cbb79433badebe2acc9bedf` |

## Live baseline and transport

Before watchdog disarm, the target passed:

- exact Linux 7.1.4, PID 1 systemd, and running system state;
- runtime-masked automatic udev and module coldplug;
- both exact trace flags and immutable mode-`0400` `Y` core parameters;
- OverlayFS `/`, exact read-only NFSv4.2 lower, and stable USB carrier;
- zero physical block devices and zero block-backed mounts;
- zero failed units and zero current fatal kernel signatures;
- GPUCC `okay`, with GPU, GMU, Adreno SMMU, UFS, display consumers, RTC,
  reserved RMTFS, and every remote processor disabled;
- no loaded GPUCC module and no DRM render node;
- 29 readable thermal zones with a 36.8 C maximum; and
- the original rollback watchdog alive at 229 seconds of its 900-second
  interval after the added quiet-log check.

One boot-time PMIC-arbiter transaction warning and call trace appeared for
register `0xcf08`. It was outside the GPUCC/CCF path. A further 12-second
quiet interval produced no new warning or fatal message while system state,
zero-storage, USB carrier, and thermals remained healthy. The event is
retained as a separate baseline observation; it is not evidence about the
clock stall. The private baseline log is 33,449 bytes, mode `0600`, with
SHA-256
`c1057336837a6209e8cfd1d56b5f44baf4f198002327b1b2e264f3f923d3d7fc`.

The first fixed staging `load-gpucc-diagnostic` marker was lost during ACM
re-enumeration. The bounded transport recovery rediscovered a stable endpoint
and replayed the exact same idempotent load command once; that replay passed.
The one-shot `execute` action was sent exactly once and was never retried.

The target exposed one standard `console-ramoops` file. A private, mode-`0600`
copy is 226,203 bytes with SHA-256
`2ccf9be7f3582b0a70440292fb26423f344598797ca536887ccd41a3d5fa7d41`.
It contains only the preceding Linux 5.4.210 staging console, no Linux 7.1
target content, and no case-sensitive fatal signature. Its five warnings are
the same known staging-vendor messages seen by v12: three in
`_regulator_disable`, one in `device_create_file`, and one in `enable_irq`.
After watchdog reset, the exact fallback exposed zero pstore records.

## Delivered trace

The host captured exactly 7 GPUCC-driver markers, 21 Qualcomm common-clock
markers, and 59 generic CCF markers. The original network-root watchdog
disarm PASS and probe BEGIN each appeared exactly once. Neither probe PASS nor
probe FAIL appeared before the USB/SSH transport departed. The module-load
return marker and independent-watchdog expiry notice also could not traverse
the departed transport.

The decisive ordered CCF sequence was:

```text
phase=orphan-reparent-begin clock=gpu_cc_ahb_clk ret=0
phase=orphan-scan-entry clock=gpu_cc_ahb_clk ret=0
phase=orphan-parent-lookup-begin clock=gpu_cc_ahb_clk ret=0
phase=orphan-parent-shape clock=gpu_cc_ahb_clk ret=2
phase=orphan-runtime-state clock=gpu_cc_ahb_clk ret=13
phase=orphan-parent-cache-begin clock=gpu_cc_ahb_clk ret=0
phase=orphan-parent-cache-complete clock=gpu_cc_ahb_clk ret=0
phase=orphan-parent-lookup-complete clock=gpu_cc_ahb_clk ret=0
phase=orphan-scan-complete clock=gpu_cc_ahb_clk ret=0
phase=orphan-scan-entry clock=disp_cc_mdss_pclk0_clk_src ret=1
phase=orphan-parent-lookup-begin clock=disp_cc_mdss_pclk0_clk_src ret=0
phase=orphan-parent-shape clock=disp_cc_mdss_pclk0_clk_src ret=7
phase=orphan-runtime-state clock=disp_cc_mdss_pclk0_clk_src ret=7
phase=orphan-get-parent-begin clock=disp_cc_mdss_pclk0_clk_src ret=0
```

The shape encoding is `(num_parents << 1) | has_get_parent`. The display value
`7` therefore means three parents and a `get_parent()` callback. Runtime-state
bits are provider present (`1`), runtime PM enabled (`2`), status suspended
(`4`), and `pm_runtime_active()` (`8`). The display value `7` means its
provider exists, runtime PM is enabled, its status is suspended, and
`pm_runtime_active()` is false.

The GPUCC shape value `2` means one parent and no callback, so its parent-cache
lookup completed normally. Its runtime value `13` records provider presence,
suspended status, and a true `pm_runtime_active()` helper result while
`rpm_enabled` is false. That helper treats disabled runtime PM as active; the
value is not proof that GPUCC hardware was powered.

No display `orphan-get-parent-complete`,
`orphan-parent-cache-begin`, `orphan-parent-cache-complete`, or outer
parent-lookup completion followed.

## Source localization and interpretation

Linux source maps `disp_cc_mdss_pclk0_clk_src` on SM8350 to
`drivers/clk/qcom/dispcc-sm8250.c`. It is a three-parent RCG at command offset
`0x2098`, using `clk_pixel_ops`. That operation table maps `get_parent()` to
`clk_rcg2_get_parent()` in `drivers/clk/qcom/clk-rcg2.c`.

After local setup, the callback's first substantive operation is:

```c
ret = regmap_read(rcg->clkr.regmap, RCG_CFG_OFFSET(rcg), &cfg);
```

V13 brackets only the callback as a whole. Its final marker proves callback
entry and excludes the later CCF parent-cache lookup, but it cannot distinguish
local setup from the regmap call, prove that the call began, or determine
whether it returned.

The display clock-controller probe enables runtime PM, resumes the provider
for mapping and clock registration, and then puts it. V13 directly records
that provider as runtime-suspended when the later GPUCC registration revisits
its orphan.

The global orphan scan runs while CCF's `prepare_lock` is held. Existing CCF
code deliberately obtains broad provider runtime-PM references outside that
lock in paths such as `clk_pm_runtime_get_all()`, because a provider's
resume/suspend callback may itself need the prepare lock. Therefore adding a
display-provider runtime resume directly inside this locked scan could
deadlock. V13 does not justify that change.

The result is not evidence of a GPUCC branch-register access or GPU hardware
fault. It identifies a cross-provider interaction: late GPUCC clock
registration revisits a runtime-suspended DISPCC orphan and does not return
from its parent callback.

## Rollback and cleanup

The probe did not return during its stability interval. The independent
75-second watchdog was the only armed reset path; USB/SSH departed and the
exact persistent fallback returned. The reset notice could not traverse the
disappearing USB link, so the host log ends at the callback boundary rather
than the watchdog message.

Final checks passed:

- exact fallback kernel `5.4.134-qgki-perf-00001-g6c308144c23e`, ext4 root,
  and strict key-only SSH;
- zero Fastboot and ADB devices, with the exact fallback USB gadget present;
- zero retained pstore records, current fatal signatures, or diagnostic
  modules;
- 73 readable fallback thermal zones with a 38.1 C maximum;
- inactive system NFS service and mount daemon;
- zero exports, NFS listeners, NFS threads, and network-root bind mounts;
- restored `ip_nonlocal_bind`, zero exact temporary firewall rules, active
  firewalld, and active ModemManager;
- explicit, non-autoconnecting fallback USB profile restored; and
- no temporary host sleep inhibitor.

## Decision and next gate

GPUCC remains **rejected for normal coldplug**. V13 fulfilled its diagnostic
purpose but does not justify powering DISPCC inside the locked scan, skipping
the global orphan scan, forcing a parent, or changing any clock or runtime-PM
behavior. No second live v13 probe is justified.

Before another live attempt, v14 must begin with source design and tests:

1. add a default-off, exact-clock trace inside `clk_rcg2_get_parent()` that
   brackets the existing regmap read while preserving exactly one read and all
   return behavior;
2. reject broad RCG tracing, extra reads, runtime-PM control, hardware control,
   or an enlarged watchdog budget through source and mutation tests;
3. reproduce two clean kernel/module builds and two wrapper/package paths;
4. separately evaluate an upstream-quality behavioral fix, either avoiding
   unrelated orphan callbacks until a candidate parent is available or
   acquiring required provider PM references outside `prepare_lock`;
5. require lock-order analysis and focused tests before any runtime-PM
   behavior change; and
6. only after the diagnostic candidate passes every offline gate, consider one
   attended zero-storage probe with the same independent watchdog, exact
   fallback, and complete host cleanup.
