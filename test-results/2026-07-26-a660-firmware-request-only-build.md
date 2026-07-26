# A660 SQE/GMU request-only kernel — offline build acceptance

Date: 2026-07-26

Result: **the default-off, one-shot A660 firmware-request-only diagnostic
patch compiles reproducibly against the exact accepted Linux 7.1.4 source,
and two independent clean builds are byte-identical**. The kernel Image,
configuration, ABI, GPUCC module, MDT-loader module, and every module other
than `msm.ko` remain byte-for-byte equal to the accepted registration build.
The changed MSM module requests only the exact A660 SQE and GMU catalog
entries, then rejects the first DRM open before ucode, runtime power, GPU
hardware initialization, GMU/HFI startup, or ZAP/SCM authentication.

This is an offline kernel acceptance only. At this build checkpoint no
firmware export, NFS root, staging archive, wrapper, temporary-boot package,
or live v4 candidate had been accepted. The phone was not contacted, NFS
stayed inactive, and nothing was flashed.

## Exact boundary

The accepted inputs are:

- Linux source commit `d9ac316489f4258d389d6298659d5e9c22183400`,
  tree `c796deb1cc54e942f8bb46a2c76a7199e19e5c92`;
- kernel release `7.1.4-rog5-a660reg1`;
- the accepted registration config and build;
- GMU error-propagation patch SHA-256
  `0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637`;
- request-only patch SHA-256
  `3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054`;
- accepted registration-v3 live report SHA-256
  `2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79`;
  and
- accepted registration-v3 marker SHA-256
  `8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f`.

The request-only patch adds a mode-`0400` module parameter that is false by
default, an atomic one-attempt guard, and an exact A660.1 helper. The helper
calls only `adreno_load_fw()`. Success emits the bounded marker
`A660 firmware-only passed; reject open` and returns `EUCLEAN`; request
failure returns the real error; a second attempted open returns `EALREADY`.
The six source mutations remain rejected, and strict `checkpatch.pl` reports
zero errors, warnings, or checks.

The patched source hashes are:

| Source | SHA-256 |
|---|---|
| `drivers/gpu/drm/msm/msm_drv.c` | `c350e28c18ca723372fc044240a69b452b3698ce57df269a2dad0ad9e2cb569e` |
| `drivers/gpu/drm/msm/msm_gpu.h` | `431f78761bbbfe92eab44f685aba653c6e05b54f140fd24fef1358667f05a6c7` |
| `drivers/gpu/drm/msm/adreno/adreno_device.c` | `3654f703a3930add3c131e2bc77453fd1bc506a374075168a5ddbcd66f558379` |
| `drivers/gpu/drm/msm/adreno/a6xx_gmu.c` | `126d1011942083ad63516de0bee1d62f18db4752199a1cbc6cfb5be3230e4ace` |

## Fail-first and rejected build evidence

Commit `555e179b0bbd4b20465ef2929865863dc217c6c2` records the missing-build-tool
failure before the builder, verifier, and comparator existed. The completed
tooling is:

- `scripts/device/build-mainline-a660-firmware-request-only-candidate.sh`;
- `scripts/device/verify-mainline-a660-firmware-request-only-build.sh`;
- `scripts/device/compare-mainline-a660-firmware-request-only-builds.sh`; and
- `scripts/device/test-mainline-a660-firmware-request-only-build-contract.sh`.

Two later failures were retained as evidence rather than accepted:

1. The first complete build used
   `/tmp/rog5-a660-firmware-request-only-source`. Kernel/BTF debug paths made
   that noncanonical source location observable in otherwise unrelated
   outputs. Its Image SHA-256 was
   `fef2c4bb1c2dd64e47958c1de7c05f1cd264ab2cd20a1fb2a7ca0660f7b91add`,
   GPUCC was
   `cefa63f834c96207185c9cb56ce29633e65cc6cb793627c8f75402d1491c696a`,
   MDT-loader was
   `2aa479355582a67be80ebe4b133fd2f1e2edf3d748124a8d2ece34818c684399`,
   and MSM was
   `539121d87068582e2d24bcae8ffc56ebd7160633f2247cadd12e0113d586303c`.
   The verifier rejected it at the unchanged-Image boundary. The builder now
   pins `/tmp/rog5-a660-registration-source`, matching the accepted build.
