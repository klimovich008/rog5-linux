# A660 GMU resume-entry v8 — offline build acceptance

Date: 2026-07-26

Result: **PASS offline; HOLD for root/export/gate preparation and live use**

## Outcome

The default-off, exact-A660.1, one-shot GMU resume-entry diagnostic compiles
from the pinned Linux 7.1.4 source and accepted patch stack. Two independent
clean builds are byte-identical.

Relative to the accepted and consumed v7 ucode-allocation predecessor:

- `.config`, `Image`, `Image.gz`, `Module.symvers`, `gpucc-sm8350.ko`, and
  `mdt_loader.ko` are byte-identical;
- only `msm.ko` differs among installed module payloads;
- both deterministic module archives have the same file list and symlink
  targets, with `msm.ko` as their sole changed regular file;
- the new MSM module retains the accepted firmware-request-only and
  ucode-allocation-only modes and adds the read-only
  `gmu_resume_entry_only` mode;
- all required entry, rollback, and failed-open markers are present;
- the MSM module has BTF and the exact accepted ABI/vermagic;
- neither build tree nor module archive embeds A660 SQE, GMU, or ZAP
  firmware; and
- KMS and phone storage remain excluded from this diagnostic kernel.

This is an offline build acceptance only. The phone was not contacted, no
NFS export or candidate root was created, no temporary boot package was
prepared, and nothing was flashed.

## Safety boundary

The source and mutation suites prove that one deliberate first open can
reach `a6xx_gmu_resume()` after the initialization guard and return
`EUCLEAN` before:

- `gmu->hung` changes;
- GMU CX or GX runtime-PM gets;
- clock rate changes or clock enable;
- secure setup, bandwidth votes, MMIO, or IRQ enable;
- GMU firmware start or HFI start;
- GPU hardware initialization, ZAP/SCM, submit, or render.

The normal outer runtime-PM failure path balances its attempted get and
disables runtime PM. The open-side rollback then reuses the live-accepted v7
cleanup for all ucode objects, IOMMU mappings, CPU vmaps, and firmware
references. A missed entry marker, surviving GPU, wrong chip, mixed mode,
second attempt, cleanup failure, or successful open fails closed.

## Pinned source and patch stack

