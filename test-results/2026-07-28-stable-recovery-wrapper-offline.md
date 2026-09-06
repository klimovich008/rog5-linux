# Stable recovery wrapper reproducibility — 2026-07-28

Result: **PASS offline; ephemeral trust root; not boot-authorized**

## Scope

This checkpoint extended the shell-free stable-recovery initramfs proof
through two clean ASUS vendor-kernel builds, two Android boot-v3 repacks, and
two unsigned AVB wrappers. It performed no phone action, did not modify the
temporary-boot allowlist, and did not create or use a production signing key.

The private half of the ephemeral Ed25519 test key existed only inside an
OpenSSL pipeline and was never written to disk. The generated images remain
under the ignored `build/` tree.

## Pinned inputs

```text
ASUS source marker  3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8
reference config    e8605b42cd27d372cea195811c3ff064346390a235572a0018c9dc8d048b5da4
wrapper config      df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
boot-v3 template    292a14e212826a250de501d4d502dda6973097ed172cd9324d82cf88d82fd657
mkbootimg.py        d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a
unpack_bootimg.py   7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef
avbtool.py          6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff
kernel builder ID   34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941
kernel builder      sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c
```

## Test-only outputs

```text
test public key  64004a42496a76e59520e23eb9cbd512fb0e41f2c42f0c29271f4aa82ece2ccb
initramfs A      7fce0a3570a1c51c7704485411065b364a7701c40b1c9586f2134b4e57ec9224
initramfs B      7fce0a3570a1c51c7704485411065b364a7701c40b1c9586f2134b4e57ec9224
kernel Image A   303d3767261f1ca9e105d7fd5dbb6ab7f18110aeba0cf3daecb1d01c4cb80175
kernel Image B   303d3767261f1ca9e105d7fd5dbb6ab7f18110aeba0cf3daecb1d01c4cb80175
raw boot A       4029ab83f2470195054213aee77201f6bc29b78d52c14196afeb3203a09804bf
raw boot B       4029ab83f2470195054213aee77201f6bc29b78d52c14196afeb3203a09804bf
AVB boot A       64e0b8efe8af04e40fd90b2c84d050447fd618c3add919d111934d2cb3502ec8
AVB boot B       64e0b8efe8af04e40fd90b2c84d050447fd618c3add919d111934d2cb3502ec8
```

The raw Android boot-v3 image is 58,101,760 bytes. The AVB image is exactly
100,663,296 bytes. Its algorithm is `NONE`, partition name is `boot`, and the
hash-descriptor digest is
`0e0076bf45991a3e107d51669047b730ccbd850681e39f6c8417f178b6fb6ad0`.
`avbtool verify_image` verified both the footer/vbmeta structure and the
complete boot-partition hash.

Unpacking the raw image recovered the exact kernel and initramfs bytes.
The command line contains one fixed
`rog5.recovery_cidr=169.254.77.2/30` and the rollback timeout, and does not
contain the previous `/16` address. It correctly omits the target-only
`rog5.ufs_discovery=1`: the ASUS wrapper does not define
`CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY`, while recovery `/init` independently
locks and verifies every discovered physical block node read-only before USB
bind.

## Repeatable gate

`scripts/host/test-stable-recovery-wrapper-offline.sh` turns this proof into
an explicit full-build gate. It requires two already byte-identical
stable-recovery initramfs inputs and a fresh ignored output directory. It
then:

- validates the source marker, reference config, boot template, Android image
  tools, and kernel-builder identity;
- uses network-disabled containers and two distinct empty output trees;
- builds the vendor 5.4.210 wrapper twice and checks the embedded initramfs
  occurs exactly once;
- repacks and compares raw and AVB images;
- unpacks the result, checks exact kernel/ramdisk bytes and required command
  line tokens, rejects the target-only UFS token, and verifies the AVB
  descriptor.

Example with test-only initramfs inputs:

```sh
JOBS=16 scripts/host/test-stable-recovery-wrapper-offline.sh \
  build/stable-recovery-wrapper-offline/initramfs-a/rog5-stable-recovery.cpio.gz \
  build/stable-recovery-wrapper-offline/initramfs-b/rog5-stable-recovery.cpio.gz \
  build/stable-recovery-wrapper-repeat
```

The gate never updates boot policy or invokes `fastboot`.

## Promotion status

This closes offline wrapper reproducibility for an ephemeral trust root. A
production candidate still requires explicit approval before creating or
using its signing key, two clean release builds with the approved public key,
independent review, atomic manifest/allowlist pin updates, and the separately
authorized staging-only live sequence.

## Superseded command-line note

The `/30` command-line token above is historical evidence for this build.
The subsequent independently reviewed hardening pass removes
`rog5.recovery_cidr` entirely because the address is fixed by `/init`, and
repeats the complete two-build wrapper/AVB gate. See
[stable recovery review hardening](2026-07-28-stable-recovery-review-hardening-offline.md).
