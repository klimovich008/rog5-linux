# What would irritate a real user (2026-09-29, bundle production-7.2.7-r185)

Scope: the phone as a daily Linux phone (Phosh), as a desktop on an external
monitor (GNOME desktop mode) and as a small server behind USB hubs. Evidence
comes from the live phone (read-only commands, 20:44-21:05 CEST, boot
`8d2b9bee`, up 1 h 35 min, on a USB-C hub with USB power), from the journal of
the 25 boots kept today (09:56-21:00), from 30 core dumps, and from the test
reports in `test-results/2026-09-2[6-9]*`.

Status labels: **confirmed** (seen on the phone today), **likely** (seen in the
code/config or the docs, but not reproduced today), **historical-fixed** (seen
today or earlier, fixed since). Effort: S = hours, M = a day or two, L = a week
or more / upstream work.

Caveat: today was a heavy development day (15+ kernel installs, DP bring-up,
standby experiments). Some crash counts are higher than a normal user would
see. Each item says whether it needs a lab action to trigger.

## Top 10

| # | What the user sees | Status | Effort |
|---|---|---|---|
| 1 | Plugging or unplugging the USB-C monitor hub can crash Phosh. The session ends, every open app closes, and the phone drops to the lock screen. | confirmed (12 Phosh segfaults today) | M |
| 2 | Switching between phone and desktop mode, or unplugging the monitor, closes every app. Chromium even core-dumps on the way out. | confirmed (by design) | L |
| 3 | The phone gets a new Wi-Fi MAC and a new IP address on every boot, so SSH, port forwards and router reservations break after each reboot. | confirmed (6 boots, 6 addresses) | S |
| 4 | The phone can reboot on its own. After an unattended package update it restarts as soon as the panel is off, even during a server job, music, or desktop mode with the panel dark. | likely (the config says so; not seen today) | S |
| 5 | The brightness slider has only about 4 real steps, so there is no fine dimming at night. | confirmed (open investigation) | L |
| 6 | Wi-Fi takes 11 s to come back after every wake from suspend. | confirmed (14 of 14 resumes) | M |
| 7 | Background polling at idle spawns about 10 processes/s and keeps PID 1 at about 2.4 % of a core. A dead Tailscale unit fails every 60 s (102 times this boot). | confirmed | S-M |
| 8 | Standby drains the battery: about 79 mA in suspend, and DDR never reaches low power. | confirmed (docs, 2026-09-29 probe) | L |
| 9 | The external monitor is capped at 1920x1080@60 (no 4K or ultrawide modes). Desktop mode pins the display clocks at maximum, so the phone runs warm. | confirmed | M-L |
| 10 | Everyday hardware is missing: 3.5 mm jack, cameras, fingerprint, NFC, Bluetooth headset microphone (HFP). | confirmed | L |

## Blocking

### 1. Phosh crashes on monitor hotplug; all apps are lost
- **User sees:** the phone jumps to the lock screen and everything open is gone. It happens when the USB-C HDMI hub/monitor is attached or removed while Phosh runs.
- **How often:** 12 Phosh SIGSEGV core dumps today (10:53-16:21), all while the hub/monitor was in use. Several came 2-3 min after boot, while the DP link still bounced (HPD cycling).
- **Evidence:** `coredumpctl list`. Three signatures:
  - `g_object_get_data` from phosh+0x6c3e8 (output removal), with `remove_shield_by_monitor: assertion 'PHOSH_IS_MONITOR'` just before;
  - `gtk_widget_destroy` from phosh+0x6b8d8 (16:21:35, right after "DisplayID checksum invalid" from a DP connect);
  - a gesture handler (`gtk_gesture_set_sequence_state`, 14:27:27), preceded by `phosh_monitor_get_fractional_scale: assertion 'phosh_monitor_is_configured'`.
  After the crash, systemd logs `mobi.phosh.Shell.service: Failed to schedule restart job ... destructive`. The whole gnome-session stops, and `rog5-phosh` (Restart=always) brings up a new locked session.
