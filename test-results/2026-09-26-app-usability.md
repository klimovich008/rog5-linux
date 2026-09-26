# App usability on the Denial mobile session (2026-09-26)

Phone: ROG Phone 5, `production-7.2.7-r98`, Arch Linux ARM aarch64, Denial
`/opt/denial` = upstream 85b2303e + shell 0001/0004/0006 + compositor 0005/0006
(see `patches/denial-shell-85b2303e/README.md`). Panel 1080x2448, scale 2.5,
logical 432x979. Apps were driven over Wi-Fi SSH (192.168.1.180) with uinput
touch/keys (`scripts/device/bench/vtouch.py`). Each app was launched from the
home-screen icon, and its Wayland traffic was traced with `WAYLAND_DEBUG=1` on a
relaunch. GPU use was read from `/proc/<pid>/fdinfo` (`drm-driver: msm`,
`drm-engine-gpu` ns) and memory is PSS summed over the app's processes.
Screenshots are in `test-results/2026-09-26-app-usability/`, 360x816 (1/3
panel scale). The full set of 83 shots is in the session scratchpad
`/tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/apps/`.

Nothing was upgraded. Every install was first checked with
`pacman -S --print`, and none upgraded an installed package. `systemd`
is still 261.3-1. In total 255 packages were installed (1.66 GiB). Their
cached package files were deleted afterwards, and root now has 11 GB free.

## Results

