# Builds and required artifacts

## Version strategy

Development follows current stable Linux 7.1.4 so board work is written against the newest upstream Qualcomm, DRM/MSM, and A660 code. Linux 6.18.39 is the deployment/LTS comparison target: kernel.org projects 6.18 maintenance through December 2028. Board changes should be kept small enough to compile on both where APIs permit.

Linux version numbers are not capability grades. A 7.x build is accepted only if it passes more hardware gates than the stable 5.4 baseline.

## Inputs kept in Git

- source revision manifest and URLs
- kernel configuration requirements fragment
- reviewed ASUS board DTS and any new bindings/drivers, once developed
- Arch/systemd service definitions and small BusyBox-compatible recovery scripts
- build, packaging, smoke, hardware, and regression tests
- redacted reports and artifact SHA-256 identities

## Inputs kept private

- stock/vendor boot, vendor-boot, DTBO, and partition images
- decompiled running vendor DTB/DTS
- Qualcomm, ASUS, Pixelworks, Wi-Fi, modem, DSP, and GPU firmware
- SSH private keys, Wi-Fi credentials, API tokens, email, CV, and account data
- complete boot command line and device identifiers

Private inputs live outside the repository and are referenced only by path or hash. They must never be bundled into a public source archive.

## Build products

| Product | Purpose | Current status |
|---|---|---|
| vendor-derived 5.4.210 image #20 | recoverable working server baseline | passes core suite; GPU rejected |
| Linux 7.1.4 `Image.gz` and modules | current-stable compile/toolchain baseline | reproducible PC build; recovery Image passes one attended kexec |
| upstream SM8350 comparison DTBs | schema and subsystem reference | five build/parse/hash checks pass; never boot on ASUS hardware |
| ASUS serial skeleton DTB | verify board source and DTB toolchain | memory, TLMM, disabled UFS, and left-side USB contracts compile and pass static checks; never boot |
| ASUS minimal recovery DTB | USB2 high-speed NCM/ACM recovery with storage disabled | passes offline, two staging cycles, and Linux 7.1 target recovery |
| ASUS A660 tier DTB | upstream Freedreno/GMU bring-up after recovery | isolated two-node overlay and pinned upstream firmware pass offline guards; hardware tests pending |
| ASUS hardware DTB and modules | incremental subsystem bring-up | planned behind tier gates |
| locked Arch server rootfs | signed packages, SSH, VPN/hotspot tools | historical suite passes; contains the previous module set and is not a current boot candidate |
| locked Arch Plasma rootfs | headless-first target with Plasma/KRDP and browser/network tools | manifest-pinned 2,007,186,653-byte network-root archive passes live headless gates; newer 2,007,027,068-byte development archive adds the isolated, resource-bounded `rog5-agent` service plus redacted runtime metrics and passes a clean round trip but is not promoted or booted |
| target initramfs | RAM-only recovery shell, USB NCM/ACM, optional SSH, rollback | v18 passes staging twice and one Linux 7.1 target/rollback cycle |
| GPU target initramfs | isolated A660 probe after base recovery passes | historical archive is derived from the unsafe v2 base; do not boot |
| kexec staging initramfs | carry mainline kernel/DTB/initramfs through header-v3 boot | v18 passes nested load, separate execute, Linux 7.1 target, and rollback |
| read-only UFS discovery bundle | enumerate the UFS topology without mounts or host-originated writes | v1 was rejected safely; reproducible v2 passes offline and live with 116/116 nodes read-only, zero blocked commands, contained power state, and automatic rollback; never flash |
| UFS-disabled network-root bundle | boot an ordinary distro from read-only NFS plus a volatile OverlayFS upper | fourteen-file v3 bundle reproduces with a retained exitrd; normal coldplug and one normal systemd reboot pass with complete cleanup; never flash |
| GPUCC/CCF network-root diagnostic/candidate | trace the SM8350 GPU clock-controller with every consumer disabled | v17 reuses the exact v15 bits, atomically enters the trace-free target, completes GPUCC registration, binds one device for 30 seconds, and reboots cleanly; this accepts only the isolated clock-controller foundation, never flash |
| GPUCC plus Adreno SMMU network-root candidate | register only the idle SMMU before any GPU/GMU consumer | v18 stopped on a detector false positive; v19 safely rejected no-bind; v20 stopped before action on the unset `(null)` override representation; the sole v21 cycle bound `arm-smmu`, reached runtime suspend with zero firmware/render/storage activity, and rolled back cleanly; consumed and removed from the runnable allowlist; never flash |
| A660/GMU registration tier | separate registration from first DRM open before building a live candidate | the sole v3 cycle used one exact SMMU reprobe, loaded seven reviewed modules, attached GPU/GMU to two IOMMU groups, created one unopened headless render node, retained zero firmware/storage/faults, and returned through exact fallback with complete cleanup; consumed and removed from the runnable allowlist; never flash |
| A660 SQE/GMU request-only tier | make one diagnostic DRM open fail after exact firmware requests but before ucode/power/HFI/ZAP | the sole v4 cycle requested SQE/GMU exactly once, returned `EUCLEAN`, retained zero later hardware/storage/fault evidence, and returned through exact fallback plus cleanup; consumed and removed from the runnable allowlist; never flash |
| A660 ucode-allocation tier | isolate SQE/shadow/reglist creation before GPU/GMU runtime power or register access | source/patch and duplicate builds pass; v5 exposed a compiler-inlining-blind wrapper oracle; the [sole v6 cycle](../test-results/2026-07-26-a660-ucode-allocation-v6-live-rejected.md) safely rejected raw sizes `43288/4/4096` against page-rounded expectations before snapshot comparison; v5/v6 are consumed; the [v7 offline correction](../test-results/2026-07-26-a660-ucode-allocation-v7-offline.md), [HOLD](../test-results/2026-07-26-a660-ucode-allocation-v7-prelive-hold.md), and [GO](../test-results/2026-07-26-a660-ucode-allocation-v7-prelive-go.md) chain pins separate raw/object layers, logical `4/4`, equal snapshots, a protected root, and a one-shot runner; the [sole v7 live cycle](../test-results/2026-07-26-a660-ucode-allocation-v7-live-accepted.md) passes exact allocation/rollback plus settled snapshot with zero later hardware events; consumed and non-runnable; never flash |
| A660 GMU resume-entry v8 tier | prove the normal first-open call graph reaches GMU resume while excluding every inner GMU resource operation | source/patch mutation suites, two complete clean builds, zero-fuzz target runtime, compiler-relocation gate, and runtime mutations pass; config/Image/ABI and every installed module except `msm.ko` remain exactly v7; the [sole live cycle](../test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md) reached exact GMU entry/rollback and deliberate `EUCLEAN`, then safely rejected a zero-extended signed-return oracle and exposed a second process-global runtime-PM count flaw; specific inner resource probes remained zero; exact fallback/cleanup passed; v8 is consumed and non-runnable; never retry or flash |
| A660 GMU resume-entry v9 oracle tier | correct only the two v8 userspace trace assumptions before any deeper hardware step | [offline runtime acceptance](../test-results/2026-07-26-a660-gmu-resume-entry-v9-runtime-offline.md) reuses the exact v8 kernel/module, normalizes signed/zero-extended 32-bit `EUCLEAN`, scopes generic runtime PM by GPU device, reproduces controls, and rejects twelve mutations; the protected-root/HOLD/GO chain pins the exact delta, one-shot runner, credentials, private evidence, and verifier-first bounded server; the [sole live cycle](../test-results/2026-07-27-a660-gmu-resume-entry-v9-live-accepted.md) accepts one GPU-device outer PM event, signed `EUCLEAN`, exact rollback, logical `4/4`, and equal settled GEM state with zero inner resource/storage/retained-FD evidence; exact fallback and cleanup pass; permanently consumed and server-non-runnable; never retry or flash |
| A660 GMU/CX runtime-PM v10 tier | isolate the first normal GMU-device resume and linked CX-supplier transition before GX or later resources | the [offline kernel acceptance](../test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md) source-pins the call graph, rejects twelve patch mutations, and reproduces two isolated Linux 7.1.4 builds; the [runtime acceptance](../test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-runtime-offline.md) regenerates both controls and rejects fourteen oracle mutations; the [protected-root/pre-live HOLD](../test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-prelive-hold.md) verifies an exact consumed-v9 delta, target/watchdog gate, no-retry runner, verifier-first bounded server, actual unarmed zero-state refusal, and connected fallback health; config/Image/ABI and every installed module except `msm.ko` remain exactly accepted v8; no v10 live cycle is authorized, retry or flash |
| isolated PMIC network-root bundles | evaluate RTC and power key without exposing storage | v4 reproducibly exposed a near-epoch RTC and is rejected; v5 reproducibly registers the power-key path and passes guarded dependency/reboot gates, with physical press pending; never flash |
| temporary Android boot image | reversible two-stage `fastboot boot` testing | v18 passes two attended live cycles; never flash |
| diagnostic module sources | read raw ramoops and arm bootloader recovery without storage access | maintained under `tools/diagnostics/`; built privately against the exact fallback kernel |
| release boot image | possible persistent deployment | prohibited until every release gate passes |

