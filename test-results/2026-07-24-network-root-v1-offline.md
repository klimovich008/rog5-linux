# UFS-disabled network-root v1 offline result

Status: **PASS offline; rootfs/export/live gates pending**. The bundle is
eligible only for an attended temporary `fastboot boot` followed by a separate
kexec decision. It must never be flashed.

## Purpose

This is the first normal-distribution gate after accepted read-only UFS
discovery. Linux mounts a fixed host NFSv4.2 export read-only over USB NCM,
places a capped tmpfs above it with OverlayFS, and runs the distribution's
`/sbin/init`. Phone storage remains absent from both the DTB and kernel.

The live gate was not attempted during this result. Installing/enabling the
host NFS service and changing its runtime firewall boundary require separate
confirmation.

## Test-first implementation

The target-init, kernel-fragment, and kexec-loader tests were added before the
implementation and initially failed because their files did not exist. They
now pass and enforce:

- exactly one fixed `rog5.netroot=1` mode;
- a 60-900 second rollback window;
- zero physical storage and zero block-backed mounts before USB and again
  before `switch_root`;
- fixed `169.254.77.2/30` and `169.254.77.1` addresses;
- read-only NFSv4.2 over TCP plus a 2 GiB `nodev,nosuid` tmpfs upper;
- built-in NFS/OverlayFS/ACM/NCM and `/proc/config.gz`; and
- absent SCSI, UFS, SCSI disk/BSG/RPMB, and UFS/combo/PCIe/SuperSpeed QMP
  paths.

The bundle-contract test also failed before its writer/verifier existed and
now requires the exact fourteen products, nested verifiers, no persistent
write command, and AVB/config/storage boundaries. The Linux rootfs-host test
likewise failed before the native scripts existed and now checks signed input,
metadata preservation, exact modules, and absence of broad container
privileges.

## Source and reproducibility

- Linux source: `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`
  (`v7.1.4`)
- Compiler: Ubuntu clang 18.1.3
- Base fragment SHA-256:
  `9ace4a115c08c541b26d8dbf553ba4efc18024f79cb4e306b096c17c5bd27ab2`
- Network-root fragment SHA-256:
  `bb6fa83f706aa1ec317c4597b0a98cc2f993a90ada76cccd27e306c1470f2be5`
- Target initramfs SHA-256:
  `83460dce3b1d900ac34a37388b68d5c055f4bf0b41b9945962d298bd2ce1d06e`

Two fresh, network-disabled kernel output volumes produced byte-identical
config, `Image`, `Image.gz`, module archive, and metadata. The final config
passes every required NFS/OverlayFS symbol and has no enabled UFS/SCSI/QMP
storage path. The module archive contains no UFS-named module.

Two target initramfs builds and two nested staging initramfs builds are
byte-identical. Both layers contain no authorization key, SSH host identity,
machine identity, or private key. Two clean ASUS source/output pairs produced
byte-identical wrapper config, embedded initramfs, Image, and metadata. Two
header-v3 repacks and unsigned AVB packages are byte-identical.

The complete fourteen-file verifier checks every manifest hash, both
initramfs layers and nested payloads, the accepted UFS-disabled recovery DTB,
wrapper and mainline configs, exact kernel releases, Android boot metadata and
command line, and the unsigned AVB footer.

## Canonical products

| Product | Size | SHA-256 |
|---|---:|---|
| ASUS wrapper Image | 69,372,416 | `7a58ba1db2b96c63002be30c590c560cc9f36c02ce461fae3f47df19a548f78d` |
| ASUS wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| embedded/staging initramfs | 27,036,227 | `8d692e5bac4b4c343b280aadc7f1434af903140ac1813c2f5e7ff12d3c06a83b` |
| Linux 7.1.4 network-root Image | 40,049,152 | `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf` |
| compressed Linux Image | 14,751,785 | `a1756e36f42a57c90bd85ef33d68aa1424768a45f272cc0514c2992ace0ae6e5` |
| Linux network-root config | 239,677 | `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f` |
| matching modules | 300,439,504 | `5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9` |
| UFS-disabled USB2 DTB | 102,774 | `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6` |
| target initramfs | 5,838,910 | `83460dce3b1d900ac34a37388b68d5c055f4bf0b41b9945962d298bd2ce1d06e` |
| raw header-v3 image | 96,415,744 | `89ab2b55eae92e622937ac3fd1785bf76721c9ec93ce9a87c0126c29005cfe87` |
| unsigned AVB image | 100,663,296 | `3998cfdd62e0f40a6562c6fad1fb96ebc54ffaba5affee21c4f16644e40ed228` |

The exact local manifest is `artifacts/network-root-v1/SHA256SUMS`; all
fourteen canonical identities are mirrored in `manifests/artifacts.tsv`.

## Arch input and remaining boundary

The signed Arch Linux ARM input reverified at 818,293,654 bytes with SHA-256
`3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a`
under the pinned signing-key fingerprint. Rootless Podman extracted it with
ACL/xattr support, and the registered emulator executed the filesystem as
`aarch64`.

The final rootfs still needs a clean-repository package/module stage and
round-trip verification. After that, the host export must be configured
read-only and restricted to the dedicated USB peer. Live acceptance then
requires exact kernel release, read-only NFS lower, volatile OverlayFS upper,
zero storage, `multi-user.target`, key-only SSH, stable USB, clean logs, and
automatic fallback.

No network-root artifact was transferred to or booted on the phone. No
partition was mounted, written, resized, formatted, or flashed.
