# Network-root v14 DISPCC RCG parent-read diagnostic — live result

Date: 2026-07-25

Result: **bounded diagnostic failure with successful rollback**. V14 proved
that the existing `disp_cc_mdss_pclk0_clk_src` parent callback reached its
single existing regmap read and did not return from that call boundary. The
final marker was:

```text
phase=parent-read-begin clock=disp_cc_mdss_pclk0_clk_src ret=0
```

The matching `parent-read-complete` marker never arrived. Neither the outer
callback-complete marker nor any later CCF parent-cache marker appeared. This
localizes the first non-returning operation to the existing
`regmap_read()` call. It does **not** by itself prove a hardware fault,
distinguish an interconnect stall from a software locking problem, or justify
accessing a runtime-suspended provider.

The independent 75-second SysRq watchdog reset the phone to the exact
persistent fallback. Nothing was flashed, Linux 7.1 exposed no physical
storage, standard pstore retained no target-kernel fatal record, and all
temporary host NFS, firewall, inhibitor, address, and service state was
removed.

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
  `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a`.
- All three diagnostic parameters were read-only, default-off, and enabled
  exactly once only for this exact-compatible boot.
- The trace added logging and deliberate 100 ms delivery delays. It did not
  add, skip, or modify a clock, parent, register, reset, power domain,
  regulator, storage, or persistent-state operation.
- The inherited orphan limit was two entries. The maximum marker delay was
  4.2 seconds inside a prevalidated 75-second watchdog budget.
- The original 900-second network-root rollback watchdog remained armed
  through the baseline and payload gate. It was disarmed only when the
  independent 75-second process-group watchdog was ready to replace it.
- The probe and module load were invoked once. No module-load or `execute`
  action was retried after kexec.
- No firmware, credential, personal data, full command line, or private device
  identifier entered this report. The complete 11,166-byte probe log remains
  private outside the repository with mode `0600`; its SHA-256 is
  `776cf447b64da2ad87c41cb3ba449be163821fc2923290e02ce38853c1d5ac80`.

## Reproducible candidate

The
[v14 offline report](2026-07-25-network-root-gpucc-rcg2-diagnostic-offline.md)
records the complete source, mutation, duplicate-build, wrapper, package,
transport, and privileged-host gates. The final diagnostic source is commit
`6e40861cc51c067f9989c4513003e8fbd046c22f`, tree
`49ef6cb95768496b8f926b11e428ea224406464e`. Its patch SHA-256 is
`ac7975bf5f4cb2791f45a2fe8b5b811c7e60fd4692f8aff4cd71a2f2150fa3c6`.

The two clean Linux builds and two ASUS wrapper/package builds matched
byte-for-byte. The live inputs were:

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 Image | `5759d3d15ca60f260aa89731aa78c94acd5d183eca67dc24c3723f8877f213e3` |
| Linux 7.1.4 Image.gz | `b0e722af9b3777a1f83e546991394026b8337ab5ec06f29f0b305e1eedf79e4b` |
| matching module archive | `9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1` |
| external `gpucc-sm8350.ko` | `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `eb5b173bb44707aa67c601150b8c40016bb20d277792926028c99ed97a066ee6` |
| ASUS wrapper Image | `8676bbc20e79febfdf38782582a2e3b4bcb7658ee6b49ea4c61df2b9db61b2d0` |
| raw boot image | `1aa1597c31fb390a62fa8727de0e9b17bfcd05f57df69f0c7d1a916f965b0528` |
| temporary-boot AVB image | `29c3f0e7516e3ef8f7141c527a269d668d53bd9097fbf7e11c507b64010b91b2` |

## Live baseline and transport

Before watchdog disarm, the target passed:

- exact Linux 7.1.4, PID 1 systemd, and running system state;
- runtime-masked automatic udev and module coldplug;
- all three exact trace flags and immutable mode-`0400` `Y` core parameters;
- OverlayFS `/`, exact read-only NFSv4.2 lower, and stable USB carrier;
- zero physical block devices and zero block-backed mounts;
- zero failed units and zero current fatal kernel signatures;
- GPUCC `okay`, with GPU, GMU, Adreno SMMU, UFS, display consumers, RTC,
  reserved RMTFS, and every remote processor disabled;
- no loaded GPUCC module and no DRM render node;
- 29 readable thermal zones with a 36.8 C maximum; and
- the original rollback watchdog alive at 264 seconds of its 900-second
  interval.

The private baseline log is 38,563 bytes, mode `0600`, with SHA-256
`73747bfd21df8d3f05250a4a5212d99773f63f1b2122af1bae991b09a292f748`.
Immediately before the probe, all 29 target thermal zones remained readable
with a 36.5 C maximum and the fatal-signature count remained zero.

The first fixed staging `load-gpucc-diagnostic` marker was lost during ACM
re-enumeration. The bounded transport recovery rediscovered a stable endpoint
and replayed the exact same idempotent load command once; that replay passed.
The one-shot `execute` action was sent exactly once and was never retried.

The target exposed one standard `console-ramoops` file. A private, mode-`0600`
copy is 229,963 bytes with SHA-256
`2622e73000cbc443d46fa4b340d20d1b435105bef2da79f31e43a0c6c4d3c417`.
It contains only the preceding Linux 5.4.210 staging console, no Linux 7.1
target content, and no case-sensitive fatal signature. Its five warnings are
the same known staging-vendor classes already retained by the preceding
diagnostics. After watchdog reset, the exact fallback exposed zero pstore
records.

## Delivered trace

The host captured exactly 7 GPUCC-driver markers, 21 Qualcomm common-clock
markers, 59 generic CCF markers, and one RCG2 parent-read marker. The original
network-root watchdog disarm PASS and probe BEGIN each appeared exactly once.
Neither probe PASS nor probe FAIL appeared before the USB/SSH transport
departed. The module-load return marker and independent-watchdog expiry notice
also could not traverse the departed transport.

The seven GPUCC markers completed mapping and both PLL configurations, then
reached registration:

```text
ROG5 GPUCC diagnostic: begin
ROG5 GPUCC diagnostic: map-complete
ROG5 GPUCC diagnostic: pll0-begin
ROG5 GPUCC diagnostic: pll0-complete
ROG5 GPUCC diagnostic: pll1-begin
ROG5 GPUCC diagnostic: pll1-complete
ROG5 GPUCC diagnostic: registration-begin
```

The decisive ordered parent sequence was:

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
phase=parent-read-begin clock=disp_cc_mdss_pclk0_clk_src ret=0
```

