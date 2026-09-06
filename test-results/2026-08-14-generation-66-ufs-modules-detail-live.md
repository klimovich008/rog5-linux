# Generation 66 local-image Arch live result

Date: 2026-08-14

Result: **PASS. The sole RAM-only Generation 66 cycle reached exact UFS,
local-image Arch Linux, systemd, and strict key-only SSH in 328.363 seconds,
then returned to exact Alpine fallback. Generation 66 is consumed and must
never be retried or flashed.**

The cycle ran from exact reviewed repository head
`e9f47600f95ca636f24a47aa25a1ba943525f7a2`. Exact-head, merge-compatibility,
QEMU, and candidate-publication CI passed before the boot. The target boot ID
was `eabe1d14-df19-479b-ac36-662af8698126`.

The four sealed UFS modules loaded and the target advanced from `ufs-ready`
entry to `storage-locked` in 5.029 seconds. It then resolved exact userdata
`/dev/sda23`, mounted userdata and the 16 GiB local image `ro,noload`, verified
the persisted Generation 64 marker, mounted the tmpfs OverlayFS, and completed
`switch_root`. Runtime acceptance reported:

- Linux `7.1.4-gae717d919f87`;
- 116 read-only physical block nodes and exactly two block-backed mounts;
- zero blocked block queries, blocked SCSI commands, journal-recovery events,
  and UFS errors;
- no backlight device; and
- strict key-only SSH with one volatile Ed25519 host key.

No NFS root was used. No flash, slot, GPT, partition, erase, format, or raw
phone-storage operation occurred. The successful target path made no new
persistent write; it only verified the exact marker written by Generation 64.

`systemd-analyze` measured 46.229 seconds in the kernel and 3 minutes 2.754
seconds in userspace. End-to-end accepted SSH was 51.637 seconds faster than
the approximately 380-second Generation 20 NFS reference. The measured
critical path still included `systemd-resolved.service` at 21.119 seconds,
`dbus-broker.service` at 53.485 seconds, `sshd.service` at 10.070 seconds, and
the final storage/SSH attestation at 42.800 seconds. Device-unit blame is not
by itself proof of serialized delay.

Normal systemd reboot returned Alpine with distinct boot ID
`67d5e984-78b1-4145-9e07-888ea140551e` on the exact original USB port. The
signed fallback postmortem recorded exact `PS_HOLD` / `HARD_RESET`, no PMIC
watchdog signal, zero fatal tokens, and maximum temperature 41.5 C. Pstore was
unavailable and remains inconclusive. Intent resolution was exactly
`TARGET_ACCEPTED`; fallback profile restoration, host cleanup, and restoration
of the unrelated Steam socket passed.

Private evidence remains outside Git. Selected file identities are:

- stage records: `fcea605b8c9a8cbc6747ee0219f88849917813fb66715c24d9baa286434e1610`;
- runtime: `5d3254c6a97eba38f804a02446db7f2fa1bb31e50c5f6e6698b469817024b5dc`;
- diagnostics: `21cdb33288ddd01695e6506599c29f57753e2c086411313388ad39dd21b33666`;
- signed fallback postmortem:
  `9f4b48bb47a11d5ce2cf8bcc0d25c68739a5639e4db9daf279ecf190765874a9`;
  and
- timing record: `015a4eb7f7ac249fda267d4ffbc6befad5f0b1d2c5b1235654605bfe9d3e3a65`.
