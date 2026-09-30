# What would irritate a real user (2026-09-29, bundle production-7.2.7-r185; re-checked 2026-09-30 on r201 and r205)

**Re-check 2026-09-30 (bundle production-7.2.7-r201, kernel build r104 =
series.production up to 0143, without 0125-0129 and 0136-0139).** Fixed items keep their text and carry a **Fixed**
line with the commit; open items carry **Still open**. Two new items (16,
17) came from the night review and the DP work. Phone facts marked
"verified 2026-09-30" were read on the phone (read-only) on r201.

**Evening re-check 2026-09-30 (bundle production-7.2.7-r205 since 18:20,
kernel build r108 = series.production up to 0144 without 0128/0129, DTB
platform-cpucap-dp4-btmtc-memx-dtb-r9; fallback safe-r8).** Updates are marked
"(evening)". Items 16 and 17 moved, and three new items (18-20) came from the
day's work. Phone facts marked "verified on r205" were read on the phone
(read-only) at 18:50.

| # | Item | Now |
|---|---|---|
| 1 | Phosh crashes on monitor hotplug | fixed, stress test pending (2e39d4b3, 967775d4, c9c08aaa) |
| 2 | Changing mode closes every app | open (by design); idle hand-back and unplug handling improved (598189d9) |
| 3 | New MAC/IP every boot | fixed (1c490e07) |
| 4 | Unattended updates reboot by themselves | fixed (1fc3b826, cda84165, 38b9f114, 78214337) |
| 5 | Brightness has ~4 levels | open |
| 6 | Wi-Fi gone 11 s after wake | open |
| 7 | Idle background churn | mostly fixed (598189d9, 2b662fd3, 445ef722); sleep policy still polls |
| 8 | Standby drain | open; bisect kit (78214337) needs requalifying for DTB r9 |
| 9 | Monitor 1080p only, hot | mostly fixed: HBR2 (0110, 6bffb233), no DPU pin (729c5e4a, ca10325b), 4 lanes (955c6afe); 5120x1440/100 Hz see 17; lower-power link 0145 (b19831d3) goes into r109 |
| 10 | Missing hardware | open |
| 11 | Early throttling | improved: `rog5-perf-mode` (1ad11e4f) with `auto` (95a3c7d5), `perf_on_power=always` (b15a6719) |
| 12 | Slow app launch | open |
| 13 | Slow to be fully ready | improved: Wi-Fi radio thermal gate (4c3dd95f); r201 at 23 s + 33 s, r205 at 21 s + 35 s |
| 14 | ~11 h of logs | fixed (598189d9, 78214337) |
| 15 | Charger does not wake the phone | open |
| 16 | Steam title-bar drag does nothing (new) | fixed (c75efe81), shim lifecycle test pending |
| 17 | 100 Hz and 5120x1440 hidden by 0114 (new) | open: 4-lane DP works (0136-0139); the modes need the `dpu_mode_clk_check=halved` test |
| 18 | Games crash with SIGBUS (new, evening) | fixed pending a retest: memx no-map + `rog5-sea-retire` (a79182ba) |
| 19 | Music and jobs cut by suspend on battery (new, evening) | fixed (10cc4116) |
| 20 | USB disks mounted only after a GUI login (new, evening) | improved: `rog5-usb-storage` (93f91107); gvfs interplay untested |

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
- **Fixed:** phosh 0.57.0-1.1 (2e39d4b3, lock shields on hotplug) and phoc 0.57.0-1.2 (967775d4, c9c08aaa: inert layer surfaces on DP unplug); phosh 1.2/1.3 also publish the lock state to logind (bace25b8, 729c5e4a). No Phosh or phoc core dump since 2026-09-30 00:00 (verified 2026-09-30, phosh 0.57.0-1.3, phoc 0.57.0-1.2); the deliberate plug/unplug stress test (whats-left test 3) is still pending.

