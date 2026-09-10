# Stable-recovery wrapper configuration slimming

## Purpose and status

The ASUS 5.4 wrapper exists only to start the stable recovery initramfs. It
does not need the complete Android/GKI, display, GPU, audio, radio, debug, or
general-purpose filesystem configuration inherited from the working vendor
baseline.

`rog5-stable-wrapper-slim-v1` is a separately identified, compile-only
experiment. It does not replace the accepted stable-recovery cache, the
corrected headless candidate, or any live allowlist entry:

- `status=experiment`
- `authority=none`
- no production private key
- no phone contact
- no boot or flash permission

The policy is split into:

- [`rog5-stable-wrapper-slim-v1.fragment`](../configs/kernel/rog5-stable-wrapper-slim-v1.fragment),
  the reviewed Kconfig delta;
- [`rog5-stable-wrapper-slim-v1.json`](../configs/kernel/rog5-stable-wrapper-slim-v1.json),
  the identity, required-capability, forbidden-symbol, and minimum-reduction
  contract;
- [`verify-stable-wrapper-slim-config.py`](../scripts/host/verify-stable-wrapper-slim-config.py),
  the fail-closed baseline/candidate auditor;
- [`generate-stable-wrapper-slim-config.sh`](../scripts/host/generate-stable-wrapper-slim-config.sh),
  the network-disabled generator;
- [`build-asus-kexec-stage-slim.sh`](../scripts/device/build-asus-kexec-stage-slim.sh),
  the source-sealed compile-only builder.

## Retained recovery boundary

The candidate keeps the wrapper's boot-critical CPU, RAM, clock, regulator,
interconnect, UFS, USB gadget, kexec, ramoops/pstore, thermal, charging,
reboot, and PMIC power-key paths. USB DWC3 is gadget-only, ConfigFS exposes
only ACM and NCM functions, and loadable modules are disabled.

The candidate removes Android/GKI compatibility layers, DRM/display/GPU,
sound, wireless/radio, PCI, optional HID devices, netfilter, tracing/debug
families, and ordinary root filesystems. This is wrapper reduction, not the
target server-kernel configuration.

Some apparently unrelated cores remain because this ASUS tree has
non-upstream dependency behavior:

- `INPUT_QPNP_POWER_ON` remains built in because disabling it activates an
  ASUS header fallback that duplicates `qpnp_pon_wd_config` in
  `gpio_keys` and `msm-poweroff`.
- HID core and USB HID remain because ASUS accessory/gamepad objects are
  compiled unconditionally by vendor Makefiles. Optional HID device drivers
  remain disabled.
- the minimal media/V4L2 core remains because the video techpack is also
  compiled unconditionally. Camera device/subdriver, radio, DVB, SDR, CEC,
  USB-media, and CVP feature families remain disabled.
- ASUS Auralight accessory drivers remain disabled; converting their
  baseline module state into built-ins produced duplicate `apply_state` and
  `mode2_state` definitions.
- disabling modules promotes eight other baseline modules to built-ins:
  `ASUS_GLOBAL_VAR`, `EDAC_QCOM`, both hall-sensor drivers, `MSM_RDBG`,
  `QCOM_LLCC_PERFMON`, `SLIMBUS`, and `SLIMBUS_MSM_NGD`. They are an explicit
  allowlist and required-config set; any ninth promotion fails the audit.

These compatibility cores do not claim working HID, camera, video, GPU, or
desktop functionality. Removing the unconditional vendor objects is a future
source-level cleanup and must receive its own compile and structural gates.
The eight module promotions are also source-audit debt; explicit policy makes
them visible rather than silently treating `m` and `y` as equivalent.

The wrapper deliberately has no SELinux policy or audit subsystem because the
fixed initramfs boots with SELinux disabled and exposes no login or shell.
That decision applies only to this recovery wrapper, not the target server
kernel. The hardening floor requires KASLR, strict kernel RWX, init-on-allocate,
and the security framework while disabling `debugfs` and `/dev/mem`.
`MAGIC_SYSRQ` retains the accepted full mask for attended physical
postmortem/UART recovery:
`CONFIG_MAGIC_SYSRQ_DEFAULT_ENABLE=0x1` uses Linux's special all-functions
sentinel. It is explicit policy and must be reconsidered before live
promotion.

## Fail-closed build contract

The generator pins the accepted baseline, fragment, profile, auditor,
source-seal tool, builder image, and ASUS source tree. The low-level builder
pins the accepted baseline, candidate, profile, auditor, source-seal tool,
initramfs, and source tree; it runs inside the caller-selected builder image
and records the actual compiler version. Every build recomputes the portable
79,030-entry source seal and requires:

```text
tree_format=rog5-kernel-source-tree-v1
tree_sha256=592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a
```

The builder also requires an empty output, fixed build user/host/version/time,
the pinned Clang 18 environment, the exact post-`olddefconfig` configuration,
a second hash of the staged initramfs, and
`status=experiment`/`authority=none` metadata. It contains no ADB, fastboot,
SSH, privilege, or physical-storage transport.

Seven hostile auditor tests plus one positive test reject changed
requirements, reduced CPU count,
forbidden or unreviewed additions, insufficient reductions, authority/status
inflation, changed identities, non-canonical or duplicate input, unreviewed
module-to-built-in promotion, and symlinked inputs. Each negative test checks
the exact policy error so an earlier hash failure cannot mask an untested
branch. Static host and builder contracts bind the safety and reproducibility
controls and compute the profile/fragment/auditor/source-seal hashes rather
than only grepping their literals.

## Offline result

The exact evidence is recorded in the
[2026-07-30 offline report](../test-results/2026-07-30-stable-wrapper-config-slimming-offline.md).
Relative to the accepted wrapper configuration:

| Measure | Accepted baseline | Slim v1 | Reduction |
|---|---:|---:|---:|
| built-in (`=y`) symbols | 1,880 | 1,279 | 601 |
| active (`=y` or `=m`) symbols | 1,934 | 1,279 | 655 |
| configuration lines | 6,836 | 4,985 | 1,851 |
| raw `Image` bytes | 50,498,048 | 34,787,840 | 15,710,208 (31.11%) |

Two distinct initially empty host build trees were mounted at the same
normalized container path and produced identical `.config`, `Image`, and
path-stable build metadata. Each Image was independently inserted into the
accepted Android
boot-header-v3 template with the exact stable-recovery initramfs. The raw
images and 100,663,296-byte unsigned AVB wrappers match byte-for-byte; unpack
and AVB verification recover the exact kernel and ramdisk and report
`Algorithm: NONE`, partition `boot`.

## Reproduction and promotion

Generate the reviewed candidate in a new ignored directory:

```sh
scripts/host/generate-stable-wrapper-slim-config.sh \
  artifacts/recovery-stage-v18/config-5.4.210-kexec-stage-builtin-recovery \
  build/stable-wrapper-slim-v1-config
```

Run the focused policy tests before compiling:

```sh
python3 scripts/host/test-stable-wrapper-slim-config.py
scripts/host/test-stable-wrapper-slim-config-contract.sh
scripts/device/test-asus-kexec-stage-slim-build-contract.sh
```

The low-level builder deliberately requires caller-supplied, hash-pinned
baseline, candidate, initramfs, and empty output paths. A release proof must
run it twice in separate clean output trees and repeat the boot-v3/AVB
unpack-and-verify gate.

No live use follows automatically. Promotion may use the central standing
authorization only after a separately reviewed temporary-boot allowlist
change and an attended recovery-only test that preserves the installed
fallback. A compile or structural pass never authorizes `fastboot boot`,
flashing, signing, or a target-kernel experiment.
