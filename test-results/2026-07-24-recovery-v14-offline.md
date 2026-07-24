# Recovery v14 offline result

Status: **PASS** for a reproducible, credential-free two-stage recovery bundle
with fail-closed physical-storage isolation. This candidate has not yet been
booted. Nothing was flashed or written to the phone while building it.

## Change from rejected v13

V13 returned to the fallback system before its exact recovery USB product
enumerated. Its storage loop targeted every block object, including volatile
loop, RAM, and zram devices.

V14 retains the pre-USB rejection of every block-backed mount. It then selects
only top-level block objects with a real sysfs `device` and each child carrying
a `partition` marker. On the live fallback inventory this selects all seven
UFS LUNs and 109 partitions while excluding 33 volatile block objects. Every
selected node must accept `blockdev --setro` and return `1` from
`blockdev --getro`; any failure forces rollback before USB exposure.

This narrower policy is the current hypothesis for fixing v13. It is not
accepted until the exact `ROG5_recovery` USB identity and live storage checks
pass.

## Reproducibility

- Target initramfs was built twice and is byte-identical.
- Staging initramfs was built twice and is byte-identical.
- Fresh source/output pairs
  `rog5-asus-v14a-source` / `rog5-asus-v14a-build` and
  `rog5-asus-v14b-source` / `rog5-asus-v14b-build` produced byte-identical
  config, embedded initramfs, metadata, and wrapper Image.
- Both source preparations and wrapper builds used `--network=none`.
- Two independent header-v3/AVB repacks are byte-identical.
- The expanded full verifier passes in a network-disabled container.

## Access and safety contract

- Access mode is `acm-only`.
- Both archives contain no `authorized_keys` or private-key material.
- Both stages arm the 180-second forced-reboot rollback before storage or USB.
- The target DTB keeps UFS, QMP/SuperSpeed, and the secondary USB controller
  disabled.
- The host accepts only the exact recovery USB product, not the fallback
  gadget sharing its vendor/product ID.
- The workflow invokes only `fastboot boot`.

## Accepted v14 products

| Product | Size | SHA-256 |
|---|---:|---|
| ASUS wrapper Image | 69,372,416 | `42066d5f433dfbefda9e025ecf37a32558bc7e76bbd057594ea2ace659e37330` |
| ASUS wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| embedded staging initramfs | 26,597,615 | `f034b62fd9aff9a6a2098899c845e43b315613578ee349003e35189230e9198c` |
| Linux 7.1 Image | 38,406,656 | `4d6f3ecaa8d2af0b1e1fddd0655af469e867d596f8f3eae0a20583b058fbe697` |
| USB2 recovery DTB | 102,774 | `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6` |
| target initramfs | 5,838,985 | `2d91a7c988341b00b63a471a5ecc413e6e7c3363af3af6d3fff33b0ea2bcac00` |
| staging initramfs | 26,597,615 | `f034b62fd9aff9a6a2098899c845e43b315613578ee349003e35189230e9198c` |
| raw header-v3 image | 95,977,472 | `840afff6f5d8041c13619f3070e115357c77f1300fe9c5d6661363403a84feff` |
| unsigned AVB image | 100,663,296 | `9cd6f875b3a32293eda7805ed0d68c09aa7d6b93fc98e096e34328900632a86d` |
| wrapper build metadata | 442 | `7889f5119401e0e9c264f52f17b3493c791d7089ab9c0e5497083fbe49d6207c` |

## Remaining live gate

Use the manifest-pinned v14 image through attended `fastboot boot`. Accept
only `ID_MODEL=ROG5_recovery`, then prove the rollback marker and processes,
RAM-backed root, zero block-backed mounts, and read-only state of every
physical disk and partition. Let the timer return to fallback and repeat
before any attended Linux 7.1 kexec.
