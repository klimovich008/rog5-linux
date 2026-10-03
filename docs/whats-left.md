# What's left (short version)

As of 2026-09-30 evening, kernel bundle r205 (kernel build r108, DTB r9;
fallback safe-r8).

**Update 2026-10-01** (bundle `main-k111-d10-261001a`, kernel k111, DTB d10):
GNOME offers 5120x1440@60 and 3840x1080@60/100 on the MSI over 4 lanes and
switches between them (0139 default; the replug series of test 9b is still
due); the bottom-port stick survives s2idle with its data intact (test 4,
partly: meter readings still due); the speaker robustness run passed at 80 %
volume (test 5, partly: suspend/reboot cycles still due). The current counts
are in [`status/components.json`](status/components.json).
The picture below shows the same list at a glance (green ready, yellow
partial, blue needs a test, red missing); it is generated from
[`status/components.json`](status/components.json) by
`tools/status-map/render.py`.

![status map](images/status-map.svg)

## Parked branches (2026-10-04)

The work below is not in the main line. Merge a branch only after its test passes on the phone.

- `agent/boot-splash-261002`: phoc shows the boot artwork in its first frame (phoc 0.57.0-1.3).
  It is not installed; the phone runs phoc 0.57.0-1.2. It still needs a visual check.
- `agent/usb-bottom-charging-20261001`: USB bottom port stage C (opt-in charging through the bottom port).
  It is not qualified.
- `agent/gpu-perf-exp`: an experiment, EXPERIMENT 0107 (LLCC GPU write-allocate),
  plus the `gpu_ab.py` A/B benchmark. It has not been benchmarked.

The September GPU/OLED experiment branches have been superseded.

## Fixed since 2026-09-29

- **Monitor**: no more blue screen at the first enable (0130-0135), and GNOME
  runs without the fixed high display clock (5 of 5 clean starts). Native DP
  monitors get HBR2 (the MSI runs 3840x1080 at 60 Hz), and the side port now
  drives all 4 DP lanes (4 x HBR2 in both orientations after a replug, r202).
- **Bottom USB-C port** switches its 5 V on by itself when a device is
  plugged in (0144; seen on r204 and r205).
- **Games crashing with SIGBUS** (Dota 2 under FEX): the 64 MiB of memory that
  aborts on instruction fetch is no longer used (memx), and a service retires
  any further bad block (`rog5-sea-retire`). A Dota retest is still due.
- **Steam** can be dragged by its title bar and resized at its edges in GNOME
  (a small preload shim, c75efe81). DXVK 3 now has what it needs on the
  phone's own Vulkan driver (vulkan-freedreno 26.2.3-1.1, held back from
  updates); BioShock runs on x86 Proton 9 (DXVK 2.5.1) under FEX.
- **Music and background jobs** keep the phone awake on battery (the sleep
  policy honours audio playback and sleep inhibitors, 10cc4116).
- **Server disks**: a configured USB disk is mounted at boot, without a
  login (`rog5-usb-storage`; 28 s into the r205 boot).
- **Charging**: the battery is kept at 70-80 % and the phone runs from the
  charger at the limit (bypass; `rog5-charge-policy`). Performance mode is
  used on any external power (`perf_on_power=always`).
- **Fallback** boot (safe-r8) can now restore update snapshots (safe-r7
  could not).
- **Speakers** play at full strength (PipeWire 16-bit), and the speaker
  protection firmware runs on both amplifiers with the phone's factory
  calibration (full volume only while it runs).
- **Phosh/phoc**: the monitor plug/unplug crashes are fixed (no crash since
  2026-09-30 00:00; the stress test is test 3).
- **Desktop mode** fails closed: any doubt about the lock screen keeps GNOME
  off. It no longer polls in the background, and a lit monitor keeps the phone
  awake, also on battery.
- **Updates** reboot only when the phone is idle (no remote client, no sound,
  01:00-06:00), and their snapshots leave your files out (~6 GB instead of ~27 GB).
- **Everyday**: the phone is called `rog5`, the battery percentage is shown,
  USB sticks and ISO images mount in Files, 5 GiB compressed swap (zram
  zstd), Wi-Fi comes up ~15 s sooner after boot, and the logs keep 1 GB.
- **Steam** runs natively (arm64); x86 games run through FEX (Half-Life ran).

## Missing

- **Phone calls / mobile data / GPS**: the modem is not brought up (out of
  scope for now).
- **Cameras, fingerprint reader, NFC, AirTriggers**: no drivers yet.
- **Earpiece, 3.5 mm headphone jack, Bluetooth headset microphone, sound over
  the monitor cable**.
- **Deep standby**: the phone sleeps, but memory never enters its deepest
  state (~79 mA in standby). The cause is still being traced; the test
  builds for that (test 7) were made for an older DTB and must be rebuilt
  for the current one first.
