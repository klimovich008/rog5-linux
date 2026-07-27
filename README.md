# ROG Phone 5 native Linux

Reproducible bring-up work for native Arch Linux ARM on the ASUS ROG Phone 5 (`anakin`, Snapdragon 888 / SM8350). The target is a dependable phone-server with a minimal Plasma Desktop Wayland session, remote administration, screen-off operation, charging, Wi-Fi/VPN hotspot support, and upstream-style GPU acceleration. Alpine remains only in the proven vendor-kernel baseline and the small recovery environment. The long-term goal is a maintainable Linux 7.x board port.

This repository contains documentation, test tooling, configuration fragments, and artifact hashes. It intentionally does **not** contain proprietary firmware, credentials, personal data, Android partition dumps, or large boot images.

## Current result

The known-good temporary boot image runs vendor-derived kernel `5.4.210-qgki-perf #20`. Its smoke suite passes DRM/panel, touch, charging, USB networking, Plasma Mobile, power-button screen control, UPower, Wi-Fi client, and hotspot. The display defaults off while the server remains active.

For the mainline userspace path, the fail-closed hotspot policy now passes a
real packet regression in isolated, network-disabled namespaces: only the
simulated VPN path works; IPv4/IPv6 ordinary-uplink leakage, unsolicited
client ingress, and VPN-loss fallback are blocked; cleanup is exact. Radio,
real WireGuard, DHCP/DNS, throughput, thermal, and battery acceptance remain
hardware gates.

The newer Arch development root now also passes its full stage and clean
archive round trip with a locked `rog5-agent` account. Its on-demand Chromium
service is loopback-only, cannot reuse the Plasma user's home or credentials,
has no device access or capabilities, and can write only its private
`/var/lib/rog5-agent` state. Native systemd controls cap it at two CPUs, 2 GiB
RAM, 512 MiB swap, and 256 tasks, lower its CPU/I/O scheduling weight, and
stop rapid restart loops. No email, CV, browser session, API token, or
provider account is present. This artifact is verified offline but has not
replaced the live-tested network root or run on the phone.

The same image stages a one-shot redacted runtime collector for later
headless, Plasma, KRDP, browser, and screen-off comparisons. It records
aggregate memory/PSS, CPU ticks, thermals, battery telemetry, display state,
cgroup usage, and interface byte counters while omitting command-line,
address, MAC, SSID, serial, and credential data.

One hard blocker remains: the vendor KGSL driver initializes Adreno 660 on the first `/dev/kgsl-3d0` open, but the second open fails while the GMU handles `PwrLimitsExitIdl`, followed by a CP page fault. This reproduces without Mesa and remains after disabling optional power features and forcing rails/clocks on. GPU acceleration is therefore not an accepted feature yet.

The historical v2 recovery image temporarily booted and produced logs showing
Linux 7.1 reaching `/init`, configfs, and an internally configured USB gadget.
A later audit invalidated its safety classification: the v2 staging `/` was a
writable physical UFS filesystem, and its target DTB enabled UFS and the
QMP/SuperSpeed PHY. Nothing was flashed, but v2 is superseded and must not be
booted again.

The later v6 candidate embedded the staging initramfs in the 5.4 kernel and
used a USB2-only target DTB with UFS and QMP disabled. It passed its then-current
offline suite, but live ACM data and automatic rollback failed, so v6 is also
rejected. Source fixes for both failures and a fresh Linux 7.1 build exist;
two clean Linux 7.1 kernel/module/DTB builds are now byte-identical. The
credential-free v12 target/staging initramfs, ASUS wrapper, and temporary boot
image were each rebuilt twice and are byte-identical. The complete offline
verifier passes in explicit `acm-only` mode, including the PM wake-lock,
USB2-only DTB, nested hashes, boot-header, AVB, and no-authorized-key checks.
V12 was not booted: a final audit found that it did not force block devices
read-only before exposing USB, so it is superseded. Recovery v13 adds a
fail-closed pre-USB storage gate to both initramfs layers: it rejects any
block-backed mount, applies and verifies `BLKROSET` on every enumerated block
device, and forces rollback on any failure. Its complete credential-free
dependency chain and temporary boot image were independently reproduced and
pass the expanded offline verifier. Its first temporary boot returned to the
fallback system before the exact recovery USB identity appeared, so v13 is
rejected. The host workflow also exposed and fixed an identity bug: recovery
and fallback share `1d6b:0104`, so the exact product string is now mandatory.

Recovery v14 keeps the block-backed-mount rejection but applies `BLKROSET`
only to physical disks and their partitions, excluding volatile loop, RAM,
and zram objects. Two complete clean builds and two repacks are byte-identical,
and the expanded offline verifier passes. Its live attempt nevertheless
returned to fallback in the same 21-second interval without recovery USB, so
v14 is also rejected.

