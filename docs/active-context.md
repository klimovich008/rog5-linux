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
Display60 V1 is consumed and must never be retried. It entered the exact target
kernel and passed UFS/storage, then emitted `runtime FAIL` before switch-root.
The cause is the optional status installer using an unexposed BusyBox command,
the wrong pre-switch-root destination, and an uncreated wants directory. Exact
fastboot and fresh V11 fallback were proven; no panel result was reached.

Display60 V2 is also consumed. It fixed the runtime boundary and emitted
`switch-root PASS`, then returned automatically to fresh V11 before target SSH.
Display60 V3 disabled Wi-Fi startup and reached target SSH, disproving a display
panic at that boundary. Status userspace, NCM, battery, storage and fallback
worked. Display failed earlier: DSI `vdda` and PHY `vdds` were dummy, REFGEN was
unavailable, DSI deferred, and its PLL did not lock. V3 is consumed.

Display60 V4 removed both dummy-supply warnings but module-based REFGEN was not
available to the built-in DSI probe. A matching V11 module probe bound
`88e7000.regulator` and created `/sys/class/regulator/.../name=refgen`, proving
the driver and base DT. REFGEN is now built in; `Module.symvers` is unchanged.

Display60 V5 reached switch-root and remained alive on NCM, but only its fresh
ephemeral SSH key appeared. Strict host-key pinning correctly refused it; the
persistent key never arrived before automatic rollback. The runner's 870-second
envelope also ended 30 seconds before the 900-second rollback. V5 is consumed.

The offline architecture checkpoint is complete. The signed display-diagnostic
archive now installs one read-only systemd observer that sends an exact record
to `169.254.77.1:8077`. Its host collector validates candidate, release, boot
ID, source/destination, fixed field order, bounds, hex and dmesg hash. It does
not use SSH, toggle the panel, or touch storage. The exact V5 BusyBox accepted
all shell and applet options. Focused tests took 1.813 seconds; the active tier
took 101.965 seconds.

## Next actions

1. Freeze and publish the observer checkpoint, then compose one successor from
   the unchanged V5 kernel/DT/modules plus the new initramfs only.
2. Start the NCM collector before COMMIT and use a 1,020-second parent envelope;
   preserve strict SSH host-key pinning as a later acceptance layer.
3. Use the successor only to determine REFGEN/DSI/DRM/fb/backlight state.
4. Test repeated power-key blank/unblank only after safe panel registration is
   proven. Keep 90/120/144 Hz and Pixelworks PQ disabled.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24/read-only storage scope, V11 fallback, and permanent non-retry after COMMIT.
Do not flash, alter slot A, modify GPT, or send guessed DSI/Iris commands. Keep
the screen off by default and do not add KDE/GNOME/GPU work to this milestone.