The shape encoding is `(num_parents << 1) | has_get_parent`. The display value
`7` means three parents and a `get_parent()` callback. Runtime-state bits are
provider present (`1`), runtime PM enabled (`2`), status suspended (`4`), and
`pm_runtime_active()` (`8`). The display value `7` means its provider exists,
runtime PM is enabled, its status is suspended, and `pm_runtime_active()` is
false.

No `parent-read-complete`, display `orphan-get-parent-complete`, display
parent-cache marker, outer parent-lookup completion, or GPUCC registration
completion followed.

## Source localization and interpretation

Linux source maps `disp_cc_mdss_pclk0_clk_src` on SM8350 to
`drivers/clk/qcom/dispcc-sm8250.c`. It is a three-parent RCG at command offset
`0x2098`, using `clk_pixel_ops`. That operation table maps `get_parent()` to
`clk_rcg2_get_parent()` in `drivers/clk/qcom/clk-rcg2.c`.

V14 placed `parent-read-begin` immediately before the existing call:

```c
ret = regmap_read(rcg->clkr.regmap, RCG_CFG_OFFSET(rcg), &cfg);
```

It placed `parent-read-complete` immediately after the same call, preserving
one read, its original arguments, and all original return behavior. The first
marker appeared and the second did not. The non-returning boundary is
therefore inside that call, not in the callback's preceding local setup,
subsequent mux decoding, return path, or CCF's later cached-parent lookup.

The display clock-controller probe enables runtime PM, resumes the provider
for mapping and clock registration, and then puts it. V14 directly records
that provider as runtime-suspended when the later GPUCC registration revisits
its orphan.

The global orphan scan runs while CCF's `prepare_lock` is held. Existing CCF
code obtains broad provider runtime-PM references outside that lock in paths
such as `clk_pm_runtime_get_all()`, because a provider resume/suspend callback
may itself need the prepare lock. Adding a display-provider runtime resume
inside this locked scan could deadlock and is not authorized by this result.

The trace also cannot distinguish a non-returning MMIO transaction from an
interconnect, regmap-lock, or provider-state interaction beneath
`regmap_read()`. A behavioral fix requires separate lock-order analysis and
tests; it must not be inferred from this diagnostic patch.

## Rollback and cleanup

The probe did not return during its stability interval. The independent
75-second watchdog was the only armed reset path; USB/SSH departed and the
exact persistent fallback returned with a changed boot identity. The SSH
client ended with the expected transport status after the gadget departed.

Final checks passed:

- exact fallback kernel `5.4.134-qgki-perf-00001-g6c308144c23e`, ext4 root,
  and strict key-only SSH;
- zero Fastboot and ADB devices, with one fallback ACM and zero recovery ACM;
- zero retained pstore records, current fatal signatures, or diagnostic
  modules;
- 73 readable fallback thermal zones with a 38.5 C maximum;
- inactive system NFS service and mount daemon;
- zero exports, NFS listeners, NFS threads, NFS mounts, and network-root bind
  mounts;
- restored `ip_nonlocal_bind`, zero exact temporary firewall rules, active
  firewalld, and active ModemManager;
- explicit, active, non-autoconnecting fallback USB profile restored; and
- no temporary host sleep inhibitor.

## Decision and next gate

GPUCC remains **rejected for normal coldplug**. V14 fulfilled its diagnostic
purpose and must not be rerun. It does not justify powering DISPCC inside the
locked scan, skipping the global orphan scan, forcing a parent, enabling a
consumer, or changing a clock or runtime-PM state.

Before another live GPUCC attempt:

1. model the exact `prepare_lock`, orphan-list, provider runtime-PM, regmap,
   and DISPCC resume lock ordering from source;
2. write failing source, mutation, and concurrency tests for any behavioral
   candidate before changing kernel code;
3. prefer a general CCF/provider-lifetime correction over an ASUS-only forced
   parent or unconditional display power-on;
4. prove that the candidate neither calls provider runtime-resume beneath
   `prepare_lock` nor skips a legitimate orphan reparent;
5. reproduce two clean kernel/module and wrapper/package paths with unchanged
   storage, consumer, and rollback boundaries; and
6. only then consider one attended zero-storage probe under a fresh diagnostic
   version and the same independent watchdog.

A660 DRM/MSM, GMU, firmware, IOMMU, display, and accelerated desktop work
remain behind that separate behavioral-fix gate.
