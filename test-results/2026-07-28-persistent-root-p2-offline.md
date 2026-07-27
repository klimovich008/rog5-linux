# Persistent Arch P2 read-only boot acceptance

Date: 2026-07-28

Result: **PASS OFFLINE; LIVE PENDING.** The complete temporary-boot and
nested-kexec package is reproducible, credential-free, fail-closed, and ready
for one attended boot. No P2 target boot has occurred, and Gate P3 remains
prohibited.

## Safety boundary

This gate temporarily boots an ASUS 5.4.210 recovery wrapper, loads a
Linux 7.1.4 target, and enters the already staged Arch root as a read-only
OverlayFS lower. It does not flash, repartition, format, fsck, replay the ext4
journal, select a root generation, or write a boot partition.

The target:

1. requires the exact dedicated read-only UFS kernel configuration;
2. requires the accepted 116-node UFS topology, previously observed as 7
   physical disks plus 109 partitions;
3. applies and verifies read-only state to all 116 physical nodes;
4. accepts only measured `userdata` partition `/dev/sda23`;
5. mounts it once as `ext4 ro,noload`;
6. verifies the complete 181,242-entry Arch seal before handoff;
7. uses a 2 GiB tmpfs for the OverlayFS upper and work directories;
8. boots Arch systemd with key-only SSH and every physical backlight off;
9. rejects blocked UFS commands, journal recovery, UFS/SCSI errors, extra
   block-backed mounts, a changed root seal, or a selected/promoted root; and
10. retains an independent 600-second direct SysRq reset that returns to
    Alpine without depending on Arch shutdown.

The sealed root remains `UNBOOTED`. Both `/rog5/state/good` and
`/rog5/state/next` must remain absent.

## Anchored inputs

| Input | Identity |
|---|---|
| Linux base commit | `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` |
| accepted read-only UFS commit | `cfd385a1c754684dd28b63a4559e04baa5e902b1` |
| accepted source tree | `d2f03d2055227b8b72ab41be949847a066924c5a` |
| accepted UFS/USB2 DTB | `36802458928e2970a0043f6a27d106e6aa4911fd89b2f548e7c08275d164aaf0` |
| persistent-root seal | `e201955dead61a04ca0e70d67fcea18750940330421334c91cfe2c760e7fb3ff` |
| persistent-root tree | `b71eccbe5275f8d125a6d3251fff166b57f196c23984b845e31666ecaaea9a8c` |

The Linux 7.1.4 configuration differs from the accepted UFS-discovery
configuration in exactly one setting: `CONFIG_OVERLAY_FS=m` becomes
`CONFIG_OVERLAY_FS=y`. Ext4 and the read-only UFS discovery boundary remain
built in.

## Reproducibility

- Two hardened native-AArch64 verifier builds are byte-identical. The
  67,232-byte PIE depends only on musl libc and reproduces the canonical
  Python whole-tree seal.
- Two target initramfs builds are byte-identical and contain no private key,
  SSH host identity, authorization file, account token, or machine identity.
- Two clean Linux 7.1.4 builds have identical config, `Image`, `Image.gz`,
  and metadata.
- Two staging initramfs builds are byte-identical. Every inherited file from
  the accepted UFS staging archive is unchanged except the exact target
  Image, unchanged accepted DTB, target initramfs, fixed loader, and their
  manifest.
- Two clean ASUS 5.4.210 wrapper builds are byte-identical. Independent
  inspection finds the exact staging archive embedded once.
- Two header-v3 repacks and unsigned AVB images are byte-identical. Unpacking
  the final raw image reproduces the exact wrapper and external staging
  archive. The AVB footer uses algorithm `NONE` and the image is for an
  unlocked, attended `fastboot boot` only.

The two Linux 7.1.4 compiler processes completed successfully and printed
their PASS records. Their parent shell invocations later returned nonzero
because the build script was edited while those already-running shells were
still reading it. The completed outputs were then independently verified,
compared byte-for-byte, and passed the dedicated verifier. The final script
passes `sh -n`, ShellCheck at warning level, and its fail-first suite.

## Canonical products

| Product | Size | SHA-256 |
|---|---:|---|
| persistent-root verifier | 67,232 | `6a67a4e0d228efab0d0e47ee4c5d6947af3df157e8110c6bf9c7444c1b4e71dd` |
| Linux 7.1.4 target Image | 38,607,360 | `832757fc6b97554813a14049123667bc6f5b225e6204ca048d73c3a36c76469f` |
| Linux 7.1.4 target Image.gz | 14,389,404 | `284df01f13326cf9468e5b79aba478011fca7a72ac1e895c82f9f5d1b8db90cf` |
| Linux 7.1.4 config | 242,248 | `8a7fabffa076a65d09529ef1004c315e1296e547a02d08c362031d0363ba63c3` |
| Linux 7.1.4 metadata | 896 | `77c5049acdbecb529d9c3ba05e72e413964a9733f12354bda1c81e31e5babff9` |
| UFS/USB2 target DTB | 102,766 | `36802458928e2970a0043f6a27d106e6aa4911fd89b2f548e7c08275d164aaf0` |
| target initramfs | 5,853,365 | `a7518e67c0355efb3e31865ffb6c120739463b3a49794da66798250183f61d13` |
| nested staging initramfs | 26,688,618 | `206ea5897fcbc12d8213041c133357a1f0055c3e233ec8d1a75fc6795e95a2a5` |
| ASUS 5.4.210 wrapper Image | 69,372,416 | `e87c845b6e63bdd097f19058e36746c2bcbeb662dcb77b686c70ffdef161d0b4` |
| ASUS wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| ASUS wrapper metadata | 422 | `ca8d42d8c5de33b32a6ca252de6d8721393be2bc2a46b4e6ebdb2cb5f196556f` |
| raw header-v3 boot image | 96,067,584 | `fd614701b859c77a1d5b7187cc7a83623d1ae71b673e3aebcb9691e1bb9b2237` |
| unsigned AVB boot image | 100,663,296 | `ac60d65c7ca89c92320c978470a0cf3803a2e8b063a24489182fc031a42232ee` |

