# Stable recovery re-freeze integration

Status: **offline integration passes; production key and boot image are not
created**

This is the closure plan for replacing the accepted v18 interactive recovery
with one frozen, framed control platform. It records the exact reusable
inputs, the shell-free delta, the verification boundary, and what remains
before any phone boot can be considered.

## Reused, pinned inputs

The re-freeze deliberately reuses only components whose identity and purpose
are already understood:

| Input | Identity | Use |
|---|---|---|
| accepted v18 target initramfs | `852b02a2cbcb2dfd43598269ff1b2b10cb1542e90ab7a7aa32d1a26c7cc645fc` | credential-scrubbed Alpine userspace base |
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
inputs, removes SSH host/user credentials,
the SSH server and client entry points, getty, machine identity, and set-ID
files, then installs:

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
3. complete UFS discovery checks when requested and lock every physical block
   node read-only;
4. configure unbound NCM and ACM gadget functions and rescan device nodes;
5. repeat storage and UFS power-containment checks;
6. start the fixed responder;
7. require its canonical per-boot session file while the responder is alive;
8. monitor responder liveness and force rollback on exit;
9. bind the USB device controller;
10. configure only `169.254.77.2/30` on `usb0`.

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
- builds and extracts the initramfs twice;
- checks exact binaries, modes, trust-root bytes, loader hash, ordering, fixed
  network address, and absence of legacy access paths;
- rejects a 31-byte public key;
- rejects an all-zero 32-byte public key;
- proves both output archives are byte-identical.

The first passing integration on 2026-07-28 produced these test-only
identities:

```text
responder  479ac6c7e0269a0ebb67e6c07745216ae37e79c61da60a3a862c51194a3b67ea
fetcher    920c9bb3ccb4ab4b3fc3ad783532c5620ed31b3bd52377c8fe3e340fd865702f
verifier   ce0f2d997c0243b43e417a41fb5daadd89dfde7b2738ce3bb2e33783ba403b4c
initramfs  0f3f58020bf835ed280072eaabf34a839f26219c825eca56fa85c50e7fe769e4
```

The initramfs identity includes an ephemeral test public key. It is therefore
not a release identity and must never enter the temporary-boot allowlist.

## Remaining promotion boundary

Before a stable candidate exists:

1. obtain explicit confirmation to create or use a production signing key;
2. keep the private key outside the repository and build tree;
3. embed only its reviewed raw public key;
4. build the initramfs, wrapper kernel, raw boot image, and AVB wrapper twice;
5. update all source, artifact, and temporary-boot pins atomically;
6. complete independent review and the staged live-promotion sequence in the
   roadmap.

No production signing credential, boot wrapper, AVB image, host installation,
or phone action is performed by the current offline integration.