Large products go under ignored `build/`, `dist/`, or `artifacts/` directories. Every candidate receives a source commit, config hash, compiler version, file sizes, and SHA-256 manifest.

## Build order

1. Validate scripts, known artifacts, and kernel config symbols.
2. Compile current stable Linux plus known upstream SM8350 DTBs to prove the native ARM64 toolchain.
3. Translate only the minimal ASUS boot contract: reserved memory, regulators, disabled UFS, one USB controller, serial/reboot.
4. Compile and run `dtbs_check`; package and verify the RAM-only two-stage recovery image.
5. Use temporary boot, keep UFS disabled until host-visible recovery works, and stop immediately on watchdog, reset, thermal, or USB regression.
6. Add charging, input/display, radios/remotes, then GPU in separate commits and test tiers.
7. Cross-compile-test the board series on 6.18 LTS and current stable.
8. Add BTF/eBPF and GodShell only after the hardware platform is stable.

Native phone builds default to one parallel job. Four jobs heated rapidly; even two jobs eventually approached 45 C at the battery sensor during the first compile. Each build was stopped cleanly and resumed from the object cache at a lower job count. The fragment also disables unrelated ARM64 SoC families, ACPI, Xen, KVM, and NFS so the final image is a DT-based Qualcomm server kernel rather than a distribution-wide ARM64 build.

