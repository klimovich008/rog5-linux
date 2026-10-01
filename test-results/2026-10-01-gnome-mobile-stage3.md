# GNOME Shell Mobile: stage 3 (first live session) and Phosh retired

Date: 2026-10-01 19:53-20:05, bundle `main-k113-d13-261001a`, user present.

- Revert armed (`rog5-gm-revert`, 15 min), then
  `rog5-shell switch gnome-mobile --pin-is-6-digits` at 19:53:55: watchdog
  armed, GDM started, `gnome-mobile ready after 13 s`. The user logged in on
  the greeter with the PIN; session `XDG_SESSION_DESKTOP=gnome-mobile`,
  `LockedHint=no` after unlock.
- User check: "It works" (scale, touch, rotation, OSK, power key lock and
  PIN unlock).
- Bug found and fixed (23a4f220): GDM 50 leaves logind's `Desktop` empty,
  so `rog5-shell gsd-power-allowed` let gsd-power start in the mobile
  session. The guard now also reads the user manager's
  `XDG_SESSION_DESKTOP`, only on a gnome-mobile boot. gsd-power was ended
  with SIGTERM in the running session (the unit refuses a manual stop).
- `pam_gnome_keyring.so` is missing (gnome-keyring not installed): GDM logs
  a PAM warning per login; harmless.
- `rog5-shell greeter-monitors`: no panel-only configuration yet (the scale
  was not changed in Settings), so GDM keeps its default.
- Kept: `/run/rog5-keep-gnome-mobile`, revert timer stopped.
  `/etc/rog5/shell` = gnome-mobile (next boot too).
- PIN changed for `phone` with `chpasswd` from stdin (shadow 0:0:600:1
  unchanged, faillock reset).

Phosh retired at the user's choice ("retire, keep as backup"): it no longer
starts (the selector skips rog5-phosh and rog5-desktop-mode), but phosh,
phoc and phosh-mobile-settings stay installed as the watchdog's fallback.
The "Phone mode" launcher is hidden for `phone`
(`~/.local/share/applications/rog5-phone-mode.desktop`, NoDisplay).
Uninstall after stages 4 (battery standby), 5 (docking) and 6 (boot path).

Not yet tested: boot into GNOME Mobile (GDM PIN at boot), stage 3a lock
behaviour, standby on battery, docking on the monitor, the reauth retry loop
with GDM down (stage 1 finding).
