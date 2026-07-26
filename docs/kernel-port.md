# Linux 7.x board-port plan

## Why 7.1.4

As of 2026-07-22, Linux 7.1.4 is the current stable kernel. It is a better research baseline than an unmaintained 6.7 SM8350 fork because upstream already contains SM8350 SoC support, the MSM DPU/DSI display stack, A660 GPU support, Qualcomm remoteproc, PMIC GLINK, UFS, and DWC3 infrastructure.

The missing piece is board support. Linux 7.1.4 has SM8350 DTS files for the Qualcomm HDK/MTP, Microsoft Surface Duo 2, and Sony Sagami devices, but no ASUS `anakin` DTS. postmarketOS pmaports at commit `29afb81e…` likewise has no ROG Phone 5 package; its generic SM8350 kernel package is archived and based on an old 6.7 fork.

This project therefore creates a new board DTS and minimal supporting drivers/quirks on top of upstream. It does not rewrite the Linux kernel from nothing.

Linux 6.18 is also retained as the LTS comparison branch because kernel.org projects maintenance through December 2028. Current-stable 7.1 is the development baseline; 6.18 is the eventual long-lived deployment candidate if it passes the same hardware matrix.

## Inputs

- Linux stable v7.1.4 source, pinned by commit.
- Running vendor device tree exported from `/sys/firmware/fdt` or `/proc/device-tree` for comparison only.
- ASUS-released kernel source and the working 5.4.210 configuration as behavioral references.
- Stock Android DTBO/vendor boot metadata and partition backups.
- Upstream SM8350 HDK, MTP, Surface Duo 2, and Sony Sagami DTS files.
- Locally extracted firmware, never committed.

## Bring-up phases

### Phase A — reproducible compile

1. Cross-compile upstream `Image.gz` and known SM8350 DTBs on the PC to prove the pinned source and toolchain. These comparison DTBs must never be booted on the ASUS device.
2. Start the board port from `arm64 defconfig` plus `configs/kernel/rog5-mainline.fragment`.
3. Compile a serial-only `sm8350-asus-rog-phone5.dts` skeleton, then add reviewed memory/reserved-memory references, UFS, and one USB controller. The skeleton itself is never booted.
4. Run `dtbs_check`, `make W=1`, and record warnings.
5. Produce `Image.gz`, the recovery-grade ASUS DTB, modules, initramfs, and a header-v3 temporary boot image with hashes.

### Phase B — recovery-grade boot

Only console, a RAM-only initramfs, USB NCM/ACM, SSH, watchdog visibility, and reboot are required. UFS remains disabled until host-visible remote recovery works. Display, radio, charging, audio, cameras, and GPU remain disabled. The image is used only with `fastboot boot`.

### Phase C — power and charging

Port PMIC GLINK/battery telemetry, Type-C role detection, charging, thermal zones, and CPU/GPU cooling. Validate current direction and battery temperature before enabling performance modes.

### Phase D — input and display

Add the exact AMS678 ER2 panel description, DSI DSC timings, FocalTech touch, backlight, and power button. The vendor display chain also contains a Pixelworks Iris/i6 processor and per-mode light-up configuration; Linux 7.1.4 has no matching upstream bridge driver. Determine whether a safe pass-through mode exists or port the minimal bridge initialization before treating display as available. Implement fixed 60/90/120/144 modes; do not claim VRR because the panel advertises no qsync/DFPS support.

### Phase E — radio and remote processors

Bring up ADSP/CDSP/modem/SLPI one at a time with correct reserved memory and firmware paths. Add Wi-Fi only after remoteproc and power stability. Preserve the known radio startup delay until measurement proves it unnecessary.

### Phase F — mainline GPU

Use upstream DRM/MSM Freedreno rather than vendor KGSL. Validate A660 firmware, IOMMU mappings, GMU idle transitions, repeated render-node opens, Turnip, and KWin. This is expected to remove the current vendor KGSL second-open failure, but it is not assumed until tested.

The compile-only GPU tier is deliberately a two-node overlay: enable upstream `&gpu` and select the upstream SM8350 zap-shader path. Linux 7.1 already supplies the A660/GMU/SMMU hardware description and driver. The three matching payloads from `linux-firmware` 20260622 pass pinned hashes and the zap image is valid Qualcomm DSP6 ELF32. They remain outside Git and outside the recovery package until the base recovery boot passes on hardware.

