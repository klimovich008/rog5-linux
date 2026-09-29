# ROG5 current state

Native Arch Linux ARM on the ASUS ROG Phone 5 (SM8350) with Phosh as the
phone shell and GNOME as the desktop mode on an external display. Linux
7.2.7 with the `patches/linux-7.2.7` series; cellular is out of scope.

<!-- BEGIN GENERATED: scripts/host/render-current-state.py from docs/status/components.json -->
Status as of 2026-09-29 (r187) (source: `docs/status/components.json`).

| | Bundle | Kernel build | DTB | Installed |
|---|---|---|---|---|
| Default | `production-7.2.7-r189` | 7.2.7 build r92 | platform-cpucap-dp-sbumux-dtb-r2 (`09094112`) | 2026-09-29 |
| Fallback | `production-7.2.7-safe-r7` | 7.2.7 build r69 | platform-usbbtm-dtb-r2 (`bafe0488`) | kept on p24 as the fallback |

Components: 29 ready, 10 partial, 6 needs a test, 13 missing.

Partial:

- Boot & updates / Unattended package updates: may reboot while the phone is used as a server (idle = backlight off)
- Boot & updates / Boot time: ~75 s to Phosh; initramfs waits, UFS 9.5 s
- Display & shell / Brightness: about 4 real steps
- External display / GNOME desktop mode: switching closes all apps
- Connectivity / Wi-Fi: stable MAC/IP since 2026-09-29; 11 s reconnect after wake
- USB / Bottom port (USB 2.0 host): 5 V switched by hand
- Power / Idle background wakeups: desktop-mode switcher and sleep policy poll
- Performance / Performance mode: rog5-perf-mode CLI; no toggle in Phosh yet
- Sensors & hardware / RGB logo LED
- Server / Journal retention: 200 MB cap keeps ~11 h

Needs a test:

- Boot & updates / Boot splash: r187 keeps the bootloader logo until phoc (0107/0108); needs a visual check
- Display & shell / Phosh: hotplug crash fixed in phosh 0.57.0-1.1 (lock shields); needs a real plug/unplug test
- External display / DP-only without perf pin: 0106 NoC QoS candidate
- Connectivity / Hotspot
- Power / Battery standby measurement: needs the phone unplugged
- Audio / Bluetooth audio

Missing:

- Boot & updates / Reboot to fastboot: reboot argument ignored by the shutdown script
- Display & shell / High refresh rate: 60 Hz only
- External display / HBR2 / higher modes: lane-1 errors
- Connectivity / Bluetooth headset mic (HFP)
- Connectivity / Cellular modem: out of scope
- Connectivity / GPS
- Connectivity / NFC
- Power / Deep standby (CX/DDR collapse): DDR held at 200 MHz by another RPMh master; ~79 mA
- Audio / Earpiece
- Audio / 3.5 mm jack
- Sensors & hardware / Cameras
- Sensors & hardware / Fingerprint
- Sensors & hardware / AirTriggers

<!-- END GENERATED -->

## Where to look

- [What's left](whats-left.md): the short list, the status map and the tests
  that need the user's hands. [User irritations](user-irritations.md) has
  causes and fixes.
- [Development](development.md): build, RAM trial, install a default,
  rescue, the fast module loop.
- Newest results: `ls -t test-results/2026-09-* | head`, and the month index
  [test-results/README.md](../test-results/README.md).
- Reusable lessons: grep `development-lessons.md` for the specific issue.
- History: the July-September log that used to be this file is
  [history/current-state-log-2026-07-to-09.md](history/current-state-log-2026-07-to-09.md)
  (318 KB; grep it). Archived code and docs:
  [history/cleanup-2026-09-29.md](history/cleanup-2026-09-29.md).

## Boot chain (summary)

Slot A is stock ASUS WW33 (charging and rescue). boot_b holds a 96 MiB ASUS
5.4 wrapper whose recovery initramfs mounts p24 `arch_root_a`, reads
`/boot/rog5-linux/selector`, verifies the Ed25519-signed inner bundle (Image,
DTB, initramfs, manifest) and kexecs it. An uncommitted boot of the primary
falls back to the fallback bundle. The root is p24 (read-only lower) with an
overlay on `userdata:/rog5/root/root-overlay-v1.ext4`. Trials RAM-boot a
128 MiB wrapper with `production-ram-trial.py` (no flashing); a trial image
becomes the default with `install-default-kernel.py`.

## Keeping this file current

`docs/status/components.json` is the only status source:

1. Edit it: `bundles` (default and fallback after an install) and the
   component statuses (`ready`, `partial`, `untested`, `missing`).
2. `python3 scripts/host/render-current-state.py` rewrites the block above;
   `python3 tools/status-map/render.py` redraws `images/status-map.svg`.
3. `scripts/host/test-render-current-state.py` (active tier) fails when the
   block and the JSON disagree.

Put narrative in a dated `test-results/` report and reusable lessons in
`development-lessons.md`, not here.
