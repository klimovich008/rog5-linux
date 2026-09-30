# What's left (short version)

As of 2026-09-30, kernel bundle r201 (kernel build r104).
The picture below shows the same list at a glance (green ready, yellow
partial, blue needs a test, red missing); it is generated from
[`status/components.json`](status/components.json) by
`tools/status-map/render.py`.

![status map](images/status-map.svg)

## Fixed since 2026-09-29

- **Monitor**: no more blue screen at the first enable (0130-0132), and GNOME
  runs without the fixed high display clock (5 of 5 clean starts). Native DP
  monitors get HBR2 (the MSI runs 3840x1080 at 60 Hz).
- **Speakers** play at full strength, and the speaker protection firmware runs
  on both amplifiers with the phone's factory calibration.
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
  builds for that are ready (test 7).
- **High refresh rate on the phone panel (90/120/144 Hz)**.
- **HDR** on the monitor (later).
- **USB 3 speed** on the side port (the monitor's hub runs at USB 2.0).
- **HDMI adapters above 1080p60** (the hub's HDMI converter stays dark at the
  faster link rate).
- **"Restart to fastboot"** from Linux (it currently just reboots).

## In progress

- **4 DP lanes, 5120x1440 and 100 Hz** on the MSI monitor. These modes are
  hidden for now because they came up blue; they stay hidden until they test
  clean and the restriction is relaxed.
- **24-bit sound**: the 24-bit path reaches the speakers far too quietly, so
  PipeWire plays 16-bit for now.
- **Steam window dragging**: dragging Steam by its title bar does nothing in
  GNOME.

## Works, but not fully finished

- **Desktop mode** starts only when you tap "Desktop mode" (manual) until one
  supervised boot test (test 1) shows it waits for your PIN. Switching
  between phone and desktop mode still closes all apps.
- **Monitor USB after a replug** sometimes fails (error -71); a helper resets
  the port and it comes back, which can take a minute or more. The kernel fix
  waits for test 2.
- **Bottom USB port** needs its 5 V switched on by hand (`rog5-usb-bottom
  on`); the automatic version is built but not switched on (test 4).
- **Speaker protection** runs, but needs a long loud test (test 5).
- **New monitors** may put the phone panel into GNOME's screen layout; a
  helper that keeps it out is not written yet.
- **Wi-Fi** needs ~11 s to reconnect after the phone wakes.
- **Brightness** has only about 4 real steps.
- **Performance mode** switches itself on with a charger and a monitor
  (`rog5-perf-mode auto`); there is no Phosh toggle yet.
- **Boot screen**: the ASUS logo should stay until the spinner (needs your
  visual check).
- A rare **SIGBUS crash** (seen with Steam on 2026-09-30) is still being
  traced; the kernel now logs where it happens.

Details and causes: [`user-irritations.md`](user-irritations.md).

## Tests only you can do (need hands, a cable or a monitor)

| # | Test | What to do | Tell me |
|---|---|---|---|
| 1 | Desktop mode at boot (supervised) | I switch desktop mode to auto. Reboot with the monitor attached, don't touch the phone for 2 min, then unlock with the PIN | GNOME must stay off until the PIN, then start. Did it? |
| 2 | Monitor USB replug (-71) | Unplug the monitor's USB-C cable, wait 5 s, plug it back the same way round, hands off 90 s; repeat 3-5 times while I watch the logs | Keyboard/mouse back each time? |
| 3 | Monitor hotplug (Phosh fix) | Plug/unplug the monitor 5x on the lock screen, then with apps open, then desktop mode twice | Did Phosh restart or apps close? |
| 4 | Bottom port, automatic 5 V | Boot the trial I prepare, put a USB power meter on the bottom port; plug a stick or keyboard, unplug it, leave it empty | Meter readings with and without a device; did the device work? |
| 5 | Speakers, long and loud | 30 min of loud music with bass at full volume; pause and resume, lock and wake once mid-song, then reboot and play again | Crackle, cut-outs, volume drops, hot back? |
| 6 | Steam title bar | When I ask: open Steam in desktop mode and try to drag it by its title bar while I record the events | Did it move at all? |
| 7 | Standby test builds | For each test build I prepare (sensors off, audio DSP off, compute DSP on): pull the cable when I say, screen off, wait ~5 min, plug back | Just do it; I read the counters |
| 8 | Battery standby | Unplug the phone, lock it, leave it 1-2 h | Battery % before/after |
| 9 | 4-lane DP (when ready) | Plug the MSI monitor into the new build | Which modes show? 5120x1440 / 100 Hz stable? |
| 10 | Bluetooth audio | Pair headphones, play music | Works? Sound quality? |
| 11 | Hotspot | Turn on the Wi-Fi hotspot, connect another device | Internet on the other device? |
| 12 | Boot screen | Reboot and watch the screen | What glitches do you see and when? |
| 13 | HDMI hub | With the hub's HDMI converter plugged in, while I run HDMI compatibility tests | Picture or not, per step |
| 14 | Next fastboot visit | Run `fastboot getvar all` (read-only) | Paste the output (slot flags) |
