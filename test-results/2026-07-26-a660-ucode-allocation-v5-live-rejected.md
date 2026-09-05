# A660 ucode-allocation v5 — safe live rejection

Date: 2026-07-26

Result: **the sole permitted v5 RAM-only cycle completed the kernel's
three-object allocation and rollback, but the userspace gate rejected the
result because its CPU-vmap oracle expected four calls to the public
`msm_gem_get_vaddr()` wrapper. The accepted Clang build inlines three of those
logical acquisitions inside `msm_gem_kernel_new()`, so only one public-wrapper
call was observable. The gate stopped before its settle period and pre/post
GEM snapshot comparison; v5 therefore does not pass and is not GPU
acceptance. Exact fallback and complete host cleanup passed. V5 is consumed
and must not be served or retried.**

## Exact attended boundary

The live cycle started from pushed repository checkpoint `4a7238c`. Its
recovery preflight found that the already accepted A660 temporary-boot images
were missing from the global artifact manifest. The manifest was corrected
before boot; no verifier was bypassed. The live inputs were:

| Input | Size | SHA-256 |
|---|---:|---|
| raw header-v3 boot image | 95,711,232 | `1f98e136913a924e6338c6b7bfc3fb925146f00efd3c77e1192f4e25c0be26bb` |
| temporary-boot AVB image | 100,663,296 | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |
| accepted MSM module | — | `fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45` |

The guarded fallback request reached the exact fastboot product, every
manifest-pinned artifact passed preflight, and the image was used through one
temporary `fastboot boot`. **Nothing was flashed.**

One exact NFSv4.2 window served only the verified root. The fixed recovery ACM
sequence accepted one load-marker rediscovery inside the same invocation,
then entered the exact network root. Strict pinned SSH verified the target
before the host invoked the v5 runner exactly once. There was no runner retry.

## Passing baseline

Before the helper was continued, the target reported:

`PASS A660-ucode-allocation baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 failed_units=0 thermal_zones=29 thermal_max_mC=38100 module_files=7 helper=exact watchdog=armed`

This proves the read-only NFS/volatile OverlayFS boundary, zero device
storage, exact two-file firmware input, unopened render node, empty diagnostic
trace, healthy systemd state, and armed rollback authority before the one
open.

## Delivered live trace

The exact one-open helper requested SQE and GMU firmware once each. The kernel
diagnostic entered and returned successfully, then emitted:

`A660 ucode-allocation-only passed and rolled back; reject open`

The PID-filtered trace recorded:

| Event | Count/result |
|---|---:|
| diagnostic entry / return | `1 / 1`, return `0` |
| VMA map entry / successful return | `3 / 3` |
| VMA unmap | `3` |
| VMA close | `3` |
| GEM unpin | `3` |
| GEM free | `3` |
| public `msm_gem_get_vaddr` wrapper | `1` |
| public `msm_gem_put_vaddr` wrapper | `2` |
| `msm_gem_kernel_put` | `2` |
| ucode unload | `1` |
| firmware request / release | `2 / 2` |

The three map returns were all zero. No later GPU/GMU runtime-power, HFI,
ZAP/SCM, or render-open trace appeared before rejection.

The userspace gate then stopped with:

`FAIL CPU vmap trace count is 1, expected 4`

This is the decisive v5 result. The gate rejected at that count check, so its
20-second settle and post-run debugfs GEM snapshot comparison were not
reached. The snapshot comparison was not reached, and no live
`gem_snapshot=equal` claim is made.

## Compiler-relocation diagnosis

The v5 oracle assumed every logical CPU-vmap operation would enter a public
wrapper symbol. That assumption is false for the accepted module. Its exact
symbol table includes:

| Symbol | Address | Size |
|---|---:|---:|
| `msm_gem_get_vaddr_locked` | `0x3468` | `0x20` |
| `msm_gem_get_vaddr` | `0x35d4` | `0x50` |
| `msm_gem_put_vaddr_locked` | `0x3644` | `0x80` |
| `msm_gem_put_vaddr` | `0x36c4` | `0x88` |
| `msm_gem_kernel_new` | `0x4734` | `0x124` |
| `msm_gem_kernel_put` | `0x4858` | `0x104` |
| `adreno_fw_create_bo` | `0x159f8` | `0x9c` |
| `a6xx_ucode_unload` | `0x225a0` | `0x150` |
| `a6xx_ucode_load` | `0x25158` | `0x374` |

The module's `.rela.text` records prove:

