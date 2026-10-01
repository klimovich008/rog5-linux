# GNOME Shell Mobile for the ROG Phone 5 (opt-in session)

Status (2026-10-01): prepared on the host, **not yet run on the phone**.
Phosh stays the default shell. GNOME Shell Mobile is an opt-in session next
to it, with Phosh as the automatic fallback. Background and the "not yet"
recommendation the user overrode:
[investigation](../../docs/reviews/2026-10-01-gnome-mobile-investigation.md),
[Sol review](../../docs/reviews/2026-10-01-gpt-6.1-sol-gnome-mobile.md).
Review of this implementation:
[2026-10-01-gpt-6.1-sol-gnome-mobile-impl.md](../../docs/reviews/2026-10-01-gpt-6.1-sol-gnome-mobile-impl.md).

What is here:

| Path | What |
|---|---|
| `mutter-mobile/` | PKGBUILD + 4 patches: mutter-mobile 50 branch + GNOME 50.5 + fixes |
| `gnome-shell-mobile/` | PKGBUILD + 11 patches: gnome-shell-mobile 50 branch + GNOME 50.5 + fixes |
| `rog5-gnome-mobile-install` | install (with a rollback set) / rollback / check, as root on the phone |
| `../../scripts/device/rog5-shell` | shell selector, GDM watchdog, fallback to a locked Phosh |
| `../../configs/systemd/rog5-shell-*.service`, `*.service.d/50-rog5-*.conf` | boot selector, watchdog, unit gates |
| `../../configs/gnome-mobile/` | session file, GDM config, greeter dconf, user units |
| `../../scripts/device/test-rog5-shell.py` | offline tests (fake system) |

## 1. Base: GNOME 50.5 with the mobile 50 branches merged in

The phone runs Arch Linux ARM `mutter 50.5-1` and `gnome-shell 1:50.5-1`
(the repository still had 50.5-1 on 2026-10-01). GNOME Shell Mobile has no
release for 50; its `mobile-shell-devel-50` branches are based on 50.3.

**Chosen: merge GNOME 50.5 into the mobile 50 branches, port the 50.4/50.5
fixes, and build both as a pair** (`mutter = 50.mobile.0`, which the shell
requires). Rejected:

- *The mobile 50.3 branches as they are:* they lack the 50.4/50.5 lock-screen
  and notification fixes (below) and would downgrade mutter/gnome-shell.
- *The 51 `mobile` heads (51.beta):* the phone has GNOME 50; a 51 shell needs
  mutter 51 and the rest of GNOME 51, which Arch ARM does not ship yet.
- *48.mobile.0 (postmarketOS):* two releases old, and not buildable against
  GNOME 50 without the same porting work.

| Package | Fork commit | Merge | Result |
|---|---|---|---|
| mutter-mobile | `fe00ce86` (camelCaseNick/mobile-shell-devel-50, 2026-09-27) | 50.5 merges cleanly | + 0002 auto-rotate fix for phones without a tablet-mode switch (upstream 51 `25e48d8b3`, cherry-picked clean) + 0003 version `50.mobile.0` (the branches never bumped it; the shell requires `= 50.mobile.0`) + 0004 a stray `<<<<<<< HEAD` in a test file |
| gnome-shell-mobile | `d95fe2ac` (mobile-shell-devel-50, 2026-07-23) | 5 conflicts, resolved | + 0002-0011 below |

**Why camelCaseNick's mutter branch:** the official `mobile-shell-devel-50`
head (`c99af8f4`, 2026-07-26) does not compile. The host build stopped in
`clutter-actor.c` (a lone `<<<<<<< HEAD` line from 790bb4f9b) and then in
`clutter-gesture.c` (the gesture commits are half ported to GNOME 50's
`ClutterSprite`: an undeclared `set_state_after()`, calls with the old
device/sequence arguments). `camelCaseNick/mobile-shell-devel-50`
(`fe00ce86`) is the same series rebased with exactly those fixes, plus OSK
events during Wayland popups and a window "mapped" state (19 files,
+130/-41 against `c99af8f4`; it also carries the fork's inert Aliendalvik
hacks). The shell has a single 50 branch.

