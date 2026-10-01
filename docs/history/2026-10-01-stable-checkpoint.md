# Stable checkpoint 2026-10-01 (tag `stable-2026-10-01`)

What changed since the 0.1.0-alpha source (33f9f852), all installed and
tested on the phone. Default `main-k113-d13-261001a` (two committed boots,
s2idle, Wi-Fi, audio, sensors, GPU), fallback `safe-k111-d10-261001a`
(rehearsed). Details: [current state](../current-state.md),
[bundles](../bundles.md).

## Memory: +650 MiB of RAM (MemTotal 10.36 → 11.0 GiB)

- **d13 memslim** (`scripts/device/compose-memslim-dtb.sh`): unused
  carve-outs handed back to Linux: stock CMA pools 196 MiB, ION pools
  128 MiB, PIL regions of subsystems that never run (modem, camera, cvp)
  266 MiB. Each part passed its RAM trial (pressure into every freed range
  with write and exec probes, s2idle, Wi-Fi restart, no SEA/SError):
  [memory footprint §6](../../test-results/2026-10-01-memory-footprint.md).
- **k113 / 0153**: SWIOTLB 64 → 4 MiB with dynamic pools (the bounce pool
  never went above 4 slabs): +60 MiB.
- **rog5-memory-tune**: malloc hugetlb off for the session (glibc tunable),
  THP/zram settings in `/etc/rog5/memory`; `rog5-mem-report` for snapshots,
  start-up timing and pressure tests.

## Robustness

- **0151** cs35l45: the speaker-protection DSP recovers from a missed pause
  (it used to wedge silent after DP/HDMI use): quick-stop test PASS.
- **0152** msm: the GPU recovers when the GMU stops answering;
  `rog5-gpu-watchdog` reboots if it stays dead.
- Installer: atomic `exch` swap and a proven read-only remount before
  activation (no more EBUSY on p24).
- Device profile: per-phone boot values; the overlay grows to the userdata
  size of each phone variant.

## Desktop mode (Phosh ↔ GNOME on a monitor)

- Work in progress (shader compiles, games, audio, fullscreen, inhibitors)
  keeps GNOME from idling back to Phosh.
- **rog5-session-carry**: a switch no longer just kills the apps; they quit
  cleanly (browsers keep their tabs) and reopen in the other session (same
  boot, within 5 min; exclusions in `session-carry.conf`).

## Tried and rejected (kept for reference)

- GNOME Shell Mobile (opt-in packages, selector, watchdog with fallback to a
  locked Phosh, stride fix 0005): works, but the user prefers Phosh + GNOME.
- KDE Plasma Mobile 6.7.5: removed again
  ([trial](../../test-results/2026-10-01-kde-plasma-trial.md)).

## Measured, not changed

- Graphics memory in GNOME desktop mode ~440 MiB of shared RAM (normal);
  USB-C via the monitor hub: 9 V, ADSP input cap ~12.5 W; CPU video
  decode/encode figures:
  [2026-10-01-vram-usb-power-video](../../test-results/2026-10-01-vram-usb-power-video.md).

## Next

Hardware video decode/encode (Iris on SM8350), standby trials on battery,
bottom-port charging (branch `agent/usb-bottom-charging-20261001`, needs a
power-meter test).
