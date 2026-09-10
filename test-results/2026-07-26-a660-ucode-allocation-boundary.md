# A660 ucode allocation boundary — offline source audit

Date: 2026-07-26

Status: **PASS for source isolation; not authorized for a live run**

## Outcome

The exact Linux 7.1.4 A660.1 first-open path can stop after SQE buffer
creation and before GPU/GMU runtime power, GPU/GMU register access, hardware
initialization, HFI, or ZAP/SCM.

This is not a hardware-free boundary. The ucode path allocates pages, creates
GPU virtual addresses, and maps three objects through the already accepted
Adreno SMMU path. Any diagnostic at this seam must permit those three
page-table mappings and then explicitly unmap and release every object before
returning.

The unmodified cleanup path is not sufficient for an early diagnostic return:

- `a6xx_destroy()` releases the SQE and shadow object references, but does not
  release `pwrup_reglist_bo`;
- it does not balance the retained shadow CPU vmap with
  `msm_gem_put_vaddr()` or `msm_gem_kernel_put()`;
- `a6xx_ucode_load()` allocates the power-up reglist unconditionally, so a
  repeated failed open could allocate it again.

Therefore the next diagnostic must be default-off, exact-A660.1-only,
atomic-one-shot, and rollback-safe on every success and failure path. No phone,
ADB, fastboot, SSH, storage, or privileged host operation was used for this
audit.

## Pinned inputs

The verifier requires all of the following:

- source commit:
  `d9ac316489f4258d389d6298659d5e9c22183400`;
- source tree:
  `c796deb1cc54e942f8bb46a2c76a7199e19e5c92`;
- clean source worktree;
- accepted request-only v4 live report:
  `f5e1226923f82528e8cc2ad2727d38834c64761d7691559e295da43fafcfbd8c`;
- accepted request-only v4 marker:
  `912846d98ef6ee9fb3c0fa9f0b455c49d47a2f43ff72e2ba1d14c1c284cbfe32`;
- a successful run of the independent v4 live-acceptance verifier.

The source files used by the proof are hash-pinned:

| File | SHA-256 |
| --- | --- |
| `adreno/adreno_device.c` | `e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599` |
| `adreno/adreno_gpu.c` | `3bd1c6a4d15f1f31ecfbda2ea1d1a07d6b122eb2864adfaf6178e8942bc9fbe0` |
| `adreno/a6xx_catalog.c` | `f1089d825f7b52029520509a39de23c6c05c4ef432e6dff0b084dbdb4bf547b8` |
| `adreno/a6xx_gpu.c` | `29733589c6375930852cb26cfee674f83008084e6bdb792fd86164ea487bf85d` |
| `adreno/a6xx_gpu.h` | `fefca6579b234fda7c0afdcf07d5c2dbb80aade92674c45380c661e259d9f9bb` |
| `msm_gpu.c` | `5a20c0a5151a8da2646380cddf14f6cdfa34a8f953b5330fe613774ae695daa6` |
| `msm_gpu.h` | `b477ecc7f2396b4b65cb28eda9f454c885368277b421e5a11a2209ea4b317b2d` |
| `msm_gem.c` | `49b304a0602361647d9cd86acc5b798b93bfcb2c275fa88e4b0eb05eb0290b53` |
| `msm_gem.h` | `76840d1c84d6cc3b3b34b094c799f4d682998d10ac3d7888bf189b7540b869f1` |
| `msm_gem_vma.c` | `7bca4eda8aa3711b3fc0b3e3b74ff4f775ca94e6e13296cee761ee588ed4c1a2` |
| `msm_iommu.c` | `d196c1c9efb4af66729bf8eaeb26510f707b7acc1bc4edb43530315602785e29` |

## Exact first-open order

`adreno_load_gpu()` has this order:

1. `adreno_load_fw(adreno_gpu)`;
2. `gpu->funcs->ucode_load(gpu)`;
3. `pm_runtime_enable(&pdev->dev)`;
4. `pm_runtime_get_sync(&pdev->dev)`;
5. `msm_gpu_hw_init(gpu)`.

Returning from an instrumented `a6xx_ucode_load()` after rollback therefore
prevents steps 3–5. GMU resume, HFI startup, ZAP loading, and SCM
authentication are downstream of hardware initialization and are also
excluded.

Registration has already mapped GPU resources, requested the IRQ, acquired
clock/regulator handles, created the GPU VM, and attached the SMMU. This audit
does not mislabel those accepted registration effects as absent. It proves
only that the ucode seam does not activate GPU/GMU runtime power or access
GPU/GMU registers.

## Exact A660.1 specialization