### Phase G — observability and automation

Enable BTF/eBPF and run GodShell as an optional systemd-managed workload. Then add remote AI services under an unprivileged account and an explicit approval boundary for email/job actions.

## Two-stage recovery boot

ROG Phone 5 uses Android boot header v3, and the stock-style boot template has no DTB field. Passing the new ASUS DTB directly through a normal boot image is therefore not available without changing `vendor_boot`, which is outside the recovery safety boundary.

The v18 candidate uses this intended reversible two-stage route:

1. `fastboot boot` starts an ASUS-source-compatible 5.4.210 kernel with the staging initramfs built into the kernel. Nothing is flashed.
2. The built-in initramfs contains the Linux 7.1 `Image`, USB2-only recovery DTB, target initramfs, and signed Alpine ARM64 `kexec` runtime. Its offline contract contains no storage-mount logic.
3. `rog5-load-mainline-recovery` verifies all three nested hashes, disables and verifies the single Haven hypervisor watchdog, and loads the mainline kernel, DTB, and initramfs. Execution remains a separate attended command.
4. Both the staging and target initramfs arm a 180-second forced-reboot timer,
   reject block-backed mounts, apply and verify `BLKROSET` on every enumerated
   physical disk and partition, and expose USB only after that gate passes.
   Volatile loop, RAM, and zram objects remain writable. USB ACM is the
   credential-free fallback; USB NCM may use an explicitly supplied test
   address.

The recovery overlay enables only the reviewed `usb_1` wrapper and its
high-speed FEMTO PHY. The DWC3 child uses one `usb2-phy`; UFS, QMP/SuperSpeed,
the secondary `usb_2` controller, display, charging, radios, remote processors,
and GPU remain disabled. The overlay passes static inspection. The v6 bundle
passed its then-current offline verifier but failed live ACM data and rollback;
recovery v12 rebuilt the dependency chain but remained unbooted because it
lacked the pre-USB block-device lock. V13 added an all-block-device gate and
v14 narrowed it to physical storage, but both returned to fallback after 21
seconds without exact recovery USB. V15 reproduced the chain with bounded
failure delays; its exact 31-second live return identified the unnecessary
wake-lock gate before storage isolation. V16 removes that gate and all timing
delays while retaining the watchdog and physical-storage boundary. It reached
exact USB, NCM, and rollback but lacked `/dev/ttyGS0`. A local keyed v17
diagnostic proved the RAM-backed root, zero block mounts, all 116 physical
nodes read-only, and the live `mdev -s` ACM fix. V18 makes that rescan and a
second storage gate mandatory before USB binding. Its duplicate builds and
offline verifier pass. V18 staging and rollback now also pass twice with RAM
root, zero block mounts, 116 read-only physical nodes, ACM/NCM, and changed
fallback boot identities. A separately attended kexec then booted
`7.1.4-g7a5cef0db479`; its zero-storage RAM recovery, ACM/NCM, independent
watchdog, fatal-log check, and automatic fallback also passed. The next board
tier enables only reviewed UFS dependencies for read-only, no-mount discovery.