Recovery v15 was a diagnostic-only timing image. Its temporary boot returned
to fallback in exactly 31 seconds, selecting the 10-second wake-lock failure
branch and proving `/init` ran before storage isolation. The wrapper has
`CONFIG_PM_AUTOSLEEP` disabled and recovery has no userspace power manager, so
that wake-lock gate was unnecessary. Recovery v16 removed it and reached exact
recovery USB, working NCM, and automatic rollback, but ACM returned no shell
data. An authorized local v17 SSH diagnostic proved the root was RAM-backed,
there were zero block-backed mounts, all 116 physical devices were read-only,
and the watchdog worked. It isolated ACM to a missing `/dev/ttyGS0` node; a
live `mdev -s` rescan immediately restored the shell. Recovery v18 makes that
rescan fail-closed, requires the node, and repeats storage isolation before
binding USB. Two complete v18 builds and repacks are byte-identical, and the
network-isolated verifier passes. Two credential-free live staging/rollback
cycles now pass with RAM root, zero block mounts, all 116 physical devices
read-only, ACM/NCM, no SSH, and changed fallback boot identities. The separate
attended kexec gate now also passes: Linux `7.1.4-g7a5cef0db479` reached its
RAM-only recovery with zero physical block devices, working ACM/NCM and
watchdog, no fatal log signatures, and automatic return to a changed fallback
boot identity. The corrected read-only UFS discovery v2 gate also passes:
Linux `7.1.4-gcfd385a1c754` enumerated all 116 UFS disks and partitions
read-only with zero blocked commands, disabled auto-hibern8, pinned-active
runtime PM, no UFS error handler, and automatic fallback recovery. Arch/Debian
network root now also passes its complete offline reproducibility gate: two
Linux 7.1.4 builds, two target/staging initramfs builds, two ASUS wrappers, and
two header-v3/AVB repacks are byte-identical. The dedicated kernel has
NFSv4.2/OverlayFS built in and compiles SCSI/UFS/QMP storage paths out. The
signed Arch input and the final 2,007,186,653-byte headless-first Plasma
rootfs pass Linux-native staging and archive round-trip verification with the
exact network-root modules and pinned A660 firmware. The restricted host
NFS harness now also passes its privileged runtime gate on Nobara: one
NFSv4.2/TCP listener on the USB address, one exact-peer read-only export, a
successful isolated client mount, no persistent firewall state, and complete
cleanup. Four early normal boots localized a deterministic reset to hardware
coldplug. Attended, rollback-guarded module isolation then proved
`gpucc_sm8350` stalls and showed that `rmtfs_mem` overlaps the recovery
ramoops reservation. Network-root v2 disables RMTFS, GPUCC, GPU, GMU, and the
Adreno SMMU in the recovery DTB. Two normal, unmasked boots now pass exact
Linux 7.1.4, running systemd, successful udev coldplug, `multi-user.target`,
key-only SSH, OverlayFS with read-only NFS lower, zero physical storage,
stable USB/NFS, zero failed units, sane thermals, and safe watchdog disarm.
Client authorization and a single pinned server host identity also persist
across boots. Network-root v3 now retains a minimal shutdown initramfs that
unmounts OverlayFS before its tmpfs and NFS backing filesystems. Its attended
normal `systemctl reboot` test returned to the persistent fallback in about
25 seconds, with strict fallback SSH and complete NFS/firewall cleanup.
Network-root v7 also passes the isolated ADSP prerequisite after adding the
exact stock-owned ASUS RAM spans. Network-root v8 then passes one guarded
read-only SM8350 battery snapshot through the audited QRTR/PDR and
battery-only PMIC GLINK path. Charging, Type-C control, sustained
current-direction validation, display, and GPU remain isolated.
Network-root v9 independently reproduced a GPUCC-only diagnostic with every
GPU consumer disabled. V10 then added a default-off, exact-compatible trace to
the built-in Qualcomm common-clock path. Duplicate clean kernels, matching
module archives, wrappers, and packages were byte-identical. The guarded live
trace completed mapping, both PLL configurations, reset registration, and both
GDSC steps, then stopped while registering clock index 0
(`gpu_cc_ahb_clk`). Its independent watchdog restored the exact fallback and
complete host cleanup passed. Source analysis does not prove an access to the
branch register: this clock is non-critical and should enter CCF as an orphan.
Network-root v11 passed its offline gate and the attended RAM-only probe. The
trace completed allocation, prepare-lock/runtime-PM, parent lookup, orphan
insertion, phase/duty/rate, and the non-critical branch for
`gpu_cc_ahb_clk`, then stopped inside
`clk_core_reparent_orphans_nolock()`. Its independent watchdog restored the
exact fallback and complete cleanup passed. The result does not prove GPUCC
MMIO: the generic scan can inspect or reparent any existing orphan clock.
Network-root v12 passed its complete offline gate and one attended RAM-only
probe. The global scan completed the no-parent entry for newly registered
`gpu_cc_ahb_clk`, advanced to the existing
`disp_cc_mdss_pclk0_clk_src` orphan, and stopped inside that clock's
`__clk_init_parent()` call. Source order places its display RCG
`get_parent()` callback before CCF's cached-parent lookup, but v12 does not yet
distinguish those operations or prove a register access. The independent
watchdog restored the exact fallback and complete host cleanup passed. GPUCC
remains rejected. Network-root v13 passed its complete offline gate and one
attended RAM-only probe. It recorded the display orphan as a three-parent
clock whose runtime-PM-enabled provider was suspended, then entered
`disp_cc_mdss_pclk0_clk_src`'s `get_parent()` callback without reaching the
callback-complete or later parent-cache markers. Source maps that callback to
`clk_rcg2_get_parent()`, whose first substantive operation is a regmap read,
but v13 does not instrument inside the callback and therefore does not prove
that read began or identify a register access as the cause. The independent
watchdog restored the exact fallback and complete host cleanup passed. A
runtime resume must not simply be added while CCF's global `prepare_lock` is
held because provider callbacks may need the same lock. Network-root v14
passed the complete offline successor gate and one attended RAM-only
diagnostic. Its exact-clock markers reached `parent-read-begin` immediately
before the display RCG's existing `regmap_read()` but never reached
`parent-read-complete`. This localizes the non-returning boundary to that
existing call without proving whether MMIO, interconnect, regmap locking, or
runtime-suspended provider state is responsible. The independent watchdog
restored the exact fallback; zero retained pstore/fatal records and complete
host cleanup passed. V14 must not be rerun and is not a GPU fix. Network-root
v15 now passes the complete offline gate for an experimental partial backport
of the March 2025 CCF runtime-PM RFC. Its exhaustive lock model, red/green
source and mutation tests, clock KUnit suite, two mainline builds, and two
nested wrapper/package paths pass; exported symbols, modules, and the RCG2
object remain byte-identical to v14. It acquires generic all-provider
runtime-PM references before `prepare_lock`, preserves the orphan scan, and
releases them after unlocking. Its one attended RAM-only probe made DISPCC
active, completed all seven observed parent reads, and advanced GPUCC clock
registration through completed index 6 and into index 7. The 75-second
watchdog reset while 100 ms markers were still arriving continuously: a
73.901-second trace span with no gap over 0.116 seconds. This supports the
ordering hypothesis but does not prove complete GPUCC registration. V15 must
not be rerun; the next gate is an offline-verified trace-free confirmation.
See the
[v14 offline report](test-results/2026-07-25-network-root-gpucc-rcg2-diagnostic-offline.md)
and
[v14 live report](test-results/2026-07-25-network-root-gpucc-rcg2-diagnostic-live.md),
then the
[v15 offline report](test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-offline.md)
and
[v15 live report](test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-live.md).
Network-root v16 now passes its complete offline gate without changing any
kernel/package bit: its explicit confirmation transport omits all three core
trace flags, its fail-closed probe requires each parameter at count zero and
mode-`0400` state `N`, and only the delay-free outer GPUCC trace remains. A
hash-pinned read-only target baseline proves those conditions, zero storage,
consumer isolation, and the still-armed initial watchdog before any disarm.
See the
[v16 offline report](test-results/2026-07-25-network-root-gpucc-confirmation-offline.md).
The attended v16 cycle never entered the Linux 7.1 target: a 284-second
operator gap after load exceeded the staging watchdog, both later execute
invocations failed before serial transmission, and exact fallback/cleanup
passed. V16 is consumed. V17 now passes an offline gate that runs the same
trace-free load and execute actions in one guarded process, while preserving
bounded identical-load replay and non-retryable execute. See the
[v16 staging-only report](test-results/2026-07-26-network-root-gpucc-confirmation-live.md)
and
[v17 offline report](test-results/2026-07-26-network-root-gpucc-atomic-confirmation-offline.md).
The one permitted live v17 cycle now passes. The atomic transport transmitted
one execute, the trace-free GPUCC driver reached
`registration-complete ret=0`, bound exactly one device, and stayed stable for
30 seconds with every GPU/GMU/SMMU consumer, render node, and storage path
absent. Normal systemd reboot restored the exact fallback with zero retained
pstore/fatal evidence and complete host cleanup. This accepts only the
GPUCC/CCF foundation, not acceleration; the next gate is an offline-tested,
reproducible Adreno power/SMMU/GMU/firmware dependency tier. See the
[v17 live report](test-results/2026-07-26-network-root-gpucc-atomic-confirmation-live.md).
V18 passed the first, deliberately smaller offline slice: the exact v17 GPUCC
bits plus the built-in Adreno SMMU, with GPU, GMU, A660 firmware, DRM/render
nodes, and storage still disabled. Its one attended cycle then stopped safely
at the read-only baseline. A case-insensitive detector matched `fault` inside
the normal word `Default`; no watchdog was disarmed, GPUCC was not loaded, the
SMMU remained unbound, and normal reboot restored exact fallback with complete
host cleanup. V18 is consumed and must not be retried. V19 retains the exact
reproduced RAM-only binary but corrects and regression-tests the external
fault detectors, source locks, export seal, and exact NFS allowlist. Its new
independently verified copy-on-write root has all 1,008 module files, zero A660
firmware, preserved credentials, and an unchanged accepted base; NFS remains
inactive. Its one attended gate passed the corrected baseline and again
completed GPUCC registration, but the SMMU remained unbound after the full
30-second settle. No warning, fault, firmware/render/storage log, failed unit,
or unsafe temperature appeared; the armed watchdogs restored
exact fallback and complete host cleanup. V19 is consumed and must not be
retried. Source review points to a late-provider/deferred-probe boundary. V20
passed offline with the unchanged v18 binary: a new source lock proved
that platform `drivers_probe` resolves one exact unbound device and calls only
`device_attach()`, while ARM SMMU force-bind controls remain suppressed. The
baseline and probe capture `waiting_for_supplier`, `devices_deferred`,
supplier links, and direct safety counters. After five seconds of normal
autoprobe, the guarded probe may write only `3da0000.iommu` once; global
timeout extension, broad rescan, force-bind, unload, retry, firmware, render,
and storage paths are rejected. Its one live cycle then stopped at the
read-only baseline: Linux exposes a fresh unset platform `driver_override` as
`(null)`, while v20 incorrectly required an empty line. The original watchdog
remained armed; GPUCC was not loaded, `drivers_probe` was not written, the SMMU
remained unbound, and no firmware, render, or storage path appeared. Normal
fallback and complete host cleanup passed. V20 is consumed and must not be
retried. V21 passed that correction offline. Its pinned source contract
proves OF allocation starts with a NULL override, `%s` emits exact `(null)`,
and matching falls through to OF. A new read-only checker accepts only the
seven-byte `(null)\n` representation; mutation tests reject empty, malformed,
nonempty, and linked inputs, and no path writes `driver_override`. The
unchanged binary verifier passes, and the independently verified v21 root
preserves all 1,008 modules and credentials with zero A660 firmware. Its one
permitted live cycle then passed: after accepted GPUCC registration, exactly
one `3da0000.iommu` reprobe bound `arm-smmu`, stayed bound through the
30-second settle, and reached runtime suspend. Firmware requests, render
nodes, physical storage, block-backed mounts, and failed units remained zero;
normal reboot restored exact Alpine fallback and complete host cleanup. This
accepts only the idle GPUCC/SMMU foundation, not acceleration. V21 is consumed,
must never be rerun, and has been removed from the runnable NFS allowlist. See
the
[v18 offline report](test-results/2026-07-26-network-root-adreno-smmu-offline.md)
and
[v18 safe-rejection/v19 correction report](test-results/2026-07-26-network-root-adreno-smmu-v18-live-rejected.md),
then the
[v19 no-bind report](test-results/2026-07-26-network-root-adreno-smmu-v19-live-rejected.md)
and
[v20 offline report](test-results/2026-07-26-network-root-adreno-smmu-v20-offline.md),
followed by the
[v20 safe baseline-rejection report](test-results/2026-07-26-network-root-adreno-smmu-v20-live-rejected.md)
and
[v21 offline report](test-results/2026-07-26-network-root-adreno-smmu-v21-offline.md),
then the
[v21 live acceptance report](test-results/2026-07-26-network-root-adreno-smmu-v21-live-accepted.md).
The complete pinned A660/GMU source graph and its first guarded kernel build
now pass offline. Registration is a real hardware boundary: it attaches three
IOMMU contexts and programs GMU RSCC/PDC registers, while firmware, GPU
power-up, ZAP/SCM authentication, and hardware initialization wait for the
first DRM open. The new Linux `7.1.4-rog5-a660reg1` candidate makes DRM/MSM and
GPUCC manually loaded modules, disables display KMS and UFS, exports
`separate_gpu_kms`, and propagates the previously unchecked GMU power-level
error. Two isolated rootless builds and all nine acceptance outputs are
byte-identical; no firmware is embedded and the phone was not contacted. The
exact four-node DT also passes mutation tests and duplicate byte-identical
builds. Its read-only baseline and no-open registration probe pass offline. The
isolated seven-module NFS export, nested stage, two clean ASUS wrappers, two
header-v3/AVB repacks, and exact fourteen-file bundle now also reproduce and
pass their complete offline verifier. V2 now hash-pins the exact v21 live
report and acceptance marker into the probe's immutable NFS lower, removes
`NOT_ACCEPTED`, creates a new independently verified root-owned export with
seven modules and zero firmware, rejects the old export and all consumed
SMMU roots, and re-passes the unchanged binary package's complete verifier.
The next offline review caught v2's assumption that SMMU would bind
automatically after GPUCC. Registration v3 now validates the exact unset
override and performs at most one `3da0000.iommu` reprobe before any DRM
dependency load. Its new root-owned export, A660-release watchdog handoff,
180-second transition rollback, one-invocation target gate, strict host runner,
private evidence contract, and complete unchanged-binary verifier all pass.
V2 is no longer runnable. The sole v3 RAM-only cycle then passed: GPUCC and
the exact SMMU reprobe completed, seven modules registered the GPU/GMU with
two IOMMU attachments and one unopened render node, and firmware, DRM
descriptors, display connectors, storage, mounts, faults, and failed units
stayed zero. Normal reboot restored exact fallback with complete host cleanup.
V3 is consumed and no longer server-allowlisted. A mutation-tested nonsecret
marker pins the exact live report and evidence checkpoint for later tiers.
The next source audit corrected the earlier “provision without open”
shorthand: firmware files alone trigger no request, while normal `msm_open()`
immediately couples requests to ucode, runtime power, HFI, and ZAP/SCM. The
accepted next design is therefore a one-shot diagnostic open that requests
only exact SQE/GMU firmware and deliberately fails before every later step;
the default-off patch and two isolated clean builds now pass byte-for-byte,
with an unchanged Image and only `msm.ko` changed. The root-owned v4 export,
two exact firmware files, static one-open helper, mutation-tested runtime
gate, strict host runner, and unchanged AVB package now also pass their full
offline contracts. The sole v4 RAM-only cycle then requested SQE and GMU
exactly once, returned `EUCLEAN`, and retained zero ucode, power, HFI,
ZAP/SCM, DRM descriptors, storage, display, warning, or fault evidence.
Normal reboot restored exact fallback and complete host cleanup. V4 is
consumed and no longer server-allowlisted. A mutation-tested nonsecret marker
pins the exact live report and evidence checkpoint for the next GPU tier. See
the
[A660 full dependency audit](test-results/2026-07-26-a660-full-dependency-audit.md)
and
[A660 registration build report](test-results/2026-07-26-a660-registration-build.md),
then the
[A660 registration v2 report](test-results/2026-07-26-a660-registration-v2-offline.md)
and
[A660 registration v3 offline report](test-results/2026-07-26-a660-registration-v3-offline.md),
then the
[A660 registration v3 live acceptance](test-results/2026-07-26-a660-registration-v3-live-accepted.md).
The next-tier source boundary is recorded in the
[A660 firmware-only boundary report](test-results/2026-07-26-a660-firmware-only-boundary.md),
and the duplicate build acceptance is in the
[A660 request-only build report](test-results/2026-07-26-a660-firmware-request-only-build.md).
The complete pre-live root and gate are recorded in the
[A660 request-only v4 offline report](test-results/2026-07-26-a660-firmware-request-only-v4-offline.md).
The one permitted hardware cycle is recorded in the
[A660 request-only v4 live acceptance](test-results/2026-07-26-a660-firmware-request-only-v4-live-accepted.md).
The following offline
[A660 ucode-allocation boundary audit](test-results/2026-07-26-a660-ucode-allocation-boundary.md)
proves that the next seam adds exactly three SMMU mappings before GPU/GMU
runtime power or register access and must explicitly roll back SQE, shadow,
and power-up reglist state. It does not authorize another live cycle.
The corresponding
[rollback-safe patch report](test-results/2026-07-26-a660-ucode-allocation-patch.md)
passes exact stacked-source verification and eight mutations. The subsequent
[duplicate-build report](test-results/2026-07-26-a660-ucode-allocation-build.md)
accepts two byte-identical isolated builds with an unchanged
Image/config/ABI and exact MSM-only delta. The fresh
[ucode-allocation v5 offline report](test-results/2026-07-26-a660-ucode-allocation-v5-offline.md)
accepts the root-owned SQE/GMU-only export, PID-filtered balanced-trace
contract, equal pre/post GEM snapshot requirement, nested watchdog gate, and
unchanged complete boot package. The subsequent
[pre-live control acceptance](test-results/2026-07-26-a660-ucode-allocation-v5-prelive-hold.md)
accepts a fail-first-tested, exact one-invocation host runner, but records a
deliberate **HOLD**: the root is not served, NFS remains inactive, and no
phone cycle is authorized. The subsequent
[pre-live GO review](test-results/2026-07-26-a660-ucode-allocation-v5-prelive-go.md)
lifted that HOLD for exactly one attended RAM-only cycle: an explicit opt-in
permitted only the exact v5 root after its full verifier ran, while NFS
remained inactive until the bounded transition began.
The [sole v5 live cycle](test-results/2026-07-26-a660-ucode-allocation-v5-live-rejected.md)
completed the kernel's three-object rollback but was safely rejected because
the userspace oracle expected four public `msm_gem_get_vaddr()` calls and
observed one. Offline relocation analysis proves Clang inlined the other
three logical gets inside `msm_gem_kernel_new()`: the live wrapper counts
`get=1, put=2` are correct for this exact module. V5 still cannot pass because
the gate stopped before the post-settle GEM snapshot comparison. It is
consumed, absent from the NFS allowlist, and must not be retried. A fresh v6
must trace `kernel_new`/`kernel_put` directly and pass the equal-snapshot gate
before any new attended decision.