- `msm_gem_kernel_new()` has no call relocation to either
  `msm_gem_get_vaddr()` wrapper;
- `msm_gem_kernel_put()` has no call relocation to either
  `msm_gem_put_vaddr()` wrapper;
- `adreno_fw_create_bo()` calls `msm_gem_kernel_new()` at `0x15a40` and the
  public put wrapper at `0x15a60`;
- `a6xx_ucode_load()` calls `msm_gem_kernel_new()` at `0x251b8` and
  `0x251f4`, the public get wrapper at `0x252d8`, and two mutually exclusive
  version-check put branches at `0x25418` and `0x25460`; and
- `a6xx_ucode_unload()` calls `msm_gem_kernel_put()` at `0x226a4` and
  `0x226bc`.

The pinned source contract says each `msm_gem_kernel_new()` logically acquires
one CPU vmap and each `msm_gem_kernel_put()` releases one. Clang inlined those
wrapper bodies into the convenience functions. The accepted A660 path
therefore has:

- three successful logical acquisitions through `msm_gem_kernel_new()`;
- one separately observable public-wrapper get during SQE version checking;
- two logical releases through `msm_gem_kernel_put()`; and
- two observable public-wrapper puts: one after copying SQE and one on the
  successful version-check branch.

That is a logical `4 / 4` balance while public wrapper probes observe exactly
`1 / 2`, matching the live result (`cpu wrapper get=1 put=2`). The executable
offline verifier
[`verify-a660-ucode-vmap-relocations.sh`](../scripts/device/verify-a660-ucode-vmap-relocations.sh)
pins the module hash, symbol ranges, call relocations, inlining boundary, and
future logical count contract.

This explains the v5 count mismatch; it does **not** retroactively accept v5.
The missing post-settle snapshot still prevents acceptance.

## Fallback, cleanup, and evidence

The v5 runner returned failure and was not invoked again. The explicit v5 NFS
allowlist entry was removed immediately. The server detected target departure
and removed its export, listener, mounts, firewall state, and temporary USB
addressing.

The persistent Alpine fallback returned and its exact verifier passed:

`PASS exact persistent fallback ready for guarded bootloader reboot`

The privileged cleanup verifier reported:

`PASS privileged host cleanup NFS=0 exports=0 listeners=0 mounts=0 firewall-temp=0 nonlocal=0 services=restored`

The final host checkpoint also had no fastboot device, no ADB device, and a
clean synchronized Git branch. Firewalld, NetworkManager, ModemManager, and
the ordinary non-autoconnect fallback profile were restored.

Raw logs remain outside Git in a caller-owned mode-`0700` directory with
mode-`0600` files. Their nonsecret identities are:

| Private evidence | Size | SHA-256 |
|---|---:|---|
| live gate log | 9,871 | `e94a1cc45f5366c8ceb3be75a785ae2d0efa9ec2771f27e6206cba115e801dfe` |
| staging ACM log | 489 | `bcf1743eafc31fbc16e947375766368cc75afbf1980f68db7525032669db21b3` |

No serial, MAC address, boot ID, credential, private path, or raw private log
is committed.

## Consumed tier and v6 boundary

Commit `86b6663` consumes v5 and removes it from the bounded NFS server. Its
non-runnable lockout test passes. V5 must never be re-enabled or retried.

Before any new hardware decision, a separately versioned v6 must be completed
and reviewed offline. It must:

1. preserve the exact module and rollback behavior unless a separately
   justified source change is required;
2. pin the compiler-relocation verifier above;
3. trace three successful `msm_gem_kernel_new()` operations and two
   `msm_gem_kernel_put()` operations;
4. require public-wrapper counts `get=1` and `put=2`, producing logical vmap
   balance `4 / 4`;
5. retain exact pointer-balanced map/unmap/close, unpin/free, firmware,
   forbidden-event, watchdog, storage, and one-open constraints;
6. proceed through the full settle interval and require an equal pre/post GEM
   snapshot before PASS;
7. use a fresh verified root, seal, mock-tested host runner, and default-off
   serving boundary; and
8. require a new explicit attended GO review. There is no inherited live
   authorization from v5.

GPUCC/CCF, the idle Adreno SMMU, A660 registration, and firmware request-only
remain accepted from their earlier tiers. Ucode-allocation acceptance, GMU
resume/HFI, ZAP/SCM authentication, successful render open, command
submission, Mesa/Freedreno/Turnip, display, suspend, and accelerated desktop
remain pending.
