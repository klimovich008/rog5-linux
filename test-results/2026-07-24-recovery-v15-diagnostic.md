# Recovery v15 timing diagnostic

Status: **PASS offline; live timing pending**. This is not a functional
recovery candidate and must never be flashed or used for kexec.

## Question

V13 and v14 both returned the fallback USB gadget 21 seconds after fastboot
disconnected, with no exact recovery product in between. V14 ruled out the
all-block-device policy as the sole cause. Standard pstore supplied no early
console record.

V15 preserves the v14 storage and USB contract but adds bounded delays before
failure rollback:

| Failure reached in `/init` | Added delay | Expected disconnect-to-fallback interval |
|---|---:|---:|
| kernel resets before diagnostic branch | 0 s | about 21 s |
| PM wake lock cannot be acquired | 10 s | about 31 s |
| any block-backed mount is detected | 30 s | about 51 s |
| physical disk/partition lock fails | 50 s | about 71 s |
| all gates pass | none | exact `ROG5_recovery` USB product |

USB remains closed on every failure path. The 180-second watchdog remains
armed for storage failures. No failure path mounts, repairs, formats, or
writes storage.

## Offline result

- Target and staging initramfs layers were each reproduced twice.
- Two fresh output volumes using the two independently prepared v14 source
  trees produced byte-identical config, embedded initramfs, metadata, and
  wrapper Image.
- Two independent header-v3/AVB repacks are byte-identical.
- The complete verifier passes in `acm-only` mode with networking disabled.
- Neither archive contains authorization or private-key material.

## Diagnostic products

| Product | Size | SHA-256 |
|---|---:|---|
| ASUS wrapper Image | 69,372,416 | `a65e6306db562064f18d1724c5b32e0a33f4126362c0bd36fea6c0f5875eec22` |
| ASUS wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| embedded staging initramfs | 26,598,101 | `40608aa12f06c5383626029a69baa08f79c37857775ea17ed04b32171e8a0b4e` |
| Linux 7.1 Image | 38,406,656 | `4d6f3ecaa8d2af0b1e1fddd0655af469e867d596f8f3eae0a20583b058fbe697` |
| USB2 recovery DTB | 102,774 | `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6` |
| target initramfs | 5,838,964 | `2dafd56b858261f30b62316b95afa7375319190e625452952fb3ed9bd8711368` |
| staging initramfs | 26,598,101 | `40608aa12f06c5383626029a69baa08f79c37857775ea17ed04b32171e8a0b4e` |
| raw header-v3 image | 95,977,472 | `c0667d4ce36d7fe837326c7ee589d353f7fe5f448b71090b800ffc6de15364d0` |
| unsigned AVB image | 100,663,296 | `0f11061fbdcac80039d82acf29033f2d24f5d34ad7a57dde909480e3e83f6a35` |
| wrapper metadata | 442 | `2f7f2f6652381976d51eb84cf9d4fe1c27f5212681e92a7e95eb9318f7a548fb` |

The attended live command must set `BOOT_IMAGE` explicitly to the
manifest-pinned v15 AVB image. After measuring one interval, stop and replace
the timing code with a real fix; do not proceed to kexec.