That [fresh v6 offline package](test-results/2026-07-26-a660-ucode-allocation-v6-offline.md)
now passes. It reuses the exact accepted kernel bits, pins their compiler
relocations, traces three successful `kernel_new` and two `kernel_put`
operations directly, requires wrapper `get=1, put=2`, logical vmap balance
`4/4`, matching rollback object sets, and the original equal post-settle GEM
snapshot. The root-owned export and generated runtime are reproducible and
mutation-tested, while NFS remains inactive and v6 has no server case or live
runner at that root-acceptance checkpoint. The subsequent
[v6 pre-live control acceptance](test-results/2026-07-26-a660-ucode-allocation-v6-prelive-hold.md)
now adds a fail-first-tested one-invocation host runner with strict SSH
identity, exact root/package/gate inputs, and private evidence. It has no NFS
or boot control, the root still has no server case, and the decision remains
**HOLD** until a separate attended fallback and live-window review.

That [v6 pre-live GO review](test-results/2026-07-26-a660-ucode-allocation-v6-prelive-go.md)
now passes. One explicit opt-in server case runs the full protected verifier
before any host-state mutation; an actual unarmed invocation refused cleanly.
Exact fallback, distinct SSH identities, credentials, root, package, runner,
and inactive host services pass. This authorizes at most one attended
RAM-only v6 cycle under the recorded sequence, never flash and never retry.
The [sole v6 live cycle](test-results/2026-07-26-a660-ucode-allocation-v6-live-rejected.md)
is now safely rejected and consumed. The kernel emitted its successful
allocation-and-rollback marker, but the entry probe observed raw GEM request
sizes `43288`, `4`, and `4096` while the gate expected their page-rounded
forms `45056`, `4096`, and `4096`. The gate therefore stopped before the
settle and equal-snapshot check. Watchdog fallback and complete host cleanup
passed, v6 is absent from the server allowlist, and it must not be retried.
A fresh v7 must correct only this userspace oracle and still prove an equal
post-settle GEM snapshot before any GMU or rendering tier.