- **Likely cause:** Phosh 0.57 keeps stale PhoshMonitor pointers (lock shields, fractional scale) when an output goes away or comes back. A flapping DP HPD makes this much more likely.
- **Fix:** get a symbolised backtrace (phosh-debug or debuginfod) and check upstream Phosh (≥0.58) for monitor-removal fixes. Patch `remove_shield_by_monitor` and the output-removed handlers, or carry an upstream backport as with phoc. Short term: let `mobi.phosh.Shell.service` restart inside the session instead of tearing the session down. Effort **M**.

### 2. Changing mode closes every app
- **User sees:** tapping "Desktop mode" or "Phone mode", unplugging the monitor, or 10 min of GNOME idle ends the current session. Browsers, editors and terminals all close. Chromium shows its "didn't shut down correctly" state next time.
- **How often:** every switch. Today: 3 Chromium SIGTRAP dumps (12:47, 13:14, 13:40), each exactly when `rog5-phosh`/`rog5-gnome` stopped. The log says `GPU process launch failed: error_code=1002 ... GPU process isn't usable. Goodbye.` A GNOME session at 19:21:53 lasted 40 s and ended on unplug.
- **Evidence:** `configs/systemd/rog5-gnome.service` (`Conflicts=rog5-phosh.service`), `rog5-desktop-mode` log ("display unplugged -> Phosh" at 14:26, 16:22, 19:22).
- **Cause:** Phosh and GNOME are two compositors on one tty. Only Phosh can lock, so the design swaps whole sessions.
- **Fix:** a real fix means one compositor for both screens: phoc with a desktop layout on DP, or GNOME Shell mobile. Short term: warn before the switch ("apps will close"), and delay the unplug switch-back (for example 30 s, so a loose cable does not kill the session). Effort **L** (short-term items S).

### 3. New MAC and new IP on every boot
- **User sees:** the phone's address changes after every reboot (today .91, .40, .120, .34, .109, .11). SSH bookmarks, the Deck scripts and router rules stop working. The router lists a new "alarm" device each time.
- **Evidence:** NetworkManager leases per boot; the wlan0 MAC (Qualcomm/Atheros OUI 00:03:7f) differs in boots -3, -2, -1 and 0. `addr_assign_type` is 0, and NM has `wifi.scan-rand-mac-address=no`, so the random MAC comes from the driver/firmware (no board MAC provisioned), not from NM privacy settings.
- **Fix:** set a fixed MAC. Either take the stock one (the WCN6855 MAC lives in the ASUS persist/`wlan_mac.bin`) in the DT (`local-mac-address`) or a systemd `.link` file, or set `wifi.cloned-mac-address=stable` in NM. The same applies to the Bluetooth address if it is also random. Effort **S**.

