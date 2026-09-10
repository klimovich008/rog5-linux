# Network-root v12 GPUCC orphan diagnostic — live result

Date: 2026-07-25

Result: **bounded diagnostic failure with successful rollback**. V12 proved
that the newly registered `gpu_cc_ahb_clk` is not the clock that blocks the
global orphan scan. Its parent lookup returned no parent and its scan entry
completed. The scan then advanced to a pre-existing display-clock orphan and
stopped after:

```text
ROG5 CCF diagnostic: phase=orphan-parent-lookup-begin clock=disp_cc_mdss_pclk0_clk_src ret=0
```

The matching `orphan-parent-lookup-complete` marker never arrived. This
directly brackets `__clk_init_parent()` for
`disp_cc_mdss_pclk0_clk_src`; it does not yet distinguish the clock driver's
`get_parent()` callback from the later cached-parent lookup inside that
function.

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
  `79a7d3b7d81c28821dd5199cdbcfe9b2cea5b8bc59b6d6e983a61a15f05424ba`.
- Both diagnostic parameters were read-only, default-off, and enabled exactly
  once only for this exact-compatible boot.
- The trace added logging and deliberate 100 ms delivery delays. It did not
  add, skip, or modify a clock, parent, register, reset, power domain,
  regulator, storage, or persistent-state operation.
- The original 900-second network-root rollback watchdog remained armed
  through the full baseline and payload gate. It was disarmed only when the
  independent 75-second process-group watchdog was ready to replace it.
- The probe was invoked once. No module-load or `execute` action was retried
  after kexec.
- No firmware, credential, personal data, full command line, or private device
  identifier entered this report. The complete 10,158-byte probe log remains
  private outside the repository with mode `0600`; its SHA-256 is
  `df9dde7b10ecb78396f335484293c76f726a483bc48b01b1225f5f682618e303`.

## Reproducible candidate

The [v12 offline report](2026-07-25-network-root-gpucc-orphan-diagnostic-offline.md)
records the complete source, mutation, duplicate-build, wrapper, package,
transport, and privileged-host gates. The final diagnostic source is commit
`b2059b161861d6d7d1aeb9b7d93ad86b13d85048`, tree
`040d5f9b7be022489079b2ea9cab20a04934d85f`. Its patch SHA-256 is
`bc026e783fe3b7f1f15cb0e3ac6ca914d4b45897da07db0f887565b1722172e6`.

The two clean Linux builds and two ASUS wrapper/package builds matched
byte-for-byte. The live inputs were:

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 Image | `49318395c5ed4850d492e4f29ea841885692bd96b6a5b0982925769282b687d9` |
| Linux 7.1.4 Image.gz | `193fc0cafc285bab4ff065c0be624aa11b768ad43685b4605e2a0bcfb96b0bf4` |
| matching module archive | `2c246d8ceed3c37cc2afefa56710ac5bbca2bc1bce0ca0409a361f8f5923a2e8` |
| external `gpucc-sm8350.ko` | `79a7d3b7d81c28821dd5199cdbcfe9b2cea5b8bc59b6d6e983a61a15f05424ba` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `204c0403005dac69fe6b153a41ee69498265afafcbefcb6019c9b15e6263889a` |
| ASUS wrapper Image | `5edd63574f6762380d63665bff5ca1cd29dd868dc4a6dd34b5ebfd6c91c6aab9` |
| raw boot image | `97952efb30b3dd037b2179c9079ca31561ff02d31a167d29436025419f2a246e` |
| temporary-boot AVB image | `4cbf626756d8b0ef390c7a915539fb59863a3d6152d2ba9daa0cec5ab5f6c8df` |

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
- 29 readable thermal zones with a 36.2 C maximum; and
- the original rollback watchdog alive at 318 seconds of its 900-second
  interval.

The first fixed staging `load-gpucc-diagnostic` marker was lost during ACM
re-enumeration. The bounded transport recovery rediscovered a stable endpoint
and replayed the exact same idempotent load command once; that replay passed.
The one-shot `execute` action was sent exactly once and was never retried.

The target exposed one standard `console-ramoops` file. A private, mode-`0600`
copy is 226,660 bytes with SHA-256
`c11de9868b34307ad2d5ab4678dff0f7835ef69286f3e836e8a3c8a8ce0a239a`.
It contains only the preceding Linux 5.4.210 staging console, no Linux 7.1
target content, and no case-sensitive fatal signature. Its five warnings are
known staging-vendor messages in `_regulator_disable`,
`device_create_file`, and `enable_irq`; the current target log was clean.
The record was therefore classified as staging-only evidence, not a target
failure. After the watchdog reset, the exact fallback exposed zero pstore
records.

## Delivered trace

The host captured exactly 7 GPUCC-driver markers, 21 Qualcomm common-clock
markers, 52 generic CCF markers, and 7 per-orphan markers. The original
network-root watchdog disarm PASS and probe BEGIN each appeared exactly once.
Neither probe PASS nor probe FAIL appeared before the USB/SSH transport
departed.

