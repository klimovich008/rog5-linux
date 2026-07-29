# Minimal headless root and candidate adapter — offline result

Date: 2026-07-29

Result: **PASS offline; no phone or production authority**

## Outcome

This checkpoint produced the first concrete minimal mainline userspace and
ported one consumed payload into the stable-recovery bundle preparation path.

The headless Arch profile contains the signed generic Arch Linux ARM base,
the exact Linux `7.1.4-g7a5cef0db479` modules, and only three requested
additions:

```text
attr
diffutils
openssh
```

It removes the generic Arch kernel and all twelve `linux-firmware*` packages,
which represented 1,281.37 MiB installed in the base. It also removes the
published `alarm` account and excludes desktop, browser, Vulkan/Mesa, GPU
firmware, Wi-Fi, VPN/hotspot, Node/npm, ttyd, and automation-agent packages.
The root uses key-only root SSH, volatile machine and SSH host identities,
`multi-user.target`, and the existing sleep inhibitor. USB addressing remains
owned by the initramfs; both NetworkManager and systemd-networkd are disabled.

The result has 150 packages:

```text
source commit: eb61a45938c851b1b02a2f3151db5265ab9213e7
kernel:        7.1.4-g7a5cef0db479
path:          artifacts/arch/rog5-arch-headless-ssh-7.1.4.tar.gz
size:          535093875
sha256:        4e472f2fa3f21fd3a5cf6de9eaf96810104083758039e8cdeefc4e03ec4e6427
```

The 2,007,033,670-byte successor-v3 Plasma archive is retained as historical
evidence. The new archive is 73.3% smaller. No claim is made about runtime RAM
or battery savings until measured on the device.

## Candidate parity

`configs/recovery-candidates/persistent-root-p2-parity.json` maps the exact
consumed P2 kernel, DTB, and initramfs into the existing
`persistent-root-ro-v1` bundle profile. The adapter:

- accepts only tracked candidate IDs and canonical fields;
- requires `status=consumed` and `authority=none`;
- verifies exact artifact size and SHA-256 while taking private snapshots;
- delegates canonical manifest signing and atomic publication to the existing
  stable bundle packager;
- contains no network server, transport, fastboot, ADB, phone, or execute
  path.

An actual offline package of the tracked ignored P2 artifacts passed with an
ephemeral Ed25519 key. Its canonical manifest SHA-256 was:

```text
7dbabf68f532265d45f00e8521989577fd82da7a7b0dd461bae384fc82eea4fd
```

The trust-key hash is intentionally not recorded because that key was
ephemeral. The result restores no live authority to the consumed payload.

## Verification

The following passed:

```text
scripts/host/test-repository-linux.sh ci
scripts/host/test-linux-rootfs-tools.sh
scripts/host/test-arch-headless-rootfs-contract.sh
python3 scripts/host/test-prepare-recovery-candidate.py
bash syntax and ShellCheck for every changed shell path
git diff --check
real AArch64 stage verifier before archival
clean archive extraction and second AArch64 verifier
actual consumed-P2 offline bundle preparation
```

The aggregate repository tier passed the existing recovery reference, native
responder, signed-bundle verifier, fixed fetcher, host server/controller,
init-policy, fallback reboot, and QEMU contracts. It ran unprivileged where
the host-server test requires it.

The first real root build exposed two issues and failed before publication:
the inherited generic firmware family consumed 969 MiB on disk, and OpenSSH
10.4 would not print an effective configuration without a concrete connection
context and usable test host key. The final stage removes the firmware package
family and evaluates an exact `/run` copy of the SSH config with an ephemeral
host key. Both failed build volumes were inspected and removed before the
passing rebuild.

## Claude check

`claude --version` reported `2.1.220`. A bounded plan-only Opus health prompt
returned exactly `CLAUDE_OPUS_OK`. A later read-only repository-review prompt
produced no report before its 240-second bound and ended with an execution
error. It made no repository changes and is not counted as review approval.

## Remaining boundary

The archive records exact package versions, authenticated base/root module
identities, and its source commit. It is not yet byte-reproducible because the
rolling Arch repository snapshot is not pinned and `pacman-key --init`
generates local trust state.

Next work is to package this root into a signed runtime bundle and complete
fixed serve/verify/execute integration for the manifest-driven runner.
Creating or using a production recovery trust root still requires separate
explicit approval. No phone command, reboot, boot, flash, storage write,
credential use, or external service setup occurred in this checkpoint.
