# Active ROG Phone 5 Linux context

Updated: 2026-09-01

Read `docs/current-state.md` for durable device, rescue, storage, charging, and
V11 facts. Historical generations remain in Git and dated `test-results/`.

## One current question

Can the qualified V29 native Wi-Fi stack become a rollback-safe persistent
try-once bundle while preserving signed V11, p24 read-only, slot A, charging,
key-only SSH, and the exact two-node service-state write scope?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, side-port host path `1-1.2`.
- Slot A remains the ASUS WW33 rescue/charging route.
- Slot B currently contains failed standalone loader `f049dc19…`; the phone is
  absent from USB and physical fastboot is required.
- Current V11 fallback boot: unavailable; last proven
  `04ff021c-123c-4e5a-9c5a-b04bfbe24514`.
- Selector/p24 remain v1/V11; old boot_b `2867666c…` and factory backup
  `0a67358d…` are retained with an exact restore plan.
- Last proven Tailscale, key-only SSH, NCM, UFS, and p24 read-only checks pass.
- Native Wi-Fi is not present in persistent V11; its units are inactive.
- Latest battery read: Good, 8.557 V, 30.0 C.
- The background Arch keyring WKD parser failure is unrelated and separately
  queued.

## Newly proven milestone

V29 fixed the source-to-target lifecycle regression and proved systemd, native
Wi-Fi, charging, storage and fallback. The standalone
selector-v2 loader then passed twice from RAM but failed after boot_b install.
That image is retired. Commit `cba1ecf3` instead reuses one selector-v2 source
behind the proven canonical recovery executor wrapper. Local CI passed in
484.483s; exact-head, merge, QEMU and publication passed in run `33557374234`.
Canonical recovery twins `74592579…` preserve wrapper kernel `838425a8…`; AOSP
avbtool 1.4 AVB twins are `f2a73030…`. They are unbooted and unflashed.

## Frozen screen checkpoint

The power-key-toggled text status screen shows time, Wi-Fi/IP and battery with no
desktop or GPU process. V10 physically proved REFGEN, DSI, DRM, fb0, backlight,
status files and direct V11 return. The 60 Hz kernel/DT/userspace is frozen.
Power-button logic passes exact offline tests but remains physically unobserved.
Do not start higher refresh, Pixelworks PQ, GPU, desktop, audio, sensors, or
suspend work during the server MVP.

## Next actions

1. Physically enter exact fastboot and restore old boot_b `2867666c…`.
2. Reboot and prove fresh strict-SSH V11 with selector v1 unchanged.
3. RAM-test canonical `f2a73030…`; do not reuse the standalone loader.
4. Only after repeated canonical passes reconsider boot_b and selector staging.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24/read-only storage scope, V11 fallback, and permanent non-retry after COMMIT.
Do not flash, alter slot A, modify GPT, or send guessed DSI/Iris commands. Keep
the screen off by default and do not add KDE/GNOME/GPU work to this milestone.
