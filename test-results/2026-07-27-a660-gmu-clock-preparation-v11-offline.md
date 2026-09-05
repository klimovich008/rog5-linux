# A660 GMU clock preparation v11 — offline build acceptance

Date: 2026-07-27

Result: **PASS offline; HOLD for runtime controls, protected root, and live
use**

## Outcome

The separately versioned v11 diagnostic passes its pinned-source boundary,
strict patch check, eighteen hostile patch mutations, two complete isolated
Linux 7.1.4 builds, exact-v10 predecessor comparison, and final hash-pinned
build contract.

V11 balances the accepted v10 GMU/CX transition, takes and balances the GX
runtime-PM reference, captures the original core and hub rates, programs the
normal 200 MHz and 150 MHz rates, prepares and enables all seven SM8350 GMU
clocks, and then reverses every operation. It requires GX, GMU, and linked CX
to be runtime-suspended before marking the diagnostic passed. The deliberate
DRM open failure remains above secure initialization, MMIO, IRQ enable,
firmware start, HFI, hardware initialization, ZAP, and SCM.

A separate GX-only tier was deliberately skipped. The pinned SM8350 GPUCC
source assigns `gdsc_gx_do_nothing_enable` as the GX power-on callback, and
that callback does not toggle the GDSC. A GX-only candidate would add
bookkeeping without crossing a new hardware boundary. V11 therefore keeps
the GX reference balanced and advances to the first meaningful next boundary:
GMU rate programming and seven-clock preparation.

Relative to accepted v10:

- `.config`, `Image`, `Image.gz`, `Module.symvers`, `gpucc-sm8350.ko`, and
  `mdt_loader.ko` are byte-identical;
- `msm.ko` is the only changed installed module;
- the module archive has the same file list and symlink targets, with
  `msm.ko` as its sole changed regular file;
- DRM/MSM and GPUCC remain modular, KMS remains disabled, and storage remains
  excluded;
- the new module contains BTF and every predecessor diagnostic mode; and
- neither build tree nor module archive contains A660 SQE, GMU, or ZAP
  firmware.

This is an offline acceptance only. The phone was not contacted for this
checkpoint, NFS/RPC was not started, no export or protected v11 root was
created, no boot package was prepared, and nothing was booted, loaded, or
flashed.

## Diagnostic boundary

The source and patch contracts require this exact sequence:

1. accept only exact A660.1 (`0x06060001`) with exactly seven clocks and valid
   core, hub, CX, and GX handles;
2. require GMU, linked CX, and GX to begin runtime-suspended;
3. atomically move the diagnostic from unused to attempted;
4. take the GMU/CX runtime-PM reference and balance a failed get with
   `pm_runtime_put_noidle(gmu->dev)`;
5. take the GX runtime-PM reference and balance a failed get with
   `pm_runtime_put_noidle(gmu->gxpd)`;
6. capture the original core and hub rates;
7. set and verify 200 MHz core and 150 MHz hub rates;
8. prepare and enable all seven GMU clocks with the kernel bulk API;
9. disable and unprepare all seven clocks;
10. restore and verify both original rates;
11. synchronously suspend GX and GMU, settle the linked CX supplier, and
    require all three devices to report runtime-suspended;
12. atomically mark the diagnostic passed; and
13. return `EUCLEAN`, reuse the accepted GPU-load rollback, and reject the
    DRM open.

Only the completely reversed path reaches the passed state. Wrong chip,
wrong clock graph, mixed diagnostic mode, a second attempt, failed runtime-PM
or clock operation, failed rate restoration, unsuspended domain, surviving
GPU object, failed load rollback, or successful open fails closed.

## Pinned source and patch