That UFS discovery tier now passes, and network-root v2 advances the same
two-stage route to a normal Arch PID 1. Its recovery DTB additionally disables
RMTFS, GPUCC, GPU, GMU, and the Adreno SMMU; two unmasked coldplug boots pass
the headless systemd/SSH/storage/USB/NFS gates. Network-root v3 retains a
minimal shutdown initramfs and passes one normal systemd reboot to the
persistent fallback with complete host cleanup. Repeated clean cycles remain
required as new hardware tiers are enabled. GPUCC-only v10 keeps every
consumer disabled and narrows the stall to generic CCF registration of
non-critical clock index 0. Network-root v11 implements the exact-compatible
allocation, locking, runtime-PM, topology, and orphan trace and passes
duplicate clean builds, source contracts, mutations, transport tests,
wrappers, and package verification. Its attended probe completed every traced
index-0 phase through orphan insertion, rate handling, and the non-critical
branch, then stopped inside `clk_core_reparent_orphans_nolock()`. Independent
rollback and complete cleanup passed. This still does not prove
branch-register access because that global scan may invoke another orphan's
callbacks. Network-root v12 passed the offline half of the next gate: an
exact-device/default-off trace covers at most four orphan entries and all
existing parent lookup, reparent, accuracy/rate, and requested-rate operations
with a 5.6-second maximum marker delay. Source-order/mutation tests and two
clean kernel, wrapper, and package paths pass byte-for-byte. Its one attended
probe completed `gpu_cc_ahb_clk` as a no-parent orphan and advanced to
`disp_cc_mdss_pclk0_clk_src`, where `__clk_init_parent()` did not return.
The first source operation is that display RCG's `get_parent()` callback,
followed by CCF's parent-cache lookup, but v12 cannot distinguish them. Exact
fallback and cleanup passed. V13 now passes the complete offline half of that
gate: six exact-trigger markers bracket those two original operations and
record read-only provider runtime state without hardware or runtime-PM
control. Source/mutation tests, an 8-second trace bound, two clean
kernel/module builds, and two wrapper/package paths pass byte-for-byte. V13
then ran once: it recorded the display orphan's provider runtime-suspended,
entered its `get_parent()` callback, and did not reach the callback-complete or
later parent-cache markers. Source resolves that callback to
`clk_rcg2_get_parent()`, but v13 does not instrument inside it and therefore
does not prove that its regmap read began. Independent rollback, exact
fallback, and cleanup passed.

V14 passed that complete offline source gate. Its exact-clock, default-off,
mode-`0400` trace brackets the one existing display-RCG regmap read while
preserving one read and all return behavior. The inherited orphan limit drops
from four to the two entries already localized by v13. Source, mutation,
integration, and timing tests cap the added delay at 4.2 seconds and reject
extra register accesses, broad tracing, runtime-PM control, and hardware
control. Two mainline builds, credential-free staging initramfs files,
independently prepared ASUS wrappers, and Android packages match
byte-for-byte. The exact bundle verifier passes with every consumer disabled.
Its one attended RAM-only diagnostic reached `parent-read-begin` and did not
reach `parent-read-complete`. Exact fallback, zero retained pstore/fatal
records, and complete host cleanup passed. This localizes the non-returning
boundary to the existing regmap call without identifying the mechanism. V14
must not be rerun.

The behavioral gate now has an offline-accepted v15 candidate. Its exhaustive
finite-state model makes the old order and get-beneath-`prepare_lock`
mutations reach ABBA deadlock, while the candidate core and both OF-provider
paths reach neither deadlock nor reference leak. Red/green source,
integration, mutation, exact-patch, and clock KUnit tests pass. The candidate
is an experimental partial backport of the unmerged March 2025 CCF runtime-PM
RFC: it acquires generic all-provider runtime-PM references before
`prepare_lock`, preserves the orphan scan, unlocks, and then releases the
references.

Two clean mainline builds and two independently prepared nested
wrapper/package paths match byte-for-byte. Exported symbols, the full module
archive, GPUCC module, and RCG2 object remain identical to v14. V15 adds no
device-specific path, direct display-provider resume, register access, forced
parent, or consumer. See the
[v15 offline report](../test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-offline.md).

Its single attended RAM-only probe made DISPCC active, completed all seven
observed RCG reads, and completed GPUCC clock indexes 0 through 6 before
starting index 7. The 75-second watchdog fired after 73.901 seconds of
uninterrupted 100 ms trace delivery, with no marker gap above 0.116 seconds.
This supports the runtime-PM ordering hypothesis but does not prove complete
GPUCC registration. Exact fallback and host cleanup passed. V15 must not be
rerun. The
[v15 live report](../test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-live.md)
defines the next trace-free v16 confirmation gate.

V16 now passes that offline gate with byte-identical v15 kernel/package
artifacts. Its explicit load action supplies no Qualcomm/CCF/RCG2 trace flag,
and its confirmation probe requires all three built-in parameters to be
mode-`0400` `N` with command-line count zero. A hash-pinned read-only baseline
checks those states, zero storage, and consumer isolation while the initial
watchdog remains armed. Only the delay-free outer GPUCC trace remains.
Semantic and mutation tests, the baseline source test, the existing
guarded-probe suite, nine ACM pseudoterminal tests, and the complete exact
bundle verifier pass.
See the
[v16 offline report](../test-results/2026-07-25-network-root-gpucc-confirmation-offline.md).