When a native build is unavoidable, run `guard-kernel-build.sh BUILD_PID` alongside it. The default 45.0 C battery-sensor ceiling terminates the active `make` child and build wrapper while preserving the object cache.

Normal development uses the PC cross-builder. The current v18 recovery,
read-only UFS discovery, and UFS-disabled network-root bundles were built on
Nobara Linux with rootless Podman and container networking disabled. The
network-root Linux 7.1.4 config, Images, module archive, target/staging
initramfs, ASUS wrapper, and header-v3/AVB package each reproduce
byte-for-byte. The existing Windows wrapper remains available:

```powershell
powershell -NoProfile -File scripts/host/Build-MainlineInDocker.ps1
```

It runs the same pinned source, fragment, module, DTB, and verification scripts
as the native experiment. Docker retains the source volume, but the wrapper
creates a fresh object volume by default and prints its name for audit. Only
verified artifacts are copied to `dist/linux-7.1.4/`. The phone receives
nothing until a recovery image passes offline gates; copying `Image`/`Image.gz`
or the current skeleton cannot boot the device because initramfs, command line,
and Android boot-image packaging are still required.

The ASUS staging builder defaults to the smaller legacy loader. Set
`KEXEC_FILE=1` with a separate output directory to reproduce the tested
file-syscall variant; source patches 0005 and 0006 supply the libfdt address
helpers missing from the ASUS source drop.

The archived v2 recovery products retain their hashes for provenance only.
Their live staging root was writable physical UFS, and their target DTB enabled
UFS and QMP/SuperSpeed despite the former zero-storage and USB2-only claims.
Nothing was flashed. Do not boot v2, the rejected v6 candidate, or the
superseded unbooted v12 candidate. V13 and v14 are also rejected because their
exact recovery USB identity never appeared during live temporary boot. V15
identified the unnecessary wake-lock gate through its 31-second timing result
and is retained only as diagnostic evidence. V16 reached exact USB, NCM, and
rollback but not an ACM shell. The local v17 keyed diagnostic proved the
RAM/storage boundary and identified the missing `/dev/ttyGS0` node. V18 is the
reproducible credential-free candidate; both required staging/rollback cycles
and the separate attended Linux 7.1 kexec/target/rollback gate now pass.

## Reproduction records

