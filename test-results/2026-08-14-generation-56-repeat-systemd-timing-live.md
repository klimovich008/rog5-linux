# Generation 56 repeat and systemd-timing live result

Date: 2026-08-14

Status: **PASS; consumed forever. Never retry or flash this image.**

The sole RAM-only Generation 56 cycle transferred the byte-identical
`persistent-root-local-image-loader-v34` target once and entered Linux
`7.1.4-gae717d919f87`. Mainline enumerated 116 physical UFS block nodes,
resolved `userdata` as `/dev/sda23` for this boot, mounted `userdata`
and the fixed 16 GiB image `ro,noload`, and kept the OverlayFS upper on
tmpfs. No phone-storage write, flash, partition, or slot operation occurred.

The target passed UFS discovery at 11.909 seconds, entered `switch_root` at
23.371 seconds, and completed the handoff at 25.617 seconds. Retained-loader
attestation passed at target uptime 278.247 seconds, strict key-only SSH was
accepted at uptime 294.70 seconds, and lifecycle acceptance completed in
362.241 seconds. This is 17.759 seconds (4.7%) faster than the approximately
380-second Generation 20 NFS baseline and 17.565 seconds slower than
Generation 55's 344.676-second local-image cycle.

Read-only `systemd-analyze` recorded 43.699 seconds in the kernel and
3 minutes 54.559 seconds in userspace. The critical chain identified:

- `ldconfig.service`: 2 minutes 28.089 seconds;
- `systemd-vconsole-setup.service`: 1 minute 16.694 seconds; and
- `systemd-journal-catalog-update.service`: 32.996 seconds.

The sealed root already contains an exact 20,207-byte `/etc/ld.so.cache`
with SHA-256
`ae57b0740e33f19b3f748bdf8e159a65ecfb828f1339f093d91ec9ef4b8e89ed`.
The services ran because each fresh tmpfs overlay lacked systemd's
`/etc/.updated` and `/var/.updated` markers; the device-unit timings were
not on the critical chain.

A normal systemd reboot returned the exact Alpine fallback on the same USB
location. PMIC PON reported `PS_HOLD`/`HARD_RESET`, no watchdog or fatal
token was found, the maximum observed fallback temperature was 44.8 C, and
host profile cleanup passed. Pstore was unavailable, so absence of crash
evidence remains inconclusive. The mode-restricted private evidence binds
the timing, runtime, stages, intent, fallback identity, and postmortem
records by SHA-256.