- base Linux commit:
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`;
- source commit:
  `d9ac316489f4258d389d6298659d5e9c22183400`;
- source tree:
  `c796deb1cc54e942f8bb46a2c76a7199e19e5c92`;
- kernel release:
  `7.1.4-rog5-a660reg1`;
- v11 patch:
  `e7512f8e0589187bddb93f53d83a31b415ce779b3093623fad5515210cf1258b`.

Final patched-source identities:

| Source | SHA-256 |
|---|---|
| `a6xx_gmu.c` | `176391492beacf6b08a0e5d9f45bec7147809779da3a1a2f511cccaebf548c17` |
| `msm_drv.c` | `44b9d1281819a3812711786d488fac8ac727dc24f079c6d0e886ee2cb5a60c14` |
| `msm_gpu.h` | `9065053f0ed68a0a200270aa42548cb021e6e26c035dcb0c4ce53341d3c0bfca` |
| `adreno_device.c` | `2e72b3ce7aa47fad1d5c82d6ab662e6f98895bad15876b631ecafecad0308b45` |
| `a6xx_gpu.c` | `34ba40a1de4705b471a09266c51a1b5d20f06534faea6bff70d2b0025d185ae7` |
| `a6xx_gpu.h` | `5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5` |

The patch changes only three DRM/MSM files: 126 additions in `a6xx_gmu.c`,
53 additions and one deletion in `msm_drv.c`, and four additions in
`msm_gpu.h`. `checkpatch.pl --strict` reports zero errors, warnings, and
checks.

## Test-first chain

The fail-first tests were committed before their implementation:

| Boundary | Failing test commit | Passing implementation commit |
|---|---|---|
| pinned source and patch | `56dfc6e` | `67d918d` |
| deterministic build | `14ed36a` | `67d918d` |

The final controls have these identities:

| Control | SHA-256 |
|---|---|
| source-boundary test | `0694b93ae8b456107c97ed880106bd5f2d12f50c4525c080d442d3e443bcb46e` |
| source-boundary verifier | `844c7cdc1ab21078ff345474e9cbea2e8bbeb8606d55211df3ca7a62a9e5a4c8` |
| patch test | `de9d7f6142b0ca1d43eb86704bae9c6b55b74f004e0701a0de18276faa551bc9` |
| patch verifier | `d8163dba7ca18b92631830c8d272ba9b86df14e7b3e11d2f9e8cd4cdab7aebb6` |
| build-contract test | `48fd1f9cd5ee73ae4b817e49c46bd3edb0c692436df2dd784cafaa59262b6467` |
| builder | `1d288e49685889989f98ed765301990dd67a3d341ecabb07367fc813cac2c01a` |
| build verifier | `a2528b1f8d341722fb3bcd0e4a9a02bfd9655352ee9d59d220f176aa65a344f0` |
| duplicate-build comparator | `8a46b7c0b94f600d0f204bf324396223b6fc3e3842460281f549b18f93fc8f79` |

The patch suite rejects eighteen independent mutations: writable mode,
pre-consumed open, pre-attempted state, wrong chip, wrong clock count,
missing clock validation, either missing failed-get balance, either wrong
rate, missing clock disable, either missing rate restoration, asynchronous GX
or GMU rollback, missing linked-CX settle, missing GX suspended-state check,
and a successful open.

## Two isolated builds

Build A and Build B ran concurrently from empty output directories in
separate rootless Podman containers. Each used:

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

Both builds exited successfully. Both logs reached MODPOST, final MSM link,
BTF generation, module installation, deterministic archive creation, and the
PASS marker. Neither contains compiler `warning:`, `error:`, or `fatal:`
diagnostics.

The private logs are not committed. Their redacted identities are:

| Log | Bytes | SHA-256 |
|---|---:|---|
| Build A | 624,804 | `856c2a297a30af8c29bed926c6ef1abfe46041834140b1d5d491f740deef9e4a` |
| Build B | 624,804 | `996b5fb885829d249c327c711ff81db8db19cdd9b4640f00cd51b6ea2fc81f47` |

## Accepted build identities

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| build metadata | 2,828 | `5e929fef4ec6422c8aae7f7e97d98a852769c8643aadd6069655f0471056338a` |
| `.config` | 239,424 | `d2f3a6f919c3e1abf3d10d99a77165e43de0fc4888fda338f0625bae57cb35e0` |
| `Image` | 38,214,144 | `52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db` |
| `Image.gz` | 14,048,701 | `9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307` |
| `Module.symvers` | 1,155,437 | `a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477` |
| module archive | 310,065,263 | `86a163a4d065ffb66cf5befc10fdb045b955d8e227e576169a40c2ac129ad94b` |
| `gpucc-sm8350.ko` | 307,632 | `c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563` |
| `mdt_loader.ko` | 277,992 | `001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3` |
| v11 `msm.ko` | 12,424,536 | `3ca8b7996a94d9a57b3c17f26bd5be4df948ee176c6faa58b76900dbb3f47251` |

The two complete output trees are byte-identical under the comparator's
accepted-output contract. The unchanged Image proves that the diagnostic
remains module-only; the module archive differs from v10 only at `msm.ko`.

## Acceptance output

```text
PASS accepted v10 Image is unchanged
PASS clock-preparation MSM module differs only from its accepted v10 predecessor
PASS A660 GMU clock-preparation build is exact-stack, modular, firmware-clean, BTF-bearing, archive-isolated, and offline-only
PASS two clean A660 GMU clock-preparation builds are byte-identical and the clock-preparation MSM module differs only from its accepted v10 predecessor
PASS A660 GMU clock-preparation kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, offline-only, and reproducible by contract
```

## Decision and next gate

V11 is accepted as source, patch, and deterministic build evidence only. It
is not a bootable or runnable project tier.

V10 remains the next live GPU step. V11 must not be loaded, exported, added
to the bounded server, packaged for boot, or tested on hardware before:

1. the separately authorized one-cycle v10 diagnostic is completed and
   consumed;
2. v11 receives a source-pinned runtime oracle that distinguishes GMU, CX,
   GX, rate, and all seven clock operations while rejecting every later
   resource;
3. a fresh storage-free protected root and immutable manifest are built;
4. a target gate, nested watchdog, strict one-shot/no-retry runner, and
   verifier-before-state bounded server case pass mutation testing; and
5. separate pre-live HOLD and attended GO reviews pass.

This checkpoint does not prove that any clock toggles successfully on the
phone, that the GMU starts, or that GPU acceleration, rendering, display, or
suspend works. A future live cycle still requires fresh explicit
authorization. Flashing remains prohibited.
