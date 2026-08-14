# Generation 54 fast-attestation live result

Date: 2026-08-14

Status: **consumed; never retry or flash. The RAM-only cycle returned the exact
Alpine fallback and completed host cleanup.**

The cycle ran from exact repository head
`0b7e6b6e81ba372563da1b96a8c57fec452e00f5`. Its private evidence is retained
outside Git at
`/home/deck/.local/state/rog5-generation54-fast-attest-live-20260814.dV94Vb`.
The durable claim entered at 01:55:23 local time. The sealed recovery boot took
12.828 seconds, the signed v33 bundle transferred exactly once, and mainline
reported the same target boot ID through every retained stage.

Read-only UFS and local-root startup remained healthy. The first `ufs-ready`
record arrived at host monotonic 165622.522572. `switch_root` passed at
165641.045899, 18.523 seconds later. Both ext4 layers were `ro,noload`, the
16 GiB image was attached as read-only `/dev/loop0`, the tmpfs OverlayFS root
started systemd, stable NCM remained reachable, and the host pinned the
volatile key-only SSH identity at 02:00:48.

The new markers isolated one implementation defect. Attestation began at
target uptime 265.13 seconds and failed at 266.72 seconds with
`local-image loop is not exact and read-only`. A read-only SSH inspection
proved that the loop was actually exact: `ro=1`, 33,554,432 sectors
(17,179,869,184 bytes), and the expected backing path. The command failed
before reading those values because `/run/initramfs/bin/busybox` is a
musl-dynamic AArch64 ELF requesting `/lib/ld-musl-aarch64.so.1`. After
`switch_root`, that interpreter exists only at
`/run/initramfs/lib/ld-musl-aarch64.so.1`; direct BusyBox execution therefore
returned `ENOENT`. The private diagnostic record is mode `0600` and has
SHA-256 `e6b9baea9f9e5c24be453372be267d8547fc1e50e631f818e58bad6cbcc7443e`.

The bounded target rollback returned exact Alpine. Strict fallback SSH,
NetworkManager profile restoration, `FALLBACK_RETURNED` intent resolution,
and final host cleanup passed. The temporarily stopped SteamOS debug socket
was restored to its prior enabled and active state. No flash, partition,
filesystem write, or persistent installation occurred.

Generation 54 is revoked in both policy and inventory. Its failure is fully
discriminating, so no Claude escalation was required.
