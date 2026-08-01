# Stable recovery re-freeze integration

Status: **offline initramfs, wrapper, boot-v3, and AVB reproducibility pass;
production key and release candidate are not created**

This is the closure plan for replacing the accepted v18 interactive recovery
with one frozen, framed control platform. It records the exact reusable
inputs, the shell-free delta, the verification boundary, and what remains
before any phone boot can be considered.

## Reused, pinned inputs

The re-freeze deliberately reuses only components whose identity and purpose
are already understood:

| Input | Identity | Use |
|---|---|---|
| accepted v18 target initramfs | `852b02a2cbcb2dfd43598269ff1b2b10cb1542e90ab7a7aa32d1a26c7cc645fc` | pinned Alpine userspace base; scrubbed by the stable builder |
| accepted wrapper config | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` | kexec, memfd, seccomp/filter, namespaces, tmpfs, ACM, and NCM prerequisites |
| `kexec-tools-2.0.32-r2.apk` | `bd8b6951f862af1123972b521c355c655b7a2f40c2bf9cfe700edd590a101c94` | fixed legacy `kexec_load` loader |
| `xz-libs-5.8.3-r0.apk` | `76dce86852903fef7adba0285d816e5ce9ffbe9fb3ca86bbb349b97afaba1f63` | pinned kexec dependency |
| `zstd-libs-1.5.7-r2.apk` | `2bb5136c89f5b0bbe1554c8915a3b520d5aa63ae2a51d4d821eb81698db5a818` | pinned kexec dependency |
| packaged AArch64 `kexec` | `5e5d0a78b3f0bcf3921ff060f4dce5011cbac24b5e12fedeb8ca03ea5b40d015` | fixed `/usr/sbin/kexec` executable |

The ignored v18 archive and signed Alpine packages remain local build inputs;
they are not added to Git. The pre-stable Git tag remains the source archive
for superseded interactive helpers.

The compact v18 target archive is used only as a pinned Alpine filesystem
base. The resulting stable archive is intended to replace the **outer**
initramfs embedded directly in the vendor 5.4 wrapper. It does not contain
the old nested Linux Image/DTB/initramfs tuple: those become signed runtime
bundle data fetched by the fixed control plane.

## New stable image contract

`scripts/device/build-stable-recovery-initramfs.sh` requires:

1. the exact v18 base archive above;
2. the current recovery init;
3. production AArch64 static-PIE responder, fetcher, and verifier binaries;
4. the three hash-pinned Alpine packages;
5. an externally supplied raw 32-byte Ed25519 public key.

It refuses symlinked, wrong-sized, or all-zero trust roots and other malformed
inputs, removes SSH host/user credentials, the SSH server and client entry
points, getty, login/password and DHCP entry points, and machine identity. It
locks the root account and rejects any remaining set-ID or private-key-like
file, then installs:

```text
/usr/libexec/rog5-recovery-control
/usr/libexec/rog5-bundle-fetch
/usr/libexec/rog5-bundle-verify
/usr/sbin/kexec
/etc/rog5/recovery-bundle-ed25519.pub
```

The output is a reproducible root-owned `newc` archive with fixed timestamps
and gzip metadata.

## PID 1 ordering

The stable recovery init preserves this fail-closed sequence:

1. mount only virtual filesystems and arm the rollback timer;
2. atomically publish the owner-private watchdog lease as canonical
   `pid`/`starttime` fields;
3. complete UFS discovery checks when requested, lock every physical block
   node read-only, and require the measured 116-node ASUS-wrapper topology;
4. configure unbound NCM and ACM gadget functions and rescan device nodes;
5. repeat storage isolation, the exact-topology contract, and UFS
   power-containment checks;
6. mount pstore and publish a bounded owner-only postmortem snapshot/status
   without deleting records;
7. start the fixed responder, which validates and pins that status;
8. require its canonical per-boot session file while the responder is alive;
9. monitor responder liveness and force rollback on exit;
10. bind the USB device controller;
11. configure only `169.254.77.2/30` on `usb0`.

There is no DHCP, host-provided gateway, default route, SSH server,
interactive shell, getty, or arbitrary command interpreter on the control
channel. Network-root and persistent-root init variants now expose NCM only;
their previous ACM shell is archive-only.

## Offline evidence

`scripts/host/test-recovery-init-policy.py` is part of the quick repository
suite and statically enforces the control-surface and ordering rules.

`scripts/host/test-stable-recovery-initramfs.sh` is the full local integration
test. It:

- validates both pinned AArch64 builder image identities;
- builds each static helper twice and compares the bytes;
- generates an ephemeral Ed25519 key without writing the private key to disk;
- builds and extracts the initramfs under different host locales and time
  zones;
- checks exact binaries, modes, trust-root bytes, loader hash, pstore snapshot
  ordering, fixed network address, locked root, the measured 116-node
  contract, and absence of legacy access paths;
- proves malicious shell, DHCP, missing-responder, missing-address,
  authorized-key, set-ID, unlocked-root, relocated-login, and unsafe-shadow
  fixtures are rejected;
- rejects a 31-byte public key;
- rejects an all-zero 32-byte public key;
- proves both output archives are byte-identical.

The first passing integration on 2026-07-28 produced these historical,
test-only identities:

```text
responder  479ac6c7e0269a0ebb67e6c07745216ae37e79c61da60a3a862c51194a3b67ea
fetcher    920c9bb3ccb4ab4b3fc3ad783532c5620ed31b3bd52377c8fe3e340fd865702f
verifier   ce0f2d997c0243b43e417a41fb5daadd89dfde7b2738ce3bb2e33783ba403b4c
initramfs  0f3f58020bf835ed280072eaabf34a839f26219c825eca56fa85c50e7fe769e4
```

The initramfs identity includes an ephemeral test public key. It is therefore
not a release identity and must never enter the temporary-boot allowlist.

The historical subsequent full wrapper gate used another ephemeral public
key and proved two clean initramfs, vendor-kernel, raw boot-v3, and AVB
outputs byte-identical. The kernel Image identity was
`303d3767261f1ca9e105d7fd5dbb6ab7f18110aeba0cf3daecb1d01c4cb80175`;
the raw image identity was
`4029ab83f2470195054213aee77201f6bc29b78d52c14196afeb3203a09804bf`;
and the 96 MiB AVB identity was
`64e0b8efe8af04e40fd90b2c84d050447fd618c3add919d111934d2cb3502ec8`.
Unpacking recovered the exact kernel and initramfs and preserved the UFS and
read-only-storage boundary. A later hardening follow-up removes the obsolete
`rog5.recovery_cidr` token entirely: the fixed `169.254.77.2/30` address is
owned by recovery `/init`, not boot input. The ASUS wrapper correctly omits
the target-only `rog5.ufs_discovery=1`; recovery `/init` locks every
discovered physical node read-only and requires the measured 116-node
topology before USB bind. `avbtool` verified the complete hash descriptor.

The full evidence and repeatable command are in
[stable recovery wrapper reproducibility](../test-results/2026-07-28-stable-recovery-wrapper-offline.md).
`scripts/host/test-stable-recovery-wrapper-offline.sh` pins the source marker,
reference config, boot template, Android image tools, and kernel-builder
identity; runs both builds without container network access; and refuses
outputs outside the ignored `build/` tree.

The current independently reviewed hardening follow-up repeated the cross-locale
initramfs and complete wrapper gate after removing the remaining
`etc/udhcpc/udhcpc.conf` legacy DHCP artifact. It produced byte-identical
test-only initramfs
`31aa52acea3dac91fd23108bd05e7681597cfd1d082a06782f1315aad3c12108`,
kernel Image `491195f7f0e5205f3e6a4d4e52da79f03f5a4ae3ad3b92854cf41f6ed5240eea`,
raw boot-v3 `28b4fec683fd8d7bfa7305700faa837bfa14aef1608da591fb3b42bc515f5fe0`,
and AVB image `64537159174c8aea99d52d87a7eefc1c363b82acf61bbe664cfc69bed23eb21d`.
See
[stable recovery review hardening](../test-results/2026-07-28-stable-recovery-review-hardening-offline.md).

The corrected headless gate now supplies one caller-owned disposable public
key to both initramfs builds, retains the already-verified production AArch64
responder/fetcher/verifier for artifact inspection, packages the accepted
v3-isolated DTB twice, verifies both execution plans, and repeats the complete
wrapper/raw/AVB build. The twins match byte-for-byte; the private key is
destroyed before success, and every candidate remains `authority=none`. See
the
[corrected headless twin build](../test-results/2026-07-29-corrected-headless-candidate-offline.md).

## Remaining promotion boundary

Before a live candidate exists:

1. apply the central standing authorization to one admitted production
   signing operation and one admitted temporary boot; do not request the same
   consent again;
2. keep the private key outside the repository and build tree;
3. embed only its reviewed raw public key;
4. build the release initramfs, wrapper kernel, raw boot image, and AVB
   wrapper twice with the admitted public key;
5. update all source, artifact, and temporary-boot pins atomically;
6. independently review the final production-key artifact and complete the
   staged live-promotion sequence in the roadmap.

No production signing credential, release wrapper, host installation, or
phone action is performed by the current offline integration. The generated
ephemeral-key wrapper and AVB images are test-only ignored artifacts.
