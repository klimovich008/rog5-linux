# GNOME Mobile retest with mutter-mobile 50.5-1.1; user keeps Phosh + desktop GNOME

Date: 2026-10-01 21:05-21:20, bundle `main-k113-d13-261001a`.

- Reinstalled with mutter-mobile 50.5-1.1 (0005, no dma-buf stride
  override; the string is gone from libmutter-18.so.0.0.0); `pacman -Qkk`
  clean; switch: `gnome-mobile ready after 15 s`.
- Docked with the HDMI/USB hub on the side port: DP came up at once
  (pin assignment 3, 4 lanes), but the hub's USB side did not enumerate:
  `rog5-usb-reconnect`: "UCSI switched back to host during the settle",
  "nothing enumerated after re-initialisation; retry 1/3 in 35s"; the retry
  at 21:13:49 re-initialised a600000.usb (DP stayed up) and the keyboard,
  mouse and controller enumerated at 21:14:00, ~70 s after the plug. Not
  specific to GNOME Mobile; the retry timing wants shortening.
- User verdict: "GNOME desktop + Phosh is better". Back at 21:19:20
  (`rog5-shell switch phosh`, Phosh locked), stock mutter/gnome-shell
  restored at 21:19:42 (`rollback`, gdm removed 21:19:53); the user
  unlocked Phosh and started desktop mode at 21:19:55, gnome-shell at
  21:20:02 on the stock packages.

State: Phosh is the phone shell again (`/etc/rog5/shell` phosh), desktop
mode on stock GNOME. The rog5-shell selector/watchdog stay installed (no
effect in phosh mode); the GNOME Mobile packages remain cached in
`/var/cache/rog5-gnome-mobile/pkgs` for a later look.