That
[v7 offline package](test-results/2026-07-26-a660-ucode-allocation-v7-offline.md)
now passes and remains **HOLD**. It derives only from the immutable consumed
v6 root and accepted module, separately pins raw entry sizes
`4/4096/43288` and page-rounded object sizes `4096/4096/45056`, retains the
compiler-specific logical `4/4` vmap and equal settled-snapshot contracts,
and rejects changed-predecessor and rounded-as-raw seal mutations. Its
root-owned mode-`0555` Btrfs export had no NFS server case or live runner at
that checkpoint. The phone was not contacted. The subsequent
[v7 pre-live control acceptance](test-results/2026-07-26-a660-ucode-allocation-v7-prelive-hold.md)
adds a fail-first-tested exact one-invocation runner with strict SSH identity,
immutable inputs, private logging, expected reboot disconnect, and no retry.
It has no NFS/server/boot authority, the actual unarmed invocation refused,
and NFS/RPC stayed inactive. The separate
[v7 pre-live GO review](test-results/2026-07-26-a660-ucode-allocation-v7-prelive-go.md)
adds only an exact-root, verifier-before-state, explicit-opt-in NFS case.
Clean synchronized Git, protected root/package/runner hashes, distinct SSH
identities, strict read-only fallback health, inactive host services, and an
actual unarmed privileged refusal all pass with zero residue. This authorizes
at most one attended RAM-only v7 cycle with no retry and never any flash.
The
[sole v7 live cycle](test-results/2026-07-26-a660-ucode-allocation-v7-live-accepted.md)
now passes the corrected raw-size oracle, three successful distinct
allocations, exact rollback pointer sets, compiler-aware logical `4/4`,
and an equal GEM snapshot after the mandatory settle. Power/HFI/ZAP/SCM,
hardware initialization, submission, and rendering stayed zero. Normal
fallback and complete host cleanup passed; v7 is consumed and non-runnable.
The next isolated tier starts at runtime power and GMU resume, not rendering.
Its
[GMU resume-entry source audit](test-results/2026-07-26-a660-gmu-resume-entry-boundary.md)
and
[v8 offline build acceptance](test-results/2026-07-26-a660-gmu-resume-entry-v8-offline.md)
and
[v8 runtime acceptance](test-results/2026-07-26-a660-gmu-resume-entry-v8-runtime-offline.md)
now pass. Two clean Linux 7.1.4 builds are byte-identical; the Image, config,
ABI, GPUCC, MDT loader, and every installed module except `msm.ko` remain
exactly v7. The default-off, read-only, exact-A660.1 one-shot rejects
`a6xx_gmu_resume()` before GMU software mutation, inner runtime power, clocks,
MMIO, IRQ, firmware start, HFI, hardware initialization, ZAP/SCM, submit, or
rendering, then reuses the accepted v7 rollback. The zero-fuzz runtime is
reproducible, pins the compiled call/relocation layout, and rejects mode,
resume, rollback, inner-PM, clock, IRQ, HFI, snapshot, errno, predecessor,
and writable-parameter mutations. The
[v8 protected-root acceptance](test-results/2026-07-26-a660-gmu-resume-entry-v8-root-offline.md)
now also passes. PolicyKit created a consumed-v7-derived, root-owned
mode-`0555` copy-on-write root, replaced only its four versioned controls and
exact MSM module, and preserved every other file, metadata item, credential,
host identity, module, and firmware input. The verifier passed during
construction and twice afterward; five predecessor, mode, evidence, trace,
and MSM mutations were rejected. Its compound target gate also passes
offline with overlapping watchdogs and mandatory reboot. The separate
[v8 pre-live control acceptance](test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-hold.md)
adds a fail-first-tested one-invocation host runner with strict SSH identity,
immutable root/package/gate inputs, private evidence, expected reboot
disconnect, and no retry or NFS/boot/flash authority. Its mock transport,
local credential agreement, complete root re-verification, and actual
unarmed refusal pass while NFS/RPC remains inactive. The subsequent
[v8 pre-live GO review](test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-go.md)
adds only one verifier-before-state exact-root NFS case and revalidates the
complete fourteen-file transport package, protected root and all five
mutations, clean synchronized Git, separate client/server SSH identities,
strict read-only fallback health, and residue-free host state. Both real
unarmed controls refuse before action. The
[sole v8 live cycle](test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md)
then reached the exact GMU entry and rollback with deliberate `EUCLEAN`.
It failed closed because the arm64 `int` returns appeared as zero-extended
`4294967179` in an `s64` trace oracle; complete trace review also disproved
the global one-call `__pm_runtime_resume()` assumption. Specific inner
GPU/GMU PM, clock, IRQ, HFI, hardware, ZAP, and SCM probes stayed zero.
Exact fallback and complete host cleanup passed. V8 is permanently consumed
and non-runnable. The separately versioned
[v9 runtime oracle](test-results/2026-07-26-a660-gmu-resume-entry-v9-runtime-offline.md)
now passes offline using the unchanged v8 kernel module. Duplicate controls
normalize signed/zero-extended `EUCLEAN`, match outer runtime PM by GPU device,
accept the observed 21 generic calls, retain every direct zero-resource and
settled-snapshot gate, and reject twelve mutations. V9 remains HOLD until a
fresh protected root, gate, runner, and separate pre-live review pass; GMU
power preparation remains unauthorized.

