# ROG5 current state

Native Arch Linux ARM on the ASUS ROG Phone 5 (SM8350) with Phosh as the
phone shell and GNOME as the desktop mode on an external display. Linux
7.2.7 with the `patches/linux-7.2.7` series; cellular is out of scope.

<!-- BEGIN GENERATED: scripts/host/render-current-state.py from docs/status/components.json -->
Status as of 2026-09-30 (r201) (source: `docs/status/components.json`).

| | Bundle | Kernel build | DTB | Installed |
|---|---|---|---|---|
| Default | `production-7.2.7-r201` | 7.2.7 build r104 (series to 0143, without 0125-0129/0136-0139) | platform-cpucap-dp-sbumux-dtb-r7 (`99bcf5f8`) | 2026-09-30 |
| Fallback | `production-7.2.7-safe-r7` | 7.2.7 build r69 | platform-usbbtm-dtb-r2 (`bafe0488`) | kept on p24 as the fallback |

Components: 34 ready, 11 partial, 7 needs a test, 17 missing.

Partial:

- Boot & updates / Boot time: ~56 s to multi-user on r201 (23 s kernel + initramfs, 33 s userspace); Wi-Fi at ~57 s
- Display & shell / Brightness: about 4 real steps
- External display / GNOME desktop mode: event-driven, fail-closed switcher; mode manual until one supervised boot test; switching closes apps
- Connectivity / Wi-Fi: stable MAC/IP since 2026-09-29; 11 s reconnect after wake
- USB / Replug recovery (-71): rog5-usb-reconnect re-initialises the controller; kernel fix (0142 retries / 0143 session override) needs the one-replug test
- USB / Bottom port (USB 2.0 host): 5 V switched by hand (rog5-usb-bottom on); stage B (RT1715 + TCPM, automatic 5 V) built as DT feature usbbtmtc, not composed; needs a power-meter test
- Power / Idle background wakeups: desktop-mode switcher event-driven (~0.1 % CPU), tailscaled retry loop gone; sleep policy still polls every 5 s
- Performance / Performance mode: rog5-perf-mode auto: performance limits on external power with a DP display; no toggle in Phosh yet
- Audio / 24-bit playback: the S24_LE front end (q6asm PCM_V2) reaches the amps far below full scale; PipeWire forced to S16LE
- Sensors & hardware / RGB logo LED
- Apps / Steam (native arm64): Valve's aarch64 client; x86 games through FEX (Half-Life ran); title-bar drag does nothing in GNOME

Needs a test:

- Boot & updates / Unattended package updates: reboots only when idle (no remote client, no sound, 01-06 window); snapshots exclude user data (~6 GB); v2 restore passed fault injection, not yet a real rollback
- Boot & updates / Boot splash: r187 keeps the bootloader logo until phoc (0107/0108); needs a visual check
- Display & shell / Phosh: hotplug crash fixes installed (phosh 0.57.0-1.3, phoc 0.57.0-1.2), no crash since 2026-09-30 00:00; plug/unplug stress test pending
- Connectivity / Hotspot
- Power / Battery standby measurement: needs the phone unplugged
- Audio / Speaker protection DSP: running on both amps with factory calibration (0121-0124); robustness tests pending
- Audio / Bluetooth audio

Missing:

- Boot & updates / Reboot to fastboot: reboot argument ignored by the shutdown script
- Display & shell / High refresh rate: 60 Hz only
- External display / 4-lane DP, 5120x1440, 100 Hz: in progress (0136-0139, not in r104); 0114 rejects 5120x1440@60 and 3840x1080@100 until relaxed
- External display / HDMI converters above HBR: the hub HDMI PCON stays dark at HBR2; converters capped at HBR (1080p60); 0119/0134 opt-in experiments
- External display / HDR: later: port of stock VSC/HDR-metadata SDPs
- Connectivity / Bluetooth headset mic (HFP)
- Connectivity / Cellular modem: out of scope
- Connectivity / GPS
- Connectivity / NFC
- USB / USB 3 on the side port: SuperSpeed not verified; the monitor hub runs at USB 2.0 (480M) next to DP
- Power / Deep standby (CX/DDR collapse): DDR stays at 200 MHz in suspend (~79 mA), cause still traced; bisect kit ready (noslpi/noadsp/cdsp DTBs)
- Audio / Earpiece
- Audio / 3.5 mm jack
- Audio / Audio over DP
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
