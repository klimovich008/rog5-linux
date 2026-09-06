# Generation 55 retained-loader local-image live result

Date: 2026-08-14

Status: **PASS; consumed forever. Never retry or flash this image.**

The sole RAM-only Generation 55 cycle transferred the exact signed
`persistent-root-local-image-loader-v34` bundle once and entered mainline
Linux `7.1.4-gae717d919f87`. Mainline enumerated 116 physical UFS block nodes,
resolved `userdata` as `/dev/sda23` for this boot, mounted both `userdata` and
the fixed 16 GiB image `ro,noload`, and used a tmpfs OverlayFS upper. No phone
storage write, flash, partition, or slot operation occurred.

The local-root handoff reached `switch_root` 18.613 seconds after the host
received UFS-ready. The target entered `switch_root` at uptime 25.51 seconds.
The retained-musl-loader attestor then passed every storage, UFS-health, and
strict-SSH policy check at uptime 274.44 seconds. Strict key-only SSH was
accepted at uptime 291.33 seconds and 344.676 seconds after lifecycle start,
35.324 seconds (9.3%) faster than the approximately 380-second Generation 20
NFS baseline.

The accepted runtime record reported:

- two block-backed mounts and both ext4 layers `ro,noload`;
- zero blocked device queries and SCSI commands;
- zero journal-recovery and UFS-error events;
- all backlights off; and
- strict key-only SSH.

A normal systemd reboot returned the exact Alpine fallback. The fallback boot
ID was independently proved, PMIC PON reported `PS_HOLD`/`HARD_RESET` with no
watchdog marker, the maximum observed fallback temperature was 45.8 C, and
host network/profile cleanup passed. Pstore was unavailable, so absence of a
crash record remains inconclusive.

The private evidence directory is mode-restricted outside Git. Its principal
runtime, diagnostic, stage, timing, and intent records are bound by SHA-256 in
the retained private manifest. Generation 55 is revoked in the committed boot
policy and cannot be consumed again.