The panel exposes four fixed modes named 144/120/90/60. Its DRM capability blob says `qsync support=false`, `dfps support=false`, and `dyn bitclk support=false`; this is fixed refresh-rate switching, not VRR.

See the [project roadmap](ROADMAP.md), [current state](docs/current-state.md),
[hardware contract](docs/hardware-contract.md),
[builds and artifacts](docs/builds-and-artifacts.md),
[subsystem status](docs/port-status.md), [recovery DTS](docs/recovery-dts.md),
[read-only UFS discovery](docs/ufs-discovery.md),
[native network root](docs/network-root.md),
[remote GUI](docs/remote-gui.md), [Arch userspace](docs/arch-linux.md),
[test plan](docs/test-plan.md), and [kernel port plan](docs/kernel-port.md).

## Safety model

- Use `fastboot boot`, never `fastboot flash`, until every mandatory gate passes.
- Keep the untouched Android/recovery slot as the fallback.
- Treat all boot images and extracted firmware as local artifacts.
- Redact serial numbers, full kernel command lines, Wi-Fi credentials, API keys, email, and CV data from reports.
- A newer version number is not success. Storage, USB, charging, thermals, display, input, radio stability, suspend, and GPU must each pass independently.

## Repository layout

```text
configs/kernel/       mainline configuration requirements
containers/           reproducible PC cross-build environment
docs/                 state, architecture, research, and operating guidance
manifests/            artifact identities and provenance (no binaries)
scripts/device/       recovery and Arch device tests, staging, and runtime tools
scripts/host/         Linux/PowerShell fastboot, SSH, and build orchestration
test-results/         redacted, reviewable test reports
```

