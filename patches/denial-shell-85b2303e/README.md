# Denial mobile-shell patches (applied to the shipped tree)

The phone's `/opt/denial` bundle was built from unpatched upstream
denialwm/denial 85b2303e, plus the engine MSAA patch
(`patches/denial-engine`). The `patches/denial-85b2303e` series
(0001-0019) has never been built into it. The patches here apply directly to
that shipped tree, `~/.local/state/rog5-denial-20260910-r1/engine-build-r1/denial`,
and change only the Dart shell (`libapp.so`).

- `0001-quick-settings-panel-fits-its-contents.patch`: the quick-settings
  panel was a fixed 488 logical px with its contents in a scrolling
  `ListView`, so the footer was hidden behind an inner scroll. It is now as
  tall as its contents (at most 92 % of the screen, scrolling only beyond
  that). It slides in by its own height (`FractionalTranslation`). The bench
  handle position moved to y=1350 (`scripts/device/bench/run.py`).
- `0002-unlock-without-credential.patch`: "Screen lock: None" for an account
  without a password. The lock stays native: `deniald` locks, and only PAM
  (`login` service) unlocks. On Arch, `pam_unix nullok` accepts an empty
  password with no prompt, which is why the swipe alone unlocked. The new
  `SessionCredentialProbe` reads the real UID from `/proc/self/status`, then
  the `/etc/passwd` and `/etc/shadow` entries for it. It reports "no
  credential" only when the password field is empty. Unreadable files, an
  unknown user, `!`/`*` or a hash all count as a credential, so the lock
  screen stays as it was. It re-reads on every lock and when `/etc` changes
  (inotify). With no credential, the shell does three things:
  - `ShellController` starts the PAM conversation itself, at most once per
    lock. It never answers a prompt.
  - The double-tap screen-off only blanks the display.
  - The idle-lock timer is not sent to the compositor.
- `0003-keyboard-follows-editor-focus.patch`: the on-screen keyboard now opens
  whenever a text editor gains focus. This covers shell Flutter fields and
  Wayland `text-input-v3` clients. Before, the editor had to commit within the
  compositor's 250 ms touch-authorization window, measured from touch-down.
  The keyboard still closes when focus leaves (`active` false). An identical
  text-input state from the compositor means a new client touch, and it also
  closes the keyboard. An update that only changes the hint or purpose is
  ignored. A tap on the shell outside the keyboard sheet and its scroll strip
  (down and up within `kTouchSlop`) closes it. The tap region is a
  `TextFieldTapRegion`, so taps on shell text fields keep it open. Touches on
  client surfaces still dismiss on touch-down, through the compositor.
- `0004-wifi-settings-details-saved-hidden-advanced.patch` (applies after
  0001-0003): NetworkManager-backed Wi-Fi settings pages. They are reached
  from the quick-settings Wi-Fi surface (the (i) button on a saved or
  connected network, and the "Saved networks" and "Add network" buttons), and
  from Settings, Network ("Details", "Manage networks").
  - Details: signal, link speed, band and channel, security, IPv4
    address/prefix, gateway, DNS, IPv6, BSSID and device MAC, plus the
    profile's auto-connect toggle, forget, and connect or disconnect.
  - Saved networks: `Settings.ListConnections` and `GetSettings`, with an
    auto-connect switch and forget (`Delete`) on each row.
  - Add network: a hidden SSID with None, WPA/WPA2-Personal or
    WPA3-Personal security, created with `AddAndActivateConnection2` and
    `802-11-wireless.hidden`.
  - Advanced: IPv4 DHCP or static (address, prefix, gateway, DNS), a DNS
    override on DHCP (`ignore-auto-dns`), proxy none or auto (PAC URL), and
    metered.
  Saving re-reads the stored settings, changes only these fields, and writes
  them with `Settings.Connection.Update2` (to disk, no secrets; NM keeps the
  stored PSK). If the profile is active and the IP, proxy or metered settings
  changed, it then calls `Device.Reapply`. If that is refused, it calls
  `ActivateConnection` instead. The Wi-Fi surface pads itself above the
  on-screen keyboard. With iwd (no `WifiProfileBackend`), the snapshot's
  `profileManagement` is false and none of this is shown. Strings are in
  `app_en.arb`/`app_zh.arb` and the regenerated `l10n/generated`. The profile
  encoding is covered by `test/services/network_manager_profile_test.dart`.
  `flutter test` does not run in the builder, because it has no host
  `flutter_tester`. The same assertions passed in a pure-Dart harness.

The patches are unified diffs against upstream 85b2303e. Apply them in order
with `patch -p1` from the source root. Together, 0001-0003 reproduce the
shipped tree's `dart_shell/lib` exactly.

## Deployed state (2026-09-26)

`/opt/denial/lib/libapp.so` is upstream + **0001 + 0004** (sha256 c6f72921...,
built as `assembly-r3`). 0004 applies without 0002/0003.

- 0002 is withdrawn. The user chose a password lock over "no lock without a
  credential", so the stock PAM `login` unlock applies once root has a
  password.
- 0003 depends on 0002, and the user found it unreliable. The keyboard work
  will be redone on top of 0001 + 0004.
- 0005 (power key toggles the display; compositor) is written but not built.
  `deniald` is still the clean upstream build.

## Rebuild and deploy libapp.so (about 1 minute)

    EB=~/.local/state/rog5-denial-20260910-r1/engine-build-r1
    cp scripts/host/denial/assemble-shell.sh $EB/assemble-r2.sh
    podman run --rm --read-only --read-only-tmpfs=false --memory=8g --memory-swap=8g \
      --cpus=4 --pids-limit=1024 --network=none -v $EB:/build:rw -v $EB/tmp:/tmp:rw \
      -e HOME=/build/home -e TMPDIR=/build/tmp -e TAR_OPTIONS=--no-same-owner \
      localhost/rog5-denial-engine-builder:r1 sh /build/assemble-r2.sh

Output: `$EB/assembly-r2/lib/libapp.so`. The script uses `pub get --offline`,
because the builder has no network and the pub cache is already filled.
Deploy it over SSH to `/opt/denial/lib/libapp.so` (the shipped copy is kept as
`libapp.so.r1`), then run `systemctl restart rog5-denial.service`.
