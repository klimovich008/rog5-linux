# Denial Settings and top bar on the phone (2026-09-26)

Phone: ROG Phone 5, default `production-7.2.7-r113`, Denial `/opt/denial` =
upstream 85b2303e + shell 0001/0004/0006/0007/0012 (libapp `assembly-s3`,
`8fadb722...`, icon font `2ea5505e...`) + compositor 0005/0006/0008-0011/0013
(deniald `s1`, `ed92d012...`). Patches and deployed-state table:
`patches/denial-shell-85b2303e/README.md`. UI driven with uinput taps and
swipes (`/root/ufx/seq.py`, `scripts/device/bench/vtouch.py`); screenshots
with `scripts/device/bench/scanout.py` (1/3 scale); a selection is in
`test-results/2026-09-26-denial-settings-top-bar/`. Phone writes and Denial restarts were run by the coordinator
with the user's approval (the auto-mode classifier refused them from this
session).

## What was broken, and why

| # | Item | Backend | Before | Root cause | Fix |
|---|---|---|---|---|---|
| 1 | Brightness slider (QS, Displays) | deniald → logind `Session.SetBrightness` on `session/auto` | Broken: nothing changed | Denial runs as a root service without a logind session (`UnknownObject session/auto`) | 0013: a root deniald writes `/sys/class/backlight/ae94000.dsi.0/brightness` (panel driver's 0x51 path) |
| 2 | Volume slider (QS, Audio page, per-app) | deniald → libpulse | Broken: "could not start PulseAudio connection" | No sound server (PipeWire installed, no WirePlumber/pipewire-pulse, nothing running) | Packages `pipewire-pulse wireplumber pipewire-alsa`; root units `rog5-pipewire`, `rog5-wireplumber`, `rog5-pipewire-pulse`; WirePlumber rule: pro-audio profile, "Speakers" = hw:0,0 at 2 ch S16LE 48 kHz |
| 3 | Rotation tile | local Dart state | Stub: deniald rotated DSI from iio-sensor-proxy regardless | Placeholder | 0012+0013: persisted `layout.rotationLock` (default locked), deniald honours it |
| 4 | Performance tile | `/run/denia-powerd/profile.sock` | Stub: label cycled, nothing applied | denia-powerd does not exist on the phone | `rog5-powerd` (same protocol; cpufreq/devfreq limits); tile hidden without a daemon |
| 5 | Status bar cellular bars | none | Fake: always "connected" | Hard-coded | Removed (no modem) |
| 6 | Status bar Wi-Fi | none | Fake: always "connected" | Hard-coded | Follows NetworkManager: off / disconnected / 1-4 bars |
| 7 | Status bar BT, DND, notifications, charging | — | Missing | — | Icons for connected BT device, DND, unread notifications; charging bolt |
| 8 | QS Settings gear | — | Disabled ("Settings are unavailable") | Upstream placeholder | Opens Settings |
| 9 | Settings app | local app needs `DENIA_EMBED_SETTINGS=1`, else `/usr/bin/denial-settings` | Unreachable: no icon, no gear | Env not set; desktop binary absent | Drop-in `30-embedded-settings.conf` |
| 10 | Notifications | deniald `org.freedesktop.Notifications` | Only transient banners; no history | Mobile scene has no notification centre | History below the QS controls |
| 11 | Network page | NetworkManager | Secured, unsaved networks: disabled "Password required" | No password entry on the page | Join page with password (`WifiJoinNetworkRoute`) |
| 12 | Clock / time zone | `DateTime.now()`; timedated | Clock in UTC (2 h behind the user) | Phone TZ was UTC; no time zone setting | Europe/Paris set (host's zone); Date & time section (timedated `SetTimezone`, `SetNTP`) |
| 13 | Settings pages that do nothing on a phone | — | Touchpad (4 greyed controls), Desktop layout, Developer (hot reload etc. are upstream stubs), cursor, window opacity, launcher/dashboard overlays, close effects | Desktop-only | Hidden in the mobile profile (Touchpad reappears with a touchpad/mouse) |
| 14 | About | static text | No device information | — | Device, OS, kernel, processor, memory, host name |
| 15 | Power menu "Log out" | deniald exits | Black panel until reboot | `Restart=on-failure` | Drop-in `Restart=always` |
| 16 | Icon font | `flutter_assets/fonts/MaterialIcons-Regular.otf` | Every icon added after r1 drew blank/wrong | libapp deploys never shipped the tree-shaken font | Font deployed; README deploy procedure updated |

## Results on the phone

Every row is a phone observation on r113 with deniald s1 and libapp s2
(s3 for the last two rows of the Settings table), taken with uinput input and
scanout screenshots.

### Top bar and quick settings

| Item | Backend | Status | Evidence |
|---|---|---|---|
| Clock (status bar, shade, home) | `DateTime.now()`, TZ Europe/Paris | Works | 19:28 CEST shown; `timedatectl` Europe/Paris, synchronized |
| Battery % | `/sys/class/power_supply` | Works | 100 %; charging bolt shows while `status` is Charging (not observed: the battery was Full) |
| Wi-Fi indicator | NetworkManager | Works | Full bars while connected; crossed out after the tile turned the radio off (`nmcli radio wifi` disabled), bars again after it turned it on and NM reconnected |
| Cellular glyph | none | Removed | No modem; not drawn |
| DND indicator | notification policy | Works | Icon appears with Silent on, gone when off |
| Bluetooth indicator | BlueZ | Not observable | Shown only with a connected device; the controller never initialises (see below) |
| Unread-notification icon, shade history | deniald notification server | Implemented, not exercised | No notification arrived during the run; `notify-send` test left for the user |
| Performance tile | rog5-powerd | Works | balanced -> performance (policy0/4/7 min 998400/1209600/1305600, GPU min 443 MHz) -> power-save (max 1497600/1766400/1900800, GPU max 540 MHz) -> balanced; `power_profile.env` follows |
| Silent tile | notification policy | Works | Toggles, status-bar icon follows |
| Wi-Fi tile + surface | NetworkManager | Works | Off/on from the tile; surface lists ~20 networks; disconnect and reconnect of the saved network from the surface |
| Bluetooth tile + surface | BlueZ | Honest "No adapter" | Surface: "No Bluetooth adapter" |
| Rotation tile | `layout.rotationLock` -> deniald | Works (lock state); auto-rotate needs a physical test | settings.json `rotationLock` false/true follows the tile; sensor reported "undefined" (phone flat) so no rotation was due |
| Brightness slider | deniald -> sysfs backlight | Works | 10 -> 675 (`brightness`), log "writing sysfs directly" |
| Volume slider | deniald -> pipewire-pulse | Works | Sink volume 100 % -> 31 %; log "audio connected through native libpulse"; user heard beeps from both speakers after the 2 ch S16LE rule |
| Settings gear | in-shell Settings (`DENIA_EMBED_SETTINGS=1`) | Works | Opens Settings |
| Power menu | logind | Works as designed | Suspend/Hibernate show the rog5-server-inhibit blocker; Lock, Log out, Restart, Power off not pressed (Lock would lock out a password-less root; restart/power-off reboot the phone) |

### Settings

| Page | Status | Evidence / notes |
|---|---|---|
| Appearance | Works | Colour scheme, wallpaper, accent, blur, shape; cursor and window-opacity sections hidden |
| Language & time | Works | Language chips; Date & time: Europe/Paris, synchronized, NTP switch, zone list from timedated with search ("war" -> Europe/Warsaw), cancelled without changing. The Chinese chip shows tofu: no CJK font on the phone |
| Keyboard | Works (hardware keyboards) | Layout, options, repeat |
| Touchpad | Hidden | Reappears with a touchpad or mouse |
| Shortcuts | Works | 34 shortcuts listed |
| App environment | Works | Scopes and apps listed |
| Animations | Works | Only the global speed on mobile |
| Desktop layout | Hidden | Desktop only |
| Overlays | Works | Notifications and system HUD placement only |
| Lock screen | Works | Backdrop, clock scale, status |
| Audio | Works | Master volume on PipeWire; per-app list ("No applications are playing audio") |
| Displays & video | Works | DSI-1 1080x2448, 60 Hz, scale 250 %; brightness card drives the backlight |
| Network | Works | Scan, list, details, saved/add; secured networks open the join page (password field, keyboard opens; cancelled) |
| Bluetooth | Honest after s3 | s2 said "Current adapter" with a live switch; s3 shows "No adapter" and disables switch and Scan |
| Power | Works | UPower battery details (health 90 %, 577 cycles, 42.9/47.6 Wh, 8.65 V, 30 °C); idle lock/screen-off/suspend timers |
| Developer | Hidden | Upstream stubs (hot reload/restart, auto-reload, revert) and a missing `denialctl`/`denial-ui` |
| About | Works | ASUS ROG Phone 5, Arch Linux ARM, 7.2.7-rog5-production, Qualcomm SM8350 8 cores, 10.4 GB, alarm |
| All pages (s2) | Fixed in s3 | Toggle labels, row titles and dropdown values were dark on the dark panel: the embedded app had no Material theme. s3 screenshot: "Enable backdrop blur", "Blur quality  Fast", "20%" readable |

### Left for a person

- Auto-rotate with the rotation lock off (turn the phone).
- A notification (`notify-send`) to see the unread icon and the shade history.
- The charging bolt while the battery charges (below 100 %).
- The Bluetooth indicator once a controller works.
- When the embedded Settings app has a focused text field, the keyboard pans
  the whole app up under the status bar (upstream local-app pan).

## Not Denial (reported, not changed)

- **Bluetooth:** the QCA controller never initialises: "Reading QCA version
  information failed (-110)" on all 119 journaled boots, and
  `btmgmt info` lists no controller. `hwcheck.py` only checks that
  `/sys/class/bluetooth/hci0` exists, so it reports pass. The QS tile and
  surface say "No adapter" (honest).
- **Hotspot:** `rog5-hotspot` defaults to uplink `wlp1s0`; NetworkManager
  names the interface `wlan0`. There is no hotspot control in Denial.
- **Lock without a password:** root's shadow field is `x`, so PAM can never
  unlock, yet Denial still locks (the power menu "Lock", double tap, idle
  lock, a stale `/run/user/0/denia-lock-request`). A compositor gate
  (ignore lock requests while the account has no usable password; no PAM
  bypass) is written and user-approved but was refused by the auto-mode
  classifier, so it is not applied: the session scratchpad `st/proposal-lock-gate-authentication.diff`.
