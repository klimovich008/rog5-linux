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
- Slot B contains the canonical selector-v2-capable recovery `f2a73030…`.
- Current V11 fallback boot: `fcdab471-3c8d-45d8-beaf-cd06749bdedb`, with
  strict SSH, NCM, Tailscale, charging, UFS and safe thermals passing.
- Selector/p24 remain v1/V11. Old boot_b `2867666c…` and factory backup
  `0a67358d…` remain retained as recovery artifacts.
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
avbtool 1.4 AVB twins are `f2a73030…`. The exact raw composition passed two
RAM boots with distinct AVB identities and one persistent slot-B boot, always
returning to unchanged selector-V1/V11. See
`test-results/2026-09-01-canonical-selector-v2-live.md`.

## Frozen screen checkpoint

The power-key-toggled text status screen shows time, Wi-Fi/IP and battery with no
desktop or GPU process. V10 physically proved REFGEN, DSI, DRM, fb0, backlight,
status files and direct V11 return. The 60 Hz kernel/DT/userspace is frozen.
Power-button logic passes exact offline tests but remains physically unobserved.
Do not start higher refresh, Pixelworks PQ, GPU, desktop, audio, sensors, or
suspend work during the server MVP.

## Next actions

1. Reverify the signed Wi-Fi primary, V11 fallback and selector-v2 staging set.
2. Stage the bounded try-once set on p24 and relock it read-only.
3. Boot once to answer whether persistent native Wi-Fi reaches systemd, SSH,
   charging and safe thermals, then prove automatic V11 fallback.
4. Promote the primary only after repeated accepted try-once evidence.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24/read-only storage scope, V11 fallback, and permanent non-retry after COMMIT.
Do not flash, alter slot A, modify GPT, or send guessed DSI/Iris commands. Keep
the screen off by default and do not add KDE/GNOME/GPU work to this milestone.
