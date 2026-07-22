# Power, display, and UI policy

## UI choice

Use KDE components already installed:

- Plasma Mobile for the physical phone panel.
- Plasma Desktop as an optional remote/large-display session.
- NetworkManager/Plasma-NM for Wi-Fi and hotspot controls.
- Discover with the APK backend for graphical package browsing.
- KScreen for fixed refresh-rate selection once active-mode reporting is reliable.

GNOME is possible but adds a second compositor, control center, settings daemon, and application stack without solving any kernel issue. It should be tested only after KDE is hardware accelerated. Installing both as defaults would increase disk/RAM use and make power/debug results harder to interpret.

## Refresh-rate profiles

- `server`: physical screen off; retain the last mode but prefer 60 Hz before blanking.
- `battery`: fixed 60 Hz.
- `balanced`: fixed 90 Hz.
- `performance`: fixed 120 Hz.
- `maximum`: fixed 144 Hz, opt-in and never the boot default.

There is no true VRR capability in the current panel metadata. A selector must show fixed modes, not an adaptive-refresh toggle.

`scripts/device/display-profile.sh` maps those vendor mode names to KScreen's otherwise misleading mode IDs. KScreen calculates approximately 50-54 Hz from the vendor command-mode timing fields, so its displayed refresh number must not be used as the panel's physical refresh label.

## Screen-off behavior

Backlight zero is not enough for a command-mode OLED if display commits continue. The eventual implementation should combine:

1. compositor output DPMS/off when supported,
2. panel low-power/off state,
3. backlight zero as a fallback,
4. power-button wake without suspending the server,
5. a separate explicit system-suspend action.

The repository screen toggle combines Wayland DPMS with backlight zero and keeps all server services alive. Backlight control remains the fallback if DPMS is unavailable. Power measurements must compare panel-on, backlight-zero, DPMS-off, and compositor-stopped states.

## Memory policy

Do not optimize an 11 GiB device by killing useful caches. Prefer:

- one physical compositor, not simultaneous Mobile and Desktop sessions;
- remote admin via a lightweight path independent of the physical UI;
- start Chromium only on demand;
- disable unused indexers and desktop services after measuring them;
- keep zram but lower it if real swap use stays zero;
- cap log retention and stop duplicate supervisors;
- measure proportional set size and idle CPU before removing packages.

The target is a stable idle below roughly 1.2-1.5 GiB with the chosen physical shell, not an arbitrary minimum.

## Battery policy

- `schedutil` remains the initial CPU governor.
- 60 Hz and screen off are the server defaults.
- Radio startup remains delayed at low battery.
- High refresh, sustained AI inference, hotspot, and charging should be thermally budgeted together.
- Charging limits should use a real supported driver interface; never write guessed values to undocumented ASUS nodes.
- Record battery voltage/current/temperature and wall-power measurements for each profile.