- **High refresh rate on the phone panel (90/120/144 Hz)**.
- **HDR** on the monitor (later).
- **USB 3 speed** on the side port (the monitor's hub runs at USB 2.0).
- **HDMI adapters above 1080p60** (the hub's HDMI converter stays dark at the
  faster link rate).
- **"Restart to fastboot"** from Linux (it currently just reboots).

## In progress

- **5120x1440 and 100 Hz** on the MSI monitor. These modes are still hidden
  because they came up blue on 2 lanes; a switch for testing them on 4 lanes
  is in the kernel (test 9).
- **Lower DP link power**: the next kernel (r109, patch 0145) trains the
  slowest link that carries the mode (4 x HBR instead of 4 x HBR2 for
  3840x1080@60); it needs a power measurement on the MSI (test 9).
- **24-bit sound**: the fix (0125-0127) is in the running kernel, but PipeWire
  stays 16-bit until a loudness A/B (test 6).
- **Monitor at boot**: once on r202 the phone did not see the monitor when
  it booted with it attached (the audio DSP that reports the cable sent no
  DP notification, probably a start-up race); not retried on r205 (test 9).

## Works, but not fully finished

- **Desktop mode** starts only when you tap "Desktop mode" (manual) until one
  supervised boot test (test 1) shows it waits for your PIN. Switching
  between phone and desktop mode still closes all apps.
- **Monitor USB after a replug** sometimes fails (error -71); a helper resets
  the port and it comes back, which can take a minute or more. The kernel fix
  waits for test 2.
- **Bottom USB port** switches 5 V automatically, but sleep with a device
  plugged in and the power readings after unplug are not tested yet (test 4).
- **Speaker protection** runs, but needs a long loud test (test 5).
- **New monitors** may put the phone panel into GNOME's screen layout; a
  helper that keeps it out is not written yet.
- **Wi-Fi** needs ~11 s to reconnect after the phone wakes.
- **Brightness** has only about 4 real steps.
- **Performance mode** switches itself on whenever a charger is plugged in
  (`rog5-perf-mode auto`, `perf_on_power=always`); there is no Phosh toggle
  yet.
- **Bypass charging below full** (the phone running from the charger while
  the battery is below the limit) is not tested with a PD charger yet: the
  hub offers 5 V/3 A, 9 V/2.45 A, 15 V and 20 V, and the phone picked 5 V/3 A
  (test 15).
- **USB sticks**: a disk listed in `/etc/rog5/usb-storage` is mounted at boot;
  any other stick is mounted by Files (gvfs) only after you log in. Whether
  the two get in each other's way is not tested (test 17).
- **Boot screen**: the ASUS logo should stay until the spinner (needs your
  visual check).

Details and causes: [`user-irritations.md`](user-irritations.md).

## Tests only you can do (need hands, a cable or a monitor)

| # | Test | What to do | Tell me |
|---|---|---|---|
| 1 | Desktop mode at boot (supervised) | I switch desktop mode to auto. Reboot with the monitor attached, don't touch the phone for 2 min, then unlock with the PIN | GNOME must stay off until the PIN, then start. Did it? |
| 2 | Monitor USB replug (-71) | Unplug the monitor's USB-C cable, wait 5 s, plug it back the same way round, hands off 90 s; repeat 3-5 times while I watch the logs | Keyboard/mouse back each time? |
| 3 | Monitor hotplug (Phosh fix) | Plug/unplug the monitor 5x on the lock screen, then with apps open, then desktop mode twice | Did Phosh restart or apps close? |
| 4 | Bottom port, automatic 5 V | Put a USB power meter on the bottom port; plug a stick or keyboard and unplug it 10 times (both ways round), then sleep the phone 5 times with it plugged in, then reboot with it plugged in | Meter readings with and without a device; did the device work every time? |
| 5 | Speakers, long and loud | 20 play/stop cycles, one sleep between songs, one reboot, then 5 min of loud music you know at full volume | Crackle, cut-outs, volume drops, one speaker quieter, hot back? |
| 6 | 24-bit sound A/B | When I ask: listen to the same clip in 16-bit and 24-bit | Same loudness? Any distortion? |
| 7 | Standby test builds | After I rebuild them for the current DTB: for each (sensors off, audio DSP off, compute DSP on) pull the cable when I say, screen off, wait ~5 min, plug back | Just do it; I read the counters |
| 8 | Battery standby | Unplug the phone, lock it, leave it 1-2 h | Battery % before/after |
| 9 | Monitor tests | (a) Reboot r205 with the MSI attached, 3 times. (b) When I switch on the test mode: pick 5120x1440@60, then 3840x1080@100, replug each 5 times. (c) HBR3 later. (d) On r109: I measure power with the slower link (`rog5-dp-power-measure`) | Picture after each boot? Blue screen, flicker, keyboard/mouse working? |
| 10 | Bluetooth audio | Pair headphones, play music | Works? Sound quality? |
| 11 | Hotspot | Turn on the Wi-Fi hotspot, connect another device | Internet on the other device? |
| 12 | Boot screen | Reboot and watch the screen | What glitches do you see and when? |
| 13 | HDMI hub | With the hub's HDMI converter plugged in, while I run HDMI compatibility tests | Picture or not, per step |
| 14 | Next fastboot visit | Run `fastboot getvar current-slot`, `fastboot getvar slot-retry-count:b`, `fastboot getvar slot-successful:b` and `fastboot getvar slot-unbootable:b` (read-only; not `getvar all`, whose serials and identifiers stay private) | Paste those four lines |
| 15 | Bypass below full | With a PD charger (not the hub) and the battery below 80 %, while I switch bypass on | Does the charger keep the phone running without charging? |
| 16 | Games | BioShock with native ARM64 Proton (DXVK 3); Dota 2 for 30 min (it crashed with SIGBUS before memx) | Starts? Crashes? |
| 17 | USB stick at boot | Boot with a stick plugged in, log in, then replug it | Did it show up once in Files, and can you open it? |