## Quick start

On the current Nobara Linux development host, install the native Android tools
and grant serial access once, then log out and back in:

```sh
sudo dnf install android-tools
sudo usermod -aG dialout "$(id -un)"
```

The Linux recovery workflow is read-only by default. It validates the exact
manifest-pinned image and requires exactly one fastboot device. Rejected
candidates are never selected by default:

```sh
BOOT_IMAGE="$PWD/artifacts/recovery-stage-vNN/boot-5.4.210-kexec-stage-builtin-recovery.avb.img" \
  scripts/host/recovery-linux.sh preflight
```

If the exact persistent Alpine fallback is already reachable, enter fastboot
without a physical button sequence through the stock Qualcomm restart
handler. The helper first checks the pinned fallback SSH identity, kernel,
init, compatible, ext4 root, pstore, diagnostic modules, and thermals. Its
guarded action sends only Linux `RESTART2("bootloader")`, then requires exactly
one fastboot device; it does not write NVMEM, sysfs, or a partition:

```sh
SSH_KEY=/secure/path/rog5-client-key \
KNOWN_HOSTS=/secure/path/rog5-known-hosts \
  scripts/host/reboot-fallback-to-fastboot.sh preflight

ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
SSH_KEY=/secure/path/rog5-client-key \
KNOWN_HOSTS=/secure/path/rog5-known-hosts \
  scripts/host/reboot-fallback-to-fastboot.sh reboot
```

