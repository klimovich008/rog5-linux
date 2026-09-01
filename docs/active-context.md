# Active ROG Phone 5 Linux context

Updated: 2026-09-01

Read `docs/current-state.md` for durable device, rescue, storage, charging, and
V11 facts. Historical generations remain in Git and dated `test-results/`.

## One current question

Can persistent Wi-Fi V3 sustain multi-hour Wi-Fi/Tailscale/charging
liveness and unattended reboot/rescue while preserving signed V11, p24
read-only, slot A and the exact two-node service-state write scope?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, side-port host path `1-1.2`.
- Slot A remains the ASUS WW33 rescue/charging route.
- Slot B contains the canonical selector-v2-capable recovery `f2a73030…`.
- Current boot: Wi-Fi V3 `e4424825-a7b0-4d33-8a4f-fcad3f9e479b`, kernel
  `7.1.4-g1eea8970e87f`, with systemd, native Wi-Fi, NCM, Tailscale and strict
  SSH active.
- Selector `47fe38b7…` chooses signed primary manifest `3848a474…`; signed V11
  remains the fallback. Old boot_b `2867666c…` and factory `0a67358d…` remain.
- P24 is read-only; exactly `sda` and `sda23` are writable. Battery is Full/Good
  at 30.0 C and the latest maximum thermal-zone reading is 37.1 C.
- The background Arch keyring WKD parser failure is unrelated and separately
  queued.

## Newly proven milestone

Wi-Fi V2 fixed the trial-helper, record and boot-timer defects but retained the
probe's independent 600-second reboot timer. The first soak proved the exact
reset. V3 disarms both timers and passed two clean boots; soak run 2 is active.
The active tier is reduced from 103.099s to 3.191s, V3 twin target build took
6.830s, and GitHub run `33568444295` passed. See
`test-results/2026-09-02-persistent-wifi-v2-live.md`.

## Frozen screen checkpoint

The power-key-toggled text status screen shows time, Wi-Fi/IP and battery with no
desktop or GPU process. V10 physically proved REFGEN, DSI, DRM, fb0, backlight,
status files and direct V11 return. The 60 Hz kernel/DT/userspace is frozen.
Power-button logic passes exact offline tests but remains physically unobserved.
Do not start higher refresh, Pixelworks PQ, GPU, desktop, audio, sensors, or
suspend work during the server MVP.

## Next actions

1. Run a bounded multi-hour Wi-Fi/Tailscale/NCM/power liveness observation.
2. Reconfirm one unattended clean reboot and the unchanged V11 rescue path at
   the next publication milestone; do not mutate healthy trial state merely to
   manufacture a fallback.
3. Define and deploy the first persistent server workload after the soak passes.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24/read-only storage scope, V11 fallback, and permanent non-retry after COMMIT.
Do not flash, alter slot A, modify GPT, or send guessed DSI/Iris commands. Keep
the screen off by default and do not add KDE/GNOME/GPU work to this milestone.
