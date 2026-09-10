# A660 ucode-allocation kernel — offline build acceptance

Date: 2026-07-26

Result: **PASS offline; root/gate preparation and live use remain pending**

## Outcome

The default-off, rollback-safe A660.1 ucode-allocation diagnostic compiles
against the exact accepted Linux 7.1.4 source. Two independent clean builds
are byte-identical. Relative to the accepted firmware-request-only
predecessor:

- the config, `Image`, `Image.gz`, `Module.symvers`, GPUCC module, MDT-loader
  module, and every installed module other than `msm.ko` are byte-identical;
- only `msm.ko` and the archive containing it change;
- both the predecessor `firmware_request_only` mode and the new
  `ucode_allocation_only` mode are present;
- the new MSM module has BTF and retains the exact failed-open success/failure
  markers;
- neither build tree nor module archive embeds A660 SQE, GMU, or ZAP
  firmware; and
- the accepted kernel Image remains storage-disabled and KMS-disabled.

This accepts an offline build artifact only. The phone was not contacted,
NFS was not started, no rootfs or temporary-boot package was prepared, and
nothing was flashed.

## Pinned source and patch stack

- Linux source commit:
  `d9ac316489f4258d389d6298659d5e9c22183400`;
- source tree:
  `c796deb1cc54e942f8bb46a2c76a7199e19e5c92`;
