# ROG5 current state

Native Arch Linux ARM on the ASUS ROG Phone 5 (SM8350) with Phosh as the
phone shell and GNOME as the desktop mode on an external display. Linux
7.2.7 with the `patches/linux-7.2.7` series; cellular is out of scope.

<!-- BEGIN GENERATED: scripts/host/render-current-state.py from docs/status/components.json -->
Status as of 2026-10-02 (main-k116-d15-261002e) (source: `docs/status/components.json`).

| | Bundle | Kernel build | DTB | Installed |
|---|---|---|---|---|
| Default | `main-k116-d15-261002e` | k116 (series to 0168: + Iris video 0154-0168; uname 7.2.7-rog5-k116) | d15 (`16cbb384`, d13 + iris/videocc nodes) | 2026-10-02 14:02; hardware H.264/HEVC decode, firmware installed persistently |
| Fallback | `safe-k111-d10-261001a` | k111 (series to 0148) | d10 (`dda8b280`, d9 + l11off) | 2026-10-01 13:52; fallback rehearsal PASS 15:42 (safe-r8 kept on p24) |

Components: 39 ready, 11 partial, 8 needs a test, 16 missing.

Partial:

- Boot & updates / Boot time: ~57 s to multi-user on r205 (21 s kernel + initramfs, 35 s userspace)
- Display & shell / Brightness: about 4 real steps
- External display / 5120x1440, 100 Hz, HBR3: halved clock check is the default (0139); 8 bpc floor (0147) hides 5120x1440@100; GNOME offers 5120x1440@60, 3840x1080@60/100/144, 2560x1440@60/120 and switches modes (user, 2026-10-01); 3840x1080@144 only briefly tested; HBR3 opt-in untested
- External display / GNOME desktop mode: event-driven, fail-closed switcher; the user keeps mode manual (2026-10-01; auto needs a supervised lock test); apps close on a switch but rog5-session-carry quits them cleanly and reopens them in the other session (2026-10-01; first live switch with apps pending)
- Connectivity / Wi-Fi: stable MAC/IP since 2026-09-29; 11 s reconnect after wake
- USB / Replug recovery (-71): side port: rog5-usb-reconnect re-initialises the controller; kernel fix (0142 retries / 0143 session override) needs the one-replug test
- Power / Idle background wakeups: desktop-mode switcher event-driven (~0.1 % CPU); sleep policy polls every 5 s; k111: USB DDR vote follows attached devices (0148) and PM8350C L11 off (d10) — A/B with rog5-idle-power-sample pending
- Performance / Performance mode: rog5-perf-mode auto, perf_on_power=always on the phone (performance trips on any external power); no toggle in Phosh yet
- Sensors & hardware / RGB logo LED
- Sensors & hardware / Hardware video decode/encode: k116 remains the installed default. k117 F1: H.264/HEVC 300/300 bit-exact, compliance 48/48, clean power off and 5 min idle PASS, but removal hard-hangs after mark: remove. F2r: VP9 stock-sized stream-0 DPBs still rejected (0x1003); stock counts do not help; third error contained. Encoder F3 unrun (k115 hung at start). Host-only k120 (0172-0178, d15): detailed callback/devres/genpd/IOMMU markers, opt-in remove_quiesce and VP9 shared extradata, never-powered probe control, encoder tooling/tests; G1/G2/G3 plan in docs/hardware/video.md. No k120 phone qualification. Host wedge patch 0190 uses ABORT for failed gen1 sessions and contains teardown timeouts. k122 Chromium close stalls after an output-only flush; host patch 0191 uses ALL for ordinary CAPTURE streamoff and keeps OUTPUT for DRC. Series apply and ARM64 Iris W=1 objects PASS; fresh-boot qualification pending (test-results/2026-10-02-video-iris-flush-0191-host.md). CPU baseline 1080p: H.264 9.8x, HEVC 7.6x, VP9 8.4x realtime
- Apps / Steam (native arm64): title-bar drag and resize via an LD_PRELOAD shim (c75efe81); x86 games through FEX (Half-Life ran); BioShock runs on x86 Proton 9 (DXVK 2.5.1) under FEX; patched x86_64+i686 FEX Turnip (packages/mesa-fex, 26.2.0-rog5.1) installed in the FEX guest root 2026-10-01: DXVK 3.1.1 under Proton Experimental finds Turnip Adreno 660 for 32-bit BioShock (no 8-bit storage skip), s8test x86_64/i686 PASS again 2026-10-03; Dota 2 retest pending

Needs a test:

- Boot & updates / Unattended package updates: reboots only when idle (no remote client, no sound, 01-06 window); snapshots exclude user data (~6 GB); v2 restore passed fault injection and is in both bundles (safe-r8), not yet a real rollback; 2026-10-02 failed-transaction recovery, owned pacman lock, last-good durability and phone health gate tested offline (571d9273), not deployed
- Boot & updates / Boot splash: r187 keeps the bootloader logo until phoc (0107/0108); needs a visual check
- Display & shell / Phosh: hotplug crash fixes installed (phosh 0.57.0-1.3, phoc 0.57.0-1.2), no crash since 2026-09-30 00:00; plug/unplug stress test pending
- Connectivity / Hotspot
- Power / Battery standby measurement: needs the phone unplugged
- Power / Instruction-fetch aborts (SIGBUS): memx no-map 64 MiB at 0x34a000000 in d9/d10 and safe-r8 + rog5-sea-retire; no new aborts seen since; Dota 2 under FEX to retest
- Audio / 24-bit playback: 0125-0127 (V4 Q23 front end) in r108; PipeWire stays S16LE until a loudness A/B
- Audio / Bluetooth audio

Missing:

- Boot & updates / Reboot to fastboot: reboot argument ignored by the shutdown script
- Display & shell / High refresh rate: 60 Hz only
- External display / HDMI converters above HBR: the hub HDMI PCON stays dark at HBR2; converters capped at HBR (1080p60); 0119/0134 opt-in experiments
- External display / HDR: later: port of stock VSC/HDR-metadata SDPs
- Connectivity / Bluetooth headset mic (HFP)
- Connectivity / Cellular modem: out of scope
- Connectivity / GPS
- Connectivity / NFC
- USB / USB 3 on the side port: SuperSpeed not verified; the monitor hub runs at USB 2.0 (480M) next to DP
- Power / Deep standby (CX/DDR collapse): ~79 mA suspended, no CX/DDR collapse; bisect kit requalified on DTB r9 (3de9e285): likely a DDR vote from another RPMh master (ADSP); trials need the phone unplugged
- Audio / Earpiece
- Audio / 3.5 mm jack
- Audio / Audio over DP
- Sensors & hardware / Cameras
- Sensors & hardware / Fingerprint
- Sensors & hardware / AirTriggers

<!-- END GENERATED -->

## Where to look

- Latest VP9 DRC diagnosis: [stale SCRATCH registration and patch 0213](../test-results/2026-10-03-video-iris-vp9-drc-scratch.md); series apply and ARM64 Iris W=1 objects PASS; no live qualification.
- Latest VP9 analysis: [k123 BAD_POINTER comparison](../test-results/2026-10-03-video-iris-vp9-bad-pointer-analysis.md). The rejected pointers are OUTPUT2 CAPTURE buffers; the exact stock plain-NV12 layout differs from Iris's NV12_128-style allocation. No kernel fix is qualified.
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
