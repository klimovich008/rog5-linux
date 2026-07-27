# A660 GMU/CX runtime-PM v10 — offline build acceptance

Date: 2026-07-27

Result: **PASS offline; HOLD for runtime controls, protected root, and live
use**

## Outcome

The separately versioned v10 diagnostic now passes its pinned-source
boundary, patch mutation suite, strict patch style check, two complete
isolated Linux 7.1.4 builds, predecessor comparison, and final build
contract.

V10 isolates only the first normal `pm_runtime_get_sync(gmu->dev)` and the
linked CX supplier transition. It synchronously returns both domains to
suspended state and deliberately rejects the DRM open with `EUCLEAN`. It
stops before GX runtime PM, clock changes, secure setup, MMIO, IRQ enable,
firmware start, HFI, hardware initialization, ZAP, or SCM.

Relative to the accepted v8 kernel build:

- `.config`, `Image`, `Image.gz`, `Module.symvers`, `gpucc-sm8350.ko`, and
  `mdt_loader.ko` are byte-identical;
- `msm.ko` is the only changed installed module;
- the module archive has the same file list and symlink targets, with
  `msm.ko` as its sole changed regular file;
- DRM/MSM and GPUCC remain modular, KMS remains disabled, and storage remains
  excluded;
- the new module contains BTF and all predecessor diagnostic modes; and
- neither build tree nor module archive contains A660 SQE, GMU, or ZAP
  firmware.

This is an offline acceptance only. The phone was not contacted, no NFS or
RPC service was started, no export or protected v10 root was created, no
temporary boot package was prepared, and nothing was booted or flashed.

## Runtime-PM boundary

The source and patch contracts require this exact sequence:

1. accept only exact A660.1 (`0x06060001`);
2. atomically move the diagnostic state from unused `0` to attempted `1`;
3. call `pm_runtime_get_sync(gmu->dev)`;
4. if the get fails, balance its usage count with
   `pm_runtime_put_noidle(gmu->dev)` and return the original error;
5. after a successful get, synchronously suspend the GMU consumer with
   `pm_runtime_put_sync_suspend(gmu->dev)`;
6. synchronously request suspension of the linked CX supplier with the
   non-counting `pm_runtime_suspend(gmu->cxpd)`;
7. require both `gmu->dev` and `gmu->cxpd` to report runtime-suspended;
8. atomically move attempted `1` to fully passed `2`; and
9. return `EUCLEAN`, then reuse the accepted firmware/ucode GPU-load
   rollback and reject the DRM open.

Only the complete, settled rollback can reach state `2`. A failed get,
failed put/suspend, unsuspended domain, wrong chip, mixed diagnostic mode,
second attempt, surviving GPU object, failed load rollback, or successful
open fails closed.

The stop remains above `gmu->hung = false` and therefore above:

- GX-domain runtime PM;
- core-clock rate changes and bulk clock enable;
- secure initialization and bandwidth votes;
- MMIO and IRQ enable;
- GMU firmware and HFI start;
- devfreq, LLC, GPU hardware initialization, ZAP, and SCM; and
- successful open, submit, or rendering.

## Pinned source and patch