The complete ordered per-orphan sequence was:

```text
phase=orphan-reparent-begin clock=gpu_cc_ahb_clk ret=0
phase=orphan-scan-entry clock=gpu_cc_ahb_clk ret=0
phase=orphan-parent-lookup-begin clock=gpu_cc_ahb_clk ret=0
phase=orphan-parent-lookup-complete clock=gpu_cc_ahb_clk ret=0
phase=orphan-scan-complete clock=gpu_cc_ahb_clk ret=0
phase=orphan-scan-entry clock=disp_cc_mdss_pclk0_clk_src ret=1
phase=orphan-parent-lookup-begin clock=disp_cc_mdss_pclk0_clk_src ret=0
```

For `orphan-parent-lookup-complete`, `ret=0` is the expected “no registered
parent” state. For `orphan-scan-entry`, `ret=1` is the zero-based trace
position of the second orphan, not an error code. No parent-resolution,
reparent, accuracy, rate, requested-rate, scan-completion, outer
orphan-reparent-completion, runtime-PM put, index-0 registration completion,
provider completion, module-load return, probe PASS, or probe FAIL marker
followed.

## Source localization and interpretation

The missing boundary directly brackets this unmodified call in
`clk_core_reparent_orphans_nolock()`:

```c
parent = __clk_init_parent(orphan);
```

V12 therefore excludes the newly registered `gpu_cc_ahb_clk` from the
non-returning operation: its complete no-parent scan is present, and the
global list advanced to the next entry.

Linux source maps `disp_cc_mdss_pclk0_clk_src` on SM8350 to
`drivers/clk/qcom/dispcc-sm8250.c`. It is a three-parent RCG using
`clk_pixel_ops`. For a multi-parent clock, `__clk_init_parent()` first invokes
`core->ops->get_parent()`. Here that resolves to `clk_rcg2_get_parent()`,
whose first substantive operation is a regmap read of the RCG configuration
register. Only after the callback returns does CCF call
`clk_core_get_parent_by_index()`.

That source order makes the display-clock `get_parent()` callback the first
untraced candidate, but the v12 markers do **not** prove that a particular
register read occurred, that it caused the stall, or that the later
parent-cache lookup was never reached. A plausible hypothesis is that this
previously registered display-clock orphan is queried after its provider has
runtime-suspended; the display clock-controller probe enables runtime PM,
resumes for registration, and puts the provider afterward. This remains an
inference until a narrower trace records provider runtime state and brackets
the callback without changing that state.

The result is not evidence of a GPUCC branch-register access or GPU hardware
fault. It instead identifies a cross-provider interaction in generic CCF:
late GPUCC clock registration causes a global scan that revisits an existing
DISPCC orphan.

## Rollback and cleanup

The probe did not return during its stability interval. The independent
75-second watchdog was the only armed reset path; USB/SSH departed and the
exact persistent fallback returned. The reset notice could not traverse the
disappearing USB link, so the host log ends at the CCF boundary rather than
the watchdog message.

Final checks passed:

- exact fallback kernel `5.4.134-qgki-perf-00001-g6c308144c23e`, ext4 root,
  and strict key-only SSH;
- zero Fastboot and ADB devices, with the exact fallback USB gadget present;
- zero retained pstore records, current fatal signatures, or diagnostic
  modules;
- 73 readable fallback thermal zones with a 38.5 C maximum;
- inactive system NFS service and mount daemon;
- zero exports, NFS listeners, NFS threads, and network-root bind mounts;
- restored `ip_nonlocal_bind`, zero temporary firewall rules, active
  firewalld, and active ModemManager;
- explicit, non-autoconnecting fallback USB profile restored; and
- no temporary host sleep inhibitor.

## Decision and next gate

GPUCC remains **rejected for normal coldplug**. V12 fulfilled its diagnostic
purpose but does not justify skipping the global orphan scan, forcing a
parent, keeping DISPCC powered, or changing any clock or runtime-PM behavior.
No second live v12 probe is justified.

The next candidate, v13, must remain default-off and diagnostic-only:

1. preserve the exact v12 trigger, four-entry limit, global prepare-lock scope,
   call counts, list mutations, return values, and hardware behavior;
2. for each traced multi-parent orphan, bracket `ops->get_parent()` and then
   `clk_core_get_parent_by_index()` separately;
3. record only read-only structural state needed to interpret the callback,
   including parent count, callback presence, and provider runtime-PM state,
   without resuming, suspending, or otherwise controlling the provider;
4. source-test the exact operation order and a reduced marker/watchdog budget;
5. reproduce two clean kernel/module builds and two wrapper/package builds;
   and
6. only after every offline gate passes, run one attended zero-storage probe
   with the same independent watchdog, exact fallback, and complete host
   cleanup.