The patch series reproduces the merged trees exactly (checked: tree hashes
equal). The merge branches are kept as git bundles in
`~/.local/state/rog5-gnome-mobile-src/*-rog5-mobile-50.5.bundle` (private).

Conflict resolutions (gnome-shell):

- `js/gdm/authPrompt.js`: upstream's `connectObject` handler signatures
  (0a5b2bbc4) with the fork's "password authentication didn't work" message
  filter.
- `js/ui/messageList.js`: both sides kept (fork's swipe gestures, upstream's
  `_limitString()`).
- `js/ui/unlockDialog.js`: the fork deleted `NotificationsBox`; its
  lock-screen notifications use `Calendar.CalendarMessageList` instead (see
  the markup rows below). Upstream's keyboard focus navigation (470c6910c) is
  ported as a separate `vfunc_key_press_event`.
- `js/ui/workspaceAnimation.js`: deleted by the fork (workspace switching
  goes through its overview gesture); stays deleted.
- `meson.build`: version stays `50.mobile.0`.

### Upstream fixes since 50.3 and how each is covered

Method: for every one of the 108 non-merge gnome-shell commits in
`50.3..50.5`, each added line that is still in 50.5 was checked to be in the
merged tree (the same for mutter's 71). Only lines in code the fork deleted
(`NotificationsBox`, `workspaceAnimation.js`) are missing. The lock-path and
security-relevant ones:

| Upstream commit | Release | Coverage in the mobile shell |
|---|---|---|
| be3c57680 unlockDialog: escape markup in notification titles | 50.5 | **By design.** `NotificationsBox` is gone; the lock screen shows `NotificationMessage`s, whose `title` setter uses `Util.fixMarkup(text, false)` (escapes everything). Checked in `messageList.js`. |
| 94d5d7545 unlockDialog: restrict markup in notification body | 50.5 | **By design.** `body` goes through `URLHighlighter.setMarkup` → `Util.fixMarkup(text, useBodyMarkup)` (only b/i/u; URLs are detected in the text, `<a>` is not accepted). Launching those URLs while locked is blocked by 0010. |
| 8edf30c34 unlockDialog: `should-lock-session` blocks auth; 24b06f318 timeLimitsManager property | 50.5 | Merged. The fork's PIN pad bypassed the block (it types into the hidden entry and activates it at six digits): **0007** refuses input and activation while the parental-controls shield is shown. |
| 5fc616ea8 screenShield: refuse to deactivate at the screen-time limit | 50.5 | Merged into the fork's rewritten `deactivate()` (checked). |
| ea662dd2f unlockDialog: wait for authPrompt destruction before switching VT | 50.4 | Merged textually into the fork's `_otherUserClicked()`, but the fork's cancel path resets and keeps the prompt, so "Switch user" may not switch (Sol). Not reachable here: the button needs several users, and the phone has one. |
| 3e73f8cf1 unlockDialog: fix username reuse on reset | 50.4 | Merged into the fork's `_onReset()` (checked). |
| 0a5b2bbc4 authPrompt: `connectObject` for userVerifier signals; 929e431ee userVerifier: disconnect settings signals on destroy | 50.4/50.5 | Conflict resolved to upstream's form; `_onDestroy` disconnects the verifier. |
| 6954e7cf5 authPrompt: keep preemptiveAnswer while verifying; 42076add3 profile picture on Escape | 50.4/50.5 | Merged clean. |
| 470c6910c unlockDialog: keyboard focus navigation | 50.5 | Ported (conflict). |
| 412d7a8ff / 7af8e6463 xdndHandler: hide DND feedback and cursor clone while locked | 50.5 | Merged clean. |
| f79bbadb5 no accent colour for the lock-screen focus ring | 50.5 | Merged clean. |
| ad738eda9 messageList: limit title/body length | 50.5 | Merged (conflict, both sides kept). Upstream itself still renders and scans the untruncated strings, so the bound is ineffective in 50.5 too; not changed here. |
| 5df9af992 + 951426f3e notificationDaemon: internal signals only to the shell; b6ff90d14, b443183c3 serialization; 38780b223, 086c28492 activation tokens | 50.5 | Merged clean. |
| d710f00a5 shell/util: validate `create_pixbuf_from_data()`; 1fad949e6, eae83d181, 7f6fff694 polkit agent; c43812357 endSessionDialog in gdm mode | 50.5 | Merged clean (C and JS). |

### Fork problems found while reviewing the lock path, and the patches

| Patch | Problem in the fork | Change |
|---|---|---|
| 0002 | The 50 branch head has a literal `>>>>>>> eca9850fde` line in `js/ui/keyboard.js` (from commit 88dce45b7): the module does not parse, so the shell would not start. | Line removed (the 51 branch has the same code without it). |
| 0003, 0004 | From postmarketOS `temp/gnome-shell-mobile`: swipe-to-close crashed on transient popups; an idle source spun the main loop (shell issue #70, idle CPU). | As in pmOS. |
| 0005 | "Lock-screen overlays": every `org.gnome.Calls` window was reparented into the lock screen whenever Calls had a window (not only during a call), and the Emergency button launched Calls while locked. mutter-mobile 50 has no `set_forward_to_wayland_while_grabbed()`, so the path threw after the reparent. | Overlays and the Emergency button off (no modem on this build). |
| 0006 | Lock-screen notifications were tappable: the tap and the action buttons ran app code from a locked phone. Upstream's lock screen is not interactive. | No activation while `sessionMode.isLocked`; dismiss and media controls stay. |
| 0007 | PIN pad bypasses the screen-time auth block (above). | Refused while blocked. |
| 0008 | `powerManager.js` lights the panel after every resume, so `rog5-sleep-policy`'s 15 s wake windows would light it every minute. | Reads `/sys/power/pm_wakeup_irq`; only a PMIC power-key wake (or an unknown source) lights the panel. Any other wake turns the suspend action into `blank`: still locked, panel dark, the power key or user activity ends it. |
| 0009 | `powerManager.js` tests the return value of `screenShield._becomeModal()`, which GNOME 49 dropped (e350a7f1b). The test always failed, so **idle blanking never locked**: the shell showed "Unable to lock", and user activity deactivated the shield. On battery the policy's suspend locked it anyway (suspend-forced); on USB power an idle phone stayed unlocked. | Checks the shield's grab instead. |
| 0010 | (Sol) Quick settings stay usable on the lock screen, and the mobile quick-settings menu has its own notification list without the lock-screen privacy policy, so hidden notifications or bodies showed there. Detected URLs in lock-screen notifications launched from their own click gesture, past 0006. | The quick-settings list is hidden while locked or locking; no URL recognition or launch while locked. |
| 0011 | (Sol) blank/suspend/hibernate called `lock(false, true)`: locked, but the shield and lock mode came only after the fade (`showLater()`), and a power-key cancel during the awaits could light the panel uncovered. `org.gnome.ScreenSaver.Lock` returned before the lock screen was shown. The pre-suspend frame wait ran only when the action had just locked. A power press ignored in the 500 ms after resume had consumed the user-active watch. | Lock synchronously before blanking; `Lock` waits for `lock-screen-shown` again (and returns an error when locking is refused, e.g. by lockdown); wait for a frame (≤ 1 s, panel on) before every suspend; re-arm the watch. |

Noted, not changed: the 20 WIP/HACK/"stuff" commits outside the lock path
are unreviewed. As upstream, two trusted paths deactivate the shield without
the PIN: logind's `Unlock` (root: `loginctl unlock-session`) and
`org.gnome.ScreenSaver.SetActive(false)` on the session bus (processes of the
same user). The PIN unlock itself needs GDM. The fork removed the
`canLock()` check, so the shell always has a lock screen. In Phosh mode's
desktop mode (rog5-gnome, no GDM running) a GNOME lock therefore cannot be
unlocked, but `rog5-desktop-mode` already hands back to Phosh as soon as
GNOME reports a lock or idle.

## 2. Packages

`mutter-mobile` and `gnome-shell-mobile` (`pkgver=50.5`, `pkgrel=1`) have
`provides=(mutter=50.5 libmutter-18.so)` / `provides=(gnome-shell=1:50.5)`
and `conflicts=(mutter …)` / `conflicts=(gnome-shell)`, so pacman replaces the
stock packages in one transaction. makepkg only accepts `pkgrel` of the form
`integer[.integer]`, so the "mobile" mark is in the package name, not a
`.mobile1` suffix; a rebuild of the same base is `pkgrel=1.1`, `1.2`, …
Both build `-debug` packages. They are **not** in
`configs/rootfs/custom-packages.txt` (opt-in only).

**IgnorePkg:** unlike gtk2/phoc/phosh/vulkan-freedreno (patched builds under
the stock names, held with `IgnorePkg`), these names are in no repository,
so `pacman -Syu` and `rog5-update` never replace them and need no hold. The
risk is the other direction: when Arch ARM moves mutter/gnome-shell past
50.5 (GNOME 51: `libmutter-19.so`), packages that need the newer shell or
mutter make `pacman -Syu` fail its dependency check and `rog5-update` stops
updating. Before that, either rebuild on the new base (merge, re-check the
fixes, lock smoke test) or roll back (section 4).

### Build

On the phone, from a checkout. The build dependencies as root (the image has
no `sudo` rule for `phone`), the builds as `phone` (never as root):

    pacman -S --needed --asdeps base-devel git meson gobject-introspection \
        glib2-devel python-docutils sysprof wayland-protocols bash-completion \
        asciidoc evolution-data-server gnome-keybindings sassc
    cd packages/gnome-mobile/mutter-mobile && makepkg -f --nocheck
    # gnome-shell-mobile builds against mutter-mobile's headers, so as root:
    pacman -U --ask=4 mutter-mobile-50.5-1-aarch64.pkg.tar.*   # replaces mutter
    cd ../gnome-shell-mobile && makepkg -f --nocheck

Installing mutter-mobile alone for the shell build leaves the stock
gnome-shell on the mobile mutter until `rog5-gnome-mobile-install install`;
take the rollback set first (`rog5-gnome-mobile-install install` does that,
or build both on the host).

Host (what was done here): the rehearsal's aarch64 Arch root
(`scripts/host/rog5-build-rootfs` method: user namespace + qemu-aarch64
binfmt), `makepkg -f --nocheck`: ~50 min for mutter, 12-18 min for
gnome-shell under qemu; see "Host build" at the end. Natively on the phone
(8 cores) expect roughly 10-20 min and 5 min.

## 3. Session plumbing

**Selector.** `/etc/rog5/shell` = `phosh` (default; also missing/unknown) or
`gnome-mobile`. `rog5-shell-select.service` (`rog5-shell boot`, before every
display unit) writes this boot's choice to `/run/rog5-shell/effective`.
gnome-mobile is used only if gdm, both mobile packages and the session file
are installed and `/etc/gdm/custom.conf` has no automatic or timed login;
otherwise the boot is Phosh and the journal says why.

**rog5-gnome cleanup.** `ExecStopPost=` also runs after a start that its
`ExecCondition` skipped, so the desktop mode's settings reset (button
layout, idle delay, power-button action, DPU perf mode) now runs only after
a real start (marker `/run/rog5-gnome.setup`; the cleanup commands are
`-` so the marker is always removed).

**Gates.** Drop-ins give `rog5-phosh`, `rog5-desktop-mode` and `rog5-gnome`
an `ExecCondition` that passes unless the effective file says gnome-mobile,
and `gdm.service` one that passes only then. A missing file means Phosh, so
with the selector at `phosh` (or not installed) the Phosh boot is exactly
today's. A start of the wrong side (the "Phone mode"/"Desktop mode"
launchers, a D-Bus activation of GDM by an unlock prompt in desktop mode)
is skipped, never half-done. There is deliberately no `Conflicts=` between
GDM and Phosh: systemd stops a conflicting unit when the job is queued,
before the condition runs, so a refused "Phone mode" tap would have killed
the GNOME Mobile session. Ordering is one way (gdm `After=` the Phosh
units); a mutual `After=` deadlocks two pending start jobs.

