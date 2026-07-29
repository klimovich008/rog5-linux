# Headless runtime package and stable-recovery integration

Date: 2026-07-29

Result: **PASS offline; reproducible; no phone or production authority**

## Outcome

The minimal SSH-only Arch root is now a complete, separately transported
`network-root-v1` lower rather than an oversized recovery initramfs. The
signed recovery bundle remains the fixed v2 inventory:

```text
manifest
manifest.sig
Image
board.dtb
initramfs.cpio.gz
```

The root package adds one explicit no-workload record at the historical fixed
path `/etc/rog5/a660-command-manifest`. It contains:

```text
format=rog5-headless-command-manifest-v1
workload=none
```

The complete extracted tree, command manifest, persistent seal, entry count,
and archive are all independently bound. No GUI, browser, GPU, radio, VPN,
hotspot, Node, agent, reusable machine ID, SSH host private key, or production
recovery key was added.

## Root identity

The source root remains:

```text
path:   artifacts/arch/rog5-arch-headless-ssh-7.1.4.tar.gz
size:   535093875
sha256: 4e472f2fa3f21fd3a5cf6de9eaf96810104083758039e8cdeefc4e03ec4e6427
```

The canonical sealed package is:

```text
path:   artifacts/arch/rog5-arch-headless-network-root-7.1.4/root.tar.gz
size:   535110731
sha256: 5438c993aa394395d534c75fb1620f778c701eb241cb24f5ecb8deda52f2b015

package manifest sha256:
d2ea1a1c94bb2652339b498691f2fd9354f829f7c40e51e73a2da1a13f0a0678

a660_command_manifest_sha256:
99f194b32171c9c9f09d28636e351bba4cb34751997e1aa174e3466bd758a1d2

root_tree_entries: 37669
root_tree_sha256:
1351a7edcc15ecba825fe5df70f8028beae7378ed84f06c28e9d34bba45d19f7
root_seal_sha256:
fdc17a0fa6e1f62f711bb4ce2b82be11f80a20f2b445a138f5fc4d950402ce1e
```

Two complete rootless-Podman builds produced byte-identical pax-restricted
archives and package manifests. Pax-restricted format is required: ordinary
pax preserved changing access/change timestamps, while GNU/ustar lost
nanosecond mtimes and xattrs. The package keeps nanosecond mtime and xattr
fidelity without archiving unstable atime/ctime.

The first implementation correctly refused publication because extracting an
archive onto a volume mountpoint changed that directory's mtime. The corrected
format archives a real top-level `root/` directory, extracts it below the
mountpoint, and verifies the complete tree after a clean second extraction.
Two failed Podman volumes were removed; their temporary compressed outputs
were moved to the desktop Trash and remain recoverable until emptied.

## Runtime bundle

The historical `network-root-v1` initramfs was correctly rejected by the
native signed-bundle verifier because it predated the required whole-tree
verifier. It remains untouched as historical evidence. A new headless-specific
initramfs was assembled from the accepted credential-free base plus the exact
reviewed static AArch64 verifier:

```text
path:
artifacts/headless-network-root-v1/rog5-headless-network-root-initramfs.cpio.gz
size:   5978369
sha256: 819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5

embedded persistent-root verifier sha256:
bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58
```

Two clean initramfs assemblies were byte-identical. The tracked
`headless-network-root-v1` candidate combines that initramfs with the pinned
UFS-disabled Linux 7.1.4 Image and USB2-only DTB. It remains:

```text
status=offline
authority=none
```

Packaging with a newly generated ephemeral Ed25519 key and then running the
real native verifier produced:

```text
manifest_sha256:
70136ad498fad21bce5279f60cbad36359c7d6df6eb42280591071c5e1389bf6
profile=network-root-v1
target_release=7.1.4-g7a5cef0db479
```

The verifier emitted a command line containing the exact no-workload hash and
all four root identity fields. The disposable private key was destroyed with
its temporary directory. No production trust root was created or used.

## Actual consumed-P2 composition

`test-recovery-candidate-integration.py` composes the real implementation:

1. package the tracked consumed P2 candidate with an ephemeral key;
2. serve the immutable bundle once through the descriptor-oriented host
   server core on loopback;
3. fetch it with the real sandboxed fetcher test build;
4. verify its signature, kernel, DTB, initramfs, and plan with the real native
   verifier;
5. hand three sealed descriptors to the real framed responder;
6. load and execute through a fake kexec that checks the exact descriptor
   hashes and records startup unload, load, execute, and returned-executor
   unload.

With the ignored P2 artifacts present, the test used the actual consumed
payload and canonical manifest:

```text
7dbabf68f532265d45f00e8521989577fd82da7a7b0dd461bae384fc82eea4fd
```

A one-byte signature mutation reached neither load nor execute. Clean clones
and hosted CI use a tiny policy-valid bundle to exercise the same composition
without committing the ignored 44 MiB P2 payload.

## Claude review

Claude Code `2.1.220` passed a bounded Opus health prompt and a second
plan-only architecture review. The review recommended keeping
`network-root-v1`, expressing headless mode as a distinct hash-bound
no-workload manifest, and testing byte identity plus root bindings. It also
flagged an NFS time-of-check/time-of-use risk. The target initramfs already
addresses that risk by mounting the lower read-only and recomputing the
complete sealed tree before OverlayFS handoff; this behavior remains
mandatory.

Claude used no tools, files, network, credentials, or repository write
authority. Its output was advisory, not approval.

## Verification

The focused suites pass:

```text
python3 scripts/host/test-headless-network-root.py
python3 scripts/host/test-prepare-recovery-candidate.py
python3 scripts/host/test-recovery-candidate-integration.py
scripts/device/test-network-root-init.sh
NETWORK_ROOT_VERIFIER=... \
  scripts/device/verify-network-root-initramfs.sh \
  artifacts/headless-network-root-v1/rog5-headless-network-root-initramfs.cpio.gz
```

The root tests reject tree, archive, and command-manifest mutation. The
candidate tests reject live authority, unsupported status, unknown fields,
an offline non-network-root profile, and artifact identity changes. The
integration test proves actual P2 prepare/serve/verify/load/execute
composition and signature refusal.

The complete repository Linux CI tier also passes in the offline local CI
image. A transient QEMU package installation then ran the real
`qemu-system-aarch64` smoke script against the existing 42,560,000-byte test
kernel and passed the full-system kernel-to-initramfs handoff.

Claude's first post-change review received only the tracked-file diff and
correctly refused to review the omitted new files. Its concrete comments led
to the additional offline/profile refusal test and to explicit documentation
of the exact-hash `NETWORK_ROOT_VERIFIER` fallback. A second review received
the complete 2,242-line patch but reached the fixed 180-second limit without
a verdict; it made no repository change and was not treated as a gate.

No fastboot, ADB, SSH, USB device, phone command, reboot, boot, flash, block
write, production credential, or external service was used.