## Offline tests

The following pass:

```text
scripts/device/test-persistent-root-verifier.sh
scripts/device/test-persistent-root-initramfs.sh
scripts/device/test-load-mainline-persistent-root.sh
scripts/device/test-mainline-persistent-root-build.sh BUILD_A BUILD_B
python3 scripts/host/test-persistent-root-acm.py
scripts/host/test-run-persistent-root-p2-live-gate.sh
git diff --check
sh -n on every new shell source
ShellCheck -S warning on every new shell source
```

Mutation coverage rejects a changed seal, file content, mode, symlink,
xattr, promotion state, entry type, UFS identity, writable block node,
credential-bearing initramfs, wrong loader argument, unsafe timeout, changed
kernel/config/DTB/initramfs identity, and non-reproducible duplicate output.

## Current live boundary

Loading directly from the running Alpine fallback was attempted first and
failed safely: that exact vendor kernel has both `CONFIG_KEXEC` and
`CONFIG_KEXEC_FILE` disabled, so `kexec_load` returned “Function not
implemented” and the target was never executed.

The guarded fallback-to-fastboot reboot then disconnected USB, but no
fastboot, ADB, recovery ACM, or other phone USB identity appeared on the
host. The final P2 image has therefore not been transferred or booted. This
is an external connection/boot-mode HOLD, not a P2 acceptance result.

## Attended live sequence

`scripts/host/run-persistent-root-p2-live-gate.sh` is the preferred entry
point. Its mocked positive path proves this exact order:

1. clean, pushed repository and manifest-pinned boot-image preflight;
2. temporary `fastboot boot`;
3. fixed ACM load and read-only staging preflight;
4. one non-retryable `kexec -e`;
5. exact target kernel, immutable readiness record, ongoing 116-node
   read-only/storage-health state, strict SSH, systemd, screen-off state, and
   live watchdog;
6. no watchdog disarm or target reboot request;
7. automatic return to the separately pinned Alpine SSH identity;
8. exact fallback kernel/pstore/thermal state plus unchanged root seal,
   `UNBOOTED` promotion state, absent selectors, and screen off; and
9. restoration of the host's initial ModemManager state.

A synthetic target-attestation failure stops before any fallback acceptance
claim, leaves the target watchdog untouched, and still restores host state.
The test also proves that execute occurs exactly once.

The real-host unarmed boundary also passes. The clean synchronized branch,
manifest artifact, and approved external credential metadata validated, then
zero fastboot devices produced:

```text
FAIL expected exactly one fastboot device, found 0
```

The refusal occurred before ModemManager stop, temporary boot, or ACM use.
ModemManager remained active and no P2 evidence log was created. No SSH
connection or credential use against a peer occurred.

Prerequisites are exactly one phone in fastboot, the cable left connected, a
clean branch synchronized with its remote, the approved client key and
fallback known-hosts file, a caller-private evidence directory outside the
repository, and the manifest-pinned local artifact:

```sh
install -d -m 0700 /private/path/rog5-p2-evidence
ALLOW_PERSISTENT_ROOT_P2_LIVE_GATE=1 \
  ALLOW_TEMPORARY_BOOT=1 \
  ALLOW_ATTENDED_KEXEC=1 \
  SSH_KEY=/private/path/rog5-client-key \
  KNOWN_HOSTS=/private/path/rog5-fallback-known-hosts \
  EVIDENCE_DIR=/private/path/rog5-p2-evidence \
  scripts/host/run-persistent-root-p2-live-gate.sh
```

The target generates a volatile SSH host key. The runner captures the first
connection only into a fresh mode-0600 temporary file and proceeds only when
that peer reports exact `7.1.4-gcfd385a1c754`; every later target connection
is strict against the captured key. The temporary file is removed after the
cycle. The stable fallback key remains separately pinned and is never
replaced. Evidence is written mode 0600 outside the repository.

The target watchdog is not disarmed. Its direct reset must return to the
exact Alpine fallback with a changed boot identity, no fatal pstore record,
the root still `UNBOOTED`, and both selector files absent. Default timing
bounds allow 480 seconds for the sealed target to become ready and 750
seconds for the independent 600-second reset plus Alpine recovery.

## Decision

The P2 package is accepted offline and may receive one attended temporary
boot. It must never be flashed. P2 is not accepted live, and no writable UFS
probe or P3 work is allowed until the complete target-and-fallback evidence
passes.
