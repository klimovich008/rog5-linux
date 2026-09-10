# Generation 53 local image staged on phone

Date: 2026-08-13

Status: **PASS. One bounded 16 GiB ext4 image exists inside userdata; no
partition, GPT, boot slot, or raw block-device write occurred. Generation 53
has not been booted.**

The phone was the exact Alpine fallback on
`5.4.134-qgki-perf-00001-g6c308144c23e`, boot ID
`6f194272-a573-4750-9f83-4978c6237514`, with writable userdata mounted from
`/dev/sdb23`. Before staging, the previously paused `/root/usr` target was
revalidated as exactly two directories and four root-owned, single-link APK
members with their recorded hashes. Those four explicit files were removed,
then the two empty directories were removed. No wildcard or recursive delete
was used, and `/root/usr` is absent.

The retained 536,746,495-byte Arch archive and root verifier in fallback
tmpfs matched their pinned hashes. The current stager and 7,526,400-byte
root-owned AArch64 libarchive runtime were copied only to `/run`. The
production preflight passed without a phone-storage write. Valid thermal
sensors were between 26 and 37.5 degrees Celsius, no loop device was active,
and userdata had approximately 191 GiB free.

The armed staging operation ran from 23:32:38 to 23:33:13 CEST and completed
in 34.718 seconds. It created only
`/rog5/images/arch-local-a.ext4.partial`, populated and verified it, then
atomically published:

```text
/rog5/images/arch-local-a.ext4
```

Exact published identity:

- size: `17179869184` bytes;
- owner, group, mode, links: `0:0:0600:1`;
- filesystem: ext4;
- UUID: `598a876b-a8db-4859-a01a-1b864b0a87f4`;
- label: `ROG5_ARCH_A`;
- image SHA-256:
  `8f036257f9b9857450281afd3f39232835586199d0c80edb16e78b6136154697`;
- root tree SHA-256:
  `4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167`;
- root seal SHA-256:
  `02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876`.

An independent second pass reproduced the full 16 GiB image hash, passed
`e2fsck -fn`, attached the image through a read-only loop, mounted it
`ro,noload,nodev,nosuid,noatime`, verified the complete root seal and the
exact systemd, sshd, and deployment authorized-key identities, then unmounted
and detached it. No partial image, loop device, or verification mountpoint
remained.

The next separate action is the one-use, RAM-only Generation 53 lifecycle.
The target must keep userdata and the image read-only, use only tmpfs for its
OverlayFS upper, reach key-only SSH, record timing against Generation 20, and
return to exact Alpine fallback. Never flash the Generation 53 wrapper.