The build log and private DTS stay out of Git if they contain identifiers. A
redacted summary belongs in `test-results/`; exact nonsecret output hashes
belong in `manifests/`. The
[network-root v1 offline report](../test-results/2026-07-24-network-root-v1-offline.md)
records the reproducible UFS-disabled NFS/OverlayFS kernel, both initramfs
layers, ASUS wrapper, Android package, signed Arch input, verified exact-module
Plasma rootfs, and offline host isolation harness. The
[network-root v1 live report](../test-results/2026-07-24-network-root-v1-live.md)
records the privileged export, four bounded coldplug resets, two passing
diagnostic Arch boots, persistent client authorization, and next isolation
gate. The
[network-root v2 live report](../test-results/2026-07-24-network-root-v2-live.md)
records the reproducible GPU/RMTFS-isolated candidate, two passing normal
coldplug boots, persistent client/server SSH identities, storage/thermal/NFS
gates, and the original orderly-reboot defect. The
[network-root v3 live report](../test-results/2026-07-24-network-root-v3-live.md)
records the reproducible retained-exitrd candidate, full live gate, normal
systemd reboot, fallback SSH restoration, and complete host cleanup. The
[network-root PMIC input report](../test-results/2026-07-24-network-root-pmic-input-live.md)
records the safely rejected v4 RTC result and the v5 power-key dependency,
registration, reboot, and cleanup evidence; physical press observation
remains pending. The
[network-root time-bootstrap report](../test-results/2026-07-25-network-root-time-bootstrap-live.md)
records the guarded volatile correction of a 2,378,466-second drift, disabled
RTC and zero-storage proof, normal reboot, control-safe serial transport, and
complete cleanup. The
[GPUCC diagnostic report](../test-results/2026-07-25-network-root-gpucc-diagnostic-live.md)
records duplicate v9 builds, the GPUCC-only DT and external traced-module
contract, the mapping/PLL live trace, watchdog rollback, complete cleanup, and
the first common-clock instrumentation gate. The
[GPUCC common-clock report](../test-results/2026-07-25-network-root-gpucc-common-diagnostic-live.md)
records duplicate v10 builds, the built-in trace contract, exact index-0 live
boundary, CCF source localization, rollback, cleanup, and next narrower trace
gate. The
[GPUCC generic-CCF offline report](../test-results/2026-07-25-network-root-gpucc-ccf-diagnostic-offline.md)
records duplicate v11 builds and packages, exact hashes, source and transport
contracts, and timing/interpretation limits. The
[GPUCC generic-CCF live report](../test-results/2026-07-25-network-root-gpucc-ccf-diagnostic-live.md)
records the exact orphan-scan boundary, watchdog rollback, complete cleanup,
and required v12 per-orphan trace. The
[GPUCC per-orphan offline report](../test-results/2026-07-25-network-root-gpucc-orphan-diagnostic-offline.md)
records the source-order/budget contracts, duplicate v12 builds and packages,
and exact hashes. The
[GPUCC per-orphan live report](../test-results/2026-07-25-network-root-gpucc-orphan-diagnostic-live.md)
records the completed GPUCC orphan, the second-orphan display-clock boundary,
watchdog rollback, cleanup, and v13 inner-call gate. The
[GPUCC inner-parent offline report](../test-results/2026-07-25-network-root-gpucc-parent-diagnostic-offline.md)
records the exact v13 source contract, 8-second trace bound, two reproducible
kernel/wrapper/package paths, corrected 180-second repacks, and complete
offline acceptance. The
[GPUCC inner-parent live report](../test-results/2026-07-25-network-root-gpucc-parent-diagnostic-live.md)
records the runtime-suspended display-provider state, non-returning
`get_parent()` boundary, source and lock-order limits, watchdog rollback, and
complete cleanup. The
[GPUCC RCG parent-read offline report](../test-results/2026-07-25-network-root-gpucc-rcg2-diagnostic-offline.md)
records the exact v14 source contract, 4.2-second trace bound, unchanged
exported ABI, two reproducible kernel/wrapper/package paths, exact hashes, and
complete offline acceptance. The
[GPUCC RCG parent-read live report](../test-results/2026-07-25-network-root-gpucc-rcg2-diagnostic-live.md)
records the non-returning regmap-call boundary, independent watchdog rollback,
exact fallback, and complete host cleanup. The
[GPUCC runtime-PM candidate offline report](../test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-offline.md)
records the exhaustive lock model, red/green source and mutation tests, clock
KUnit result, two reproducible mainline/wrapper/package paths, exact hashes,
and one-shot live boundary. The
[GPUCC runtime-PM candidate live report](../test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-live.md)
records seven completed DISPCC reads, progress through GPUCC clock index 6,
continuous trace-budget exhaustion at index 7, exact rollback, cleanup, and
the trace-free confirmation gate. The
[GPUCC trace-free confirmation offline report](../test-results/2026-07-25-network-root-gpucc-confirmation-offline.md)
records the unchanged artifact identity, explicit trace-free transport,
fail-closed parameter checks, source/mutation tests, exact bundle verifier,
and one-shot acceptance criteria. The
[v16 staging-only report](../test-results/2026-07-26-network-root-gpucc-confirmation-live.md)
records the no-execute staging rollback and complete cleanup. The
[v17 atomic confirmation offline report](../test-results/2026-07-26-network-root-gpucc-atomic-confirmation-offline.md)
records the guard-first compound transport, 12 ACM tests, mutation rejection,
unchanged artifacts/target gates, and one-shot live boundary. The
[v17 atomic confirmation live report](../test-results/2026-07-26-network-root-gpucc-atomic-confirmation-live.md)
records complete GPUCC registration, one-device stability, disabled
consumers, normal reboot, complete cleanup, and the next Adreno dependency
gate. The
[v18 Adreno SMMU offline report](../test-results/2026-07-26-network-root-adreno-smmu-offline.md)
records the pinned source and driver graph, two-status DT boundary, duplicate
wrapper and repack results, exact artifact identities, fail-closed baseline
and probe contracts, and one-shot live gate. The
[v20 Adreno SMMU offline report](../test-results/2026-07-26-network-root-adreno-smmu-v20-offline.md)
records the exact-name driver-core source proof, deferred/supplier evidence,
one-write boundary, nested watchdogs, unchanged binary verification, isolated
v20 root, and live-eligibility decision. The
[v20 Adreno SMMU live rejection report](../test-results/2026-07-26-network-root-adreno-smmu-v20-live-rejected.md)
records the baseline-only stop, exact null-representation source diagnosis,
zero-action boundary, normal fallback, complete cleanup, and v21 requirements.
The
[v21 Adreno SMMU offline report](../test-results/2026-07-26-network-root-adreno-smmu-v21-offline.md)
records the OF allocation and NULL-format source proof, exact seven-byte
mutation suite, unchanged binary verification, isolated v21 root, and
one-shot live boundary. The
[v21 Adreno SMMU live acceptance report](../test-results/2026-07-26-network-root-adreno-smmu-v21-live-accepted.md)
records one exact-device bind, runtime suspend, the zero-firmware/render/storage
boundary, normal fallback, complete cleanup, and consumed-tier decision. The
[A660 full dependency audit](../test-results/2026-07-26-a660-full-dependency-audit.md)
records the exact GPU/GMU/IOMMU/power/firmware graph, the probe-time
RSCC/PDC writes, the deferred first-open path, the ZAP reserved-memory fit,
the unchecked GMU power-level error, and the manually loaded DRM/MSM
recommendation. The
[A660 registration build report](../test-results/2026-07-26-a660-registration-build.md)
records its fail-closed fix, modular headless config, duplicate isolated
builds, byte-identical acceptance outputs, zero UFS/firmware checks, and the
exact DT, isolated export, nested wrapper/package reproducibility, and
the then-pending live boundary. The
[A660 registration v2 report](../test-results/2026-07-26-a660-registration-v2-offline.md)
records the fail-first v21 acceptance re-lock, immutable-lower marker, new
root-owned export, old/consumed-root rejection, and full unchanged-binary
re-verification. The
[A660 registration v3 report](../test-results/2026-07-26-a660-registration-v3-offline.md)
records the exact SMMU reprobe correction, new root-owned export, nested
watchdog handoff, target/host one-shot control plane, private evidence, and
complete re-verification. The
[A660 registration v3 live acceptance](../test-results/2026-07-26-a660-registration-v3-live-accepted.md)
records the single exact reprobe, seven-module GPU/GMU registration, two IOMMU
attachments, unopened render node, zero-firmware settle, exact fallback,
complete cleanup, and consumed-root lockout. The
[A660 firmware-only boundary report](../test-results/2026-07-26-a660-firmware-only-boundary.md)
records why no-open provisioning is inert and pins the one safe source seam
for a failed-open diagnostic. The
[A660 request-only build report](../test-results/2026-07-26-a660-firmware-request-only-build.md)
records the fail-first corrections, six patch mutations, two isolated clean
builds, exact accepted hashes, unchanged Image/ABI, and offline-only boundary.
The
[A660 request-only v4 offline report](../test-results/2026-07-26-a660-firmware-request-only-v4-offline.md)
records the reproducible static helper, runtime mutations, root-owned
SQE/GMU-only export, ZAP exclusion, one-shot watchdog control plane, unchanged
full package verification, and pre-live boundary. The
[A660 request-only v4 live acceptance](../test-results/2026-07-26-a660-firmware-request-only-v4-live-accepted.md)
records the sole exact two-firmware request, `EUCLEAN` rejection, zero later
hardware/storage/fault evidence, exact fallback, cleanup, and consumed-root
lockout. Its mutation-tested nonsecret marker pins the exact report and
evidence checkpoint. The
[A660 ucode-allocation v5 offline report](../test-results/2026-07-26-a660-ucode-allocation-v5-offline.md)
records the fail-first contract, trace-backed runtime design, root-owned
reflink export, exact SQE/GMU inputs, ZAP exclusion, whole-tree comparison,
inactive NFS/non-runnable boundary, duplicate-build replay, and unchanged
full-package acceptance. The
[A660 ucode-allocation v5 live rejection](../test-results/2026-07-26-a660-ucode-allocation-v5-live-rejected.md)
records the sole temporary boot, passing zero-storage baseline, balanced
three-object rollback traces, incorrect public-wrapper oracle, exact
compiler-relocation diagnosis, unreached GEM snapshot, fallback/cleanup
proof, private evidence hashes, and consumed-tier decision. The
[A660 ucode-allocation v6 offline report](../test-results/2026-07-26-a660-ucode-allocation-v6-offline.md)
records the zero-fuzz generated runtime, compiler-pinned direct
`kernel_new`/`kernel_put` oracle, logical `4/4` balance, exact rollback object
sets, retained equal-snapshot requirement, root-owned reflink export,
changed-seal mutation, unchanged boot package, inactive NFS, and non-runnable
HOLD boundary. The
[A660 ucode-allocation v6 pre-live HOLD report](../test-results/2026-07-26-a660-ucode-allocation-v6-prelive-hold.md)
records the fail-first-tested one-invocation host runner, exact root/package/
gate inputs, strict SSH identity, private evidence, expected reboot
disconnect, local credential readiness, protected root revalidation, inactive
NFS, no phone contact, and continued non-runnable HOLD. The
[A660 ucode-allocation v6 pre-live GO report](../test-results/2026-07-26-a660-ucode-allocation-v6-prelive-go.md)
records the fail-first verifier-before-state server case, actual unarmed
refusal, exact fallback and distinct SSH identities, credential/root/package/
runner checks, inactive NFS, and one-cycle/no-retry authorization. The
[A660 ucode-allocation v6 live rejection](../test-results/2026-07-26-a660-ucode-allocation-v6-live-rejected.md)
records the passing storage-free baseline, successful kernel
allocation/rollback marker, raw-versus-page-rounded size-oracle diagnosis,
unreached settled GEM snapshot, watchdog fallback, private evidence hashes,
complete host cleanup, and permanent v6 lockout. The
[A660 ucode-allocation v7 offline report](../test-results/2026-07-26-a660-ucode-allocation-v7-offline.md)
records immutable v6 derivation, separate source-pinned raw/object size
layers, reproducible zero-fuzz runtime, unchanged accepted module and boot
package, compiler-relocation and logical `4/4` contracts, root-owned
copy-on-write export, exact-delta/credential checks, two changed-seal
rejections, inactive NFS, zero server cases/runners, no phone contact, and
the initial HOLD boundary. The
[A660 ucode-allocation v7 pre-live HOLD report](../test-results/2026-07-26-a660-ucode-allocation-v7-prelive-hold.md)
records the fail-first-tested one-invocation host runner, strict SSH identity,
exact root/package/gate inputs, local credential and protected-root checks,
private mode-`0600` evidence contract, actual unarmed refusal, inactive
NFS/RPC, no server/boot/retry authority, no phone contact, and continued
HOLD. The
[A660 ucode-allocation v7 pre-live GO report](../test-results/2026-07-26-a660-ucode-allocation-v7-prelive-go.md)
records the fail-first exact-root server case, verifier-before-state ordering,
clean synchronized Git, immutable root/package/runner hashes, distinct pinned
SSH identities, strict fallback health, inactive host services, actual
unarmed privileged refusal, zero residue, and one-cycle/no-retry/no-flash
authorization. The
[A660 ucode-allocation v7 live acceptance](../test-results/2026-07-26-a660-ucode-allocation-v7-live-accepted.md)
records three successful raw-size-pinned allocations, exact pointer-set
rollback, compiler-aware logical `4/4`, equal settled GEM state, zero
power/HFI/ZAP/SCM/storage/fault activity, normal fallback, complete cleanup,
private evidence hashes, and permanent v7 consumption. The
[A660 GMU resume-entry boundary report](../test-results/2026-07-26-a660-gmu-resume-entry-boundary.md)
records the source-pinned normal first-open propagation, entry-only seam,
outer runtime-PM rollback, v7 cleanup dependency, and exclusion of every GMU
inner power/clock/MMIO/IRQ/firmware/HFI operation. The
[A660 GMU resume-entry v8 offline report](../test-results/2026-07-26-a660-gmu-resume-entry-v8-offline.md)
records the fail-first build contract, default-off exact-chip patch and
mutations, two network-disabled clean builds, byte-identical outputs,
MSM-only predecessor/archive delta, pinned hashes, zero embedded firmware,
and offline-only HOLD decision. The
[A660 GMU resume-entry v8 runtime report](../test-results/2026-07-26-a660-gmu-resume-entry-v8-runtime-offline.md)
records immutable-v7 zero-fuzz generation, exact compiler relocations,
accepted logical `4/4` allocation/rollback, one outer and zero inner PM,
zero resource/HFI/hardware/SCM events, equal GEM snapshots, eleven rejected
mutations, no phone contact, and continued HOLD. The
[A660 GMU resume-entry v8 protected-root report](../test-results/2026-07-26-a660-gmu-resume-entry-v8-root-offline.md)
records the consumed-v7 copy-on-write root, exact controls/MSM delta,
whole-tree and credential verification, five rejected mutations, compound
target gate, inactive NFS, no phone contact, and continued non-runnable HOLD.
The
[A660 GMU resume-entry v8 pre-live HOLD report](../test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-hold.md)
records fail-first host control, one-call mock transport, immutable
root/package/gate inputs, private evidence, local credential agreement,
expected reboot disconnect, no retry, real root reverification, actual
unarmed refusal, inactive NFS/RPC, no phone contact, and continued HOLD. The
[A660 GMU resume-entry v8 pre-live GO report](../test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-go.md)
records the fail-first verifier-before-state NFS case, complete unchanged
fourteen-file package, protected root and five rejected mutations, clean
synchronized Git, credentials and distinct SSH identities, strict read-only
fallback health, actual unarmed server/runner refusals, residue-free final
host state, and authorization for exactly one RAM-only cycle with no retry or
flash. The
[A660 GMU resume-entry v8 live rejection](../test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md)
records that sole cycle: exact entry and accepted rollback, three
zero-extended `-EUCLEAN` returns, 21 unscoped generic runtime-PM calls, zero
specific inner resource events, fail-closed handling, exact fallback,
complete cleanup, private evidence hashes, and permanent v8 consumption.
The
[A660 GMU resume-entry v9 offline runtime report](../test-results/2026-07-26-a660-gmu-resume-entry-v9-runtime-offline.md)
records that correction using the unchanged v8 module: fail-first checker and
runtime chains, signed/zero-extended `EUCLEAN`, exact GPU-device PM matching,
the observed 21-call fixture, duplicate outputs, twelve rejected mutations,
and continued live HOLD. The
[A660 GMU resume-entry v9 protected-root report](../test-results/2026-07-26-a660-gmu-resume-entry-v9-root-offline.md)
records the consumed-v8 copy-on-write root, unchanged kernel/seven-module/
two-firmware payload, signed/device-scoped oracle, whole-tree and credential
checks, compound target gate, inactive NFS, fail-closed partial cleanup, no
phone contact, and continued HOLD. A strict no-retry host runner and separate
pre-live review were then accepted by the
[A660 GMU resume-entry v9 pre-live HOLD report](../test-results/2026-07-26-a660-gmu-resume-entry-v9-prelive-hold.md).
It records one-call mock transport, strict SSH identity, local client/server
credential agreement, private evidence, expected reboot disconnect, actual
unarmed refusal, clean synchronized Git, complete root reverification,
inactive NFS/RPC, zero server tokens, no phone contact, and continued HOLD.
The subsequent
[A660 GMU resume-entry v9 attended GO review HOLD](../test-results/2026-07-26-a660-gmu-resume-entry-v9-prelive-go-hold.md)
records a fail-first verifier-before-state exact-root server case, actual
unarmed zero-state refusal, unchanged fourteen-file package, complete local
root/runner/credential/host revalidation, and inactive NFS/RPC. It does not
grant GO because the phone is physically absent and the required
identity-pinned fallback health preflight cannot run. A connected persistent
fallback remained required at that checkpoint. The later
[A660 GMU resume-entry v9 live acceptance](../test-results/2026-07-27-a660-gmu-resume-entry-v9-live-accepted.md)
records the sole RAM-only cycle: current fallback and every GO gate, exact
transport identities, one GPU-device outer runtime-PM event, signed
`EUCLEAN`, exact firmware/allocation/mapping rollback, logical `4/4`, equal
settled GEM state, zero specific inner resource/storage/retained-FD evidence,
exact fallback, complete host cleanup, private evidence hashes, and permanent
v9 consumption. The
[A660 GMU/CX runtime-PM v10 offline acceptance](../test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md)
now records the pinned source boundary, mutation-tested patch, and two
byte-identical isolated builds. The separate
[runtime acceptance](../test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-runtime-offline.md)
and
[protected-root/pre-live HOLD](../test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-prelive-hold.md)
record duplicate control generation, fourteen rejected oracle mutations, the
exact consumed-v9 root delta, complete recursive verification, target and
watchdog gates, a strict no-retry runner, verifier-first exact-root NFS case,
actual unarmed zero-state refusal, inactive NFS/RPC, and connected fallback
health. V10 remains unauthorized for live runtime use; no v10 boot, retry, or
flash occurred. The
[UFS discovery offline report](../test-results/2026-07-24-ufs-discovery-offline.md)
records the guarded Linux 7.1.4 build, corrected built-in UFS PHY dependency,
reproducible nested bundle, and exact candidate hashes. The
[v2 offline report](../test-results/2026-07-24-ufs-discovery-v2-offline.md)
records the corrected power-containment build, and the
[v2 live report](../test-results/2026-07-24-ufs-discovery-v2-live.md) records
the passing 116-node read-only enumeration and automatic rollback. The
[current clean-build report](../test-results/2026-07-23-mainline-reproducibility.md)
records the rejected comparisons and the combined Python hash-seed/BTF
serialization fix. The
[recovery v18 report](../test-results/2026-07-24-recovery-v18-offline.md)
records the current reproducible candidate and artifact set. The
[v18 live report](../test-results/2026-07-24-recovery-v18-live.md) records its
two passing credential-free staging and rollback cycles. The
[Linux 7.1 live report](../test-results/2026-07-24-recovery-v18-mainline-live.md)
records the passing load, kexec, zero-storage target, and rollback. The
[v17 diagnostic](../test-results/2026-07-24-recovery-v17-ssh-diagnostic.md)
records the live storage proof and ACM root cause. The
[v16 live report](../test-results/2026-07-24-recovery-v16-live.md) records
exact recovery USB, NCM, and rollback with the missing ACM shell. The
[recovery v15 report](../test-results/2026-07-24-recovery-v15-diagnostic.md)
records the completed timing diagnosis. The
[v14 live report](../test-results/2026-07-24-recovery-v14-live.md) records its
matching early return. The
[v13 live report](../test-results/2026-07-24-recovery-v13-live.md) records its
early return and the corrected host USB identity check. The earlier
[v12 report](../test-results/2026-07-24-recovery-v12-offline.md) is retained
as superseded provenance.
