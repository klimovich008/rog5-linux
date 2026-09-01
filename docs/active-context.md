# Active ROG Phone 5 Linux context

Updated: 2026-09-01

Read `docs/current-state.md` for durable device, rescue, storage, charging, and
V11 facts. Historical generations remain in Git and dated `test-results/`.

## One current question

Can the retained WW33 AMS678 ER2 and Pixelworks Iris/i6 description be reduced
to a safe 60 Hz-only mainline DRM path that exposes fbdev for the minimal status
screen, without regressing Wi-Fi, charging, storage isolation, or fallback?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, side-port host path `1-1.2`.
- Slot A remains the ASUS WW33 rescue/charging route.
- Slot B still selects persistent signed V11.
- Current V11 fallback boot: `f70ba888-af07-492c-920d-75fef09313b5`.
- State, Tailscale, key-only SSH, NCM, UFS, and p24 read-only checks pass.
- Latest battery read: Full/Good, 8.573 V, 30.0 C.
- The background Arch keyring WKD parser failure is unrelated and separately
  queued.

## Newly proven milestone

V29 fixed the source-to-target lifecycle regression. The phone-local transaction
stopped Tailscale and persistent state, verified all 117 UFS nodes read-only,
and entered the exact signed Wi-Fi target. Target boot
`54a5e437-9a04-402a-b14e-01dbcb8a3b5d` reached `switch-root PASS`, systemd,
working `wlp1s0` carrier/DHCP, and safe battery telemetry before normal V11
fallback. V29 is consumed and must never be reused. See
`test-results/2026-09-01-native-wifi-v29.md`.

## Initial screen checkpoint

The power-key-toggled text status screen uses one compact userspace path:

- existing exact power-key press handling;
- idempotent screen on/off/toggle;
- a `tty1` status renderer for time, Wi-Fi interface/IP, and battery state;
- immediate render on power-button wake;
- one-second refresh only while on and a 30-second sleep while off;
- no SSID, MAC, desktop, compositor, GPU, or block-device access.

This is offline userspace readiness, not physical display acceptance.

The accepted kernel already enables DRM/MSM/DPU/DSI, fbdev emulation, VT, and
PMK8350 power-key input. The accepted DT intentionally disables MDSS, both DSI
controllers, both DSI PHYs, and has no panel/bridge node. Retained WW33 data
identifies the panel as Samsung AMS678 ER2, 1080x2448 command mode with DSC and
60/90/120/144 profiles behind Pixelworks Iris/i6. Current upstream has no exact
AMS678 or Iris/i6 bridge driver.

## Next actions

1. Finish focused and active-tier validation of the status-screen userspace and
   publish the checkpoint.
2. Extract only the WW33 60 Hz panel mode, reset/power GPIOs, supplies, DCS
   command sequence, DSC parameters, and Iris analog-bypass requirements.
3. Implement the smallest panel plus bridge/bypass source and DT delta. Keep
   90/120/144 Hz disabled until 60 Hz on/off is stable.
4. Run offline DT graph, regulator, GPIO, command-sequence, and driver tests.
5. Use one RAM-only phone cycle first to prove DRM/DSI/panel registration and
   safe fallback; only a later cycle should test visible status and power-key
   blank/unblank.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24/read-only storage scope, V11 fallback, and permanent non-retry after COMMIT.
Do not flash, alter slot A, modify GPT, or send guessed DSI/Iris commands. Keep
the screen off by default and do not add KDE/GNOME/GPU work to this milestone.