### 2. Changing mode closes every app
- **User sees:** tapping "Desktop mode" or "Phone mode", unplugging the monitor, or 10 min of GNOME idle ends the current session. Browsers, editors and terminals all close. Chromium shows its "didn't shut down correctly" state next time.
- **How often:** every switch. Today: 3 Chromium SIGTRAP dumps (12:47, 13:14, 13:40), each exactly when `rog5-phosh`/`rog5-gnome` stopped. The log says `GPU process launch failed: error_code=1002 ... GPU process isn't usable. Goodbye.` A GNOME session at 19:21:53 lasted 40 s and ended on unplug.
- **Evidence:** `configs/systemd/rog5-gnome.service` (`Conflicts=rog5-phosh.service`), `rog5-desktop-mode` log ("display unplugged -> Phosh" at 14:26, 16:22, 19:22).
- **Cause:** Phosh and GNOME are two compositors on one tty. Only Phosh can lock, so the design swaps whole sessions.
- **Fix:** a real fix means one compositor for both screens: phoc with a desktop layout on DP, or GNOME Shell mobile. Short term: warn before the switch ("apps will close"), and delay the unplug switch-back (for example 30 s, so a loose cable does not kill the session). Effort **L** (short-term items S).
- **Still open** (by design). Improved in 598189d9: GNOME hands back to Phosh only after its own 10 min idle, and an unplug or "off" is honoured even while GNOME starts. Desktop mode is `manual` until one supervised boot test (see [whats-left](whats-left.md), test 1).

### 3. New MAC and new IP on every boot
- **User sees:** the phone's address changes after every reboot (today .91, .40, .120, .34, .109, .11). SSH bookmarks, the Deck scripts and router rules stop working. The router lists a new "alarm" device each time.
- **Evidence:** NetworkManager leases per boot; the wlan0 MAC (Qualcomm/Atheros OUI 00:03:7f) differs in boots -3, -2, -1 and 0. `addr_assign_type` is 0, and NM has `wifi.scan-rand-mac-address=no`, so the random MAC comes from the driver/firmware (no board MAC provisioned), not from NM privacy settings.
- **Fix:** set a fixed MAC. Either take the stock one (the WCN6855 MAC lives in the ASUS persist/`wlan_mac.bin`) in the DT (`local-mac-address`) or a systemd `.link` file, or set `wifi.cloned-mac-address=stable` in NM. The same applies to the Bluetooth address if it is also random. Effort **S**.
- **Fixed:** 1c490e07 (NetworkManager stable per-network MAC).

