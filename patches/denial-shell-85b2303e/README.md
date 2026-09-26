# Denial mobile-shell patches (applied to the shipped tree)

The phone's `/opt/denial` bundle was built from unpatched upstream
denialwm/denial 85b2303e, plus the engine MSAA patch
(`patches/denial-engine`). The `patches/denial-85b2303e` series
(0001-0019) has never been built into it. The patches here apply directly to
that shipped tree, `~/.local/state/rog5-denial-20260910-r1/engine-build-r1/denial`.
0001-0004 change only the Dart shell (`libapp.so`); 0005 changes only the
compositor (`deniald`); 0006 changes both.

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
- `0003-keyboard-follows-editor-focus.patch` (**withdrawn**, replaced by
  0006; kept for reference): the on-screen keyboard now opens
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

- `0005-power-key-toggles-display.patch` (compositor): the PMIC power key
  (`pmic_pwrkey`, `KEY_POWER`, reaches deniald through libinput) is claimed
  in the libinput keyboard path before activity is noted, so press and
  release never reach the shell or a client. A press sets
  `RuntimeState::power_key_pending`; `dpms::synchronize_power_key` runs every
  event-loop iteration just before the DPMS apply step (not on the 30 Hz
  service tick the shell's double-tap request waits for). With the output
  lit it calls `IdlePolicy::blank_now` (the same compositor-owned path as the
  shell's screen-off) and logs "power key requested immediate
  compositor-owned display power-off"; with the output off it notes user
  activity, which wakes it ("power key woke the displays"). Locking on the
  power key is a separate, opt-in path: only with `DENIAL_POWER_KEY_LOCK=1`
  in the service environment does it call `Authentication::lock()` first
  (`locked=true` in the log). It is off while root has no password. No
  `/etc/shadow` probing, no PAM change. logind keeps reading the key itself
  (`HandlePowerKey=ignore`, `HandlePowerKeyLongPress=poweroff` unchanged).
- `0006-keyboard-opens-on-focus-closes-on-outside-tap.patch` (compositor +
  shell): the keyboard opens when an editor gains focus and closes when focus
  leaves or on a tap outside it. Why 0003 misbehaved: the compositor only
  reported `inputPanelVisible` when the editor committed within 250 ms of
  touch-down, so launches (foot enables text-input on focus, no touch
  involved), autofocus and slow taps never opened it, and 0003 tried to
  infer focus changes in Dart from deduplicated states that carry no
  activation serial. Also, the `TapRegion.onTapOutside` it relied on never
  fires for shell touches on the device (checked with a diagnostic build).
  - `wayland_frontend/text_input.rs`: a text-input-v3 enable (focus gain)
    and an explicit `show_input_panel` open the keyboard without a touch; a
    Flutter editor that becomes active+shown (new client, new lifecycle, or
    show after hide) is authorized without a touch. Every touch outside the
    OSK still dismisses a client editor's keyboard. The re-claim window (now
    350 ms) restarts at touch-up (`note_touch_released`, called from
    `input/flutter_route.rs`), and caret-rectangle-only commits (terminal
    redraw traffic) neither claim nor spend it. An enable bumps the
    activation serial so an unchanged state is republished after an app
    switch.
  - `flutter_runtime/service_bridge.rs`: logs "published software-keyboard
    state" when (active, visible, legacy) changes.
  - `edge_panel_layer.dart`: a translucent `Listener` over the shell sees
    every Flutter touch while the keyboard is shown; on touch-down it hit
    tests the position, and a tap (up within `kTouchSlop`) that did not land
    in the `EditableText` tap group (the keyboard sheet, its scroll strip,
    the OSK, shell text fields) closes the keyboard and unfocuses a focused
    shell editor.
  - `shell_controller.dart`: remembers the last text-input state and applies
    it again when a launch transition completes (the launch resets the panel
    after the app's editor already reported focus).

- `0007-mobile-app-fit-keyboard-resize-input-origin.patch` (shell): where a
  Wayland app sits on the phone screen, from the 2026-09-26 app test
  (`test-results/2026-09-26-app-usability.md`). `MobileWindowLayout`
  (`input/input_layout.dart`) is shared by painting
  (`window_texture_rect.dart`) and input (`shell_input_layout_coordinator.dart`):
  - Apps are configured to 0,48 .. 432x895. The bottom 36 logical px
    (`appGestureBandHeight`) are kept for the home pill, and with an app in
    front only that strip (`appGestureRect`) starts the home and app-switch
    swipes. Taps on an app's bottom row now reach it (Calculator 0 . x f(x) =).
  - Keyboard: the app the keyboard is open for is configured to the area
    above it (432x637) instead of the whole scene being panned up by the
    keyboard height. Its focused field stays visible (foot prompt, Firefox
    and Chromium URL bars, Text Editor header). There is no pan and no
    right-edge scroll strip for Wayland apps; local Flutter apps keep the
    old pan.
  - Fit: an oversized window (Chromium and Firefox at a 500 px minimum width,
    System Monitor, file choosers) is scaled down to fit, keeping its aspect
    ratio. A client wider than the screen is asked for a proportionally
    taller window (`configureSize`), so after scaling it fills the screen.
    A smaller window (mpv with `keepaspect-window`, dialogs) is shown at
    its own size, centred, on the status-bar colour. Nothing is cropped or
    stretched any more. Windows at least about as tall as the keyboard area
    stay top-aligned.
  - Input: regions map the painted rectangle onto the window's
    root-surface coordinates, including the CSD geometry origin (26,23 for
    GTK3, 25,25 for GTK4, 16,10 for Chromium) and the scale. This supersedes
    the old `denial-85b2303e/0019`, and the tap offset is gone. The resize
    replaces the caret-aware pan of old 0013-0017 (Firefox publishes no
    usable caret, and a resize serves every client). The publisher now
    rebuilds on window and geometry changes (as old 0016 did).
- `0008-keyboard-follows-taps-scaled-touch-input.patch` (compositor):
  - `text_input.rs`: a shell touch still closes the keyboard at once. A
    touch on the focused client is resolved at touch-up + 350 ms: an editor
    that commits fresh state claims the keyboard, and a disable closes it.
    Otherwise a tap (moved less than 12 px, one finger) decides:
    - terminal purpose (foot): the keyboard toggles;
    - a tap within 24 px of the caret's line: the keyboard opens (a field
      that was already focused, which sends nothing when tapped again);
    - an editor with no usable caret (Chromium sends none, Firefox an
      empty one): the keyboard opens;
    - any other tap: the keyboard closes (Calculator's own keypad).
    Drags and scrolls leave it as it was. The due state is settled in the
    30 Hz keyboard service pass (`settle_software_keyboard`).
  - `input.rs`/`flutter_route.rs`: a region drawn at another scale gets its
    touch focus and location in root-surface coordinates
    (`touch_focus_at`). Smithay's `location - origin` cannot express a
    scale. The tap point used for the caret test comes from the window's
    root region (`root_surface_point`), so taps on popups also work.
- `0009-locked-window-corners-are-app-content.patch` (compositor): the
  desktop touch gestures claimed a 64x64 "move" corner at each corner of
  every window, geometry-locked ones included. On the phone those touches
  were swallowed, for example the Calculator undo button, and the 0 and =
  keys once the app ended above the pill strip. A locked window cannot
  move, so its corners are now ordinary content.
- `0010-flush-clients-after-shell-window-commands.patch` (compositor):
  configure events queued by a shell window command (the keyboard resize)
  were only flushed with unrelated client traffic, 1.3-2.8 s later. They are
  now flushed right after the commands are applied (about 30 ms).

The patches are unified diffs against upstream 85b2303e. Apply them in order
with `patch -p1` from the source root: 0001, 0004, 0005, 0006, 0007, 0008,
0009, 0010 (0002/0003 are withdrawn and do not combine with 0006). The build
trees are exactly upstream + 0001 + 0004 + 0005 + 0006 + 0007 (Dart,
`engine-build-r1/denial/dart_shell/lib`; the base without 0006 is kept at
`engine-build-r1/dart_shell-lib.base-0001-0004`) and upstream + 0005 + 0006 +
0008 + 0009 + 0010 (`cargo-arm64-power-r1/source/compositor`).

## Deployed state (2026-09-26, after 0007-0010)

| file | content | sha256 | backup on the phone |
| --- | --- | --- | --- |
| `/opt/denial/deniald` | upstream + 0005 + 0006 + 0008 + 0009 + 0010 (compositor), build `p10` | `51959007...` | `/opt/denial/deniald.0005-0006` (`644c98c8...`), `/opt/denial/deniald.upstream` (`8698b071...`) |
| `/opt/denial/lib/libapp.so` | upstream + 0001 + 0004 + 0006 + 0007 (Dart), `assembly-r9` | `c65bb6fa...` | `/opt/denial/lib/libapp.so.0001-0004-0006` (`1064f485...`), `/opt/denial/lib/libapp.so.0001-0004` (`c6f72921...`) |

To go back to the 0005/0006 state: stop `rog5-denial`, copy the two
`.0005-0006`/`.0001-0004-0006` backups over the live files, and start it.

Local copies: `~/.local/state/rog5-denial-20260910-r1/cargo-arm64-power-r1/artifacts/`
(`deniald-p10`, `libapp-r9.so`; before 0007-0010: `deniald-p4`, `libapp-r6.so`). `DENIAL_POWER_KEY_LOCK` is not set, so the
power key only toggles the display. To lock as well once root has a
password, add `DENIAL_POWER_KEY_LOCK=1` to the unit's `Environment=`.

Verified on the phone (7.2.7-r98): a uinput `KEY_POWER` press
(`scripts/device/bench/vpower.py`; press and release in one write, so logind
never sees a held key) blanked DSI-1
(`dpms` Off, "powered off KMS output through DRM DPMS" 0.18 s after the
press) and the next press woke it; logind only logged "Power key pressed
short". foot launched from its home icon opened the keyboard; OSK typing
reached foot; a tap on foot closed it. Add network (Wi-Fi) autofocused its
SSID field with the keyboard open; tapping the dialog background closed it;
tapping a field reopened it; field-to-field kept it; Cancel closed it. The
edge-swipe keyboard on the home screen closed on a tap on the wallpaper.
(Before 0007/0008, a tap on a focused Wayland client did not reopen the
keyboard, and the keyboard panned the app up by its height.)

Verified on the phone with 0007-0010 (production-7.2.7-r102, 2026-09-26;
screenshots under the session scratchpad, `ufx/shots/`):
- foot: the prompt and output stay visible above the keyboard (foot is
  configured 432x637), and a tap toggles the keyboard with the resize
  following in about 30 ms.
- Chromium: the omnibox is focused at launch. After the keyboard was closed
  from the status bar, a tap on the omnibox reopened it. The 500 px window
  is scaled to the full screen.
- Firefox: a precise tap on the small "+" tab button opened a tab. The URL
  bar and its dropdown stay visible above the keyboard.
- Calculator: C 0 . 1 + 2 = typed "0.1+2" = 2.1, the corner keys (0, =, undo)
  and the bottom row included. Keypad taps do not open the keyboard, and a
  tap on the entry does.
- System Monitor: scaled to fit, and its tab taps land. mpv at its own
  432x243 is centred, not stretched.
- A swipe up from the pill (y 952 of 979) still goes home with an app in
  front.
Not verified: Text Editor typing (key events reach it, but no text appeared
in the restored draft in this run, with or without the OSK). Known and
older than this change: the right-hand keyboard edge-swipe target (the
bottom 10 px, x >= 212) overlaps the pill, so a swipe that starts on the very
bottom edge right of centre opens the keyboard instead of going home.

## Rebuild and deploy deniald (about 3 minutes)

    cd ~/.local/state/rog5-denial-20260910-r1/cargo-arm64-power-r1
    python3 run.py TAG      # build-TAG.log, build-TAG-result.json

`run.py` runs the offline aarch64 cargo build (image `rust-build-r3`,
`--features flutter --bin deniald --bin denialctl`) on `source/` (a plain
copy, so no clean-git check; it checks the `Cargo.lock` hash instead). The
`target/` there was copied from a later build, so after replacing `source/`
touch every file (`find source -type f -exec touch {} +`). Otherwise cargo
keeps a stale `denial-flutter-engine` that wants engine symbols the phone's
engine lacks, and deniald exits with "required Flutter engine symbol is
unavailable". Deploy by staging `deniald.new`, then `systemctl stop
rog5-denial`, `mv deniald.new deniald`, and start it.

## Rebuild and deploy libapp.so (about 1 minute)

    EB=~/.local/state/rog5-denial-20260910-r1/engine-build-r1
    cp scripts/host/denial/assemble-shell.sh $EB/assemble-r2.sh
    podman run --rm --read-only --read-only-tmpfs=false --memory=8g --memory-swap=8g \
      --cpus=4 --pids-limit=1024 --network=none -v $EB:/build:rw -v $EB/tmp:/tmp:rw \
      -e HOME=/build/home -e TMPDIR=/build/tmp -e TAR_OPTIONS=--no-same-owner \
      localhost/rog5-denial-engine-builder:r1 sh /build/assemble-r2.sh

The current build used `$EB/assemble-r6.sh` (the same, plus `flutter analyze
--no-pub lib`, which must report no issues) with output `assembly-r6`.
Output: `$EB/assembly-r2/lib/libapp.so`. The script uses `pub get --offline`,
because the builder has no network and the pub cache is already filled.
Deploy it over SSH to `/opt/denial/lib/libapp.so` (the shipped copy is kept as
`libapp.so.r1`), then run `systemctl restart rog5-denial.service`.
