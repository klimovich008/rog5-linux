# ROG5 current state

Native Arch Linux ARM on the ASUS ROG Phone 5 (SM8350) with Phosh as the
phone shell and GNOME as the desktop mode on an external display. Linux
7.2.7 with the `patches/linux-7.2.7` series; cellular is out of scope.

<!-- BEGIN GENERATED: scripts/host/render-current-state.py from docs/status/components.json -->
Status as of 2026-09-30 (r205) (source: `docs/status/components.json`).

| | Bundle | Kernel build | DTB | Installed |
|---|---|---|---|---|
| Default | `production-7.2.7-r205` | 7.2.7 build r108 (series to 0144, without 0128/0129; 0145 goes into r109) | platform-cpucap-dp4-btmtc-memx-dtb-r9 (`4a919c15`) | 2026-09-30 18:20 |
| Fallback | `production-7.2.7-safe-r8` | 7.2.7 build r69 | platform-usbbtm-memx-dtb-r3 (`bb4668b4`, usbbtm-r2 + memx) | 2026-09-30 with r205; current init (v2 restore), speakers at -12 dB |

Components: 34 ready, 10 partial, 11 needs a test, 17 missing.

Partial:

- Boot & updates / Boot time: ~57 s to multi-user on r205 (21 s kernel + initramfs, 35 s userspace)
- Display & shell / Brightness: about 4 real steps
- External display / 4-lane DP: 0136-0139: 4 x HBR2 in both orientations after a replug (r202); one boot with the monitor attached got no DP notification from the ADSP (suspected race), not retested on r205
- External display / GNOME desktop mode: event-driven, fail-closed switcher; mode manual until one supervised boot test; switching closes apps
- Connectivity / Wi-Fi: stable MAC/IP since 2026-09-29; 11 s reconnect after wake
- USB / Replug recovery (-71): side port: rog5-usb-reconnect re-initialises the controller; kernel fix (0142 retries / 0143 session override) needs the one-replug test
- Power / Idle background wakeups: desktop-mode switcher event-driven (~0.1 % CPU), tailscaled retry loop gone; sleep policy still polls every 5 s
- Performance / Performance mode: rog5-perf-mode auto, perf_on_power=always on the phone (performance trips on any external power); no toggle in Phosh yet
- Sensors & hardware / RGB logo LED
- Apps / Steam (native arm64): title-bar drag and resize via an LD_PRELOAD shim (c75efe81); x86 games through FEX (Half-Life ran); BioShock runs on Proton 9; DXVK 3 on native ARM64 Proton not game-tested; FEX x86 Mesa lacks 8-bit storage

Needs a test:

- Boot & updates / Unattended package updates: reboots only when idle (no remote client, no sound, 01-06 window); snapshots exclude user data (~6 GB); v2 restore passed fault injection and is in both bundles (safe-r8), not yet a real rollback
- Boot & updates / Boot splash: r187 keeps the bootloader logo until phoc (0107/0108); needs a visual check
- Display & shell / Phosh: hotplug crash fixes installed (phosh 0.57.0-1.3, phoc 0.57.0-1.2), no crash since 2026-09-30 00:00; plug/unplug stress test pending
- External display / 5120x1440, 100 Hz, HBR3: hidden by 0114 unless msm.dpu_mode_clk_check=halved (0139); HBR3 opt-in (0138); none tested on the 4-lane link
- Connectivity / Hotspot
- USB / Bottom port (USB 2.0 host): stage B (RT1715 + TCPM): automatic 5 V on attach on r204/r205 (0144 PDC edge/level); s2idle with a device, detach power readings and 0144 retention across CX collapse unproven
- Power / Battery standby measurement: needs the phone unplugged
- Power / Instruction-fetch aborts (SIGBUS): memx: no-map 64 MiB at 0x34a000000 (a79182ba) + rog5-sea-retire; Dota 2 under FEX to retest
- Audio / Speaker protection DSP: running on both amps with factory calibration on r205 (0121-0124); robustness tests pending
- Audio / 24-bit playback: 0125-0127 (V4 Q23 front end) in r108; PipeWire stays S16LE until a loudness A/B
- Audio / Bluetooth audio

Missing:

- Boot & updates / Reboot to fastboot: reboot argument ignored by the shutdown script
- Display & shell / High refresh rate: 60 Hz only
- External display / DP link power policy: 0145 msm.dp_link_policy (4 x HBR instead of 4 x HBR2 for 3840x1080@60) committed, goes into r109; then rog5-dp-power-measure on the MSI
- External display / HDMI converters above HBR: the hub HDMI PCON stays dark at HBR2; converters capped at HBR (1080p60); 0119/0134 opt-in experiments
- External display / HDR: later: port of stock VSC/HDR-metadata SDPs
- Connectivity / Bluetooth headset mic (HFP)
- Connectivity / Cellular modem: out of scope
- Connectivity / GPS
- Connectivity / NFC
- USB / USB 3 on the side port: SuperSpeed not verified; the monitor hub runs at USB 2.0 (480M) next to DP
- Power / Deep standby (CX/DDR collapse): ~79 mA suspended, no CX/DDR collapse; bisect kit (noslpi/noadsp/cdsp DTBs) pinned to DTB r5, needs requalifying against r9
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