### 4. Unattended updates reboot the phone by themselves
- **User sees:** the phone restarts with no warning, closes apps and SSH sessions, and comes back locked.
- **Evidence:** `configs/systemd/rog5-update.service` sets `ROG5_UPDATE_REBOOT=idle`. In `initramfs/rog5-update`, `display_idle()` only checks that every backlight is 0, then `systemctl reboot`. The timer runs hourly. Today's update (17:26, 0.83 MiB) peaked at **6.8 GB of memory**, with no swap. No reboot was traced to it today (the next boot came from a lab reset).
- **Cause:** "Panel off" is used as "user is away". It is not true for server work, music with the screen off, SSH users, or desktop mode.
- **Fix:** default to `never`, or reboot only when there is no logind session activity, no remote client (reuse `rog5-sleep-policy`'s detector), no audio stream and no desktop mode, and send a notification first. Look at why the snapshot copy needs GBs of RAM. Effort **S**.
- **Fixed:** reboots only when the system is idle: no remote client, external display, stay-awake file or shutdown inhibitor (1fc3b826), no sound playing and only in the 01:00-06:00 window, snapshot copy under `MemoryHigh=2G` (cda84165); restores wait the same way and never force-reboot (38b9f114); snapshots exclude user data (~6 GB instead of ~27 GB) with a crash-safe journaled restore (78214337). The new restore passed fault injection but has not run a real rollback on the phone yet.

## Annoying

### 5. Brightness has about 4 real levels
- **User sees:** the slider jumps in big steps. The low end is either quite bright or black; there is no smooth night-time dimming.
- **Evidence:** status line "3-level brightness"; `test-results/2026-09-27-brightness-*.md` and `docs/reviews/2026-09-29-gpt-6-astra-brightness-review.md`. The DDIC applies only the high bits of the 10-bit DBV. Status "not resolved".
- **Cause:** a DSI command path problem (HS/LP packet delivery through the Pixelworks Iris bridge).
- **Fix:** run the pending E0-E2 readback experiments. As a stopgap, map the slider to the working levels so it does not look broken. Effort **L** (stopgap S).
- **Still open.**

### 6. Wi-Fi is gone for 11 s after every wake
- **User sees:** after unlocking, apps show "offline" and messages and SSH stall for about 11 s.
- **Evidence:** boots -1..-3: 14 of 14 resumes, association 10.9 s and DHCP 11.1 s after `PM: suspend exit`. wpa_supplicant logs `CTRL-EVENT-DISCONNECTED ... locally_generated=1 reason=3` before each suspend. The ~11 s is constant, which suggests a fixed wait (scan/firmware re-init), not the radio. `trial.py` allows up to 45 s.
- **Fix:** keep the association across s2idle (NM sleep/wake handling, ath11k suspend without disconnect as WoWLAN-lite), or at least reconnect to the last BSSID without a full scan. Effort **M**.
- **Still open.** (598189d9 holds Wi-Fi power save for 60 s instead of toggling it per SSH connection; the reconnect time is unchanged.)

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
- **Mostly fixed:** the desktop-mode switcher is event-driven (udev DRM + logind signals, ~0.1 % CPU instead of 1.6 %) and the Wi-Fi power-save toggling has a 60 s hold (598189d9); the ramdisk tailscaled skips itself while the USB link is down and while the packaged tailscaled runs (2b662fd3, 445ef722); the headless sway desktop starts on demand only (598189d9). **Still open:** `rog5-sleep-policy` polls every 5 s (evening: it now also checks audio playback and sleep inhibitors, 10cc4116, see item 19).

### 8. Standby battery drain
- **User sees:** noticeable overnight drain in suspend (about 79 mA at the pack; awake idle with the screen off is about 100-106 mA).
- **Evidence:** `test-results/2026-09-29-standby-ddr-floor.md`: DDR stays at 200 MHz in s2idle, cxsd/aosd/ddr counters stay 0, and the holder is not the APPS side (ADSP/SLPI/TZ candidates). The ADSP wakes 7-30 times a minute for battmgr.
- **Fix:** the boot-time bisects already planned (SLPI off, ADSP variant, CDSP load). Effort **L**.
- **Still open.** The bisect kit is ready (78214337: noslpi/noadsp/cdsp DTB variants, CDSP firmware fetch, `rog5-standby-bisect-measure`); the boots need the cable pulled (whats-left test 7). Sol's review: `reviews/2026-09-30-gpt-6.1-sol-standby.md`.
  (evening) `compose-standby-bisect-dtb.sh` still pins DTB r5; the variants must be rebuilt on DTB r9 (keeping memx; the no-ADSP variant also removes the bottom port's automatic 5 V) before test 7 (Sol evening review, item 6). Still ~79 mA with no CX/DDR collapse.
  (late evening) Kit requalified on DTB r9 (baseline/noslpi/noadsp/cdsp; noadsp also disables the bottom port's 5 V chain, the VA macro and LPI pinctrl) and the measure script no longer depends on qcom_stats "apss", which mainline never fills; rpmhpd sync_state is complete at runtime, so it is not the blocker (`test-results/2026-09-30-standby-blockers-r9.md`).

### 9. External monitor: 1080p only, and hot while in use
- **User sees:** a 4K or 32:9 monitor runs at 1920x1080@60 only. In desktop mode the phone gets warm even when idle.
- **Evidence:**
  - `/etc/tmpfiles.d/rog5-dp.conf` sets `msm.dp_max_rate=270000` (HBR; HBR2 gives about 25k symbol errors/s on lane 1), and `/etc/phosh/phoc.ini` pins `[output:DP-1] mode = 1920x1080@60Hz`.
  - `rog5-gnome.service` writes `fix_core_clk_rate 460000000` and 15.5 GB/s ab/ib votes with `perf_mode 2` for the whole GNOME session. Whether 0099-0101/0106 make this unnecessary is untested ("still needs the monitor").
  - Every DP enable logs `LM_4/LM_5, invalid DSPP_-1` dpu errors and the bring-up "DP sink @Nms" dumps.
- **Fix:** test r185 without the pin (count INTF underruns). If clean, drop the ExecStartPre. Fix HBR2 margin (vlevel/pre-emphasis tables) before removing the phoc.ini pin. Remove the DP debug logging from production. Effort **M** (pin removal S once tested; HBR2 L).
- **Mostly fixed:** native DP monitors get HBR2; only DP-to-HDMI/DVI converters are capped at HBR (0110, 6bffb233, e7cc18e6); the MSI 491C runs 3840x1080@60. The first-enable blue screen was a DSPP reassignment, fixed at the root by 0130-0132 (729c5e4a), and `rog5-gnome` no longer pins the DPU clock (ca10325b, 5/5 clean GNOME first enables on r104). **Still open:** 5120x1440 and 100 Hz (item 17); the hub's HDMI converter stays dark at HBR2 (0119/0134 opt-in experiments).
  (evening) The side port drives 4 lanes (0136-0139, kernel r105 and later, 955c6afe): 4 x HBR2 in both orientations after a replug on r202. One r202 boot with the monitor attached got no DP notification from the ADSP (suspected start-up race), not retested on r205. 0145 (`msm.dp_link_policy`, b19831d3) trains the lowest link rate that carries the mode (4 x HBR instead of 4 x HBR2 for 3840x1080@60, MMCX SVS instead of SVS_L1); it goes into r109 and needs `rog5-dp-power-measure` on the MSI.

### 10. Missing hardware
- **User sees:** no camera app, no fingerprint unlock, no NFC, no 3.5 mm headphone jack, and Bluetooth headsets are A2DP-only (no microphone). There is no earpiece sink in PipeWire either (only "Speakers").
- **Evidence:** `test-results/2026-09-27-compare-platform.md` (#11 cameras: no sm8350 camss/camcc upstream; #12 Goodix fingerprint needs the TEE; #8 NFC unmanaged), `2026-09-27-compare-audio.md` (#3 ES928x jack codec has no mainline driver; #8 HFP not carried on UART HCI). `wpctl status`: one sink, one source.
- **Fix:** document these as unsupported in Settings/port-status so users do not hunt for them. ES928x driver (L), cameras (L, upstream). The NFC VEN GPIO check is a 30 s power item (S).
- **Still open.** Audio over the DP cable is also missing.

### 11. The phone throttles early under sustained load
- **User sees:** games and benchmarks slow down after a few minutes.
- **Evidence:** during today's GPU benchmark the skin sensor read 44.8 C (trip at 42 C). Cooling devices `devfreq-3d00000.gpu 1/9`, `cpufreq-cpu4 1/15`, `cpufreq-cpu7 1/18`, GPU max 778 of 840 MHz. The step_wise policy caps big at 1766 MHz and prime at 1901 MHz at 42 C, and throttles much harder at 46 C.
- **Cause:** a deliberate skin policy (stock starts even earlier, at 36 C). It works as intended, but it is a trade-off.
- **Fix:** a "performance" profile (power-profiles-daemon hook) that raises the 42 C trip while on the charger or with the fan accessory. Effort **S**.
- **Improved:** `rog5-perf-mode normal|performance` (1ad11e4f), and `auto` (95a3c7d5) picks the performance trips on external power with a DP display connected; set on the phone. No Phosh toggle yet.
  (evening) `perf_on_power=display|always|never` in `/etc/rog5/perf-mode` (b15a6719); the phone has `always`, so any external power (also a headless server on a hub) gets the performance trips (verified on r205).

### 12. Apps are slow to appear from the Phosh grid
- **User sees:** Firefox cold start takes 7-9 s (2.6 s warm). The Calculator spinner shows for about 4 s. The Firefox launch splash timed out twice today (13:46, 14:26: `Startup of app 'Firefox' ... timed out`).
- **Evidence:** `test-results/2026-09-27-phosh-suspend.md` (launch timing); the journal. The Chromium splash timeouts stopped after the 13:24 override (see Historical).
- **Cause:** a cold page cache, the `uclamp.min 400` session boost only on the Phosh session, and possibly a Firefox app-id/StartupWMClass mismatch when a window opens on DP.
- **Fix:** preload or `vmtouch` the Firefox libs at boot; check the Firefox app_id against `StartupWMClass=firefox` on DP; measure again. Effort **S-M**.
- **Still open** (not re-measured).

### 13. Slow to be fully ready after boot
- **User sees:** the lock screen after about 33 s. Wi-Fi comes up about 25 s later, and sound, sensors and auto-rotate only about 39 s into userspace.
- **Evidence:** `systemd-analyze`: 21.4 s (kernel incl. ramdisk) + 39.2 s (userspace). The critical chain is `rog5-wifi-radio` 26.6 s → `rog5-bluetooth` 5.5 s → `rog5-audio` 0.6 s → `rog5-sensors`. Audio and sensors wait for Wi-Fi and BT by design ("after Wi-Fi and Bluetooth").
- **Fix:** check whether the audio/sensor ordering after Wi-Fi is still needed (it was a QUP/ADSP ordering workaround). If so, start audio/sensors in parallel with the 26 s Wi-Fi radio bring-up. Effort **M**.
- **Improved:** the Wi-Fi radio no longer waits for the SoC junction zones (4c3dd95f, ~16 s per boot); r201 reached multi-user at 23 s (kernel + initramfs) + 33 s (userspace) and Wi-Fi associated at ~57 s (verified 2026-09-30). The audio/sensor ordering is unchanged. (evening) r205: 21.2 s + 35.5 s = 56.7 s (verified on r205).

### 14. Only about 11 hours of logs are kept
- **User sees:** "what happened last night?" cannot be answered. The journal starts at 09:56 today.
- **Evidence:** `journalctl --disk-usage` 192 MB. `/etc/systemd/journald.conf.d` sets `SystemMaxUse=200M`, based on the 16 GiB overlay, which is now 128 GiB (106 GB free). Most of the volume is noise: 4117 `systemd` lines this boot (session scopes, tailscaled retries).
- **Fix:** raise the cap to about 1-2 GB, or exclude the journal from the update snapshot. Cut the noise (item 7). Effort **S**.
- **Fixed:** `SystemMaxUse=1G` (598189d9), and the journal is left out of update snapshots (78214337).

### 15. Plugging in the charger does not wake a sleeping phone
- **User sees:** no screen or charging feedback when plugging in while asleep.
- **Evidence:** 0084 (charger-attach wakeup) was pulled after it hung the phone on plug-in (`2026-09-27-phosh-suspend.md`, 2026-09-28 entry). The plug-in wake test is still pending.
- **Status:** likely. Effort **M**.
- **Still open.**

### 16. Steam cannot be dragged by its title bar (new, 2026-09-30)
- **User sees:** in GNOME desktop mode, dragging the native Steam window by its own title bar does nothing; the window stays where it opened.
- **Status:** confirmed (night review 2026-09-30, "Open, with a plan"). In progress.
- **Likely cause:** mutter ignores the move request from Steam's CEF client-side title bar (probably the root coordinates it sends under XWayland). Not proven yet.
- **Fix:** capture the X events (`xev`/`xinput` on the Steam window) while the user drags (the former whats-left test 6, no longer needed), then fix the request or add a window rule; meanwhile Super+drag should move it (GNOME default, not tried yet). Effort **M**.
- **Cause (found):** CEF's X window covers each Steam window with a full input shape, so SDL's hit test never sees the click and no `_NET_WM_MOVERESIZE` is sent; steamwebhelper's own code that cuts the drag areas out of that shape returns early because a per-window flag is never set.
- **Fixed (evening):** `steam-arm64-drag.so`, an LD_PRELOAD shim active only for the known steamwebhelper build ID and code bytes, sets that flag; title-bar drag and edge resize work (c75efe81; cutting those holes by hand on the phone first made drag and resize work, user-confirmed; the OpenGL composer override 6b3369cd is dropped). After an unknown Steam update it prints one line (`... shim needs updating`) and only forwards; `ROG5_STEAM_DRAG=0` leaves it out. **Still open:** Sol's note that the shim keeps raw object pointers in a 128-entry table without cleanup on destruction; window churn (open/close many windows) is not tested yet.

### 17. 100 Hz and 5120x1440 are hidden on the MSI monitor (new, 2026-09-30)
- **User sees:** the MSI MPG491C offers only up to 3840x1080@60 in the display settings; its 100 Hz and 5120x1440 modes do not appear.
- **Status:** confirmed, deliberate for now. In progress.
- **Evidence:** 0114 (f42d4c32) rejects modes whose full pixel clock exceeds the DPU core clock, because 5120x1440@60 and 3840x1080@100 came up blue on the 2-lane link. Sol's DPU-clock review (`reviews/2026-09-30-gpt-6.1-sol-dpu-clock.md`) calls 0114 a quarantine of two failing modes, not a proven limit, and ranks QoS/fetch latency at the first enable above the pixel-rate limit. The monitor offers DP pin assignment C (4-lane DP).
- **Fix:** 4-lane DP (0136-0139, not in r104; 0139 makes the 0114 check switchable for A/B tests), then relax 0114 for modes that test clean. Effort **M-L**.
- **Still open (evening):** 4-lane DP works (r105 and later, see item 9), but 5120x1440@60 and 3840x1080@100 have not been tried on it: `echo halved > /sys/module/msm/parameters/dpu_mode_clk_check` (0139) exposes them for the test, HBR3 is a separate opt-in (0138). Whats-left test 9.

### 18. Games crash with SIGBUS (new, 2026-09-30 evening)
- **User sees:** a game (Dota 2 under FEX) or Steam dies with SIGBUS.
- **Evidence:** 0116 logs user synchronous external aborts with the PFN: instruction-fetch-only aborts at 0x34b4xxxxx/0x34bcxxxxx (r202: pfn 0x34bc8d, 0x34bc91 under Dota 2). The memx overlay (`dts/qcom/sm8350-asus-rog-phone5-exec-abort-memory.dtso`) documents why: most likely the ASUS wrapper's QTEE shared-memory bridge, left registered read/write, no execute.
- **Fixed (pending a retest):** DT feature memx maps out 64 MiB at 0x34a000000 (no-map), and `rog5-sea-retire` soft-offlines any further block that aborts (a79182ba). The reservation is in both DTBs (r9 and safe-r8); the retire service needs 0116's abort log, which the r69 fallback kernel does not have. **Still open:** Dota 2 for 30 min (whats-left test 16); the reservation is a mitigation, not a proven bridge teardown, and the 128 MiB RAM-trial wrapper is not checked separately (Sol evening review, item 1).

### 19. Music and background jobs stop when the phone suspends on battery (new, 2026-09-30 evening)
- **User sees:** on battery with the screen off, music stops and a detached job pauses 60 s later.
- **Evidence:** `rog5-sleep-policy` suspended with `--check-inhibitors=no` and checked neither audio nor sleep inhibitors (Sol evening review, item 5).
- **Fixed:** 10cc4116: an ALSA playback substream RUNNING/DRAINING, any block/block-weak sleep inhibitor (except rog5-server's own) and a charger-attached force-discharge keep the phone awake. Bluetooth playback is not counted. No on-battery music/inhibitor test is recorded yet.

### 20. USB disks are mounted only after a GUI login (new, 2026-09-30 evening)
- **User sees:** a server disk on the hub is not there after a reboot until someone logs in; a stick present at boot is not mounted.
- **Evidence:** gvfs/udisks mount removable media only for a logged-in session (Sol evening review, gap table).
- **Improved:** `rog5-usb-storage` (93f91107) mounts the filesystems listed in `/etc/rog5/usb-storage` (by UUID/LABEL) at boot and on plug, only after the p2-attest boot gate; on r205 the configured disk was mounted at 28 s (gate PASS at 25 s; verified on r205). **Still open:** unconfigured sticks still wait for gvfs after login; whether gvfs and `rog5-usb-storage` get in each other's way is not tested (whats-left test 17).

## Cosmetic / sloppiness

- **The device is called "alarm" everywhere:** hostname, Bluetooth name (`bluetoothctl show`), DHCP hostname on the router, the prompt, and the journal. Tailscale calls it `rog5`. Fix: `hostnamectl set-hostname rog5` in the image. **S**, confirmed. **Fixed:** 598189d9 (`configs/hostname`); the phone reports `rog5` (verified 2026-09-30).
- **Saved default audio output is `auto_null`:** `wpctl status` → "Default Configured Devices: Audio/Sink auto_null". PipeWire falls back to Speakers today, but if the dummy sink ever appears first (early boot, before `rog5-audio` at about 38 s), sound goes nowhere. Fix: clear the WirePlumber default-nodes state and set Speakers. **S**, confirmed. **Fixed:** 598189d9 drops the stale `auto_null` default.
- **Microphone probe errors at each session start:** `spa.alsa: 'hw:0,0'/'hw:0,1': capture open failed: Invalid argument` and `no backend DAIs enabled for MultiMedia1`. The "Built-in microphones" source works; the pro-audio profile probe fails. Fix: disable the pro-audio profile for the card in a WirePlumber rule. **S**, confirmed. **Fixed:** MultiMedia1/2 are playback-only in the DT (a5b7ee30, DTB r5 and later); no capture-probe errors on r197.
- **Denial leftovers still installed and running:**
  - `rog5-session-bus.service` ("Session D-Bus for the Denial session", a root dbus-daemon) is enabled and running;
  - `rog5-powerd` and `rog5-battery-log` ("for the Denial session") are enabled;
  - `/opt/denial` takes 194 MB;
  - the phoc.ini comment still refers to Denial.
  Fix: disable them, or remove them if Denial is retired. **S**, confirmed.
  2026-09-29: Denial is retired; its units, daemons and configs are removed from
  the repository (docs/history/cleanup-2026-09-29.md); the phone-side uninstall
  is separate.
  **Fixed** on the phone too: the three units are gone and `/opt/denial` is
  removed (verified 2026-09-30).
- **Workarounds whose reason has gone:**
  - `~phone/.config/environment.d/60-rog5-mutter.conf` sets `MUTTER_DEBUG_DISABLE_HW_CURSORS=1`. The test result itself says the cursor A/B test was confounded and the real cause was the DPU clock. The software cursor costs GPU time and adds pointer lag in desktop mode.
  - `/etc/drirc` forces `tu_restrict_subgroup_size_64` for every Vulkan app, to avoid one Geekbench hang.
  Re-test both on r185 and keep them only if still needed. **S**, confirmed present.
  **Still open:** both are still installed on r201 (verified 2026-09-30). Now that
  0130-0132 fixed the DP blue screen, the cursor workaround can be A/B tested again.
- **Phosh background is blue, not the intended black:** the system dconf default sets `primary-color='#000000'` (OLED power), but the user database overrides it with `'#2050c0'`. Likely set by an earlier restore or test. **S**, likely. **Fixed:** the user value is `'#000000'` again (verified 2026-09-30).
- **Battery percentage is hidden in the top bar** (`show-battery-percentage=false`). Most phone users expect it. **S**. **Fixed:** 598189d9 (`show-battery-percentage=true` in the system dconf).
- **Kernel WARNs and faults on every boot:** 2 WARN traces from `clk_core_disable`/`clk_core_unprepare` during `msm` probe (DSI PLL reparent), so the kernel is tainted `W` from boot. There are also 4-7 SMMU "Unhandled context fault" lines at boot (display handover SIDs). They are harmless, but they hide real problems in bug reports. **M**, confirmed. **Not seen on r201:** 0 WARN traces and 0 SMMU context faults in this boot's kernel log (verified 2026-09-30); keep watching.
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
  **Partly fixed:** `rog5-wayvnc-phone` runs only beside phoc (95b93d72; 0 failures on r201).
  **Still open:** `Atomic commit failed` on DSI-1 (7 on the r201 boot) and the rest.
- **Sensors:**
  - iio-sensor-proxy reports "No proximity sensor", though the VCNL36866 has one (the phone does not blank on the ear or in a pocket);
  - `rog5-sensors` logs `Could not open /vendor/factory/gsensor_{x,y,z}.nv`, so the accelerometer is uncalibrated.
  **M**, confirmed.
  **Partly fixed:** proximity works (`PROXIMITY_NEAR_LEVEL=239` from this unit's
  factory calibration, 2902038a). **Still open:** accelerometer calibration.
- **Clock after a crash:** after the 17:29 hard reset the new boot started 18 s in the past (boot -4 first entry 17:28:52 < boot -5 last 17:29:10), until NTP. The RTC offset is saved only at shutdown and after NTP. Fix: save it periodically. **S**, confirmed once. **Still open.**
- **Background services a phone does not need:** Evolution data servers, localsearch indexer, GNOME Smartcard/Wwan/PrintNotifications/UsbProtection daemons, plus a permanent headless sway (93 MB) with two wayvnc servers. None was busy in the sample, but they cost memory and wakeups. **S**, confirmed present. **Partly fixed:** the headless sway desktop starts on demand only, and GNOME Software no longer downloads updates in the background (598189d9). The rest is still open.
- **Project docs are stale:** the generated status block in `docs/current-state.md` still says "Production 7.2.7 r93/r98 default"; the phone runs r185. `manifests/current-artifact.json` still points at a 7.1.4 runtime. Not user-facing, but it misleads the next person. **S**, confirmed. **Fixed:** one status source, `status/components.json`, with a generated block (612dfd56); `manifests/` archived (de0132a9).

## Historical-fixed (seen today or recently, fixed since)

| Item | Evidence | Fixed by |
|---|---|---|
| Phosh spinner outlived Chromium's startup | `Startup of app 'Chromium' ... timed out` 13:11, 13:23; the stock `chromium.desktop` has the literal `StartupWMClass=@@startup_wm_class` (Arch ARM packaging bug) | `~phone/.local/share/applications/chromium.desktop` (13:24, `StartupWMClass=chromium`, `StartupNotify=false`); no timeout since. Upstream it to the package. |
| phoc crash loop at session start | 7 SIGABRT 11:32:31-11:33:07: `config_ini_handler: assertion failed: (strcmp ("Hz", end) == 0)` | phoc.ini mode now `1920x1080@60Hz`. A typo in phoc.ini still takes the session down; validate the file on install. |
| squeekboard abort loop in GNOME | 5 SIGABRT 13:36:37-40, "No virtual keyboard manager Wayland global available" | not seen in later GNOME sessions |
| Geekbench Vulkan GPU hang | `gpu fault ... hangcheck recover!` 15:19, 15:20 (plus 2 Geekbench segfaults) | `/etc/drirc` (15:27); see the sloppiness item |
| Side-port hub died over suspend | 31k SMMU faults + `Host System Error` (r183) | 0105 (r184+) |
| USB (to PC) did not re-enumerate after replug | user report 2026-09-26 | `rog5-usb-reconnect` (logs "PASS device enumerated after re-initialisation") |
| rog5-tailscaled retried every 5 s | 221 restarts in 20 min | 60 s retry, then skips while the USB link is down and while the packaged tailscaled runs (2b662fd3, 445ef722) |
| Apps opened on the invisible sway desktop | 2026-09-28 | sway-base.conf, `XDG_CURRENT_DESKTOP=Phosh:GNOME` |
| gnome-session abort "VT already taken" | 15:57:03 | test-induced (GNOME restart loop) |
| Phone reset during suspend entry (boot -5 ends at `PM: suspend entry`) | 17:29 | test-induced (xHCI unbind before suspend) |
| Phone reset after an xHCI unbind (same 17:29 reset) | likely a NULL-hcd dereference in `dwc3_qcom_read_usb2_speed()` (strong inference, no oops record) | 0117 (d486b4ec), 0141 (efbfe2b7) |
| Desktop mode could start GNOME from a locked phone at boot | Phosh's `GetActive` only means "panel blanked" | LockedHint yes->no of rog5-phosh's own session (9129e796, bace25b8), fail-closed re-confirmation (00986001); mode `manual` until the supervised boot test |
| DP blue screen at the first enable | a GAMMA_LUT commit moved DP to LM_2/3+DSPP while the encoder read PP_4/MERGE_3D_2 | 0130-0132 (729c5e4a); DPU pin off (ca10325b) |
| Speakers silent, then very quiet | SENARY back end at S16 against the 24-bit clock; the S24_LE front end reaches the amps far below full scale | f8aa5a5d, 33d3ea26 (0 dB), e29c5ad3 (PipeWire S16LE; the 24-bit path is still open); protection DSP on both amps (dfc54acc) |
| Monitor USB dead after boot or replug (-71) | r194 first boot | reconnect retries (fb89fff3, 66f9944a); kernel fix pending the replug test (0142/0143, efbfe2b7) |
| USB drives not shown in Files/Disks, ISO mounting refused | udisks masked, then a polkit rule that refused every loop | b8582e7e, fd8f73b0, fd6dd9e5 |
| Steam title bar did not drag (item 16) | CEF's X window took every click, so SDL's hit test never ran | c75efe81 (LD_PRELOAD shim) |
| Games died with SIGBUS (item 18) | instruction-fetch aborts in 0x34b4xxxxx/0x34bcxxxxx | memx no-map + rog5-sea-retire (a79182ba); Dota retest pending |
| Bottom USB-C needed 5 V by hand | the RT1715 ALERT never fired: SPI 566 still marked edge from stock | 0144 PDC edge/level (317451ad, eaea30b8); auto 5 V on attach on r204/r205 |
| Fallback could not restore update snapshots | safe-r7 predates the v2 seal | safe-r8 with the current init (ac8220d2) |

## Not reproduced / unverified

- **Per-app GPU for phoc:** `/proc/<phoc>/fdinfo` exposes `drm-engine-gpu` (404 ms on client 50), so the data exists. If Resources still shows nothing for phoc, the issue is in Resources (for example it ignores the msm-kms fd or multiple clients), not the kernel.
- **Audio stalls on seek (q6asm retrigger, 2026-09-26, Denial/ALSA direct):** not re-tested under PipeWire, which keeps the PCM open. Needs a seek test in Showtime/mpv.
- **DP first-enable underrun on r185 (0106):** needs the monitor (see item 9).
- **App launch times:** not re-measured today (no launches allowed while the phone was locked).

## Method notes

- Commands were read-only, except one 20 s `/proc` spawn sampler and one 6 s `monitor-sensor` run after the GPU benchmark finished (20:53:27).
- A per-unit `NRestarts` loop over user units (`runuser` per unit) ran on the phone from 20:46:45 to 20:50:31 and timed out on the host side. That was during the benchmark's last segment (uv2 results at 20:39, done at 20:53), so that segment may carry some extra CPU load.
- No permission denials. No DP debugfs, rpmh or display-RSC access, no driver unbinds, no secrets printed.
