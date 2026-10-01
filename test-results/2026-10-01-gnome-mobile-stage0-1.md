# GNOME Shell Mobile: stages 0 and 1 on the phone

Date: 2026-10-01 19:10-19:45, bundle `main-k113-d13-261001a`, merge a47409b7
(`agent/gnome-mobile-261001` into the production branch). Plan:
`packages/gnome-mobile/README.md` section 6. The user's Phosh session stayed
up and locked throughout.

## Stage 0: install, rollback rehearsal, install - PASS

- `rog5-install-userspace` from a `git archive` of a47409b7: selector,
  watchdog, fallback units and the ExecCondition drop-ins installed;
  `rog5-shell status`: next boot and this boot `phosh`; `--check` clean
  apart from the three known local edits.
- Host-built packages (SHA256SUMS checked) in
  `/var/cache/rog5-gnome-mobile/pkgs/{mutter-mobile,gnome-shell-mobile}`
  (`ROG5_GM_PKGDIR`), so stage 3 can reuse them.
- First attempt: nothing changed, because the hourly `rog5-update` held the
  pacman lock (it installed 12 routine upgrades at 19:12-19:16 and waits for
  a reboot to commit; mutter/gnome-shell untouched). The installer refused
  to go on without a complete rollback set, as designed.
- Second run: install (rollback set: stock mutter 50.5-1, gnome-shell
  1:50.5-1 downloaded, the repository still has those versions) → check →
  `pacman -Qkk` 0 altered files (gdm's `/etc/gdm/custom.conf` differs from
  the package: the installer's file) → `systemctl is-enabled gdm` disabled →
  rollback (stock back, gdm removed) → install again (same checks).
- Phosh: `rog5-phosh` active, phosh and phoc running, `LockedHint=yes`.

Installed now: mutter-mobile 50.5-1, gnome-shell-mobile 50.5-1, gdm 50.3-1
(disabled). Desktop mode (GNOME on the monitor) now runs on these packages
as well; it has not been tried on them yet.

## Stage 1: headless shell on the phone - PASS (with one finding)

`gnome-shell --headless --virtual-monitor 405x918` as `phone` with a private
bus, runtime dir and home; renderer: gbm on `/dev/dri/renderD128` (GPU).

- `Main.layoutManager.isPhone` → `(true, 'true')`.
- Screenshots (`2026-10-01-gnome-mobile-stage1/`): mobile home grid, quick
  settings (Wi-Fi, Dark Style, brightness), lock screen with the 6-digit PIN
  pad and no Emergency button. The OSK does not show headless (no touch
  device), as on the host.
- JS errors: 0.
- Idle CPU, unlocked, after 150 s settle: 2.46 s over 300 s (0.82 %), 0
  frames painted, no log output. Pass (< 1 %).

Finding: locked without GDM the unlock dialog retries reauthentication in a
loop (`_reportInitError` → `_verificationFailed` → `_cancelAndReset` →
`begin`, ~1200 times in 10 min); gnome-shell then uses 4.3 % CPU on the
lock clock and 5.7 % with the PIN pad up (102 frames in 30 s, the error
label). Headless this is a test artefact (no GDM), but it is what a locked
phone would do if GDM died: stage 3a's "GDM frozen" case must measure it,
and the retry wants a back-off before GNOME Mobile can be the default.

## Next

Stage 3 needs the user (6-digit PIN, phone in hand): see README section 6.
Rollback at any time: `ROG5_GM_PKGDIR=/var/cache/rog5-gnome-mobile/pkgs
sh /run/rog5-repo/packages/gnome-mobile/rog5-gnome-mobile-install rollback`
(or from any checkout).