The `0x06060001` catalog entry has:

- `a660_sqe.fw`;
- `a660_gmu.bin`;
- no AQE firmware;
- `ADRENO_QUIRK_HAS_HW_APRIV`;
- no automatic-preemption quirk;
- `a6xx_gpu_funcs`.

The module default is `enable_preemption=-1`. Since this A660.1 entry has no
`ADRENO_QUIRK_PREEMPTION`, the exact default path has one ring. The A660 SQE
version branch accepts `a660_sqe.fw` and does not set `has_whereami`; the
HW_APRIV quirk independently requires the privileged shadow object.

## Allocation and mapping result

The consumed v4 root's accepted SQE file is 43,292 bytes with SHA-256
`d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76`.
`adreno_fw_create_bo()` drops the four-byte firmware header, so the copied
payload is 43,288 bytes. `msm_gem_new()` page-aligns every object.

| Object | Requested bytes | GEM bytes | Pages | GEM flags | IOMMU protection |
| --- | ---: | ---: | ---: | --- | --- |
| SQE firmware | 43,288 | 45,056 | 11 | `MSM_BO_WC \| MSM_BO_GPU_READONLY` | read |
| RPTR shadow | 4 | 4,096 | 1 | `MSM_BO_WC \| MSM_BO_MAP_PRIV` | read, write, privileged |
| power-up reglist | 4,096 | 4,096 | 1 | `MSM_BO_WC \| MSM_BO_MAP_PRIV` | read, write, privileged |
| **Total** | **47,388** | **53,248** | **13** |  |  |

There is no AQE object on this A660.1 entry. The GMU firmware remains a
requested firmware object; `a6xx_ucode_load()` does not create a GMU GEM
buffer.

Each of the three objects follows this mapping chain:

`msm_gem_kernel_new()` → `msm_gem_get_and_pin_iova()` →
`msm_gem_pin_vma_locked()` → `msm_gem_vma_map()` → `vm->mmu->map()` →
`msm_iommu_map()` → `iommu_map_sgtable()`.

The SQE bytes are copied through a CPU vmap and its vmap reference is dropped.
The version check temporarily acquires and drops that CPU mapping again.
Shadow and reglist CPU vmaps remain held for normal runtime use, which is why
diagnostic rollback must use `msm_gem_kernel_put()` for those two objects.

## Required rollback

A safe diagnostic cleanup helper must:

1. unpin the SQE IOVA and put the SQE GEM object, then clear SQE object,
   pointer, and IOVA state;
2. call `msm_gem_kernel_put()` for the shadow object, then clear shadow
   object, pointer, and IOVA state;
3. call `msm_gem_kernel_put()` for the power-up reglist object, then clear
   reglist object, pointer, IOVA, and emitted state;
4. run on allocation success and on every partial-allocation failure;
5. finish before returning the deliberate `EUCLEAN`;
6. reject a second attempt atomically.

`msm_gem_unpin_iova()` closes a non-KMS GPU VMA through
`put_iova_spaces(..., true, "close")`, which reaches `iommu_unmap()`. Thus
balanced rollback can remove the three new SMMU mappings before the failed
open returns.

## Explicitly excluded work

This boundary does not permit:

- `pm_runtime_enable()` or `pm_runtime_get_sync()` for the GPU;
- GPU or GMU MMIO reads/writes;
- regulator, clock, interconnect, or power-domain activation;
- GMU firmware start or HFI startup;
- ZAP request, PAS authentication, or SCM calls;
- a surviving DRM file descriptor;
- display, storage, or persistent-device changes;
- reuse of the consumed v4 export.

## Verification

The fail-first test initially returned:

```text
FAIL missing executable A660 ucode-allocation boundary verifier
```

After the source verifier was added:

```text
PASS A660 ucode allocation is source-isolatable with three SMMU mappings and mandatory explicit rollback
PASS A660 ucode allocation has an offline-tested pre-power boundary with explicit three-object rollback required
```

Commands:

```sh
SOURCE_DIR=/path/to/exact/linux-7.1.4 \
  scripts/device/test-a660-ucode-allocation-boundary.sh

shellcheck \
  scripts/device/verify-a660-ucode-allocation-boundary.sh \
  scripts/device/test-a660-ucode-allocation-boundary.sh
```

Both shell syntax and ShellCheck pass.

## Decision

The source boundary is accepted for offline diagnostic design. It does not
authorize a build, export, or live cycle by itself.

Next: implement a default-off exact-A660.1 one-shot diagnostic with explicit
three-object rollback, mutation-test it, reproduce two isolated builds, and
only then decide whether a fresh RAM-only root and attended gate are justified.
