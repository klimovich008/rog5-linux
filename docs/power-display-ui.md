# Power, display, and UI policy

## UI choice

The Arch target stages one KDE stack:

- Plasma Desktop Wayland for the physical panel and KRDP session.
- greetd for the on-demand `graphical.target` login path.
- NetworkManager/Plasma-NM for Wi-Fi and hotspot controls.
- KScreen for fixed refresh-rate selection once active-mode reporting is reliable.
- KRDP for remote access to the active Plasma session.

GNOME, Plasma Mobile, Discover/PackageKit, and a second display manager are not part of the target. They add background services or duplicate the selected compositor without helping kernel bring-up. Add one later only for a measured requirement that the minimal Plasma Desktop cannot meet.

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

The vendor-kernel baseline screen toggle combines Wayland DPMS with backlight zero and keeps all server services alive. The Arch image stages the same explicit interface:

```sh
rog5-screen-toggle.sh off
rog5-screen-toggle.sh on
rog5-screen-toggle.sh toggle
```

It discovers the writable backlight, validates its range, preserves brightness, and changes its state record only after a successful sysfs write. `rog5-server-inhibit.service` uses systemd's native inhibitor API to block system sleep and short power-key shutdown without blocking idle display blanking; stopping that service restores explicit suspend policy. Headless logind ignores a short power press, while a long press retains the emergency power-off action. Plasma/PowerDevil power-button screen toggling still requires a live input test after the mainline input port.

Linux 7.1 network-root v5 now registers the PMK8350 power-key path after the
reviewed `qcom_pon` parent module is loaded. The resulting input is named
`pmic_pwrkey`, uses the `pm8941-pwrkey` driver, advertises `KEY_POWER`, and has
wakeup enabled. A real short press was not observed during the bounded
attended windows, including a protected 120-second normal-mode repeat, so the
physical switch/IRQ path is still pending. The reusable
`monitor-network-root-pwrkey.sh` gate holds a low-level logind inhibitor and
requires both the Linux `KEY_POWER` press and release records. This tier cannot
yet provide a visible power-button indication because DRM, panel, backlight,
and LEDs remain intentionally disabled. Backlight control remains the fallback
if DPMS is unavailable once display bring-up begins. Power measurements must
compare panel-on, backlight-zero, DPMS-off, and compositor-stopped states.

## Memory policy

Do not optimize an 11 GiB device by killing useful caches. Prefer:

- boot to headless `multi-user.target` and start the single Plasma compositor only when needed;
- remote admin via a lightweight path independent of the physical UI;
- keep ttyd loopback-only and start headless Chromium only on demand;
- disable unused indexers and desktop services after measuring them;
- keep zram but lower it if real swap use stays zero;
- cap log retention and stop duplicate supervisors;
- measure proportional set size and idle CPU before removing packages.

The first diagnostic Arch headless sample reported 11,296,876 KiB total,
10,947,312 KiB available, about 341 MiB unavailable, 12 running services, and
0.06 one-minute load. Network-root v2 then passed normal coldplug twice with
about 10.4 GiB available and 33 sane thermal zones. Repeat idle CPU, service,
temperature, and wall-power measurements over a longer interval before
trimming services.

## Battery policy

- `schedutil` remains the initial CPU governor.
- 60 Hz and screen off are the server defaults.
- Radio startup remains delayed at low battery.
- High refresh, sustained AI inference, hotspot, and charging should be thermally budgeted together.
- Charging limits should use a real supported driver interface; never write guessed values to undocumented ASUS nodes.
- Record battery voltage/current/temperature and wall-power measurements for each profile.

These are target policies. Linux 7.1 now runs Arch/systemd and persistent
key-only SSH over USB network root with normal headless coldplug. Display,
session, battery, charging, and power behavior remain untested because their
DT nodes and board wiring have not passed separate promotion gates.