| # | App (package) | Works? | Keyboard auto-open on field tap / close on outside tap | Issues | Root cause | Improvement |
|---|---|---|---|---|---|---|
| 1 | Firefox 156 (`firefox`) | Yes, after the userChrome fix | Yes/yes, but the tap must land 26 px right and 23 px below the field; when the field is at the top it is hidden while typing | Window 500 px wide by default, cropped (back/forward and menu off-screen). Every tap lands 26 px left and 23 px up of the finger. The keyboard pans the whole app up, so the URL bar and top form fields are invisible while typing. Opening a URL from another process fails (remote needs D-Bus) | Chrome CSS `min-width` of 450+ CSS px. **Mobile input regions ignore the CSD window-geometry origin (26,23)**. The keyboard viewport is a fixed full-height pan, not caret-aware | `userChrome.css` min-width override (applied). Build and deploy Denial patches 0019 (input origin) and 0014-0017 (caret-aware pan) |
| 2 | Chromium 153 (`chromium`) | Partly | Yes/yes for fields that are not focused. A tap on the already-focused omnibox (focused at startup) does **not** open it | Refuses to start as root without `--no-sandbox`, so the icon did nothing. Minimum width 500 DIP, so the window is cropped. The first-run ToS dialog (600x510) had its buttons off-screen. Input offset (16,10). `--force-device-scale-factor` breaks sizing (1032-px window) | Denial runs apps as root. Chromium minimum window size. The OSK policy needs a fresh commit after the touch, and Chromium sends nothing when an already-focused field is tapped | `~/.config/chromium-flags.conf` (applied). Denial: scale oversized windows down to fit. Policy: show the OSK after a tap while that client's text-input stays enabled |
| 3 | foot 1.28 (already installed) | Yes | Opens at launch (enable on focus) and closes on a status-bar tap | Prompt and output are hidden behind the pan while typing. Very small default font. Starts in `/` | Fixed pan (as in #1). Launch cwd = deniald's cwd | Caret-aware pan (0015). `foot.ini` font size. Denial should launch apps with cwd=$HOME |
| 4 | Files: nautilus 49 → **Thunar 4.20** (`thunar`, added) | nautilus: **no**. Thunar: yes | Thunar: yes/yes (location entry) with the offset compensated | nautilus exits with "Running as root is not supported" and the launch splash hangs about 10 s with no error. Thunar (GTK3) is cropped slightly, is desktop-style, and shows a root warning banner | Session runs as root. The GTK3 CSD offset | Run the session as a normal user (long term). Nautilus hidden from the grid (applied) |
| 5 | Text Editor 49 (`gnome-text-editor`) | Yes | Opens at launch and on a tap in the text; closes on an outside tap | While typing, the header bar and first lines are hidden behind the pan (typed text is invisible until the keyboard closes) | Fixed pan | 0015 caret-aware pan |
| 6 | mpv 0.40 (`mpv`) | Yes, with two caveats | n/a | By default the video is zoomed and cropped. **Audio stalls on any seek or loop**, and the video freezes with it (the A/V clock waits on ALSA). Decoding is software (no hwdec) | mpv shrinks its window to the video aspect (432x243) and Denial stretches it to cover. **q6asm-dai: after a stop/start retrigger, hw_ptr never advances** (`Error queuing playback buffer -16`, 1121 times). The kernel has no Venus V4L2 decoder, and Turnip has no Vulkan video | `keepaspect-window=no` (applied). Kernel: fix q6asm trigger START after STOP (near patches 0049-0051). Denial: letterbox (contain) instead of cover |
| 7 | Image Viewer 49 (`loupe`) | Yes (open files from the CLI) | n/a (the file chooser has no reachable entry) | "Open Files…" gives a GTK file chooser far wider than the screen, with Open/Cancel off-screen. The bottom nav/zoom buttons sit in the gesture band | Desktop-sized dialog. The shell's bottom gesture band swallows taps | Scale-to-fit for oversized windows/dialogs. Stop the gesture band eating taps (or shrink the app window above it) |
| 8 | Calculator 49 (`gnome-calculator`) | Yes | The OSK opens at launch (the entry autofocuses) and **covers the keypad**. A tap on the entry reopens it; an outside tap closes it | The bottom row (0 . x f(x)) and the lower half of "=" sit in the gesture band and can't be tapped | The 0006 policy opens the OSK on focus even when the app has its own keypad. Gesture band | Per-app "don't auto-open on launch" (or only open after a touch for GTK4 autofocus). Gesture band fix |
| 9 | Weather 49 (`gnome-weather`) | Yes, once a session bus exists | Yes/yes (city search popover, stays above the keyboard) | From the icon it did nothing: `Exec=gapplication launch` needs session D-Bus activation. The activated service then failed with "Failed to open display" until the bus had `WAYLAND_DISPLAY`. The Hourly/Daily switcher is in the gesture band. geoclue location was not used (manual city). Data from met.no loaded over Wi-Fi | No session bus in the Denial environment | Session bus for the root session (running now as a transient unit; proposed unit below) |
| 10 | System Monitor 49 (`gnome-system-monitor`) | Starts, poor fit | n/a | 620 px wide window, cropped 94 px each side, and tab taps miss | GTK4 minimum width | Scale-to-fit. `top`/`htop` in foot is the usable alternative |

GPU check: every GL/Vulkan client used the A660 (`msm` DRM client with
non-zero GPU time). Firefox WebRender used 250-480 ms of GPU time. Chromium's
GPU process had a client. The GTK4 apps use the GL renderer (8-75 ms). mpv
used `gpu-next` on Vulkan "Turnip Adreno 660". Thunar (GTK3) draws with cairo
on the CPU, which is normal for GTK3. llvmpipe was not seen anywhere.

Startup, from the icon tap to the window or focused editor. These are rough
figures from the logs:

| App | Startup | PSS (MiB) |
|---|---|---|
| Firefox | 3.2 s | 574-615 (11 processes) |
| Chromium | 2-3 s (first run ~7 s) | 463 (9 processes) |
| Calculator | 0.9 s | 80-106 |
| Text Editor | 0.6 s | 80 |
| Loupe | ~1 s | 91-147 |
| Thunar | ~1 s | 82 |
| Weather | ~2 s | 105 |
| System Monitor | ~3 s | 126 |
| mpv | <0.5 s | 231 while playing 1080p30 H.264 (~0.66 of one core, software decode) |
| foot | — | 38 |

No app crashed, and no GPU faults appeared during the run. The deniald
SIGABRT core dumps at 09:43 happened before this session.

Rotation: the accelerometer is on the SLPI (libssc), not IIO. Denial's
`orientation_sensor.rs` waits for iio-sensor-proxy on the system bus, and that
was not installed. After installing `iio-sensor-proxy` 3.9 (built with libssc)
and adding a udev rule that tags `fastrpc-sdsp` with `ssc-accel`,
`monitor-sensor --accel` reports an accelerometer ("Tilt changed: face-up").
Auto-rotate itself was **not tested**: it needs someone to physically rotate
the phone, and Denial's rotation lock defaults to on. During the first
`monitor-sensor` run the kernel logged 34 SLPI `Handover signaled, but it
already happened` warnings. These still need to be checked, and so does idle
power with the proxy running.

Audio: both speakers are reached through ALSA `default` → hw:0,0, mono S24_LE
48 kHz, played at mpv volume 35-40. Nobody listened this time, but the stream
ran and `hw_ptr` advanced on a fresh open. The retrigger hang is reproducible
with audio-only mpv and one IPC `seek 5`: `hw_ptr` stays 0 afterwards, and a
fresh open works again. No sound server is installed. Firefox usually needs
PulseAudio/PipeWire.

## On-screen keyboard: what happens and why

The deployed policy is 0006: the keyboard opens on a text-input-v3 `enable`
(focus gain) or `show_input_panel`. Any touch outside the keyboard dismisses
it. The editor can reclaim it by committing within 350 ms of touch-up.
Measured behaviour:

* **Auto-open on field tap works in every app with text-input-v3.** That
  covers GTK3 (Firefox, Thunar), GTK4 (Calculator, Text Editor, Weather),
  Chromium with `--enable-wayland-ime --wayland-text-input-version=3`, and
  foot. Taps held 0.08, 0.2 and 0.35 s all opened it. Chromium enables within
  ~110-230 ms of touch-down and Firefox within ~120-220 ms.
* **Close on outside tap works in all of them.** The client sends `disable`,
  or the touch dismisses the keyboard.
* **Gap 1: re-tapping an already-focused field.** Chromium focuses the
  omnibox at startup. The keyboard is not shown then (no enable after
  mapping), and tapping the omnibox sends no new commit, so it never opens
  until the user taps elsewhere and back. GTK4 re-commits on every tap and
  doesn't have this problem.
* **Gap 2: wrong tap position in CSD windows.** For Firefox and Thunar (GTK3
  CSD, geometry origin 26,23), GTK4 apps (25,25) and Chromium (16,10), the tap
  reaches the app shifted up and left by that origin. On top toolbars this
  hits the row above: the URL-bar tap selected the tab strip or "+", and in
  Thunar it opened the Bookmarks menu. The trace showed `wl_touch.down` at
  `surface = screen - (0,48)`, while painting drops the geometry origin.
  Source: `dart_shell/lib/src/state/shell_input_layout_coordinator.dart`
  `_inputRegionsForWindow` builds `sourceRect` from `(0, rect.top - contentTop)`
  without `window.contentCoordinateRect`'s origin. Desktop mode uses it. Local
  patch **0019-map-mobile-input-to-content-origin** fixes exactly this but has
  never been built into `/opt/denial`.
* **Gap 3: the focused field is hidden while typing.** The keyboard pans the
  whole app up by the keyboard height. Fields near the top (URL bars, form
  tops, the text editor's first lines, the terminal prompt) end up off-screen.
  Bottom fields do become visible above the keyboard. Firefox publishes a
  useless caret `(26,23,0,0)`. GTK4 and Chromium publish real ones. Local
  patches **0014-0017** (caret geometry and a caret-aware pan) address this
  and are also unbuilt. A resize-on-keyboard mode (configure the app to
  `height - keyboard`) would help apps that don't publish a caret.
* The Calculator and Text Editor open the keyboard at launch (autofocus). For
  Calculator this hides its own keypad.

## Other shell/compositor findings

* **The bottom gesture band swallows taps.** Taps below about y=915 of 979
  logical never reach the app, while the app window is configured 931 px tall
  from y=48. This affects Calculator's bottom row, Loupe's nav buttons,
  Weather's view switcher and dialog buttons (Chromium ToS). Either shrink
  the app configure height by the band, or pass taps through and keep only
  swipes (`ShellMetrics.gestureRect`/`edgePanelGestureRect`).
* **Windows larger than 432 px, or smaller than configured, are cropped or
  stretched rather than fitted.** Firefox (500), Chromium (500/600),
  System Monitor (620) and the GTK file chooser are cropped. mpv at 432x243 and
  Chromium at 500x267 were stretched ("cover"). The fix is a Phosh-style
  scale-to-fit, i.e. contain and shrink.
* **No session D-Bus.** Apps get `LANG=C` and no `DBUS_SESSION_BUS_ADDRESS`.
  Results: Weather can't launch, dconf settings aren't saved, Firefox remote
  open/xdg-open don't work, and there are no portals. The per-app environment
  support (`applicationEnvironment` in `/root/.config/denial/settings.json`)
  handles the variables, and it is re-read on every launch.
* **Everything runs as root.** Nautilus refuses outright, Chromium needs
  `--no-sandbox` (the sandbox is lost), and Thunar shows a warning.
* The home grid doesn't watch a new `/usr/local/share/applications`
  directory: overrides appeared only after a rescan was triggered. Hidden apps
  leave holes in the grid. Dependency packages add non-app launchers (Avahi,
  qv4l2, lstopo, Thunar settings).
* A failed launch (nautilus) shows the icon splash for about 10 s, with no
  error message.

## Improvements, ranked by impact

1. **Build and deploy the Denial patches 0019 and 0013-0017** (Denial
   compositor + shell). 0019 fixes the tap offset that breaks all top toolbars
   and URL bars in CSD apps. 0014-0017 keep the focused caret visible above
   the keyboard.
2. **Keyboard reopen on tap of an already-focused field** (Denial
   `wayland_frontend/text_input.rs`): after a client tap, if that client's
   text-input is still enabled when the reclaim window ends, publish
   `input_panel_visible=true`. Also consider a resize-on-keyboard mode for
   clients without a caret rectangle.
3. **Gesture band and window fit** (Denial shell/compositor): let taps
   through the bottom band, or configure apps above it. Scale oversized
   windows down to fit, and letterbox undersized ones instead of stretching.
4. **Kernel q6asm-dai restart:** after `TRIGGER_STOP` → `START` (seek, loop,
   pause), `q6asm` queuing fails with -EBUSY and `hw_ptr` stalls. Every player
   and browser freezes on seek. Until it is fixed, a sound server that keeps
   the PCM open (PipeWire) would work around it for apps.
5. **Session plumbing** (packaging/service): a proper root (or, better,
   user) session bus started before Denial, with the activation environment
   set, and `LANG=C.UTF-8`. Longer term, run the session as a normal user
   (nautilus, the Chromium sandbox). Proposed unit, **not installed** (the
   persistent service was refused):

   ```ini
   [Unit]
   Description=Root session D-Bus for apps launched by Denial
   After=dbus.service
   Before=rog5-denial.service
   [Service]
   ExecStartPre=/usr/bin/install -d -m 0700 /run/user/0
   ExecStart=/usr/bin/dbus-daemon --session --nofork --nopidfile --address=unix:path=/run/user/0/bus
   ExecStartPost=/bin/sh -c 'for i in $(seq 1 25); do [ -S /run/user/0/bus ] && break; sleep 0.2; done; DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/0/bus exec /usr/bin/dbus-update-activation-environment WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/0 XDG_CURRENT_DESKTOP=Denial XDG_SESSION_TYPE=wayland DESKTOP_SESSION=Denial LANG=C.UTF-8 DISPLAY=:0 HOME=/root'
   Restart=on-failure
   [Install]
   WantedBy=multi-user.target
   ```

Smaller items: hardware video decode (Venus V4L2 in the kernel), a `foot.ini`
font size, launching apps with cwd=$HOME, a launch-failure toast, and an
auto-rotate physical test with the rotation lock off.

## Changes made on the phone (all reversible)

| Change | Revert |
|---|---|
| Installed firefox chromium nautilus gnome-text-editor loupe gnome-calculator gnome-weather gnome-system-monitor mpv, then thunar, then iio-sensor-proxy (with libssc, libqmi, libqrtr-glib, libmbim, protobuf, protobuf-c, abseil-cpp). 255 packages in total, list in `/root/apptest/installed-2026-09-26.txt`. It created the users/groups avahi and geoclue | `pacman -Rns` the top-level packages |
| Deleted the cached package files of those 255 packages from `/var/cache/pacman/pkg` (older cache entries kept) | — |
| `/root/.config/denial/settings.json`: `applicationEnvironment.default` = `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/0/bus`, `LANG=C.UTF-8` (backup `/root/apptest/denial-settings.json.orig`) | Restore the backup |
| Transient unit `rog5-apptest-session-bus.service` (`systemd-run`, dbus-daemon on `/run/user/0/bus`), with its activation environment set via `dbus-update-activation-environment`. It is gone after a reboot, and the settings entry then points at no bus (the same as before) | `systemctl stop rog5-apptest-session-bus` |
| `/root/.config/chromium-flags.conf`: `--no-sandbox --ozone-platform=wayland --enable-wayland-ime --wayland-text-input-version=3` | Delete the file |
| Firefox profile `taf05vhk.default-release`: `user.js` (`toolkit.legacyUserProfileCustomizations.stylesheets`) and `chrome/userChrome.css` (min-width override, hide the VPN/account buttons). `xulstore.json` restored from `/root/apptest/xulstore.json.orig` | Delete both files |
| `/root/.config/mpv/mpv.conf`: `keepaspect-window=no`, `volume=40` | Delete the file |
| `/usr/local/share/applications/*.desktop` NoDisplay overrides: avahi-discover, bssh, bvnc, qv4l2, qvidcap, lstopo, thunar-bulk-rename, thunar-settings, org.gnome.Nautilus | Delete the directory's files |
| `/etc/udev/rules.d/81-rog5-ssc-accel.rules` (fastrpc-sdsp gets `ssc-accel ssc-proximity`); iio-sensor-proxy started (udev/systemd-activated) | Delete the rule, `udevadm control --reload`, `pacman -R iio-sensor-proxy` |
| Test media: `/root/Pictures/{test-1080p.png,mandel-portrait.jpg}`, `/root/Videos/test-1080p-h264.mp4` (39 MB). Test helpers and logs in `/root/apptest/` | `rm -r` |

No reboot, no kernel, boot, network, credential or `/opt/denial` changes.
Denial was not restarted.