- base Linux commit:
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`;
- source commit:
  `d9ac316489f4258d389d6298659d5e9c22183400`;
- source tree:
  `c796deb1cc54e942f8bb46a2c76a7199e19e5c92`;
- kernel release:
  `7.1.4-rog5-a660reg1`;
- v10 patch:
  `5eef04eb711443acaaf4295e926577f90073b8ab62414cff3d18de2272d3a152`.

Final patched-source identities:

| Source | SHA-256 |
|---|---|
| `a6xx_gmu.c` | `cc76b2865877853f5e9d9508f704d242dc35847625ce94aa4fa14f608743c1a4` |
| `msm_drv.c` | `ec7e4a1820b03b27ba51691a2b6afaa993384a467c68db353fc691adec8b5957` |
| `msm_gpu.h` | `5fa397c9fd1dade1040074ec3dbbf67258eee3a6f23ef4da30169a40b3d4393a` |
| `adreno_device.c` | `2e72b3ce7aa47fad1d5c82d6ab662e6f98895bad15876b631ecafecad0308b45` |
| `a6xx_gpu.c` | `34ba40a1de4705b471a09266c51a1b5d20f06534faea6bff70d2b0025d185ae7` |
| `a6xx_gpu.h` | `5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5` |

The patch changes only three DRM/MSM files: 33 additions in `a6xx_gmu.c`,
52 additions and one deletion in `msm_drv.c`, and four additions in
`msm_gpu.h`. `checkpatch.pl --strict` reports zero errors, warnings, and
checks.

## Test-first chain

The work preserves a fail-first history:

| Boundary | Failing test commit | Passing implementation commit |
|---|---|---|
| pinned source boundary | `ce19241` | `29f13db` |
| diagnostic patch | `a72598e` | `b373e2c` |
| deterministic build | `590de97` | `2b304ed` |

The source-boundary controls have these identities:

| Control | SHA-256 |
|---|---|
| boundary test | `a8cdc695ac4cf6f93d28273da91767d9df1d0f4d0459df8c89c745f7af00bd8b` |
| boundary verifier | `6ba90691000f9369b5fdfdbf235495f9afeba4984c11596888cc1213717d7b06` |
| patch test | `dcdba2e67ab4ace306215f691969d5a5fcb5e6c550249c83df69abd1133e5f71` |
| patch verifier | `7fff8e1c43d1230bd4a16fa9a31d472ce2c89dad50b3ccda940638bb1ab7e548` |

The patch suite reruns the accepted-v9 predecessor umbrella and rejects
twelve independent mutations: writable mode, pre-consumed open,
pre-attempted state, non-atomic attempt, non-atomic pass, wrong chip, missing
failed-get balance, asynchronous consumer rollback, decrementing the linked
CX reference, either missing suspended-state check, and a successful open.

The final hash-pinned build controls have these identities:

| Control | SHA-256 |
|---|---|
| build contract test | `2f0e9a9b4b77884dacd9a26b1522bf5c1cda06d355e0785851c6be51ea202ffd` |
| builder | `20cc3807f088a80408a3456d4a39b9b2ad8f1e16a072eec4c8f70ffa54619aea` |
| build verifier | `c8cd5867a0cf028cc9650202054e07a8b83eed0a964ef8de5eb747d0528456cd` |
| duplicate-build comparator | `a8995851cef801b21052050b5b4838f004fcdc4bb2b9528b660f88151fcb71fe` |

## Final QA correction

The first report draft repeated an unverified strict-style claim from the
pre-acceptance notes. A direct `checkpatch.pl --strict` run instead found
eight trailing-space lines in the patch envelope. Acceptance stopped.

The whitespace was removed without changing any applied C source identity.
The patch was re-pinned, both complete isolated builds were rerun from empty
outputs, and the full predecessor-to-v10 verifier was repeated. Config,
Image, ABI, module archive, and `msm.ko` remain byte-identical to the first
pair. Only `build-meta.txt` changed because it records the corrected patch
hash. The final patch now passes strict checking with zero errors, warnings,
or checks. No pre-correction metadata or log is accepted by this report.

## Two isolated builds

Build A and Build B ran concurrently in separate rootless Podman containers.
Each used:

- builder image digest
  `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`;
- Ubuntu clang 18.1.3;
- no network;
- a read-only root, repository mount, and pinned-source mount;
- a distinct private output directory;
- an executable, `nosuid`, `nodev`, size-limited 8 GiB `/tmp`;
- all Linux capabilities dropped and `no-new-privileges`;
- deterministic Kbuild identity and timestamp, `PYTHONHASHSEED=0`, and one
  `pahole` job; and
- eight compile jobs.

Both builds exited successfully and emitted:

```text
PASS Linux 7.1.4 storage-disabled A660 GMU/CX runtime-PM build
```

Both logs reached MODPOST, final MSM link, BTF generation, module
installation, deterministic archive creation, and the PASS marker. Neither
contains compiler `warning:`, `error:`, or `fatal:` diagnostics.

The private logs are not committed. Their redacted identities are:

| Log | Bytes | SHA-256 |
|---|---:|---|
| Build A | 624,428 | `308deb9314ca16a068a606e57e4dc4739b9d539d3eee26fca4806fcd4624dc05` |
| Build B | 624,428 | `b3777e060bec3f01db2b42a709842923312564926455dbb41ea89983cff29be2` |

## Accepted build identities

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| build metadata | 2,456 | `dbc7270338b3c0589863db84fa9bc2abc63a1dfcfb42f83c1394f48122c298cb` |
| `.config` | 239,424 | `d2f3a6f919c3e1abf3d10d99a77165e43de0fc4888fda338f0625bae57cb35e0` |
| `Image` | 38,214,144 | `52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db` |
| `Image.gz` | 14,048,701 | `9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307` |
| `Module.symvers` | 1,155,437 | `a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477` |
| module archive | 310,053,805 | `87e5c3bae7d5034b64aea7212be8372506bf8b28cbdca7fb1b79bb20db50b9d0` |
| `gpucc-sm8350.ko` | — | `c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563` |
| `mdt_loader.ko` | — | `001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3` |
| v10 `msm.ko` | 12,409,128 | `c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d` |

The two complete output trees are byte-identical under the comparator's
accepted-output contract. The unchanged Image proves that this diagnostic
remains module-only; the module archive differs from v8 only at `msm.ko`.

## Acceptance output

```text
PASS accepted v8 Image is unchanged
PASS GMU/CX runtime-PM MSM module differs only from its accepted v8 predecessor
PASS A660 GMU/CX runtime-PM build is exact-stack, modular, firmware-clean, BTF-bearing, archive-isolated, and offline-only
PASS two clean A660 GMU/CX runtime-PM builds are byte-identical and the GMU/CX runtime-PM MSM module differs only from its accepted v8 predecessor
PASS A660 GMU/CX runtime-PM kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, offline-only, and reproducible by contract
```

## Decision and next gate

V10 is accepted as source, patch, and deterministic build evidence only. It
remains **HOLD** for all device-facing use.

Before any live review, a separate test-first chain must add:

1. a source-pinned runtime oracle that classifies exact GMU-device and linked
   CX-supplier PM activity while rejecting GX, clocks, MMIO, IRQ, firmware,
   HFI, hardware, ZAP/SCM, storage, and retained DRM descriptors;
2. a fresh storage-free protected root and independently verified immutable
   artifact manifest;
3. a target gate, nested watchdog, strict one-shot/no-retry host runner, and
   verifier-before-state bounded server case;
4. mutation tests covering runtime counts, device identity, ordering,
   suspended state, rollback, snapshots, authorization, and cleanup; and
5. separate pre-live HOLD and attended GO reviews.

Even after those controls pass, a live cycle requires new explicit
authorization. Any authorization must be limited to one attended RAM-only
boot with immediate fallback and no retry. Flashing remains prohibited.