2. A canonical-path rebuild reached the exact accepted Image and intended MSM
   hashes, but its interactive execution session delivered `TERM` before
   `modules_install`. The old cleanup trap removed the temporary source and
   then let the script continue. The incomplete output has no archive or
   metadata and was rejected. Fail-first signal tests now require explicit
   `INT=130` and `TERM=143` exits before the `EXIT` cleanup runs.

The full rejected trees remain under ignored local `artifacts/` paths for
inspection. Neither failure changed the pinned source or contacted the phone.

The first complete-verifier run also exposed a test-only host permission
assumption: recursive `diff` followed the archive's canonical
`/root/build/...` symlink. A fail-first regression now requires both archives
to carry the same exact link target, removes those extracted links, and only
then recursively compares payloads. No build output changed for this fix.

## Two isolated clean builds

Build A and Build B ran concurrently from empty, distinct host output
directories. Each rootless Podman container had:

- image digest
  `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`;
- networking disabled;
- a read-only container root;
- read-only repository and pinned-source mounts;
- a distinct writable output mount;
- a private 8 GiB `/tmp` tmpfs;
- `JOBS=8`, deterministic build identity/timestamp, `PYTHONHASHSEED=0`, and
  one BTF job; and
- Ubuntu clang 18.1.3.

Build A ran from 12:47:23 to 13:09:05 CEST; Build B ran from 12:49:18 to
13:11:00 CEST. Both exited zero and their complete logs contain no compiler
warning, error, or fatal line. The stopped containers were removed only after
their logs, state, metadata, and host artifacts were captured.

## Accepted byte-identical outputs

All nine outputs below are byte-identical between clean Build A and Build B
and are now hard-pinned by the verifier:

| Output | Size | SHA-256 |
|---|---:|---|
| `.config` | 239,424 | `d2f3a6f919c3e1abf3d10d99a77165e43de0fc4888fda338f0625bae57cb35e0` |
| `arch/arm64/boot/Image` | 38,214,144 | `52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db` |
| `arch/arm64/boot/Image.gz` | 14,048,701 | `9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307` |
| `modules.tar.gz` | 310,066,113 | `04149f41648f12925a6f04261eed96bfecdd6174a10462c82c36213fef0d1bc9` |
| `Module.symvers` | 1,155,437 | `a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477` |
| `drivers/gpu/drm/msm/msm.ko` | 12,377,320 | `eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082` |
| `drivers/clk/qcom/gpucc-sm8350.ko` | 307,632 | `c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563` |
| `drivers/soc/qcom/mdt_loader.ko` | 277,992 | `001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3` |
| `build-meta.txt` | 1,732 | `1cf2ea81cfc836f852827a8e0dbe8d8803c288a405f6ae66625de5dca7e51824` |

The config, Image, Image.gz, Module.symvers, GPUCC, and MDT-loader hashes are
exactly the accepted registration values. After extracting both module
archives, removing the one expected MSM payload and comparing the canonical
build-link target separately, every remaining entry is identical. Neither
archive nor either build tree contains SQE, GMU, or ZAP firmware.

The final verifier output for each build is:

```text
PASS accepted registration Image is unchanged; firmware-only MSM module differs exactly; config, ABI, every other module, storage exclusion, and zero embedded firmware remain accepted
PASS A660 firmware-request-only kernel build is exact-patch, unchanged-Image, modular, firmware-clean, and reproducible by contract
```

The independent comparator reports:

```text
PASS two clean A660 firmware-request-only builds are byte-identical and the firmware-only MSM module differs only from its accepted registration predecessor
PASS A660 firmware-request-only kernel build is exact-patch, unchanged-Image, modular, firmware-clean, and reproducible by contract
```

All four build scripts pass POSIX shell syntax, ShellCheck 0.11.0, and
`git diff --check`. The pinned source worktree remains clean.

## Subsequent boundary

The next permissible offline work was to create and independently verify a
new root-owned, versioned export derived from the accepted registration
baseline; replace only `msm.ko`; install exact SQE and GMU files mode `0644`;
keep ZAP absent; add a one-open AArch64 helper; and build a source-locked
watchdog gate. That work subsequently passed, including exact revalidation of
the unchanged DT, staging archive, ASUS wrapper, and AVB temporary-boot image;
see the
[request-only v4 offline report](2026-07-26-a660-firmware-request-only-v4-offline.md).

Nothing in this build report alone authorizes a live v4 cycle. No live v4
cycle had run at the later offline checkpoint.
