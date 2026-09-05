# Recovery v12 offline result

Status: **PASS** for a reproducible, credential-free two-stage recovery
bundle. This is an offline candidate only: it has not been booted, flashed, or
written to the phone.

## Host and builder

- Host: Nobara Linux 44, x86-64, native Btrfs workspace.
- Container runtime: rootless Podman 5.8.4.
- Builder image ID:
  `34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941`.
- Builder image digest:
  `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`.
- Source preparation, both kernel builds, comparisons, and verification used
  `--network=none`.

## Access and safety contract

- Access mode is explicitly `acm-only`.
- The pinned base initramfs contained one inherited `authorized_keys` file.
  Both builders now delete it before optionally installing an explicitly
  supplied public key.
- Both output initramfs archives contain no `authorized_keys`, private key, or
  other authentication material.
- Recovery starts `sshd` only when an authorized key exists; v12 logs that SSH
  is disabled and keeps the supervised ACM shell available.
- Both stages arm the 180-second forced-reboot rollback and require
  `CONFIG_PM_WAKELOCKS=y`.
- The Linux 7.1 recovery DTB keeps UFS, QMP/SuperSpeed, and the secondary USB
  controller disabled.

No credential was read or used to build or verify v12.

## Pinned inputs

- ASUS kernel source archive:
  `3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8`.
- ASUS reference config:
  `e8605b42cd27d372cea195811c3ff064346390a235572a0018c9dc8d048b5da4`.
- Base Alpine initramfs:
  `100e33ea4bc7e2d568450418bba3617f24394e8bb122a39fd5db334555d3bdca`.
- Accepted Linux 7.1 Image:
  `4d6f3ecaa8d2af0b1e1fddd0655af469e867d596f8f3eae0a20583b058fbe697`.
- Accepted USB2-only recovery DTB:
  `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6`.
- Header-v3 metadata template:
  `0581770a53831e917e51a6c00064dd19c404815000997010ba429a87caad789e`.

The template supplies only the already-reviewed boot header, ramoops command
line, and platform metadata. The repacker replaces its kernel and ramdisk and
replaces the recovery CIDR and timeout. The verifier unpacks the result and
compares both payloads with the v12 files.

## Reproducibility

- Two target initramfs builds were byte-identical.
- Two staging initramfs builds were byte-identical.
- Two fresh ASUS source volumes and two fresh output volumes produced
  byte-identical config, embedded initramfs, build metadata, and Image.
- Two independent header-v3/AVB repacks were byte-identical.
- The complete verifier passed in `acm-only` mode.
- Negative checks rejected `acm-only` with a key, `ssh` without a valid key,
  malformed public-key input, and an unknown access mode.
- The clean-mainline comparator now rejects the same directory through path
  aliases, preventing a false reproducibility pass.

## Accepted v12 products

| Product | Size | SHA-256 |
|---|---:|---|
| ASUS wrapper Image | 69,372,416 | `4d864589e99afd7e6829e26bb823aec01873d34d733221eb8152208d765496a0` |
| ASUS wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| embedded staging initramfs | 26,596,614 | `f1fde63864a2ca11f7334bee4e59689fc4f7f9aebde15591ca1412c1d0cb845e` |
| Linux 7.1 Image | 38,406,656 | `4d6f3ecaa8d2af0b1e1fddd0655af469e867d596f8f3eae0a20583b058fbe697` |
| USB2 recovery DTB | 102,774 | `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6` |
| target initramfs | 5,839,080 | `42f774391b71cb2b34aedab9e3f3160398a3ff2d4db76adf90ae044221429e38` |
| staging initramfs | 26,596,614 | `f1fde63864a2ca11f7334bee4e59689fc4f7f9aebde15591ca1412c1d0cb845e` |
| raw header-v3 image | 95,977,472 | `f4c5cab9f0365ab2c7dee3966233b3650eadd969f9bb334d301dc279009a9a7c` |
| unsigned AVB image | 100,663,296 | `334dcf501dbb0fc20ce2108fdeb5d7d43a5e5d166a3d29612720783c9a028160` |

## Remaining live gate

The phone enumerates on the new Linux host as USB gadget `1d6b:0104` and
`/dev/ttyACM0`, but no v12 phone action was attempted. The host still needs
normal serial permissions plus installed `adb`/`fastboot`. After that, the
first attended test is `fastboot boot` only, credential-free ACM inspection,
proof that every writable mount is RAM-backed, proof that UFS is unavailable,
and observed automatic return to the fallback OS.
