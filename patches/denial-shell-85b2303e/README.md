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

The patches are unified diffs against upstream 85b2303e. Apply them in order
with `patch -p1` from the source root. Together, 0001-0003 reproduce the
shipped tree's `dart_shell/lib` exactly.

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
