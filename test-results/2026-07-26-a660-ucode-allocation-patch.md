# A660 ucode-allocation diagnostic patch — offline source acceptance

Date: 2026-07-26

Status: **PASS at source/patch level; subsequent build accepted separately;
live use remains pending**

## Outcome

Patch
`0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch` implements the
source boundary accepted in the preceding audit. It is:

- false by default;
- exposed only through a mode-`0400` module parameter;
- mutually exclusive with the accepted request-only diagnostic;
- atomically limited to one open attempt;
- restricted to exact A660.1 chip ID `0x06060001`;
- rollback-complete for SQE, AQE if present, shadow, power-up reglist, GPU
  IOVAs, retained CPU vmaps, and diagnostic firmware references;
- deliberately failed-open with `EUCLEAN`; and
- isolated before GPU/GMU runtime power, GPU hardware initialization, HFI,
  and ZAP/SCM.

The patch also replaces the incomplete normal A6xx ucode teardown with the
same balanced helper. This releases the power-up reglist and balances retained
shadow/reglist CPU vmaps during ordinary driver destruction.

This checkpoint does not claim that the patch compiles. No build output,
network root, boot package, or live cycle is accepted by this report.

## Pinned inputs

- source commit:
  `d9ac316489f4258d389d6298659d5e9c22183400`;
- source tree:
  `c796deb1cc54e942f8bb46a2c76a7199e19e5c92`;
- accepted predecessor patch:
  `3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054`;
- ucode-allocation patch:
  `6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2`.

The verifier first runs the independent predecessor verifier, proves that
0014 cannot apply directly to the clean source, applies 0013 in an isolated
temporary tree, and only then applies 0014.

The exact 0014 diff is:

```text
32	14	drivers/gpu/drm/msm/adreno/a6xx_gpu.c
1	0	drivers/gpu/drm/msm/adreno/a6xx_gpu.h
71	0	drivers/gpu/drm/msm/adreno/adreno_device.c
26	0	drivers/gpu/drm/msm/msm_drv.c
1	0	drivers/gpu/drm/msm/msm_gpu.h
```

The five final stacked source hashes are:

| Source | SHA-256 |
| --- | --- |
| `msm_drv.c` | `bf109068950c2e04d6121a5aea8bee7c20d7c3535a05107728e197351fc6e3c6` |
| `msm_gpu.h` | `d3312f908da1702a4f0e63b3e9aed9f77ed7fe352381c2e31647b8225e2993ec` |
| `adreno_device.c` | `0954e9cc45a948c02dbecca34d41f1343f004880a983403baa668b3c96a095c2` |
| `a6xx_gpu.c` | `34ba40a1de4705b471a09266c51a1b5d20f06534faea6bff70d2b0025d185ae7` |
| `a6xx_gpu.h` | `5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5` |

## Open control plane

The new parameter is:

```c
static bool ucode_allocation_only;
module_param(ucode_allocation_only, bool, 0400);
static atomic_t ucode_allocation_only_consumed = ATOMIC_INIT(0);
```

`msm_open()` first rejects the ambiguous case where both diagnostic modes are
armed. If only `ucode_allocation_only` is armed, it:

1. atomically changes the attempt state from 0 to 1;
2. returns `EALREADY` for every later attempt;
3. calls `adreno_load_ucode_only()`;
4. returns the real helper error on failure;
5. emits
   `A660 ucode-allocation-only passed and rolled back; reject open`; and
6. returns `EUCLEAN`.

The unchanged firmware-request-only branch and normal
`load_gpu()`/`context_init()` path remain after this new branch.

## Exact diagnostic transaction

`adreno_load_ucode_only()`:

1. requires a registered GPU and `ucode_load` callback;
2. checks chip ID `0x06060001`;
3. rejects any pre-existing firmware, GEM object, pointer, or IOVA state;
4. requests catalog firmware through `adreno_load_fw()`;
5. calls the existing A6xx `ucode_load()` once;
6. requires SQE, shadow, and power-up reglist objects with nonzero IOVAs and
   requires AQE to be absent;
7. calls `a6xx_ucode_unload()` on success and every partial-allocation
   failure; and
8. releases and clears every diagnostic firmware reference.

The helper contains no runtime-PM, regulator, clock, interconnect, GPU/GMU
register, hardware-init, HFI, ZAP, or SCM call.

## Balanced rollback

`a6xx_ucode_unload()` performs:

| State | Rollback |
| --- | --- |
| SQE | `msm_gem_unpin_iova()` + `drm_gem_object_put()` |
| optional AQE | `msm_gem_unpin_iova()` + `drm_gem_object_put()` |
| shadow | `msm_gem_kernel_put()` |
| power-up reglist | `msm_gem_kernel_put()` |

It then clears every object pointer, CPU pointer, IOVA, and
`pwrup_reglist_emitted`. `msm_gem_kernel_put()` balances both the CPU vmap and
GPU IOVA before dropping the object. The normal `a6xx_destroy()` now calls
this helper instead of retaining a separate partial cleanup sequence.

## Fail-first and mutation evidence

Fail-first commit `b89c979` initially returned:

```text
FAIL missing A660 ucode-allocation diagnostic patch
```

The completed test rejects eight independent mutations:

1. mode-`0600` writable parameter;
2. pre-consumed atomic state;
3. non-atomic consume;
4. wrong A660 chip ID;
5. skipped `ucode_load()`;
6. shadow object put without balanced CPU-vmap/IOVA cleanup;
7. reglist object put without balanced CPU-vmap/IOVA cleanup; and
8. successful DRM open.

Strict `checkpatch.pl` reports zero errors, warnings, or checks. POSIX shell
syntax, ShellCheck, and `git diff --check` pass.

Final output:

```text
PASS ucode-allocation patch is default-off, exact-A660, one-shot, rollback-complete, failed-open, and pre-power
PASS A660 ucode-allocation diagnostic patch is mutation-tested, one-shot, rollback-complete, and isolated before GPU power
```

## Decision

The patch is accepted for isolated compilation. It is not accepted for a
rootfs or phone.

Subsequent duplicate-build acceptance is recorded in the
[ucode-allocation build report](2026-07-26-a660-ucode-allocation-build.md).
That later checkpoint does not retroactively authorize a root or phone cycle;
those remain separately gated.