V16's attended cycle stopped before Linux 7.1 target entry: the trace-free
payload loaded, a 284-second operator gap exceeded the staging watchdog, and
both later execute paths failed before serial transmission. Exact fallback
and cleanup passed, so this is no evidence for or against the kernel
candidate. V16 is consumed. V17 offline-accepts the same kernel and target
contract with an atomic, guard-first load-to-execute host sequence. Its 12 ACM
tests, semantic/mutation suite, and complete nested bundle verifier pass. See
the
[v16 staging-only report](../test-results/2026-07-26-network-root-gpucc-confirmation-live.md)
and
[v17 offline report](../test-results/2026-07-26-network-root-gpucc-atomic-confirmation-offline.md).
V17's sole live cycle passes: the compound transport sent exactly one execute,
the trace-free GPUCC module completed registration, bound one device, and
remained stable for 30 seconds. Every real consumer, render node, and storage
path stayed absent; no new warning or fault appeared. Normal reboot restored
the exact fallback and complete cleanup. This accepts the experimental CCF
ordering only as the isolated GPUCC foundation. Before enabling a consumer,
the next candidate must source-test and reproduce the complete GPU
power/regulator/interconnect, Adreno SMMU, GMU, reserved-memory, and firmware
dependency graph. See the
[v17 live report](../test-results/2026-07-26-network-root-gpucc-atomic-confirmation-live.md).

V18 splits that graph at the first independently testable consumer boundary.
Pinned Linux 7.1.4 source proves the Adreno SMMU needs exactly seven clocks,
one GPUCC CX GDSC, twelve IRQs, and generic ARM SMMU runtime PM, with no
firmware path. Its overlay enables only GPUCC and the SMMU; GPU and GMU remain
disabled. The unchanged v15 Image/modules/target initramfs and external GPUCC
module are combined with a reproducible DT, nested stage, clean-built ASUS
wrapper, and temporary-boot package. All offline gates pass without contacting
the phone. See the
[v18 offline report](../test-results/2026-07-26-network-root-adreno-smmu-offline.md).
Its one attended control-plane run stopped safely at the read-only baseline:
`fault` matched inside the normal word `Default`, before watchdog disarm,
module load, or SMMU bind. Exact fallback and cleanup passed, so v18 is
consumed and must not be retried. V19 retains the exact reproduced v18 binary
while correcting and regression-testing only the external detectors, source
locks, export seal, and NFS allowlist. Its isolated firmware-free export and
full offline verifier pass. Its attended gate then passed baseline and GPUCC
registration but safely rejected because the SMMU remained unbound after the
full settle. No warning, fault, firmware, render, storage, failed-unit, or
unsafe-temperature message appeared; watchdog fallback and cleanup passed.
V19 is consumed. V20 keeps the same binary and now passes a source-locked
exact-device control plane: platform `drivers_probe` performs exact-name
lookup and one unbound-device `device_attach()`, while the ARM SMMU force-bind
attributes remain suppressed and the ten-second global deferred timeout stays
unchanged. The target captures waiting/deferred/supplier state, permits five
seconds of normal autoprobe, and can issue only one `3da0000.iommu` request
under nested 90/150-second watchdogs. The full binary verifier and isolated
firmware-free v20 root passed offline; the phone was not contacted at that
checkpoint. Its one live cycle later stopped at the read-only baseline because
the source-consistent unset `driver_override` text is `(null)`, not an empty
line. The original watchdog remained armed; no GPUCC load,
`drivers_probe` write, SMMU bind, firmware/render/storage action, or unsafe
cleanup occurred. V20 is consumed.

