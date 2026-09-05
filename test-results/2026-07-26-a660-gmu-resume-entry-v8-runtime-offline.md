# A660 GMU resume-entry v8 runtime offline acceptance

Date: 2026-07-26

Decision: **PASS offline / HOLD live**

This checkpoint accepts only the reproducible target-side baseline and
one-open runtime probe for the already accepted v8 kernel diagnostic. It does
not create or serve a network root, contact the phone, authorize a boot, allow
a retry, or authorize flashing.

## Immutable predecessor

The runtime generator starts from
`scripts/device/build-a660-ucode-allocation-v7-runtime.sh`, SHA-256
`ac4412f6710b1c6bb1d6f87bb6850157aa136a55301db84884843784bae6bf7c`.
That generator reproduces the consumed v7 baseline and probe before either v8
patch is applied.

The following accepted evidence is hash-pinned:

| Input | SHA-256 |
| --- | --- |
| accepted v7 live report | `ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a` |
| GMU resume-entry source boundary | `41c06dcd895fcc873638ddf40dce0b0d5dd5bbf9e148f5d3abd5521b072c320d` |
| reproducible v8 kernel build report | `6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c` |
| accepted v8 kernel patch | `a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051` |
| v8 `msm.ko` | `b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861` |

## Reproducible runtime

Two zero-fuzz patches derive the v8 controls from immutable v7:

| Artifact | SHA-256 |
| --- | --- |
| baseline patch | `fe3355d5dcb8a4f16b15ac5a3554b00ab8c5477d619eb7466edcdb0b2cf95e2d` |
| probe patch | `fa6f8d984595fa4fb399404108b431b14e299287357cf98a6aef30ec67f2aece` |
| generated baseline | `3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23` |
| generated probe | `832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255` |

The builder was run twice into independent empty directories. Both generated
baseline files compared equal, both probe files compared equal, and both
copies passed the semantic verifier.

The runtime requires:

- exactly one `adreno_load_gpu()` entry and NULL return;
- exactly one outer `__pm_runtime_resume()`;
- exactly one `adreno_runtime_resume()`, `a6xx_gmu_pm_resume()`, and
  `a6xx_gmu_resume()`, each returning `EUCLEAN`;
- exactly one atomic GMU-entry hit and one successful
  `adreno_rollback_gpu_load_only()` call;
- the accepted v7 allocation/cleanup contract: two firmware requests and
  releases, three maps/unmaps/closes/unpins/frees, three `kernel_new`, two
  `kernel_put`, public wrappers `1/2`, logical vmap balance `4/4`, and equal
  pre/post-settle GEM snapshots;
- zero inner runtime-PM calls, clock-rate changes, IRQ enables, HFI start,
  devfreq resume, LLC activation, hardware initialization, ZAP, and all
  audited SCM calls;
- `gmu_resume_entry_only=Y`, `ucode_allocation_only=N`, and
  `firmware_request_only=N`, all mode `0400`;
- one exact helper open returning `OPEN_ERRNO=117`, no retained DRM
  descriptor, no physical storage, no block-backed mount, safe thermals,
  running systemd, and the independent watchdog.

## Compiler-relocation gate

`scripts/device/verify-a660-gmu-resume-entry-vmap-relocations.sh` pins the
accepted module hash, symbol addresses/sizes, and exact AArch64 `CALL26`
relocations.

It proves that v8 retained accepted v7 allocation and rollback state despite
Clang inlining: three logical objects still produce `kernel_new=3`,
`kernel_put=2`, wrapper `get=1`, wrapper `put=2`, and logical `4/4`.

It also pins the diagnostic call chain:

- `msm_open()` has the exact v8 lazy-load and rollback call sites;
- `adreno_load_gpu()` has one outer runtime-PM resume call;
- `a6xx_gmu_pm_resume()` calls `a6xx_gmu_resume()` before devfreq resume;
- the GMU-entry atomic hit precedes both inner runtime-PM calls, both
  `clk_set_rate()` calls, both IRQ enables, and HFI start.

The relocation verifier passes:

```text
PASS A660 GMU resume-entry v8 relocations module=b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 gmu_hit_before_inner_pm=1 logical_gets=4 logical_puts=4 wrapper_gets=1 wrapper_puts=2 kernel_news=3 kernel_puts=2 snapshot=still-required
```

## Fail-first and mutation results

Before implementation, the runtime contract failed because the builder and
verifier were absent. After implementation, the complete test passes:

```text
PASS A660 GMU resume-entry v8 runtime is reproducibly generated and rejects mode, resume, rollback, inner-PM, clock, IRQ, HFI, snapshot, errno, predecessor, and writable-parameter mutations
```

Rejected mutations cover:

- enabling the consumed v7 ucode-only mode instead of v8;
- omitting GMU-resume or rollback evidence;
- permitting a second runtime-PM resume, a clock-rate change, an IRQ enable,
  or HFI start;
- omitting the settled GEM snapshot comparison;
- accepting a successful open instead of exact `EUCLEAN`;
- changing the consumed predecessor identity; and
- making the diagnostic parameter writable.

All four shell tools and both generated controls pass `sh -n` and ShellCheck.
Static transport/storage scans reject ADB, fastboot, SSH/SCP, block-device
writes, storage-backed mounts, direct poweroff, and reboot outside the later
compound gate.

## Safety decision

V8 remains **HOLD**. The next authorized work is offline only:

1. derive a copy-on-write protected v8 root from the immutable consumed v7
   root;
2. replace only the versioned runtime controls, seal, helper name, and exact
   MSM module;
3. verify the whole-tree delta, credentials, unchanged boot package, and
   mutation cases;
4. add a strict no-authority runner and record a separate HOLD checkpoint.

Only a later verifier-before-state GO review may add one exact-root NFS case
and decide whether one attended RAM-only cycle is justified. Nothing in this
report authorizes flashing.
