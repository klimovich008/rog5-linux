# KDE Plasma Mobile 6.7.5 trial (rejected), 2026-10-01 21:29-21:50

Bundle `main-k113-d13-261001a`, user present.

- Installed 161 packages from Arch ARM extra (plasma-mobile, plasma-desktop,
  plasma-nm, plasma-pa, kscreen, powerdevil, bluedevil, plasma-settings,
  qmlkonsole; 249 MiB; plasma-keyboard is the OSK, maliit-keyboard is not
  in the repository). PAM service `kde` is in /usr/lib/pam.d.
- Trial unit `rog5-plasma.service` (User=phone, tty7, startplasmamobile,
  Conflicts with rog5-phosh/rog5-gnome); rog5-desktop-mode had to be stopped
  (it starts Phosh when neither Phosh nor GNOME runs). Revert timer 15 min.
- KWin and plasmashell came up on the panel; `kscreenlockerrc
  LockOnStart=true` was not honoured (LockedHint=no until a
  `loginctl lock-session`); the mobile keypad lock screen then worked.
- Docked: KWin keeps a layout per output set (`kwinoutputconfig.json`);
  `kscreen-doctor output.DP-1.priority.1 output.DSI-1.disable` turned the
  panel off while docked (DSI disabled, DPMS Off, bl_power 4).
- User verdict: "KDE works like shit" → rollback to Phosh + GNOME.

Rollback lessons:
- Plasma runs KWin/plasmashell as systemd **user** units
  (plasma-kwin_wayland.service etc.): stopping the system unit left KWin
  holding wayland-0, phoc then failed ("unable to lock lockfile
  wayland-0.lock") and dumped core. Fixed by stopping the plasma-* user
  units, then restarting rog5-phosh (came up locked).
- Removed exactly the 161 packages of the 21:29 transaction (`pacman -Rn`,
  dry run clean), the trial unit, and KDE's files in ~phone (configs kept in
  `~/.local/share/rog5-kde-trial-config-20261001.tar.gz`, 297 MB Baloo index
  deleted).
- Plasma had rewritten `org.gnome.desktop.wm.preferences button-layout`
  (back to "appmenu:") and created `~/.config/gtkrc-2.0` with
  `gtk-alternative-button-order = 1` (removed; it affects GTK2 apps such as
  Steam). gtk-theme, icons, fonts and color-scheme were unchanged.