V21 passed the separately source-tested correction. It pins the OF
platform allocation path, zero initialization, NULL `%s` formatting,
override match semantics, and OF fallthrough. Its read-only seven-byte
checker accepts exact `(null)\n`, rejects mutations, and is the only change to
the unchanged binary's target control plane. The complete verifier and a new
isolated, firmware-free v21 root pass; v20 remains preserved but cannot be
served. Its sole live cycle then loaded accepted GPUCC, issued one exact
platform reprobe, bound `arm-smmu`, and reached runtime suspend with zero
firmware, render, storage, mount, or failed-unit activity. Normal reboot,
persistent fallback, and complete host cleanup passed. V21 is consumed,
removed from the runnable NFS allowlist, and must never be retried. This
accepts only the idle SMMU foundation; acceleration remains out of scope. See
the
[safe-rejection report](../test-results/2026-07-26-network-root-adreno-smmu-v18-live-rejected.md)
and the
[v19 no-bind report](../test-results/2026-07-26-network-root-adreno-smmu-v19-live-rejected.md).
The
[v20 offline report](../test-results/2026-07-26-network-root-adreno-smmu-v20-offline.md)
records the source proof, exact live boundary, fail-first suite, root seal, and
historical live-eligibility decision. The
[v20 safe baseline-rejection report](../test-results/2026-07-26-network-root-adreno-smmu-v20-live-rejected.md)
records the no-action stop, source diagnosis, fallback, and v21 boundary. The
[v21 offline report](../test-results/2026-07-26-network-root-adreno-smmu-v21-offline.md)
records the source proof, mutation suite, unchanged binary, isolated root, and
one-shot live boundary. The
[v21 live acceptance report](../test-results/2026-07-26-network-root-adreno-smmu-v21-live-accepted.md)
records the exact bind, runtime suspend, zero-consumer boundary, fallback, and
cleanup.

The complete A660/GMU graph has now passed source audit, and the guarded
registration kernel is built. Linux `7.1.4-rog5-a660reg1` keeps DRM/MSM,
GPUCC, and MDT loading modular; disables MSM display KMS and all UFS paths;
and applies a fail-closed fix for the ignored GMU power-level result. Two
rootless, network-isolated builds produced byte-identical configs, Images,
module archives, symbol tables, critical modules, and metadata. No A660
firmware is embedded and no phone state changed. See the
[registration build report](../test-results/2026-07-26-a660-registration-build.md).
The exact four-node DT now also passes mutation tests and duplicate builds.
The read-only baseline and independent-watchdog registration probe pass
offline against the exact seven modules. The isolated seven-module export,
nested stage, two clean ASUS wrappers, two boot repacks, and exact
fourteen-file bundle reproduce and pass offline. Registration v2 now
mutation-tests and hash-pins the exact accepted v21 report/marker, reads it
only from the immutable NFS lower, removes `NOT_ACCEPTED`, builds a new
root-owned seven-module/zero-firmware export, rejects the old and consumed
roots, and re-passes the unchanged package's complete verifier. See the
[registration v2 report](../test-results/2026-07-26-a660-registration-v2-offline.md).
Registration v3 then fixes the remaining automatic-bind assumption by carrying
the accepted exact `3da0000.iommu` reprobe forward before DRM dependencies.
Its new export, A660 watchdog handoff, compound target gate, strict one-shot
host runner, and complete verifier all pass offline. See the
[registration v3 report](../test-results/2026-07-26-a660-registration-v3-offline.md).
The sole live cycle then passed one exact SMMU reprobe, seven-module GPU/GMU
registration, two IOMMU attachments, one unopened headless render node, a
zero-firmware 30-second settle, exact fallback, and complete host cleanup.
V3 is consumed. See the
[registration v3 live acceptance](../test-results/2026-07-26-a660-registration-v3-live-accepted.md).
The next audit proves that provisioning files without an open triggers
nothing. It accepts only a future diagnostic first-open branch that requests
SQE/GMU firmware and deliberately fails before ucode, runtime power, hardware
initialization, HFI, or ZAP/SCM. The default-off patch, six mutation
rejections, and two isolated clean builds now pass; the Image is unchanged
and only `msm.ko` differs. The exact SQE/GMU-only root, ZAP-absent policy,
static one-open helper, mutation-tested watchdog gate, strict host runner, and
unchanged package pass offline. The sole live cycle then requested SQE and GMU
exactly once, returned `EUCLEAN`, crossed no ucode/power/HFI/ZAP boundary,
retained zero DRM descriptors/storage/faults, and returned through exact
fallback plus complete cleanup. V4 is consumed. A mutation-tested nonsecret
marker pins the exact report and evidence checkpoint. See the
[firmware-only boundary report](../test-results/2026-07-26-a660-firmware-only-boundary.md)
and
[request-only build report](../test-results/2026-07-26-a660-firmware-request-only-build.md),
then the
[request-only v4 offline report](../test-results/2026-07-26-a660-firmware-request-only-v4-offline.md)
and
[request-only v4 live acceptance](../test-results/2026-07-26-a660-firmware-request-only-v4-live-accepted.md).