**GDM, PIN at boot.** gnome-shell can only unlock through the gdm daemon,
and GDM cannot run without being the display manager, so gnome-mobile mode
is a GDM greeter without autologin: the PIN at boot (on-screen keyboard),
then the "GNOME Mobile" session (preselected through AccountsService). GDM
is never enabled; the selector starts it. The drop-in also runs
`rog5-kms-reset` first (mutter after phoc kept a stale plane on the panel
CRTC) and `Requires=` the watchdog.

**Watchdog** (`rog5-shell-watchdog.service`, root). Armed before GDM starts,
and by `rog5-shell switch gnome-mobile` before Phosh is stopped. Within 90 s:
GDM active, a gnome-shell that answers a `ShellVersion` property read on its
session bus (served by the shell's main loop; `Peer.Ping` would be answered
by the GDBus thread of a hung shell), that has the touchscreen
(`ASUS ROG5 MP2 front FTS3658U`) open, and the panel lit (DSI-1 enabled,
DPMS On) at least once. "Answering" means: the shell belongs to the active
session on seat0, the bus name `org.gnome.Shell` is owned by that very
process (`GetConnectionUnixProcessID`), and its `ShellVersion` is read. Then
it supervises: GDM inactive for 10 s, no answering shell for 45 s (a
GDM-started Phosh in the active session counts), or 3 crashed shells in 5 min (a shell
that died before it ever answered, or within 30 s while the same user's
shell came back; logins and logouts switch between the greeter's and the
user's uid and do not count). Without seat information no shell counts as
alive. If the watchdog itself fails for good (5 starts in 5 min;
`RestartMode=direct`, so retries do not pass through "failed"),
`OnFailure=` runs `rog5-shell-fallback.service`. On any failure: `/etc/rog5/shell` and the effective file go
to phosh, the reason goes to `/var/lib/rog5/shell-fallback`, GDM is stopped,
GDM's logind sessions are terminated, gnome-shell/DRM holders get TERM then
KILL until `/dev/dri/card1` is free, the mobile session settings are
restored (as the phone user, with its own clean environment),
`rog5-phosh` + `rog5-desktop-mode` start, and Phosh must report
`LockedHint=yes` within 30 s. Only compositor-side processes are signalled
(logind keeps fds of session devices too). Phosh is started only once the
GNOME compositor processes are gone. If they do not go away, or Phosh does
not report a lock, the whole sequence runs once more; after a second
failure the phone stays dark (SSH works) instead of unlocked.

**gsd-power.** The mobile shell's `powerManager.js` blanks, locks and handles
the power key; its gsd fork drops gsd-power. Here a user-unit drop-in
(`ExecCondition=rog5-shell gsd-power-allowed`) skips gsd-power when the
user's logind session has `Desktop=gnome-mobile` or is GDM's greeter. It is
decided per logind session because the lingering user manager keeps
environment variables across sessions. Phosh and the desktop mode keep
gsd-power.

**Session settings** (dconf is not per session): `rog5-gnome-mobile-session`
(user unit pulled in by `gnome-session@gnome-mobile.target`) saves and sets
`power-button-action=nothing` (the shell maps it to blank; Phosh's default
`suspend` would make gsd-media-keys ask logind to suspend, which the
permanent `rog5-server` inhibitor turns into a polkit prompt) and restores
it on stop; the fallback restores it too.

**rog5-sleep-policy** stays the owner of suspend. With 0008 the shell keeps
the panel dark after the policy's wakes and lights it itself after a
power-key wake, so in gnome-mobile mode the policy does not replay the power
key at all (a replay is a toggle and could blank the panel again). For
Phosh it still replays, and now re-reads DPMS right before the press. Known
limit: a power press within 500 ms of a non-user wake is ignored by the
shell (stale-event guard); press again.
The shell's sleep delay inhibitor locks before every policy suspend
(`systemctl suspend --check-inhibitors=no` still waits for delay inhibitors).

**On-screen keyboard:** gnome-shell's own OSK (mobile layouts); squeekboard
cannot work under mutter (no `zwp_virtual_keyboard_v1`) and stays Phosh's.
The greeter gets `screen-keyboard-enabled=true` (`/etc/dconf/db/gdm.d`).

**Scale 8/3 on the panel:** mutter accepts 8/3 (405x918 logical, below the
shell's 500x1000 phone threshold). Set it once in the first session
(Settings → Displays → 267 %, or `gdctl`), then `rog5-shell greeter-monitors`
copies the panel-only configuration to `/etc/xdg/monitors.xml` for the GDM
greeter. The existing desktop-mode configuration (panel off, DP primary) is
what mutter uses when the monitor is attached, so docking gives the desktop
UI on DP.

**Remote access:** wayvnc needs wlroots protocols and already skips itself
outside phoc (`ExecCondition=pgrep phoc`). In the mobile session use
gnome-remote-desktop (RDP; not installed yet):
`pacman -S gnome-remote-desktop`, then as `phone`:
`grdctl rdp set-credentials <user> <password>; grdctl rdp enable;
systemctl --user enable --now gnome-remote-desktop`. Port 3389 is reachable
over the trusted interfaces only (USB `usb0`, Tailscale, hotspot;
`rog5-firewall.nft`). Needs its own acceptance test. The headless Sway
desktop (`rog5-desktop`) is independent and stays.

**Session boost:** `rog5-session-boost` also floors `gnome-shell` and
`Xwayland`; the watchdog restarts it when a user's shell comes up.

## 4. Rollback

Quick, keeps the packages: `rog5-shell switch phosh` (Phosh on its lock
screen now, and at the next boot).

Full, one command (root):

    packages/gnome-mobile/rog5-gnome-mobile-install rollback

It sets Phosh, reinstalls the stock `mutter`/`gnome-shell` (and any
`mutter-devkit`/`-docs` that were installed) from
`/var/cache/rog5-gnome-mobile/stock`, removes gdm (`--keep-gdm` keeps it), the
debug packages and the session files. `install` refuses to start without a
complete rollback set (pacman cache → repository download of exactly the
installed version → `bacman`). `install`, `check` and `rollback` all run the
same validation first: every listed package has exactly that name, version
and architecture (from the archive's metadata) in the set, exactly one
archive each, or nothing changes. Rehearse it once (stage 0) before the first
real session: Phosh and the desktop mode are not isolated from a replaced
mutter/gnome-shell.

## 5. What the user must do

- **A 6-digit PIN.** The mobile PIN pad submits at the sixth digit and has
  no Enter key. A shorter PIN only works through the full-keyboard toggle; a
  longer one fails at digit six every time, and three failures lock the
  account for 10 minutes (`pam_faillock` defaults; root SSH clears it with
  `faillock --user phone --reset`). The PIN cannot be checked without reading
  it, so `rog5-shell set|switch gnome-mobile` asks for `--pin-is-6-digits`.
  Change it on the phone in Settings → System → Users → Password (or
  `passwd` as `phone`) if it is not 6 digits.
- Enter the PIN at every boot in gnome-mobile mode (the GDM greeter). The
  GDM login also unlocks the keyring, which the Phosh boot never did.
- Be present (with root SSH open) for stages 3-6.

## 6. Phone test plan

Each stage needs the user's OK. Stages 0-2 do not touch the running session
beyond what is stated. Run as root over SSH unless noted; `R` = the checkout
on the phone (e.g. `/home/phone/build/rog5-linux`).

**Stage 0 - install, rehearse the rollback (no user action).**

    pacman -Q mutter gnome-shell                 # 50.5-1 and 1:50.5-1
    $R/scripts/device/rog5-install-userspace     # rog5-shell, selector, gates
    systemctl daemon-reload && systemctl start rog5-shell-select
    rog5-shell status                            # next boot/this boot: phosh
    # packages: copy the host-built files into $R/packages/gnome-mobile/<pkg>/,
    # or build them there as phone (section 2)
    $R/packages/gnome-mobile/rog5-gnome-mobile-install install
    $R/packages/gnome-mobile/rog5-gnome-mobile-install check
    pacman -Qkk mutter-mobile gnome-shell-mobile gdm | tail -3
    $R/packages/gnome-mobile/rog5-gnome-mobile-install rollback   # rehearsal
    pacman -Q mutter gnome-shell                 # stock again
    $R/packages/gnome-mobile/rog5-gnome-mobile-install install

Pass: rollback set complete; `pacman -Qkk` clean; `systemctl is-enabled gdm`
is `disabled`; Phosh still on its lock screen with `LockedHint=yes`, apps
untouched; `systemctl status rog5-phosh` shows the condition passed.

**Stage 1 - headless check (no DRM; the phone's session is untouched).** As
`phone`, with a private bus, runtime dir and home:

    export HOME=$(mktemp -d) XDG_RUNTIME_DIR=$(mktemp -d)
    dbus-run-session -- sh -c 'gnome-shell --headless --unsafe-mode --virtual-monitor 405x918 --mode=user > $HOME/shell.log 2>&1 & sleep 40;
      gdbus call --session -d org.gnome.Shell -o /org/gnome/Shell -m org.gnome.Shell.Eval "Main.layoutManager.isPhone";
      gdbus call --session -d org.gnome.Shell.Screenshot -o /org/gnome/Shell/Screenshot -m org.gnome.Shell.Screenshot.Screenshot false false $HOME/home.png;
      gdbus call --session -d org.gnome.Shell -o /org/gnome/Shell -m org.gnome.Shell.Eval "Main.keyboard.open(); Main.panel.statusArea.quickSettings.menu.open()";
      sleep 3; gdbus call --session -d org.gnome.Shell.Screenshot -o /org/gnome/Shell/Screenshot -m org.gnome.Shell.Screenshot.Screenshot false false $HOME/qs-osk.png;
      gdbus call --session -d org.gnome.Shell -o /org/gnome/Shell -m org.gnome.Shell.Eval "Main.screenShield.lock(false); Main.screenShield._dialog.activate()";
      sleep 3; gdbus call --session -d org.gnome.Shell.Screenshot -o /org/gnome/Shell/Screenshot -m org.gnome.Shell.Screenshot.Screenshot false false $HOME/pin.png;
      pid=$(pgrep -n -x gnome-shell); sleep 600; ps -o %cpu=,cputime= -p $pid; kill $pid'
    grep -E "JS ERROR|TypeError|SyntaxError" $HOME/shell.log

Pass: `isPhone` → `(true, 'true')`; the screenshots show the mobile home
screen, quick settings, the OSK and the PIN pad (no Emergency button); no JS
errors; CPU time over the 10 idle minutes < 6 s (< 1 %).

**Stage 2 - lock review.** Done on the host (section 1 and the Sol review);
pass: no open security finding. Repeat after every rebase.

**Stage 3 - first GNOME Mobile session, live switch, Phosh fallback armed
(user present).** Prerequisite: the PIN is 6 digits.

    systemd-run --on-active=15min --unit=rog5-gm-revert /bin/sh -c \
      '[ -e /run/rog5-keep-gnome-mobile ] || /usr/local/sbin/rog5-shell switch phosh'
    rog5-shell switch gnome-mobile --pin-is-6-digits
    journalctl -fu rog5-shell-watchdog          # "gnome-mobile ready after N s"

User: the GDM greeter on the panel → tap the user → PIN on the OSK → GNOME
Mobile. Then: Settings → Displays → scale 267 % if it is not already; touch
lands where tapped; rotation; the OSK in a text field; power key → dark and
locked; power key → PIN pad; PIN unlocks. Root meanwhile:
`loginctl show-session $(loginctl show-user phone -p Display --value) -p LockedHint -p Desktop`
(yes while locked, no after; `Desktop=gnome-mobile`),
`systemctl --user -M phone@ status org.gnome.SettingsDaemon.Power.service`
(skipped by its condition), `journalctl -b --user -M phone@ | grep -E "JS ERROR|POWERMANAGER"`.
Keep: `touch /run/rog5-keep-gnome-mobile`, then `rog5-shell greeter-monitors`.
Pass: all of the above; the greeter at 8/3 after the next switch.

**Stage 3a - lock behaviour (supervised; root SSH open for
`faillock --user phone --reset`).**
- Wrong PIN ×3 → error message, then the faillock message; reset from SSH.
- Notification markup and actions while locked, as root:
  `systemd-run --user -M phone@ --wait notify-send -A ok=OK '<b>T</b><a href="x">a</a>' '<i>b</i><img src="file:///x"/>'`
  → the title shows the tags as text, the body only italics; tapping it or
  "OK" does nothing while locked.
- GDM frozen: lock, `kill -STOP $(pgrep -x gdm)`, enter the PIN → stays
  locked (error or timeout); `kill -CONT` → PIN works.
- Races: power key twice fast; `systemctl suspend` while the PIN pad is up;
  DP plug/unplug while locked.
- Escapes: edge swipes, quick settings, OSK long-press, a Bluetooth keyboard's
  Super, Alt+Tab, Ctrl+Alt+T, Escape on the PIN pad.
- PIN lengths: 5 digits → nothing is submitted; the full-keyboard toggle +
  Enter works.

Pass: no app frame visible and no app input on any output while locked; GDM
down → stays locked; no Emergency button, no Calls over the lock screen;
PIN pad and faillock as described.

**Stage 4 - power (battery).** Unplug USB power; power key blank; wait for
the policy's suspend (60 s) and several 15 s wake windows; then 10 power-key
wakes; then a 30 min standby with `rog5-standby-measure`.
Pass: `journalctl -b | grep 'rog5-sleep-policy\|POWERMANAGER'` shows
"keeping the screen off" on policy wakes and the panel stays dark; every
power-key wake lights it (no double blank from the replay); no
`POWERMANAGER` exceptions; standby within 5 mA of the Phosh baseline (~79 mA).

**Stage 5 - docking.** MSI hub + monitor, apps open: plug (desktop UI on
DP, panel off), unplug (phone UI), 5 cycles; then 5120x1440@60 and
3840x1080@100; lock while docked. Then in `phosh` mode once: desktop mode
(`rog5-gnome`) still works with the mobile packages and hands back to Phosh
on lock/idle.
Pass: apps survive every cycle; the UI flips; no gnome-shell core dump; no
DPU underrun in `dmesg`; the lock screen covers both outputs.

**Stage 6 - boot path and fallback.**

    rog5-shell set gnome-mobile --pin-is-6-digits && reboot   # with, then without the monitor
    # break GDM on purpose:
    mkdir -p /etc/systemd/system/gdm.service.d
    printf '[Service]\nExecStart=\nExecStart=/bin/false\n' > /etc/systemd/system/gdm.service.d/99-break.conf
    rog5-shell set gnome-mobile --pin-is-6-digits && reboot
    cat /var/lib/rog5/shell-fallback; rog5-shell status          # fell back, next boot phosh
    rm /etc/systemd/system/gdm.service.d/99-break.conf; systemctl daemon-reload
    rog5-shell switch gnome-mobile --pin-is-6-digits              # then, once ready:
    kill -STOP $(pgrep -u phone -x gnome-shell)                   # hung shell

Pass: the greeter appears and the PIN starts the session (both boots); the
broken GDM and the hung shell each end in Phosh **locked** within 90 s (hung:
45 s + fallback), with the reason recorded.

**Stage 7 - a week of daily use** in gnome-mobile mode; then the user
decides the default.

## Host build

Done 2026-10-01: both packages built on the host (aarch64 under qemu) from
exactly this patch series, and a headless smoke test passed (mobile UI,
`isPhone` at 405x918, lock → PIN pad without Emergency button, unlock fails
closed without GDM). Details, checksums and the phone's read-only state:
[test-results/2026-10-01-gnome-mobile-host-build.md](../../test-results/2026-10-01-gnome-mobile-host-build.md).
The package files are in `~/.local/state/rog5-gnome-mobile-build/packages/`
(private); copy them into `mutter-mobile/` and `gnome-shell-mobile/` of the
phone's checkout before `rog5-gnome-mobile-install install`.
