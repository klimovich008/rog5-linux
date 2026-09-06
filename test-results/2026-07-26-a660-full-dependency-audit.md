# A660/GMU complete dependency graph — offline source acceptance

Date: 2026-07-26

Result: **the exact Linux 7.1.4 A660 dependency graph passes its offline
source contract; no live GPU/GMU candidate is accepted yet**. The phone was
not contacted, booted, or modified. Nothing was flashed.

This audit follows the consumer-disabled v18 Adreno SMMU candidate. It does
not supersede the pending one-shot v18 SMMU bind/runtime-suspend gate and does
not claim a render node, firmware startup, GPU power, or acceleration.

## Exact inputs

The audit is pinned to Linux commit
`d9ac316489f4258d389d6298659d5e9c22183400`, tree
`c796deb1cc54e942f8bb46a2c76a7199e19e5c92`, and a clean source tree. The
accepted network-root config has SHA-256
`68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f`.

The source contract hashes and inspects the SM8350 DTS and HDK reference,
GPU/GMU bindings, DRM/MSM and Adreno paths, Qualcomm Adreno SMMU callbacks,
MDT loader, and SCM interface. It reuses the independently accepted v18
Adreno SMMU contract.

The exact upstream firmware set is:

| Firmware | Size | SHA-256 |
|---|---:|---|
| `qcom/a660_sqe.fw` | 43,292 | `d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76` |
| `qcom/a660_gmu.bin` | 55,252 | `8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7` |
| `qcom/sm8350/a660_zap.mbn` | 1,054,648 | `5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d` |

Firmware remains an ignored local artifact and is not committed.

## Device-tree and kernel dependency boundary

The pinned A660 graph contains:

- GPU registers, IRQ 300, Adreno SMMU context IDs 0 and 1, ten OPPs from
  315 MHz through 840 MHz, and a reference to the GMU;
- GMU, RSCC, and PDC register ranges, HFI and GMU IRQs, seven clocks, CX and
  GX power domains, Adreno SMMU context ID 5, and one 200 MHz GMU OPP;
- the existing 8 KiB no-map `pil_gpu_mem` reservation; and
- the HDK reference ZAP firmware name
  `qcom/sm8350/a660_zap.mbn`.

The accepted config already has DRM/MSM, Qualcomm SCM/MDT/RPMh power,
command-db, AOSS QMP, LLCC, RPMh regulators, interconnect, PM-domain, and
Adreno SMMU dependencies built in. GPUCC remains a module.

The ZAP ELF has three program headers. Its relocatable load segment occupies
1,976 bytes from physical offset `0x1000`; `qcom_mdt_get_size()` rounds the
maximum extent to 4 KiB. The exact payload therefore fits in the 8 KiB
reserved region with 4 KiB remaining. This proves only the static size
boundary, not SCM authentication on this phone.

## Two distinct execution boundaries

Enabling the GPU and GMU nodes is not a passive discovery test. Driver
registration maps GPU and GMU registers, requests GPU/HFI/GMU interrupts,
attaches the GPU and GMU IOMMU contexts, allocates GEM/GMU memory, attaches CX
and GX power domains, parses OPP/RPMh votes, and initializes HFI.

Most importantly, `a6xx_gmu_rpmh_init()` writes the GMU RSCC and PDC
configuration during registration. A future registration-only live gate must
therefore use a watchdog and treat those MMIO writes as the first new hardware
boundary.

Firmware and active GPU startup are deferred until a process first opens the
DRM device:

1. `msm_open()` invokes the lazy GPU load path.
2. Freedreno requests the SQE and GMU firmware.
3. GPU runtime PM enables clocks and starts GMU firmware and HFI.
4. GPU hardware initialization begins.
5. The ZAP path loads the MDT payload and asks SCM to authenticate and reset
   GPU PAS ID 13.

The built-in parameter spelling is `msm.separate_gpu_kms=1`. It permits a
headless GPU-only DRM device, but it does not remove either execution
boundary.

## Known source risk

In this exact source, `a6xx_gmu_init()` calls
`a6xx_gmu_pwrlevels_probe(gmu)` without checking its return value. That helper
can return probe deferral or an RPMh/OPP parsing error. The first full
candidate must either fix the return propagation in a small reviewed kernel
patch or prove a fail-closed equivalent before registration is attempted.

This risk is unresolved and must not be silently accepted by a live test.

## Test-first evidence

Commit `8fb7c11` added the contract test first. Its expected initial result was:

`FAIL missing executable A660 full dependency verifier`

Commit `1f60c7b` added the pinned verifier. The exact verifier and wrapper test
now return:

`PASS pinned Linux 7.1.4 A660 graph: probe-time GPU/GMU IOMMU plus RSCC/PDC setup, deferred first-open firmware/power/SCM, exact 4 KiB zap payload in 8 KiB no-map memory, and complete built-in dependencies`

`PASS exact Linux 7.1.4 A660 GPU, GMU, IOMMU, power, firmware, and deferred-open graph is source-audited`

Both scripts pass syntax checks, the pinned ShellCheck container, and
`git diff --check`. The verifier contains no ADB, fastboot, mount, block-device,
or device-write path.

## Safest next candidate

The accepted Image has `CONFIG_DRM_MSM=y`. If GPU and GMU are enabled in its
DTB, built-in probing can enter the RSCC/PDC boundary automatically when
dependencies appear. That is too little control for the first test.

The next candidate should instead derive from the storage-disabled v18
network-root base and build both `CONFIG_DRM_MSM=m` and
`CONFIG_SM_GPUCC_8350=m`. Its contracts must require:

1. the unchanged v18 SMMU gate to pass first;
2. exact GPU and GMU DT nodes plus `msm.separate_gpu_kms=1`;
3. manual one-shot GPUCC load and acceptance;
4. manual one-shot `msm.ko` load under an independent watchdog;
5. no process, service, udev rule, probe, or diagnostic opening a DRM node;
6. acceptance limited to registration, IOMMU attachment, and stable idle;
7. immediate normal reboot after PASS, with no module unload or retry; and
8. a later, separately built and separately attended first-open gate for
   firmware, GMU resume, ZAP/SCM, and GPU hardware initialization.

The historical GPU builders derived from the unsafe UFS-enabled v2 base must
not be reused. No v19 build exists yet, and no live action is authorized by
this report.