The ucode-allocation source boundary is now accepted offline. On exact
A660.1 it creates one SQE object, one privileged shadow object, and one
privileged power-up reglist object through three GPU-VM/SMMU mappings before
GPU/GMU runtime power or register access. The normal A6xx destroy path does
not fully release this state, so a future diagnostic must provide explicit
all-path rollback and an atomic one-shot gate. See the
[ucode-allocation boundary report](../test-results/2026-07-26-a660-ucode-allocation-boundary.md).

The default-off rollback-safe diagnostic now passes its exact patch verifier,
strict checkpatch, and eight source mutations; see the
[ucode-allocation patch report](../test-results/2026-07-26-a660-ucode-allocation-patch.md).
Two isolated builds now pass with byte-identical outputs, an unchanged
Image/config/ABI, an exact MSM-only delta, BTF, and zero embedded firmware;
see the
[ucode-allocation build report](../test-results/2026-07-26-a660-ucode-allocation-build.md).
The fresh root/gate now passes offline with exact PID-filtered balanced
mapping/GEM/firmware trace requirements, equal pre/post GEM snapshots, nine
forbidden power/HFI/ZAP/SCM probes, nested watchdogs, and a fully reverified
unchanged boot package; see the
[ucode-allocation v5 offline report](../test-results/2026-07-26-a660-ucode-allocation-v5-offline.md).
The exact one-invocation host runner now passes its fail-first and mock
transport suite with strict SSH identity and private evidence handling. The
[pre-live control acceptance](../test-results/2026-07-26-a660-ucode-allocation-v5-prelive-hold.md)
keeps the decision at **HOLD**: the root remains non-runnable through the NFS
launcher, the phone was not contacted, and any live cycle is still
unauthorized at that checkpoint. The subsequent
[pre-live GO review](../test-results/2026-07-26-a660-ucode-allocation-v5-prelive-go.md)
added one fail-first-tested, explicit-opt-in, verifier-before-state NFS case
for exact v5 and passed the fallback/host preflight. This authorized at most
one attended RAM-only ucode-allocation cycle, not any later GPU tier.
The [sole v5 cycle](../test-results/2026-07-26-a660-ucode-allocation-v5-live-rejected.md)
then completed the kernel rollback but was rejected at the userspace
public-wrapper count (`get=1`, expected `4`) before snapshot comparison.
Exact `.rela.text` analysis shows that Clang inlined three logical
acquisitions into `msm_gem_kernel_new()` and two releases into
`msm_gem_kernel_put()`; wrapper counts `get=1, put=2` therefore match the
compiled path and logical balance remains `4/4`. This diagnosis does not turn
v5 into a PASS because the equal post-settle GEM snapshot was never reached.
V5 is consumed and non-runnable. A versioned v6 must trace the convenience
helpers directly, preserve every storage/watchdog/forbidden-event guard, and
pass a new offline HOLD/GO process before hardware use.

The
[v6 offline package](../test-results/2026-07-26-a660-ucode-allocation-v6-offline.md)
now passes that offline half. It deliberately reuses the exact accepted
kernel module because the defect was in the userspace oracle, then
hash-pins the module and its `.rela.text` layout. Generated v6 controls trace
three successful `msm_gem_kernel_new()` returns and two
`msm_gem_kernel_put()` calls, combine them with the remaining public wrapper
events into logical `4/4` balance, verify exact rollback object sets, and
retain equal post-settle GEM snapshots. Runtime, root, gate, and changed-seal
mutation suites pass. The subsequent
[pre-live control acceptance](../test-results/2026-07-26-a660-ucode-allocation-v6-prelive-hold.md)
adds a fail-first-tested exact one-invocation runner, but it cannot start NFS
or boot the phone. V6 is still non-runnable and **HOLD**; no phone cycle is
authorized.

