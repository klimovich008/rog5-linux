# Stable-recovery wrapper configuration slimming — offline result

- Date: 2026-07-30
- Result: **PASS — compile and structural evidence only**
- State: `status=experiment`, `authority=none`, unbooted

## Scope

This run reduced the broad accepted ASUS 5.4 stable-recovery wrapper
configuration without changing the accepted cached wrapper or a live
headless-core candidate. It used the retained ASUS source volume and pinned
network-disabled kernel-builder container. It did not contact the phone, use
a signing/private key, run ADB/fastboot/SSH, or access physical storage.

## Bound inputs

| Input | SHA-256 or identity |
|---|---|
| accepted baseline config | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| slim fragment | `a302ef08910b24a638da63230e6496f3c93a2828baa3ed6e51d7cbc393916231` |
| slim policy profile | `3fb9eaf91f32cf01c09cc8653feb4a52c421f4a95bdd8e022576211ad7cff9f0` |
| candidate config | `bee39a247b4eef5f5282bad7e09b75853b851ed8b9161981803a08d53b4ac8fb` |
| portable ASUS source tree | `592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a` |
| source archive marker | `3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8` |
| source-seal tool | `b5ed3261a858680b05a3a7247e2d7948e722f71be812fcdc66972594d22c097a` |
| config auditor | `6d988b18c3ae70f5bd91be8e6051119911886be0b4eaeb3759eddf3f5a8ac744` |
| builder image ID | `c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec` |
| builder image digest | `sha256:8513960144bb1ca77878a1364c03fb100c8b87fffb8440fd37a6cc4fc0043b41` |
| stable-recovery initramfs | `6927d91d5c590ada1f6cae44cfa126c15470008f79949ca3256a45ee3edc4fff` |
| compiler | `Ubuntu clang version 18.1.3 (1ubuntu1)` |

Every final clean compile recomputed the portable source seal before Kconfig
or compiler execution. The seal covered 79,030 entries: 73,717 regular files,
5,272 directories, and 41 symlinks.

## Configuration audit

| Measure | Accepted baseline | Slim v1 | Reduction |
|---|---:|---:|---:|
| built-in symbols | 1,880 | 1,279 | 601 |
| active (`=y` or `=m`) symbols | 1,934 | 1,279 | 655 |
| lines | 6,836 | 4,985 | 1,851 |

The candidate retains boot/CPU/RAM, UFS, gadget-only USB ACM/NCM, kexec,
pstore/ramoops, thermal, charging, reboot, and PMIC power-key support. It
forbids the Android/GKI, DRM/GPU/display, sound, wireless/radio, PCI, optional
HID, debugging, netfilter, module, and ordinary filesystem families listed in
the tracked profile.

Seven hostile Python tests plus one positive case passed. They cover
required/minimum mutations,
forbidden and unreviewed additions, reduction thresholds, identity/state
inflation, canonical form, duplicate fields/symbols, unreviewed
module-to-built-in promotion, and symlink inputs. Every negative case asserts
its exact policy error, preventing an earlier identity failure from making a
policy test vacuous. The host and device static contracts also passed and
compute the cross-file policy/tool hashes.

## Dependency findings

The first-pass fragment exposed four ASUS-tree constraints and was corrected
before acceptance:

1. disabling the PMIC power-key implementation selected a header fallback
   that duplicated `qpnp_pon_wd_config`;
2. promoting ASUS Auralight modules to built-ins duplicated `apply_state` and
   `mode2_state`;
3. ASUS accessory/gamepad objects require HID core symbols despite optional
   HID drivers being disabled;
4. the unconditionally compiled video techpack requires a minimal
   media/V4L2 core despite camera-subdriver/radio/DVB/SDR/CVP features being
   disabled.

