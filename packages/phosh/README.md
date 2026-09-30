# phosh for the ROG Phone 5: monitor hotplug crash fix

Patched build of [Phosh](https://gitlab.gnome.org/World/Phosh/phosh) 0.57.0.
`PKGBUILD` is the Arch Linux packaging (0.57.0-1) with `aarch64` added,
`options=(debug)` (a `phosh-debug` package with symbols) and two patches
(0001 below, 0002 LockedHint). Current packaging: `phosh 0.57.0-1.3`
(1.2 is installed on r197).
`/etc/pacman.conf` has `phosh` in `IgnorePkg` next to `phoc` and `resources`.

## The crashes (2026-09-29)

12 Phosh SIGSEGVs in one day (10 with a core dump), all while the USB-C
hub/monitor was in use. Every
crash ended the gnome-session: `rog5-phosh` restarted it, all apps were
closed, and the phone came back on the lock screen. The stock binary is
stripped, so the offsets were matched by rebuilding 0.57.0 with the same
toolchain and by looking at the string references around each crash address.

| Signature (stock binary) | Cores | Where |
|---|---|---|
| `g_object_get_data` <- phosh+0x6c3e8 / crash at phosh+0x6c39c, from a `wl-outputs` notify | 7 | `lockscreen-manager.c`: `on_monitor_removed()` -> `remove_shield_by_monitor()` |
| `gtk_widget_destroy` <- phosh+0x6b8d8 <- phosh+0x70e7c | 2 | `on_lockscreen_unlock()` -> `g_ptr_array_unref (shields)`, called from the PIN auth callback in `lockscreen.c` |
| `gtk_gesture_set_sequence_state` -> libgtk-3 | 1 | GTK 3, not Phosh (see below) |

Both Phosh signatures have the same cause. The lockscreen manager keeps the
lock shields (the black layer surfaces on non-primary outputs, here DP-1) in
a `GPtrArray` without a reference. A shield destroys itself when the
compositor closes its layer surface, which phoc does when the output is
destroyed. A shield still in the array then leaves a dangling pointer. It is
used on the next monitor removal (`g_object_get_data: assertion 'G_IS_OBJECT
(object)' failed`, then `remove_shield_by_monitor: assertion 'PHOSH_IS_MONITOR
(shield_monitor)' failed`, and a SIGSEGV once the memory is reused) or on
unlock (`gtk_widget_destroy` on freed memory). Once one entry was invalid,
`remove_shield_by_monitor()` bailed out on every later removal. The DP link
flapped every ~20 s (HPD), so the shields that were never removed piled up
until one crash.

A shield can stay in the array after its monitor is removed. `lockscreen_lock()`
shields every monitor the monitor manager knows, including ones that are not
configured yet. Those monitors then emit `monitor-added` and get a second
shield, but `monitor-removed` removed only the first.

Upstream `main` (checked 2026-09-29, 79 commits after v0.57.0) has not changed
`lockscreen-manager.c`, so there was nothing to backport.

## The patch

`0001-lockscreen-manager-Don-t-keep-pointers-to-destroyed-.patch` (against tag
`v0.57.0`, only `src/lockscreen-manager.c`):

- A shield that gets destroyed (compositor closed it) is dropped from
  `shields` (`destroy` handler). When the manager destroys a shield itself, it
  disconnects that handler first, so the array is never modified while it is
  being cleared.
- `lock_monitor()` does not add a second shield for a monitor that already has
  one.
- `remove_shield_by_monitor()` removes all shields of the monitor and no
  longer bails out.
- The shield holds a reference on its `PhoshMonitor`, so a new monitor cannot
  reuse the address while the shield exists.

## 0002: the startup lock reaches logind (1.2, revised in 1.3)

Phosh locks in `main()` before the screen saver manager has its login1
session proxy, so logind's `LockedHint` read "no" on a locked phone until the
next lock/unlock, and `rog5-desktop-mode` (which starts GNOME only after a
LockedHint yes -> no of the same session) could not see the boot lock.
1.2 sent the state when the proxy arrived. 1.3
(`0002-screen-saver-manager-publish-the-lock-state-from-both-callbacks.patch`)
also sends it from `on_name_acquired` (lock changes are only connected
there, before or after the proxy; a change in between was lost), and sends
only the hint instead of calling `on_lockscreen_manager_locked_changed()`,
which on an unlocked state also unarms a pending lock-delay timer. Check after
a Phosh start: `loginctl show-session <id> -p LockedHint` is `yes` on the
lock screen and `no` after the PIN.

## Gesture crash (not fixed here)

The 14:27:27 crash is in GTK 3.24.52, not in Phosh. The app grid's
`GtkScrolledWindow` long-press gesture fires (`scrolled_window_long_press_cb`
-> `gtk_gesture_set_sequence_state(DENIED)`) and GTK emulates a press for the
widgets below. `_gtk_widget_emulate_press()` walks from the event widget up to
the scrolled window. The GdkWindow of the touch's last event had already been
destroyed (`user_data` NULL: a child input window of a widget in the grid that
was unrealised during the touch), so `gtk_get_event_widget()` returned NULL and
`_gtk_widget_get_parent(NULL)` crashed. The fix belongs in gtk3: return early
when the event widget is NULL or not a descendant. The `gtk-3-24` branch does
not have it yet. It happened once, 0.5 s after a DP re-plug, while a finger was
on the app grid.

## Test harness (no monitor needed)

`hotplug-test.sh` (a copy is in `/home/phone/build/` on the phone; run it as
`phone`) starts headless sway
(no DRM, no input), a nested phoc with 2 outputs (the wayland backend, one
sway window each) and the Phosh under test, locked, on a private session bus.
Closing the WL-2 window destroys phoc's output WL-2, in the same order as a DP
unplug. `CLOSE_SHIELD=1` first destroys the shield widget from gdb, which is
the state seen in the crashes. `UNLOCK=1` unlocks the test instance from gdb
after the unplug. That needs an unstripped binary. No PIN is used and the
real session is not touched.

Results on 2026-09-29:

- unpatched 0.57.0, `CLOSE_SHIELD=1 UNLOCK=1`: the same criticals as on the
  phone (`g_object_get_data: assertion 'G_IS_OBJECT (object)'`,
  `remove_shield_by_monitor: assertion 'PHOSH_IS_MONITOR (shield_monitor)'`,
  and on unlock `gtk_widget_destroy: assertion 'GTK_IS_WIDGET (widget)'`, all
  on freed memory);
- patched: `Shield ... got destroyed`, a clean removal and unlock, no
  criticals;
- patched, plain unplug: `Removing shield ...`, as before.

Separate finding: after an unplug, the gdb-forced unlock sometimes crashes in
`HdyCarouselBox` drawing (libhandy). It happened in about a third of the runs
and **equally with the unpatched build**. It was not seen without an unplug,
and it is not one of the phone's crash signatures. It is not investigated
further here.

## What you need to test (real monitor)

The crash needs a real DP output going away, which the phone cannot do on its
own. After installing (already done 2026-09-29) and one Phosh restart:

1. Lock screen, monitor unplugged: plug the hub + monitor in and wait until
   it shows the black lock shield. Unplug it, then plug it in again 5 times,
   a few seconds apart. Phosh must stay up: the lock screen stays, and no
   session restart or app loss happens.
2. Unlock with the PIN while the monitor is connected, then again right after
   unplugging it (this was the `gtk_widget_destroy` crash at 16:21).
3. Unlocked, open a few apps and plug/unplug the monitor a few times. Apps
   must stay open.
4. Desktop mode: tap "Desktop mode" (GNOME on the monitor), then return
   (unplug, or wait for the switcher), and again. Phosh comes back on its lock
   screen; unlock and check that it keeps running after one more plug/unplug.
5. Let the phone lock by itself (idle) while the monitor is connected, then
   unplug. This is the double-shield case.

Then check on the phone:

    coredumpctl list /usr/lib/phosh/phosh --since today     # no new phosh entries
    journalctl -b --grep 'remove_shield_by_monitor|G_IS_OBJECT|GTK_IS_WIDGET'   # empty

If Phosh still crashes, `phosh-debug` is installed, so `coredumpctl info` and
`coredumpctl gdb` now show function names and lines. Debug logging for the
manager: add
`G_MESSAGES_DEBUG="phosh-lockscreen-manager phosh-monitor-manager"`
(space separated) to Phosh's environment.

## Rebuild (on the phone, as the `phone` user, never as root)

    pacman -S --needed --asdeps python-docutils        # as root, for the man pages
    cd /home/phone/build/phosh                          # copy of this directory
    makepkg -f --nocheck --skippgpcheck                 # b2sums still pin the tag
    sudo pacman -U phosh-0.57.0-1.3-aarch64.pkg.tar.xz phosh-debug-0.57.0-1.3-aarch64.pkg.tar.xz

The PGP key for the signed tag is in `keys/pgp/`. Import it
(`gpg --import keys/pgp/*.asc`) and drop `--skippgpcheck` to verify the tag
too. The `check()` tests need `xorg-server-xvfb` and are skipped. When
upgrading to a newer Phosh, check whether upstream has fixed
`lockscreen-manager.c`, take the new Arch PKGBUILD/b2sum, and refresh or drop
the patch.