The attended temporary boot has a separate explicit guard and invokes only
`fastboot boot`. It never flashes:

```sh
ALLOW_TEMPORARY_BOOT=1 \
BOOT_IMAGE="$PWD/artifacts/recovery-stage-vNN/boot-5.4.210-kexec-stage-builtin-recovery.avb.img" \
  scripts/host/recovery-linux.sh boot
```

After ACM enumerates, use the fixed-action helper rather than attaching a
terminal. It opens ACM with no controlling terminal, strips cursor-position
queries, accepts no arbitrary command, and keeps rollback armed:

```sh
ALLOW_NETWORK_ROOT_ACM=1 \
  scripts/host/network-root-acm.py load-normal

# Only with the reviewed GPUCC generic-CCF diagnostic bundle:
ALLOW_NETWORK_ROOT_ACM=1 \
  scripts/host/network-root-acm.py load-gpucc-diagnostic

ALLOW_NETWORK_ROOT_ACM=1 \
ALLOW_ATTENDED_KEXEC=1 \
  scripts/host/network-root-acm.py execute
```

Validate the repository and a local artifact directory:

```powershell
powershell -NoProfile -File scripts/host/Test-Repository.ps1 -ArtifactRoot C:\path\to\RogPhone
```

Temporarily boot an image and run the non-GPU smoke suite:

