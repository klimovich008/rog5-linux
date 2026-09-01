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
- Slot B still selects persistent signed V11.
- Current V11 fallback boot: `04ff021c-123c-4e5a-9c5a-b04bfbe24514`.
- Tailscale, key-only SSH, NCM, UFS, and p24 read-only pass.
- Native Wi-Fi is not present in persistent V11; its units are inactive.
- Latest battery read: Good, 8.557 V, 30.0 C.
- The background Arch keyring WKD parser failure is unrelated and separately
  queued.

## Newly proven milestone

V29 fixed the source-to-target lifecycle regression and proved systemd, native
`wlp1s0` carrier/DHCP, safe charging, p24 read-only, and V11 fallback. V29 is
consumed. The installed boot_b remains selector-v1-only. The reproduced
selector-v2 loader ramdisk (`8adfa164…`) passed twice from RAM using distinct
AVB identities (`ca2393cf…`, `eadfc39f…`); each traversed recovery and returned
a fresh strict-SSH V11 while leaving selector-v1 and p24 unchanged.

## Frozen screen checkpoint

The power-key-toggled text status screen shows time, Wi-Fi/IP and battery with no
desktop or GPU process. V10 physically proved REFGEN, DSI, DRM, fb0, backlight,
status files and direct V11 return. The 60 Hz kernel/DT/userspace is frozen.
Power-button logic passes exact offline tests but remains physically unobserved.
Do not start higher refresh, Pixelworks PQ, GPU, desktop, audio, sensors, or
suspend work during the server MVP.

## Next actions

1. Build the final signed `persistent-native-root-wifi` try-once bundle.
2. Generate selector v2 against exact V11 fallback without staging it.
3. RAM-test the selector-v2 loader with that selector before any boot_b update.
4. Only then stage p24 and perform one persistent Wi-Fi trial.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24/read-only storage scope, V11 fallback, and permanent non-retry after COMMIT.
Do not flash, alter slot A, modify GPT, or send guessed DSI/Iris commands. Keep
the screen off by default and do not add KDE/GNOME/GPU work to this milestone.