- base Linux commit:
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`;
- source commit:
  `d9ac316489f4258d389d6298659d5e9c22183400`;
- source tree:
  `c796deb1cc54e942f8bb46a2c76a7199e19e5c92`;
- kernel release:
  `7.1.4-rog5-a660reg1`;
- `0012` GMU error propagation:
  `0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637`;
- `0013` firmware-request-only diagnostic:
  `3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054`;
- `0014` ucode-allocation diagnostic:
  `6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2`;
- `0015` GMU resume-entry diagnostic:
  `a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051`.

Final changed-source hashes:

| Source | SHA-256 |
|---|---|
| `a6xx_gmu.c` | `e42eb79a417a6eace46358f5e2666b87dd4138eb8e1af843789b2e99b84fd395` |
| `msm_drv.c` | `43e97deb263e5f845b95249612433ca183d4fd7f55be75e23be93b2a0bc83d26` |
| `msm_gpu.h` | `32dd6be7c82e25cb44377717ffb97cd941a99269c6bf977a2eb49454c0d3cfb4` |
| `adreno_device.c` | `2e72b3ce7aa47fad1d5c82d6ab662e6f98895bad15876b631ecafecad0308b45` |
| `a6xx_gpu.c` | `34ba40a1de4705b471a09266c51a1b5d20f06534faea6bff70d2b0025d185ae7` |
| `a6xx_gpu.h` | `5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5` |

## Test-first build contract

Fail-first commit `868ce29` added only
`test-mainline-a660-gmu-resume-entry-build-contract.sh`. Before the builder,
verifier, or comparator existed, it returned:

```text
FAIL missing executable A660 GMU resume-entry build tool: .../build-mainline-a660-gmu-resume-entry-candidate.sh
```

The completed tooling is:

- `scripts/device/build-mainline-a660-gmu-resume-entry-candidate.sh`;
- `scripts/device/verify-mainline-a660-gmu-resume-entry-build.sh`;
- `scripts/device/compare-mainline-a660-gmu-resume-entry-builds.sh`; and
- `scripts/device/test-mainline-a660-gmu-resume-entry-build-contract.sh`.

The contract rejects missing tools, syntax errors, unpinned source/patches or
outputs, noncanonical build paths, dirty source, nonempty output, changed
config/ABI/Image/predecessor modules, missing BTF/parameters/markers,
embedded firmware, archive drift beyond `msm.ko`, identical predecessor and
candidate MSM modules, non-distinct duplicate builds, and persistent-write
commands.

## Fail-closed preflight corrections

Two duplicate attempts stopped before compilation:

1. the minimal kernel container intentionally lacked host-side `ssh`, while
   the accepted v7 umbrella includes static host-runner tests;
2. an unchanged `a6xx_gpu.h` hash was mistyped in the new builder.

The v7 umbrella was separated into an explicit host prerequisite. The
container still verifies its pinned live report and source boundary, without
expanding the build image. The source hash typo was corrected to the
accepted value and added to the static build contract. Fresh empty output
directories were used after both corrections; no failed output was accepted.

## Two isolated clean builds

Build A and Build B ran concurrently in separate rootless Podman containers.
Each used:

- builder image digest
  `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`;
- Ubuntu clang 18.1.3;
- networking disabled;
- a read-only container root, repository mount, and pinned-source mount;
- a distinct writable output mounted at the canonical build path;
- an executable, `nosuid`, `nodev`, size-limited private `/tmp`;
- all Linux capabilities dropped and `no-new-privileges`;
- deterministic Kbuild identity/timestamp, `PYTHONHASHSEED=0`, and one
  `pahole` job; and
- eight compile jobs.

Both complete logs reached MODPOST, final MSM link, BTF generation, module
installation, deterministic archive creation, and the builder PASS marker.
Neither log contains a compiler `warning:`, `error:`, or `fatal:` diagnostic.

## Accepted hashes

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| build metadata | — | `116f702a4605363c153cb35a908b1b1031f4e430478993394fe0fdc230db42bc` |
| `.config` | — | `d2f3a6f919c3e1abf3d10d99a77165e43de0fc4888fda338f0625bae57cb35e0` |
| `Image` | 38,214,144 | `52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db` |
| `Image.gz` | 14,048,701 | `9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307` |
| `Module.symvers` | — | `a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477` |
| module archive | 310,066,644 | `38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7` |
| `gpucc-sm8350.ko` | — | `c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563` |
| `mdt_loader.ko` | — | `001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3` |
| v8 `msm.ko` | 12,397,072 | `b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861` |
| accepted v7 `msm.ko` | — | `fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45` |

The MSM vermagic is exactly:

```text
7.1.4-rog5-a660reg1 SMP preempt mod_unload aarch64
```

## Full acceptance output

```text
PASS accepted v7 Image is unchanged
PASS resume-entry MSM module differs only from its accepted v7 predecessor
PASS A660 GMU resume-entry build is exact-stack, modular, firmware-clean, BTF-bearing, and archive-isolated
PASS two clean A660 GMU resume-entry builds are byte-identical and the resume-entry MSM module differs only from its accepted v7 predecessor
PASS A660 GMU resume-entry kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, and reproducible by contract
```

## Decision

The v8 kernel build is accepted offline. Live use remains **HOLD** until a
fresh storage-free network root, default-off server/export case, bounded
one-shot gate, fallback proof, complete bundle verifier, and separate
pre-live HOLD/GO review all pass. Any later authorization permits at most one
attended RAM-only transition, immediate fallback, and permanent v8
consumption. It does not authorize flashing.