With modules disabled, eight reviewed baseline modules become built-ins:
`ASUS_GLOBAL_VAR`, `EDAC_QCOM`, both hall-sensor drivers, `MSM_RDBG`,
`QCOM_LLCC_PERFMON`, `SLIMBUS`, and `SLIMBUS_MSM_NGD`. The final policy
allowlists exactly those promotions and rejects any additional `m` to `y`
transition.

The policy also records the security tradeoff: this fixed, shell-free
recovery wrapper omits SELinux policy and audit, keeps the security framework,
KASLR, strict kernel RWX, and init-on-allocate, disables `debugfs` and
`/dev/mem`, and retains the accepted full SysRq mask for attended physical
postmortem recovery. Here `CONFIG_MAGIC_SYSRQ_DEFAULT_ENABLE=0x1` is Linux's
special all-functions sentinel. These are wrapper-only decisions and remain
subject to the separate live-promotion review.

The final twin builds completed. Existing vendor warnings include old-style
function declarations, pointer-size casts, and several stack-frame warnings;
none became a build error, and both builds emitted the same Image. These
warnings remain vendor-source debt, not evidence of runtime acceptance.

## Reproducibility and wrapper structure

| Product | Size | SHA-256 |
|---|---:|---|
| slim `.config` | 4,985 lines | `bee39a247b4eef5f5282bad7e09b75853b851ed8b9161981803a08d53b4ac8fb` |
| slim `Image` | 34,787,840 bytes | `2715e9611049b2ba7fefbc40ede8fa84118e2cdcbf73a6adfd3226ecf08ca7bc` |
| build metadata | — | `1bbd62c5583ae0fe76d2b99ec49f3b1ad9a09a90fccc4617270ec2f853d815e9` |
| raw boot-v3 image | 42,389,504 bytes | `e88fc19eb460c4c7cafd4a75cfdf865dd8319ea22e3bef0abac8446bbe6abb20` |
| unsigned AVB wrapper | 100,663,296 bytes | `c2f42b0efa31b03e1d22f5e6895a2a38dcfd8b29d3f4086c0f214c18f7523c11` |

Build A and Build B used distinct initially empty host output trees. Both
were mounted at the normalized internal path
`/root/build/asus-kexec-stage-slim`, so metadata does not embed a differing
host path. Their final configuration, Image, and metadata are byte-identical.
Independent repacks also produced identical raw and AVB images.

The raw image unpacks as Android boot header version 3. Its extracted kernel
and ramdisk exactly match the slim Image and accepted stable-recovery
initramfs. `avbtool verify_image` accepts the copied `boot.img`; its descriptor
reports `Algorithm: NONE` and partition `boot`. This proves packaging
structure only and supplies no signing authority.

The accepted broad wrapper Image was 50,498,048 bytes with SHA-256
`cf8c2aced08010a193b60f3dbc6099f6a24cebbe7473fb13be0e18a7015fd4ad`.
Slim v1 is 15,710,208 bytes smaller, a 31.11% reduction.

## Retention and cleanup

The compact ignored evidence set is
`build/stable-wrapper-slim-v1-retained-20260730`. It retains only the config,
Image, build metadata, raw boot image, and AVB wrapper. It is 170 MiB apparent
and 115 MiB allocated on the current filesystem.

After repository CI, independent review, and evidence capture passed, seven
exact ignored scratch trees were removed: two full object trees, two proof
trees, two generated-config trees, and the superseded audit tree. They
represented about 1.86 GiB apparent and 1.57 GiB of `du`-reported blocks.
Btrfs reported 200,359,936 newly available bytes after deletion because the
filesystem shares and compresses extents. The deletion did not affect the
accepted 208 MiB stable-recovery cache, the compact evidence set, or the
retained ASUS source volume.

## Authority conclusion

This result closes the hardware-free wrapper-config slimming roadmap item.
It does not replace the accepted wrapper, authorize a temporary boot, approve
a trust root, prove recovery on hardware, or permit flashing. Any live
experiment requires a fresh user authorization and a separate allowlist and
fallback review.
