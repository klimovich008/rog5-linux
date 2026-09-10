# Recovery v13 offline result

Status: **PASS** for a reproducible, credential-free two-stage recovery
bundle with fail-closed storage isolation. This is an offline candidate only:
at the time of this report it had not been booted, flashed, or written to the
phone. Its later live attempt returned before exact recovery USB enumeration;
v13 is now rejected. See the
[live result](2026-07-24-recovery-v13-live.md).

## Why v13 supersedes v12

Recovery v12 passed its then-current verifier but remained unbooted after a
final safety audit found that the ASUS staging kernel can enumerate physical
block devices without forcing them read-only. V13 adds the same pre-USB gate
to both initramfs layers:

1. reject any mount whose major:minor exists under `/sys/dev/block`;
2. call `blockdev --setro` for every enumerated block device;
3. verify every device with `blockdev --getro`;
4. force rollback before USB exposure if any check fails.

BusyBox 1.37.0 in both archives supplies `blockdev --setro` and `--getro`.
The verifier checks the init source, call ordering, and applet link in both
layers. Live `BLKROSET` behavior is still a mandatory attended gate.

## Host and builder

- Host: Nobara Linux 44, x86-64, native Btrfs workspace.
- Container runtime: rootless Podman 5.8.4.
- Builder image ID:
  `34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941`.
- Builder image digest:
  `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`.
- Fresh source/output volume pairs:
  `rog5-asus-v13a-source` / `rog5-asus-v13a-build` and
  `rog5-asus-v13b-source` / `rog5-asus-v13b-build`.
- Source preparation, both wrapper builds, comparison, and full verification
  used `--network=none`.

## Access and safety contract

- Access mode is explicitly `acm-only`.
- Neither initramfs contains `authorized_keys` or private-key material.
- SSH starts only when a separately approved public key exists; this candidate
  has none.
- Both stages arm a 180-second forced-reboot rollback and require the PM wake
  lock before storage or USB setup.
- The Linux 7.1 recovery DTB keeps UFS, QMP/SuperSpeed, and the secondary USB
  controller disabled.
- Nothing invokes `fastboot flash`.

No credential was read or used to build or verify v13.

## Pinned inputs

- ASUS kernel source archive:
  `3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8`.
- Accepted Linux 7.1 Image:
  `4d6f3ecaa8d2af0b1e1fddd0655af469e867d596f8f3eae0a20583b058fbe697`.
- Accepted USB2-only recovery DTB:
  `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6`.
- Header-v3 metadata template:
  `0581770a53831e917e51a6c00064dd19c404815000997010ba429a87caad789e`.

## Reproducibility and verification

- Two target initramfs builds were byte-identical.
- Two staging initramfs builds were byte-identical.
- Two fresh ASUS source/output pairs produced byte-identical config, embedded
  initramfs, build metadata, and wrapper Image.
- Two independent header-v3/AVB repacks were byte-identical.
- The complete verifier passed in a network-disabled container.
- The verifier checks nine exact artifact hashes, the embedded archive,
  kernel configuration, USB2-only DTB allowlist, both initramfs layers,
  storage-lock ordering and applet, nested payload hashes, boot header,
  command-line overrides, AVB footer, and credential absence.

## Accepted v13 products

| Product | Size | SHA-256 |
|---|---:|---|
| ASUS wrapper Image | 69,372,416 | `fe84d43f9c8dfb510ab24d04c3d1d1c970e65fc79807acfb356a3ebe9dd3a5d2` |
| ASUS wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| embedded staging initramfs | 26,597,361 | `786843fe2a2f73a889a2615287bd4921270528a9cd5ddbbc2a9b13399ef8c94a` |
| Linux 7.1 Image | 38,406,656 | `4d6f3ecaa8d2af0b1e1fddd0655af469e867d596f8f3eae0a20583b058fbe697` |
| USB2 recovery DTB | 102,774 | `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6` |
| target initramfs | 5,838,955 | `d749b9a6377713b282e42eab35f28e6aa45c388c4c946083edbf67636d163227` |
| staging initramfs | 26,597,361 | `786843fe2a2f73a889a2615287bd4921270528a9cd5ddbbc2a9b13399ef8c94a` |
| raw header-v3 image | 95,977,472 | `ce50bbf45cb0d7419b47b622e06c23763f92d3145935ad04809c39c61f566051` |
| unsigned AVB image | 100,663,296 | `ba25c2b765e92c23d048e0aab7cc4722e448dd97f3c9bd05df7102f34ef15e15` |
| wrapper build metadata | 442 | `481d9157c2455515c1f1175ea1a87aab77dd145143e688575b9773e085cf1f9e` |

## Superseded live gate

The one v13 `fastboot boot` transfer succeeded, but exact recovery USB never
appeared and fallback returned. V14 supersedes it with physical-storage-only
locking and a strict recovery-product host check. Persistent writes and
flashing remain prohibited.