The
[v6 pre-live GO review](../test-results/2026-07-26-a660-ucode-allocation-v6-prelive-go.md)
then adds one verifier-first, explicit-opt-in NFS case and passes exact
fallback, SSH identity, credential, root, package, runner, and inactive-host
checks. It authorizes at most one RAM-only v6 cycle under nested watchdogs and
immediate fallback. It does not accept the hardware path or permit a retry.

The [sole v6 cycle](../test-results/2026-07-26-a660-ucode-allocation-v6-live-rejected.md)
then reached the successful kernel allocation-and-rollback marker but was
rejected by a second userspace-oracle error. A function-entry kprobe sees raw
sizes: SQE `fw->size - 4 = 43288`, one-ring shadow `sizeof(u32) = 4`, and
reglist `PAGE_SIZE = 4096`. `msm_gem_new()` page-aligns those only after
entry, yielding the v6 expected set `45056/4096/4096`. The gate failed closed
before its settled snapshot comparison. Watchdog fallback and full cleanup
passed; v6 is consumed and non-runnable. A new v7 must source-pin the raw
entry-size set and still pass the unchanged equal-snapshot gate before the
port advances to GMU resume or successful open.

The
[v7 offline package](../test-results/2026-07-26-a660-ucode-allocation-v7-offline.md)
now satisfies that source boundary while reusing the unchanged accepted
module. Zero-fuzz generation and semantic mutations pin raw entry sizes
`4/4096/43288`, page-rounded objects `4096/4096/45056`, three kernel-new
returns, two kernel puts, wrapper `1/2`, logical `4/4`, complete object-set
rollback, and equal settled GEM snapshots. Its root-owned protected export is
an exact COW delta from consumed v6 and rejects predecessor and size-layer
seal mutations. It is absent from the NFS allowlist and has no live runner.
No phone contact occurred at that checkpoint. The
[v7 pre-live HOLD review](../test-results/2026-07-26-a660-ucode-allocation-v7-prelive-hold.md)
now adds an exact one-shot host runner with strict SSH identity, immutable
inputs, private logging, expected reboot disconnect, and no retry. Its mock,
credential/root, and actual unarmed-refusal checks pass. It has no
NFS/server/boot authority at that checkpoint. The separate
[v7 pre-live GO review](../test-results/2026-07-26-a660-ucode-allocation-v7-prelive-go.md)
adds one exact-root, verifier-before-state, explicit-opt-in NFS window.
Clean synchronized Git, immutable inputs, distinct SSH identities, strict
fallback health, inactive services, and actual unarmed refusals pass with
zero residue. This authorizes at most one attended RAM-only v7 cycle with no
retry and no flash.

The first PMIC input tier was then narrowed in two steps. V4 proved that the
PMK8350 RTC read path ticks but contains an unusable near-epoch value, so RTC
remains disabled and trusted time must come from the host or network. V5
enables only the PMK8350 power-key node. In a storage-isolated diagnostic boot,
the guarded `qcom_pon` parent-module probe registered the built-in
`pm8941-pwrkey` input with `KEY_POWER` and wakeup enabled, then survived normal
systemd reboot and cleanup. A physical press/IRQ observation remains required
before input is accepted. A later normal, unmasked v5 repeat passed ordinary
coldplug, full module-tree I/O, the live watchdog-disarm helper, 37 C maximum
temperature, normal reboot, and complete host cleanup. The protected
120-second event monitor received no confirmed press/release.

The historical v2 image produced staging and Linux 7.1.4 logs, including
target `/init`, NCM/ACM configuration, the `a600000` UDC, and `usb0`. It did
not, however, satisfy the claimed recovery boundary: its staging `/` was
writable physical UFS, and its target DTB enabled UFS and QMP/SuperSpeed.
Nothing was flashed, but v2 is superseded and must not be booted. Its logs
remain diagnostic evidence for the TLMM GPIO 52 reservation and built-in FEMTO
PHY work, not proof that the corrected RAM-only path passes. The raw ramoops
and bootloader restart-reason module sources are under `tools/diagnostics/`.

## Non-goals

- No blind use of a generic SM8350 MTP DTB.
- No port of proprietary Android userspace GPU libraries into the final system.
- No persistent slot change until the full release gate passes.
- No attempt to enable every peripheral simultaneously; each subsystem must have a measurable pass/fail boundary.
- No bulk conversion of the 32k-line vendor DTS into mainline syntax; only reviewed board facts and nodes are carried forward.
