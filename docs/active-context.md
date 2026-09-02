# Active ROG Phone 5 Linux context

Updated: 2026-09-01

Read `docs/current-state.md` for durable device, rescue, storage, charging, and
V11 facts. Historical generations remain in Git and dated `test-results/`.

## One current question

Can a bounded p23-backed persistent OverlayFS upper make package/keyring updates
survive reboot while preserving accepted Wi-Fi V3, signed V11, read-only p24,
slot A and exact storage-write scope?

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
- The empty volatile pacman GPG directory causes the WKD failure; no parser or
  package mutation has been applied.

## Newly proven milestone

Wi-Fi V2 fixed the trial-helper, record and boot-timer defects but retained the
probe's independent 600-second reboot timer. The first soak proved the exact
reset. V3 disarms both timers, passed two clean boots and completed 720 samples
over 2h12m43s. Strict NCM/Wi-Fi SSH, Tailscale, power, thermals and storage all
passed. The active tier is 3.145s, full local CI 479.665s, and GitHub run
`33572144028` passed. See `test-results/2026-09-02-persistent-wifi-v3-soak.md`.

## Frozen screen checkpoint

The power-key-toggled text status screen shows time, Wi-Fi/IP and battery with no
desktop or GPU process. V10 physically proved REFGEN, DSI, DRM, fb0, backlight,
status files and direct V11 return. The 60 Hz kernel/DT/userspace is frozen.
Power-button logic passes exact offline tests but remains physically unobserved.
Do not start higher refresh, Pixelworks PQ, GPU, desktop, audio, sensors, or
suspend work during the server MVP.

## Next actions

1. Define the smallest p23-backed persistent overlay image and shutdown order.
2. Prove image creation, exact mount scope, update persistence and relock in
   hardware-free tests before any phone write.
3. Stage and boot it through the existing signed try-once path, then verify
   pacman keyring initialization, an update, clean reboot and V11 rescue.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24/read-only storage scope, V11 fallback, and permanent non-retry after COMMIT.
Do not flash, alter slot A, modify GPT, or send guessed DSI/Iris commands. Keep
the screen off by default and do not add KDE/GNOME/GPU work to this milestone.
