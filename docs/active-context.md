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

This remains offline readiness, not physical display acceptance.

The display baseline now builds as `7.1.4-rog5-display60-v1`. It contains one
AMS678 ER2 60 Hz DSC mode and requires a proved Pixelworks Iris6 analog-bypass
GPIO state before transmitting panel commands. The exact DT delta enables only
DSI0, its PHY, MDSS/DPU, L12/L13, the reviewed GPIOs, and the panel graph. The
candidate DT SHA-256 is
`1806104ab0efa1a80cc1c55f81e236f8f9f8cde055c6cb2dad3cea303869ba96`.
No display candidate has been issued or booted.

## Next actions

1. Freeze the display source and run the active tier plus one full local CI.
2. Publish the coherent source checkpoint and verify exact-head CI.
3. Compose one signed RAM-only target from the exact kernel, matching modules,
   DTB, and status userspace; keep screen off by default.
4. Use one live cycle to answer whether DRM/DSI/panel initializes, exposes the
   text console, and returns to V11 fallback. Collect adjacent charging, Wi-Fi,
   storage-isolation, and display dmesg evidence without making optional fields
   fatal.
5. Test repeated power-key blank/unblank only after safe panel registration is
   proven. Keep 90/120/144 Hz and Pixelworks PQ disabled.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24/read-only storage scope, V11 fallback, and permanent non-retry after COMMIT.
Do not flash, alter slot A, modify GPT, or send guessed DSI/Iris commands. Keep
the screen off by default and do not add KDE/GNOME/GPU work to this milestone.