```powershell
powershell -NoProfile -File scripts/host/Test-Boot.ps1 `
  -BootImage C:\path\to\rog5-alpine-5.4.210-modular.img `
  -SshKey C:\path\to\rog5_ed25519 `
  -SshHost device-debug-address `
  -ExpectedKernel 5.4.210-qgki-perf
```

Validate that the mainline configuration fragment only uses symbols present in a kernel tree:

```powershell
powershell -NoProfile -File scripts/host/Test-KernelFragment.ps1 -KernelSource C:\src\linux-7.1.4
```

Cross-compile the pinned ARM64 kernel in Docker on an x86-64 PC:

```powershell
powershell -NoProfile -File scripts/host/Build-MainlineInDocker.ps1
```

Fetch and authenticate the Arch Linux ARM userspace input:

```sh
scripts/host/get-arch-rootfs.sh
```

After an offline bundle is accepted and the repository is clean, stage the
matching headless-first Plasma rootfs with an external public SSH key:

```sh
scripts/host/stage-arch-rootfs.sh /path/to/rog5_ed25519.pub
```

After the separate host-service confirmation, prepare the manifest-pinned
archive as a root-owned export source and run the attended foreground server:

```sh
pkexec dnf install nfs-utils
pkexec env PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  "$PWD/scripts/host/prepare-network-root-export.sh"
pkexec env PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  "$PWD/scripts/host/serve-network-root.sh"
```

The server uses no permanent export or firewall configuration. It binds
NFSv4.2 to `169.254.77.1`, exports a read-only bind mount only to
`169.254.77.2`, moves only the exact network-root gadget into the verified
unused built-in `drop` zone, and restores runtime state on exit. Do not run
these commands until the external-service gate is explicitly approved.
Its default attended window is 900 seconds. For a deliberately bounded
long-running diagnostic, set `ROG5_NFS_TIMEOUT=86400`; return the phone to
fallback with the validated attended procedure before that deadline because
this temporary root depends on the host export. The v3 retained-exitrd path
has one passing normal systemd reboot, but the bundle remains an attended
temporary-boot transport and must never be flashed.

The equivalent Windows workflow remains available:

```powershell
powershell -NoProfile -File scripts/host/Get-ArchRootfs.ps1
```

Fetch and verify the pinned official Google `adb`/`fastboot` package:

```powershell
powershell -NoProfile -File scripts/host/Get-PlatformTools.ps1
```

Fetch and hash-check the pinned upstream A660 firmware set:

```powershell
powershell -NoProfile -File scripts/host/Get-A660Firmware.ps1
```

Fetch and authenticate the three small Alpine ARM64 packages used by the recovery loader:

```powershell
powershell -NoProfile -File scripts/host/Get-RecoveryPackages.ps1
```

Source files remain in a named Docker volume. Each default PC build uses a
fresh object volume so stale objects cannot contaminate a release candidate;
the retained volume name is printed for audit. Verified `Image`, `Image.gz`,
modules, configuration, metadata, comparison DTBs, and the ASUS
recovery-contract skeleton plus USB2 recovery DTB are exported to
`dist/linux-7.1.4/`. This compile-only result is not a boot image: neither the
upstream DTBs nor the standalone ASUS DTBs may be booted directly on the phone.

The signed Arch input and the current locked minimal Plasma Desktop rootfs
pass their offline suites. The current archive contains the exact
`7.1.4-g7a5cef0db479` network-root modules, verified Qualcomm firmware,
key-only SSH, and no VPN/Wi-Fi/KRDP secret. Root preparation generates one
deployment-local server host key outside Git and pins `sshd` to it. Arch has
now passed two native boots with normal hardware coldplug through the
attended, read-only USB NFS gate; nothing was flashed.

The ARM64 device-side compile helpers pin and verify the source before building. The first output is deliberately a compile-only upstream SM8350 comparison build; none of its existing board DTBs is safe to boot on this phone.

On the proven vendor-kernel baseline, the installed profiles are:

```sh
rog5-power-profile.sh server       # 60 Hz, DPMS off
rog5-power-profile.sh battery      # 60 Hz
rog5-power-profile.sh balanced     # 90 Hz
rog5-power-profile.sh performance  # 120 Hz
rog5-power-profile.sh maximum      # 144 Hz
```

All profiles retain `schedutil`; high refresh does not disable thermal management or force CPU clocks.

`scripts/device/install-runtime-tools.sh` installs the tested display and screen-control helpers used by the vendor-kernel baseline after backing up every replaced file under `/root/rog5-backups/`. The Arch target instead uses systemd, greetd, Plasma Wayland, and KRDP; neither path enables a public listener or flashes a boot image.

## Source baselines

- Stable device baseline: local vendor-derived `5.4.210-qgki-perf #20` artifact.
- Mainline research baseline: Linux `v7.1.4`, commit `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`.
- GodShell evaluation: commit `4530e0fdee0dc98bea20b268273d7a3e438ceb37`.
- postmarketOS audit: pmaports commit `29afb81ed2249d1ca0148a5dc6b4280bf0402af0`; no `anakin` device package was present.

## Definition of done

The project is complete only when a reproducible temporary boot passes the full mandatory matrix, survives repeated cold boots and idle periods, retains the fallback boot path, and has no unexplained kernel faults. Flashing a default kernel and connecting personal automation accounts are separate, explicit release decisions.
