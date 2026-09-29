# ROG5 priorities

Goal (the user's words, 2026-09-29): a fully usable Linux phone that also works
as a Linux server, takes USB hubs, is reliable, gives maximum performance when
needed and is power efficient in standby. Phosh is the phone shell and GNOME
the desktop mode on an external monitor. Cellular (calls, SMS, mobile data)
is out of scope. The Denial shell was dropped on 2026-09-29.

Status is tracked per component in
[`docs/status/components.json`](docs/status/components.json) and shown in
[current state](docs/current-state.md); the user-facing list and the tests
that need the user's hands are in [what's left](docs/whats-left.md).

## Order of work

1. **Reliability and daily use.** Phosh must survive monitor hotplug and the
   phone/desktop switch without closing apps; unattended updates must not
   reboot the phone while it serves something; "restart to fastboot" should
   work; the boot splash should go straight from the bootloader logo to the
   lock screen.
2. **Standby efficiency.** Reach deep standby (CX/DDR collapse): the DDR floor
   is held by a non-APPS RPMh master (~79 mA in standby today). Keep the
   sleep policy's wakeups low.
3. **Performance when needed.** A Phosh toggle for `rog5-perf-mode`; GPU
   system cache (patch 0107) and display NoC QoS (0106) candidates;
   DisplayPort without the core-clock pin, then HBR2 for higher modes.
4. **USB and server use.** The bottom port's 5 V should follow the attached
   device instead of `rog5-usb-bottom on`; Wi-Fi should keep one MAC/IP and
   reconnect faster after wake; journal retention should cover more than a
   day.
5. **Remaining hardware.** Brightness range (the panel's Iris6 path), earpiece,
   3.5 mm jack, Bluetooth headset microphone, high refresh rate, then cameras,
   fingerprint, NFC and AirTriggers as far as feasible.

## How to work

- Each hardware question gets one RAM trial of a signed bundle
  (`production-ram-trial.py`), then `install-default-kernel.py` makes a good
  image the default; see [development](docs/development.md).
- Driver iteration uses `rog5-dev module` against the running kernel.
- Kernel patches live in `patches/linux-7.2.7`; `rebase-kernel-series.py`
  moves the series to a new stable base.
- Record each run in a dated `test-results/` report, the component status in
  `components.json`, and reusable lessons in `docs/development-lessons.md`.

The earlier roadmaps (headless server acceptance, network root, Denial) are
kept in [docs/history/](docs/history/).