- base Linux commit:
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`;
- kernel release:
  `7.1.4-rog5-a660reg1`;
- GMU error-propagation patch:
  `0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637`;
- firmware-request-only patch:
  `3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054`;
- ucode-allocation patch:
  `6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2`.

The builder applies the exact `0012` → `0013` → `0014` stack to an archive
of the clean pinned source. All three independent source verifiers run before
compilation.

The final changed-source hashes are:

| Source | SHA-256 |
|---|---|
| `a6xx_gmu.c` | `126d1011942083ad63516de0bee1d62f18db4752199a1cbc6cfb5be3230e4ace` |
| `msm_drv.c` | `bf109068950c2e04d6121a5aea8bee7c20d7c3535a05107728e197351fc6e3c6` |
| `msm_gpu.h` | `d3312f908da1702a4f0e63b3e9aed9f77ed7fe352381c2e31647b8225e2993ec` |
| `adreno_device.c` | `0954e9cc45a948c02dbecca34d41f1343f004880a983403baa668b3c96a095c2` |
| `a6xx_gpu.c` | `34ba40a1de4705b471a09266c51a1b5d20f06534faea6bff70d2b0025d185ae7` |
| `a6xx_gpu.h` | `5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5` |

## Fail-first build contract

Fail-first commit `c1a0236` added only
`test-mainline-a660-ucode-allocation-build-contract.sh`. Before any builder
or artifact existed, it returned:

```text
FAIL missing executable A660 ucode-allocation build tool: .../build-mainline-a660-ucode-allocation-candidate.sh
```

The completed tooling is:

- `scripts/device/build-mainline-a660-ucode-allocation-candidate.sh`;
- `scripts/device/verify-mainline-a660-ucode-allocation-build.sh`;
- `scripts/device/compare-mainline-a660-ucode-allocation-builds.sh`; and
- `scripts/device/test-mainline-a660-ucode-allocation-build-contract.sh`.

The first complete verifier invocation was retained as rejected test
evidence: it compared the intentionally KMS-disabled candidate config with
the older KMS-enabled v18 dependency-audit config. The latter is an input to
the inherited dependency verifier, not the candidate's byte predecessor.
Removing that invalid comparison made the verifier compare the candidate only
with the accepted firmware-request-only build. No build output changed.

Two earlier manual invocations also failed closed because they supplied the
wrong caller inputs: the registration config instead of the pinned v18
dependency config, and a flat stock firmware directory instead of the
accepted `qcom/...` firmware tree. The final gate uses the exact accepted
inputs and hashes.

## Isolated clean builds

Build A and Build B ran concurrently in separate rootless Podman containers.
Each container used:

- builder image digest
  `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`;
- networking disabled;
- a read-only root, repository mount, and pinned-source mount;
- a distinct writable host output mapped to the canonical
  `/root/build/rog5-linux-7.1.4-a660-registration`;
- the canonical temporary source
  `/tmp/rog5-a660-registration-source`;
- a private executable, `nosuid`, `nodev`, 8 GiB `/tmp` tmpfs;
- all Linux capabilities dropped and `no-new-privileges`;
- `JOBS=8`, one BTF job, `PYTHONHASHSEED=0`, and deterministic Kbuild
  identity/timestamp; and
- Ubuntu clang 18.1.3.

Build A ran from 15:38:20 to 16:02:05 CEST. Build B ran from 15:38:29 to
16:02:07 CEST. Both exited zero. A case-insensitive scan of each complete log
found zero compiler `warning:`, `error:`, or `fatal:` lines.

The ignored local evidence files are:

| Evidence | Size | SHA-256 |
|---|---:|---|
| Build A container log | 623,967 | `f5ea02ea67201ee83f2c4ef623fa55e5e29a7c58644bf9823ff5628ead9d8f0d` |
| Build B container log | 623,967 | `cd20f5aa7cb029b69737855d8b3c532d0e8b46b9ef0bc23ea7f465e50d2f55c4` |
| Container inspect JSON | 27,381 | `0b481c0d1d5ce9ba835249bc2fc7de737290ca1399a379dcbb8c2602af9079cf` |

The stopped containers were removed only after their logs and inspect state
were captured. Both complete build trees remain under ignored `artifacts/`.
The pinned source worktree remains clean.

## Accepted byte-identical outputs

| Output | Size | SHA-256 |
|---|---:|---|
| `.config` | 239,424 | `d2f3a6f919c3e1abf3d10d99a77165e43de0fc4888fda338f0625bae57cb35e0` |
| `arch/arm64/boot/Image` | 38,214,144 | `52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db` |
| `arch/arm64/boot/Image.gz` | 14,048,701 | `9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307` |
| `modules.tar.gz` | 310,053,097 | `ad3c4b441db6d2701e0e6bb945c1a4bf52d284e209873cb4b9250014386da680` |
| `Module.symvers` | 1,155,437 | `a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477` |
| `drivers/gpu/drm/msm/msm.ko` | 12,388,848 | `fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45` |
| `drivers/clk/qcom/gpucc-sm8350.ko` | 307,632 | `c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563` |
| `drivers/soc/qcom/mdt_loader.ko` | 277,992 | `001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3` |
| `build-meta.txt` | 1,996 | `9fced0679b2fa0a4a434fba7ff4b6e33ded021d7376e19c08dd09926689b8654` |

The accepted firmware-request-only predecessor MSM module is
`eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082`.
After extracting both module archives, verifying the canonical build-link
target, removing only the MSM payload and those links, and recursively
comparing the rest, every other archive entry is identical.

## Module contract

`modinfo` proves exact release
`7.1.4-rog5-a660reg1 SMP preempt mod_unload aarch64` and both read-only
diagnostic parameters:

```text
firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)
ucode_allocation_only:Allocate and roll back exact A660 ucode once before GPU power (bool)
```

The final module retains all four bounded markers:

```text
A660 firmware-only passed; reject open
A660 firmware-only failed: %d
A660 ucode-allocation-only passed and rolled back; reject open
A660 ucode-allocation-only failed: %d
```

The verifier also requires a `.BTF` section, exact predecessor config/Image
and ABI hashes, exact unchanged GPUCC/MDT hashes, no embedded A660 firmware,
and a module archive that differs only at `msm.ko`.

## Final gates

Both hard-pinned build verifiers pass without
`ALLOW_UNPINNED_BUILD`. The combined contract reports:

```text
PASS accepted firmware-only Image is unchanged; ucode-allocation MSM module differs exactly; config, ABI, every other module, storage exclusion, and zero embedded firmware remain accepted
PASS two clean A660 ucode-allocation builds are byte-identical and the ucode-allocation MSM module differs only from its accepted firmware-only predecessor
PASS A660 ucode-allocation kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, and reproducible by contract
```

All four build scripts pass POSIX shell syntax, ShellCheck 0.11.0, and
`git diff --check`.

## Decision

The exact kernel/module build is accepted as the predecessor for a new
offline root and watchdog-gate review. It is not accepted for the phone.

Next: fail-first test a fresh independently versioned RAM-only/NFS-root
export, replace only the accepted MSM module, stage exact SQE/GMU firmware
while keeping ZAP absent, add map/unmap and surviving-state evidence, and
reproduce the complete temporary-boot package. Only a later separately
reviewed checkpoint may decide whether one attended live cycle is safe.
