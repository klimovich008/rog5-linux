# Recovery v16 offline result

Status: **PASS offline; live temporary boot pending**. V16 is an attended,
credential-free, RAM-only recovery candidate. It must never be flashed.

## Change from v15

The v15 live timing measurement returned to the known fallback gadget exactly
31 seconds after fastboot disconnected. That interval selected the 10-second
failure branch around `/sys/power/wake_lock`, proving recovery `/init` ran but
storage isolation was never reached.

V16 removes that wake-lock gate and every timing-only diagnostic delay. The
wrapper configuration explicitly has `CONFIG_PM_AUTOSLEEP` disabled, and the
recovery initramfs has no userspace power manager, so no automatic suspend path
needs a wake lock. The 180-second forced-reboot watchdog remains armed before
storage or USB. Any block-backed mount or failure to make a physical disk or
partition read-only still forces rollback while USB is closed.

## Reproducibility

- Target and staging initramfs layers were each produced twice and are
  byte-identical.
- Two fresh wrapper output volumes, using the two independently prepared
  source trees, produced byte-identical config, embedded initramfs, metadata,
  and kernel Image.
- Both wrapper builds ran with container networking disabled.
- Two independent header-v3/AVB repacks are byte-identical.
- The complete verifier passes in `acm-only` mode in a network-disabled
  container.
- The verifier requires `CONFIG_PM_AUTOSLEEP` to be disabled, rejects any
  wake-lock path, checks the armed watchdog, and retains the pre-USB
  physical-storage gate.
- Neither archive contains an authorized key or private-key material.

## Candidate products

| Product | Size | SHA-256 |
|---|---:|---|
| ASUS wrapper Image | 69,372,416 | `de249cd99c8837a0f0cae96870dc0a4bad24a545e326bb8c79bfd2764652a533` |
| ASUS wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| embedded staging initramfs | 26,598,698 | `7a2d79585e38fbb8caebe5a45a19ad871198c20be0b90b29f4b9aaec83d03eb3` |
| Linux 7.1 Image | 38,406,656 | `4d6f3ecaa8d2af0b1e1fddd0655af469e867d596f8f3eae0a20583b058fbe697` |
| USB2 recovery DTB | 102,774 | `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6` |
| target initramfs | 5,839,150 | `adf022557757e44a158f34fb3e4dd3a7a594c32f2d12f4e174b5cd7926b0e043` |
| staging initramfs | 26,598,698 | `7a2d79585e38fbb8caebe5a45a19ad871198c20be0b90b29f4b9aaec83d03eb3` |
| raw header-v3 image | 95,977,472 | `08c3b91dd844daeb8ad068c7639120266b7f238d61d3830148f54e2490edfa8c` |
| unsigned AVB image | 100,663,296 | `019e62ee07b8d2c1bad3d47ae0730dad741df4af14a4a31858fedabdd6200b08` |
| wrapper metadata | 442 | `4035a4818379d1522ca59ce35a98ce33a2e14946633167a4b6ab1ace5e1a95fd` |

## Live gate

Set `BOOT_IMAGE` explicitly to the manifest-pinned v16 AVB image and use only
the guarded `fastboot boot` workflow. Accept the staging environment only if
the host sees exact normalized product `ROG5_recovery`, the root is
RAM-backed, no block-backed mount exists, every physical disk and partition is
read-only, the watchdog and supervised ACM process are alive, and the
180-second timer returns the phone to a changed fallback boot identity. Repeat
the complete staging/rollback cycle before any attended kexec attempt.