### 4. Unattended updates reboot the phone by themselves
- **User sees:** the phone restarts with no warning, closes apps and SSH sessions, and comes back locked.
- **Evidence:** `configs/systemd/rog5-update.service` sets `ROG5_UPDATE_REBOOT=idle`. In `initramfs/rog5-update`, `display_idle()` only checks that every backlight is 0, then `systemctl reboot`. The timer runs hourly. Today's update (17:26, 0.83 MiB) peaked at **6.8 GB of memory**, with no swap. No reboot was traced to it today (the next boot came from a lab reset).
- **Cause:** "Panel off" is used as "user is away". It is not true for server work, music with the screen off, SSH users, or desktop mode.
- **Fix:** default to `never`, or reboot only when there is no logind session activity, no remote client (reuse `rog5-sleep-policy`'s detector), no audio stream and no desktop mode, and send a notification first. Look at why the snapshot copy needs GBs of RAM. Effort **S**.

## Annoying

### 5. Brightness has about 4 real levels
- **User sees:** the slider jumps in big steps. The low end is either quite bright or black; there is no smooth night-time dimming.
- **Evidence:** status line "3-level brightness"; `test-results/2026-09-27-brightness-*.md` and `docs/reviews/2026-09-29-gpt-6-astra-brightness-review.md`. The DDIC applies only the high bits of the 10-bit DBV. Status "not resolved".
- **Cause:** a DSI command path problem (HS/LP packet delivery through the Pixelworks Iris bridge).
- **Fix:** run the pending E0-E2 readback experiments. As a stopgap, map the slider to the working levels so it does not look broken. Effort **L** (stopgap S).

### 6. Wi-Fi is gone for 11 s after every wake
- **User sees:** after unlocking, apps show "offline" and messages and SSH stall for about 11 s.
- **Evidence:** boots -1..-3: 14 of 14 resumes, association 10.9 s and DHCP 11.1 s after `PM: suspend exit`. wpa_supplicant logs `CTRL-EVENT-DISCONNECTED ... locally_generated=1 reason=3` before each suspend. The ~11 s is constant, which suggests a fixed wait (scan/firmware re-init), not the radio. `trial.py` allows up to 45 s.
- **Fix:** keep the association across s2idle (NM sleep/wake handling, ath11k suspend without disconnect as WoWLAN-lite), or at least reconnect to the last BSSID without a full scan. Effort **M**.

### 7. Idle background churn (battery and journal)
- **User sees:** nothing directly. Battery life and standby suffer, and the logs fill up.
- **Evidence (idle, screen off, 60 s sample):**
  - 580 new PIDs per minute, and PID 1 used 1.44 s of CPU per minute. `ps` shows `systemd` at 2 min 17 s of CPU in 95 min of uptime.
  - A 20 s spawn trace: `rog5-desktop-mode` runs `systemctl is-active` twice plus `paste` and `sleep` every 3 s (`POLL=3`), even with no monitor attached. `rog5-sleep-policy` forks cat, awk, ss and sleep every 5 s.
  - `rog5-tailscaled.service` (the ramdisk's USB-link Tailscale) fails with "USB network interface is not up" every 60 s: 102 times this boot, NRestarts=93 at 20:44. That is 5 journal lines per attempt.
  - Wi-Fi power save toggles on and off with every short SSH connection (44 log lines this boot).
- **Fix:**
  - Switcher: wait on DRM hotplug uevents (`udevadm monitor`/a udev rule starting a oneshot) and logind signals instead of polling. Skip everything while the DP connector is disconnected.
  - rog5-tailscaled: `ConditionPathExists`/`BindsTo` the USB NCM interface device unit, so it runs only when the link is up.
  - Sleep policy: use longer intervals while the screen is on and the charger is attached.
  Effort **S-M**.

### 8. Standby battery drain
- **User sees:** noticeable overnight drain in suspend (about 79 mA at the pack; awake idle with the screen off is about 100-106 mA).
- **Evidence:** `test-results/2026-09-29-standby-ddr-floor.md`: DDR stays at 200 MHz in s2idle, cxsd/aosd/ddr counters stay 0, and the holder is not the APPS side (ADSP/SLPI/TZ candidates). The ADSP wakes 7-30 times a minute for battmgr.
- **Fix:** the boot-time bisects already planned (SLPI off, ADSP variant, CDSP load). Effort **L**.

### 9. External monitor: 1080p only, and hot while in use
- **User sees:** a 4K or 32:9 monitor runs at 1920x1080@60 only. In desktop mode the phone gets warm even when idle.
- **Evidence:**
  - `/etc/tmpfiles.d/rog5-dp.conf` sets `msm.dp_max_rate=270000` (HBR; HBR2 gives about 25k symbol errors/s on lane 1), and `/etc/phosh/phoc.ini` pins `[output:DP-1] mode = 1920x1080@60Hz`.
  - `rog5-gnome.service` writes `fix_core_clk_rate 460000000` and 15.5 GB/s ab/ib votes with `perf_mode 2` for the whole GNOME session. Whether 0099-0101/0106 make this unnecessary is untested ("still needs the monitor").
  - Every DP enable logs `LM_4/LM_5, invalid DSPP_-1` dpu errors and the bring-up "DP sink @Nms" dumps.
- **Fix:** test r185 without the pin (count INTF underruns). If clean, drop the ExecStartPre. Fix HBR2 margin (vlevel/pre-emphasis tables) before removing the phoc.ini pin. Remove the DP debug logging from production. Effort **M** (pin removal S once tested; HBR2 L).

### 10. Missing hardware
- **User sees:** no camera app, no fingerprint unlock, no NFC, no 3.5 mm headphone jack, and Bluetooth headsets are A2DP-only (no microphone). There is no earpiece sink in PipeWire either (only "Speakers").
- **Evidence:** `test-results/2026-09-27-compare-platform.md` (#11 cameras: no sm8350 camss/camcc upstream; #12 Goodix fingerprint needs the TEE; #8 NFC unmanaged), `2026-09-27-compare-audio.md` (#3 ES928x jack codec has no mainline driver; #8 HFP not carried on UART HCI). `wpctl status`: one sink, one source.
- **Fix:** document these as unsupported in Settings/port-status so users do not hunt for them. ES928x driver (L), cameras (L, upstream). The NFC VEN GPIO check is a 30 s power item (S).

### 11. The phone throttles early under sustained load
- **User sees:** games and benchmarks slow down after a few minutes.
- **Evidence:** during today's GPU benchmark the skin sensor read 44.8 C (trip at 42 C). Cooling devices `devfreq-3d00000.gpu 1/9`, `cpufreq-cpu4 1/15`, `cpufreq-cpu7 1/18`, GPU max 778 of 840 MHz. The step_wise policy caps big at 1766 MHz and prime at 1901 MHz at 42 C, and throttles much harder at 46 C.
- **Cause:** a deliberate skin policy (stock starts even earlier, at 36 C). It works as intended, but it is a trade-off.
- **Fix:** a "performance" profile (power-profiles-daemon hook) that raises the 42 C trip while on the charger or with the fan accessory. Effort **S**.

### 12. Apps are slow to appear from the Phosh grid
- **User sees:** Firefox cold start takes 7-9 s (2.6 s warm). The Calculator spinner shows for about 4 s. The Firefox launch splash timed out twice today (13:46, 14:26: `Startup of app 'Firefox' ... timed out`).
- **Evidence:** `test-results/2026-09-27-phosh-suspend.md` (launch timing); the journal. The Chromium splash timeouts stopped after the 13:24 override (see Historical).
- **Cause:** a cold page cache, the `uclamp.min 400` session boost only on the Phosh session, and possibly a Firefox app-id/StartupWMClass mismatch when a window opens on DP.
- **Fix:** preload or `vmtouch` the Firefox libs at boot; check the Firefox app_id against `StartupWMClass=firefox` on DP; measure again. Effort **S-M**.

### 13. Slow to be fully ready after boot
- **User sees:** the lock screen after about 33 s. Wi-Fi comes up about 25 s later, and sound, sensors and auto-rotate only about 39 s into userspace.
- **Evidence:** `systemd-analyze`: 21.4 s (kernel incl. ramdisk) + 39.2 s (userspace). The critical chain is `rog5-wifi-radio` 26.6 s → `rog5-bluetooth` 5.5 s → `rog5-audio` 0.6 s → `rog5-sensors`. Audio and sensors wait for Wi-Fi and BT by design ("after Wi-Fi and Bluetooth").
- **Fix:** check whether the audio/sensor ordering after Wi-Fi is still needed (it was a QUP/ADSP ordering workaround). If so, start audio/sensors in parallel with the 26 s Wi-Fi radio bring-up. Effort **M**.

### 14. Only about 11 hours of logs are kept
- **User sees:** "what happened last night?" cannot be answered. The journal starts at 09:56 today.
- **Evidence:** `journalctl --disk-usage` 192 MB. `/etc/systemd/journald.conf.d` sets `SystemMaxUse=200M`, based on the 16 GiB overlay, which is now 128 GiB (106 GB free). Most of the volume is noise: 4117 `systemd` lines this boot (session scopes, tailscaled retries).
- **Fix:** raise the cap to about 1-2 GB, or exclude the journal from the update snapshot. Cut the noise (item 7). Effort **S**.

### 15. Plugging in the charger does not wake a sleeping phone
- **User sees:** no screen or charging feedback when plugging in while asleep.
- **Evidence:** 0084 (charger-attach wakeup) was pulled after it hung the phone on plug-in (`2026-09-27-phosh-suspend.md`, 2026-09-28 entry). The plug-in wake test is still pending.
- **Status:** likely. Effort **M**.

## Cosmetic / sloppiness

- **The device is called "alarm" everywhere:** hostname, Bluetooth name (`bluetoothctl show`), DHCP hostname on the router, the prompt, and the journal. Tailscale calls it `rog5`. Fix: `hostnamectl set-hostname rog5` in the image. **S**, confirmed.
- **Saved default audio output is `auto_null`:** `wpctl status` → "Default Configured Devices: Audio/Sink auto_null". PipeWire falls back to Speakers today, but if the dummy sink ever appears first (early boot, before `rog5-audio` at about 38 s), sound goes nowhere. Fix: clear the WirePlumber default-nodes state and set Speakers. **S**, confirmed.
- **Microphone probe errors at each session start:** `spa.alsa: 'hw:0,0'/'hw:0,1': capture open failed: Invalid argument` and `no backend DAIs enabled for MultiMedia1`. The "Built-in microphones" source works; the pro-audio profile probe fails. Fix: disable the pro-audio profile for the card in a WirePlumber rule. **S**, confirmed.
- **Denial leftovers still installed and running:**
  - `rog5-session-bus.service` ("Session D-Bus for the Denial session", a root dbus-daemon) is enabled and running;
  - `rog5-powerd` and `rog5-battery-log` ("for the Denial session") are enabled;
  - `/opt/denial` takes 194 MB;
  - the phoc.ini comment still refers to Denial.
  Fix: disable them, or remove them if Denial is retired. **S**, confirmed.
- **Workarounds whose reason has gone:**
  - `~phone/.config/environment.d/60-rog5-mutter.conf` sets `MUTTER_DEBUG_DISABLE_HW_CURSORS=1`. The test result itself says the cursor A/B test was confounded and the real cause was the DPU clock. The software cursor costs GPU time and adds pointer lag in desktop mode.
  - `/etc/drirc` forces `tu_restrict_subgroup_size_64` for every Vulkan app, to avoid one Geekbench hang.
  Re-test both on r185 and keep them only if still needed. **S**, confirmed present.
- **Phosh background is blue, not the intended black:** the system dconf default sets `primary-color='#000000'` (OLED power), but the user database overrides it with `'#2050c0'`. Likely set by an earlier restore or test. **S**, likely.
- **Battery percentage is hidden in the top bar** (`show-battery-percentage=false`). Most phone users expect it. **S**.
- **Kernel WARNs and faults on every boot:** 2 WARN traces from `clk_core_disable`/`clk_core_unprepare` during `msm` probe (DSI PLL reparent), so the kernel is tainted `W` from boot. There are also 4-7 SMMU "Unhandled context fault" lines at boot (display handover SIDs). They are harmless, but they hide real problems in bug reports. **M**, confirmed.
- **Session-start noise:**
  - `Atomic commit failed: Device or resource busy` on DSI-1: 5 this boot, 450 today, clustered at compositor start;
  - `rog5-wayvnc-phone.service` fails 9 times per Phosh start ("Failed to initialise wayland", a start race);
  - callaudiod "No suitable card found";
  - Phosh "Failed to get emergency contacts" (no modem);
  - `gsd-power`: `backlight ... 'max > min'` and "failed to set dim kbd backlight" (UPower sees an LED as a keyboard backlight);
  - Thunar duplicate D-Bus name;
  - GNOME Software's fwupd plugin cannot load (`libfwupd.so` missing);
  - `fbd-ledctrl` missing for the flash LED.
  Each is cheap to silence. **S** each, confirmed.
- **Sensors:**
  - iio-sensor-proxy reports "No proximity sensor", though the VCNL36866 has one (the phone does not blank on the ear or in a pocket);
  - `rog5-sensors` logs `Could not open /vendor/factory/gsensor_{x,y,z}.nv`, so the accelerometer is uncalibrated.
  **M**, confirmed.
- **Clock after a crash:** after the 17:29 hard reset the new boot started 18 s in the past (boot -4 first entry 17:28:52 < boot -5 last 17:29:10), until NTP. The RTC offset is saved only at shutdown and after NTP. Fix: save it periodically. **S**, confirmed once.
- **Background services a phone does not need:** Evolution data servers, localsearch indexer, GNOME Smartcard/Wwan/PrintNotifications/UsbProtection daemons, plus a permanent headless sway (93 MB) with two wayvnc servers. None was busy in the sample, but they cost memory and wakeups. **S**, confirmed present.
- **Project docs are stale:** the generated status block in `docs/current-state.md` still says "Production 7.2.7 r93/r98 default"; the phone runs r185. `manifests/current-artifact.json` still points at a 7.1.4 runtime. Not user-facing, but it misleads the next person. **S**, confirmed.

## Historical-fixed (seen today or recently, fixed since)

| Item | Evidence | Fixed by |
|---|---|---|
| Phosh spinner outlived Chromium's startup | `Startup of app 'Chromium' ... timed out` 13:11, 13:23; the stock `chromium.desktop` has the literal `StartupWMClass=@@startup_wm_class` (Arch ARM packaging bug) | `~phone/.local/share/applications/chromium.desktop` (13:24, `StartupWMClass=chromium`, `StartupNotify=false`); no timeout since. Upstream it to the package. |
| phoc crash loop at session start | 7 SIGABRT 11:32:31-11:33:07: `config_ini_handler: assertion failed: (strcmp ("Hz", end) == 0)` | phoc.ini mode now `1920x1080@60Hz`. A typo in phoc.ini still takes the session down; validate the file on install. |
| squeekboard abort loop in GNOME | 5 SIGABRT 13:36:37-40, "No virtual keyboard manager Wayland global available" | not seen in later GNOME sessions |
| Geekbench Vulkan GPU hang | `gpu fault ... hangcheck recover!` 15:19, 15:20 (plus 2 Geekbench segfaults) | `/etc/drirc` (15:27); see the sloppiness item |
| Side-port hub died over suspend | 31k SMMU faults + `Host System Error` (r183) | 0105 (r184+) |
| USB (to PC) did not re-enumerate after replug | user report 2026-09-26 | `rog5-usb-reconnect` (logs "PASS device enumerated after re-initialisation") |
| rog5-tailscaled retried every 5 s | 221 restarts in 20 min | 60 s retry; still loops (item 7) |
| Apps opened on the invisible sway desktop | 2026-09-28 | sway-base.conf, `XDG_CURRENT_DESKTOP=Phosh:GNOME` |
| gnome-session abort "VT already taken" | 15:57:03 | test-induced (GNOME restart loop) |
| Phone reset during suspend entry (boot -5 ends at `PM: suspend entry`) | 17:29 | test-induced (xHCI unbind before suspend) |

## Not reproduced / unverified

- **Per-app GPU for phoc:** `/proc/<phoc>/fdinfo` exposes `drm-engine-gpu` (404 ms on client 50), so the data exists. If Resources still shows nothing for phoc, the issue is in Resources (for example it ignores the msm-kms fd or multiple clients), not the kernel.
- **Audio stalls on seek (q6asm retrigger, 2026-09-26, Denial/ALSA direct):** not re-tested under PipeWire, which keeps the PCM open. Needs a seek test in Showtime/mpv.
- **DP first-enable underrun on r185 (0106):** needs the monitor (see item 9).
- **App launch times:** not re-measured today (no launches allowed while the phone was locked).

## Method notes

- Commands were read-only, except one 20 s `/proc` spawn sampler and one 6 s `monitor-sensor` run after the GPU benchmark finished (20:53:27).
- A per-unit `NRestarts` loop over user units (`runuser` per unit) ran on the phone from 20:46:45 to 20:50:31 and timed out on the host side. That was during the benchmark's last segment (uv2 results at 20:39, done at 20:53), so that segment may carry some extra CPU load.
- No permission denials. No DP debugfs, rpmh or display-RSC access, no driver unbinds, no secrets printed.
