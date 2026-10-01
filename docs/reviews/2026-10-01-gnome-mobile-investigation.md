# GNOME Shell mobile instead of Phosh + GNOME desktop mode (2026-10-01)

Question (user): can one GNOME Shell session drive both the phone panel and
an external monitor, so docking keeps the apps open and there is no Phosh to
GNOME switch? Scope: the phone as of `main-k111-d10-261001b` (Arch Linux ARM,
gnome-shell 1:50.5-1, mutter 50.5-1, gnome-settings-daemon 50.1-1,
gnome-session 50.1-1, phosh 0.57.0-1.3, phoc 0.57.0-1.2, squeekboard
1.43.1-5, no GDM). Research and design only. The phone was read only (package
versions, units, inhibitors, `monitors.xml`); nothing was built, installed or
restarted. The user was in GNOME desktop mode during the reads.

**Update, later on 2026-10-01:** the user chose to try GNOME Shell Mobile
now anyway. It is implemented as an opt-in session next to Phosh (base
GNOME 50.5 with the mobile 50 branches merged in, fixes ported, watchdog
with fallback to a locked Phosh, rollback set):
[packages/gnome-mobile/README.md](../../packages/gnome-mobile/README.md).

## Short answer

**Recommendation: not yet.** Don't replace Phosh now. Revisit when
(a) Arch Linux ARM ships GNOME 51 and (b) GNOME Shell Mobile has a branch on
a 51.x release.

The reasons:

1. **No release for GNOME 50.** GNOME Shell Mobile is still out of tree.
   Its `-50` branches are unreleased work in progress, based on 50.3. The
   shell branch is 109 commits behind 50.5, and those commits include
   lock-screen security fixes that conflict with the mobile lock-screen
   rewrite.
2. **The phone will move to GNOME 51 soon.** GNOME 51.0 has been in Arch's
   `gnome-unstable` since 2026-09-15. A port to 50 would become stale within
   weeks.
3. **The lock needs GDM.** The project has no display manager today, so the
   boot flow would have to change.
4. **The mobile power manager lights the screen after every resume.** With
   `rog5-sleep-policy`'s periodic wakes, the panel would light up every
   cycle, so the shell needs a patch.
5. **The PIN pad only works with 6-digit PINs.** It submits on the sixth
   digit and has no Enter key; any other PIN length needs the full keyboard.
6. **Docking is a global switch.** The shell is either all phone UI or all
   desktop UI, depending on which monitor is primary; there is no
   per-monitor layout.

Docking without losing apps does work in principle: there is one mutter
session, and the external monitor as primary flips the shell to the desktop
UI. That is the part the user wants. It is not production-ready on this
phone today.

**Cheaper first step.** Phosh 0.57 has a docked mode
(`src/docked-manager.c`: no auto-maximise, OSK off when a keyboard and
pointer are attached). Phosh plus docked mode on DP keeps the apps open on a
dock with no new stack. It is worth one supervised test before investing in
GNOME Shell Mobile (see "Alternative" below).

**Effort if we go ahead later (on a 51.x mobile branch):**

- About 5-7 agent days and 2-3 hours of the user's time to reach an opt-in
  session with Phosh as the fallback.
- About half a day per GNOME point release: merge, rebuild on the phone,
  lock smoke test.
- Unbounded per GNOME major release if upstream does not rebase. The
  history: 46 → 48 in 2025-03, then nothing shipped for 49, 50 or 51.

## 1. State of GNOME Shell Mobile (September 2026)

### Upstream (GNOME 46-51)

Only the building blocks are upstream.

**mutter:**

- **46.0:** new gesture framework base (!2389).
- **49:** gesture recognisers replace click/tap/pan actions (!2857,
  merged 2025-08-28). The X11 session was dropped.
- **50.rc:** touch input delivered to the wrong surface, fixed (!4914).
- **51.rc:** auto-rotate fix for phones without a tablet-mode switch
  (!4962, merged 2026-08-04). It is not in the 50.x NEWS, so mutter 50.5
  probably still has the bug.
- **Already upstream for a long time:**
  - Rotation through iio-sensor-proxy (`meta-orientation-manager.c`).
  - Mutter 50.5 manages the panel orientation only in touch mode
    (`update_panel_orientation_managed`: touch mode && accelerometer &&
    built-in monitor).
  - Touch mode is `!has_pointer` without a tablet switch
    (`meta-seat-impl.c`), so a docked mouse turns rotation and the OSK
    auto-show off.
- **Fractional scaling:** mutter 50.5 lists only `kms-modifiers` and
  `autoclose-xwayland` as experimental features. Per-monitor fractional
  scaling is therefore available without a flag; the phone's
  `monitors.xml` already uses `<layoutmode>logical</layoutmode>`.

**gnome-shell:**

- **48:** OSK look (!3555, !3553).
- **49:** the move to ClutterGesture (!2853), and the unlock prompt no
  longer resets on every tap (!3852).
- **50.1:** OSK fits small screens (!4156).
- **51:** touch scrolling in ScrollView (!4138).
- **Still open:** the is-phone property (gnome-shell !2303), the adaptive
  app grid (!3392) and OSK focus (mutter !1543). Source: the fork's
  upstreaming tracker,
  https://gitlab.gnome.org/World/MobileShell/gnome-shell-mobile/-/issues/72.
- **No mobile session mode.** Upstream `js/ui/sessionMode.js` at 51.0 has
  only restrictive, gdm, unlock-dialog and user.

**Maintainers:**

- GUADEC 2026 mobile BoF (A Coruña, 2026-07-19; notes at
  https://pad.gnome.org/6KLdColfQz-2LHVoV32mzQ):
  - Jonas Dreßler: "of 300 patches, 100 are maybe moot now or need to be
    rewritten".
  - Markus Göllnitz and Abderrahim take over maintenance; a weekly rebase
    for GNOME OS is the goal.
  - Upstream: "in principle yes", but no date.
- Carlos Garnacho, 2026-09-15
  (https://blogs.gnome.org/carlosg/2026/09/15/on-mobile-and-peer-pressure/):
  the branch is "+120437 −7156" with FIXMEs and WIPs, and must be split
  into reviewable merge requests.

### The fork

The fork lives at https://gitlab.gnome.org/World/MobileShell (moved from
`verdre/*`). It needs all three of `gnome-shell-mobile`, `mutter-mobile` and
`gnome-settings-daemon-mobile`. Branch heads were read through the GitLab
API and git on 2026-10-01:

| Repo / branch | Head | Date | Base | Own commits |
|---|---|---|---|---|
| shell `mobile` (default) | 645d0407c1fa | 2026-08-14 | 51.beta, 192 behind 51.0 | 338 |
| shell `mobile-shell-devel-50` | d95fe2ac2c2f | 2026-07-23 | 50.3+2, 109 behind 50.5 | 357 |
| shell tag `48.mobile.0` | cf9bd6b53932 | 2025-03-30 | 48.0 | 365 |
| mutter `mobile` | 179766601c36 | 2026-08-14 | 51.beta, 299 behind 51.0 | 66 |
| mutter `mobile-shell-devel-50` | c99af8f42a83 | 2026-07-26 | 50.3, 70 behind 50.5 | 54 |
| mutter `camelCaseNick/mobile-shell-devel-50` | fe00ce8682f0 | 2026-09-27 | 50.3 | 57 (+ OSK during popups) |
| gsd `camelCaseNick/gnome-50-mobile` | ea05a778f423 | 2026-09-27 | 50.1 | 2 |

Open issues: shell #85 "rebase Shell and Mutter on GNOME 50" (opened
2026-08-05) and #84 (rebase `mobile` on main). There are no tags for 49, 50
or 51.

### Distributions

**postmarketOS** (renamed Nura on 2026-09-27; pmaports at
https://gitlab.postmarketos.org/postmarketOS/pmaports, `main` 710e4b87,
2026-10-01):

- `temp/gnome-shell-mobile` 48.0-r11, `temp/mutter-mobile` 48.0-r4 and
  `temp/gnome-settings-daemon-mobile` 48.0-r6, all from the `48.mobile.0`
  tarballs. They were only rebuilt against GNOME 51 and are not rebased.
- The stable branches v25.06, v25.12 and v26.06 all ship 48.
- `postmarketos-ui-gnome-mobile` is labelled "(Experimental)" and depends
  on gdm.
- The wiki says to use 300 % scale; at 200 % the shell stays in desktop
  mode.

**Others:**

- **Fedora:** COPR `@mobility/gnome-mobile` builds the `mobile` heads as
  `51~beta.mobile.0` for rawhide (2026-08-14). There are no 50 builds.
- **GNOME OS:** branch `abderrahim/mobile-shell` pins the same 51.beta heads.
- **AUR:** `gnome-shell-mobile` / `mutter-mobile` /
  `gnome-settings-daemon-mobile` at 48.0 (2025-06-02), still with the old
  `verdre` URLs.
- **Mobian, openSUSE, Alpine, DanctNIX:** no packages found.

### Features against what this phone needs

| Need | GNOME Shell Mobile (50/51 branches) | Today (Phosh) |
|---|---|---|
| Lock with a PIN | `mobile-lockscreen`: numeric `PinUnlockKeyboard` + `PinEntryIndicator(6)` in `unlockDialog.js`, shown when `isPhone`. It auto-submits at exactly 6 digits and has no Enter key (keys 0-9, a keyboard toggle, clear). Any other length needs the full-keyboard toggle; a longer PIN fails at digit 6, and `pam_faillock` (3 failures) locks the account for 10 min. **Needs GDM** (below). | Phosh PIN pad, own PAM service `phosh`. |
| On-screen keyboard | gnome-shell's own OSK, heavily extended (mobile/number layouts, a swipe-down gesture to hide it, windows resize). Squeekboard cannot work: mutter has no `zwp_virtual_keyboard_v1` (mutter-mobile issue #1). | squeekboard |
| Home / app grid | Mobile app grid with folders, per-window workspaces, bottom bar | Phosh grid, adaptive filter |
| Gestures | Swipe up for the overview, horizontal app switch, swipe to close, pull-down quick settings | Phosh gestures |
| Rotation | mutter + iio-sensor-proxy (works with the existing SSC udev rules); on 50.x the !4962 fix is needed | Phosh/phoc |
| Notifications, quick settings | Mobile layouts, notifications on the lock screen | yes |
| Docking | One global `isPhone`: true when the primary monitor's logical size is under 500x1000 (`layout.js _checkIsPhone`). The external monitor as primary gives the desktop UI everywhere, including on the panel; the panel as primary gives the phone UI, and the external screen is a secondary GNOME monitor. Issue #63: menus and quick settings glitch onto the external screen. | Phosh docked mode (one phoc session), or GNOME desktop mode (separate session, apps close) |
| Different scale per output | Yes (mutter logical layout). The panel can't use 2.5: mutter (`meta-monitor.c`) accepts only n/d scales with d ≤ 4 that divide 1080x2448 exactly, with a logical area of at least 600x600 (the fork lowers it to 560x320). Valid: 1, 4/3, 3/2, 2, 9/4, 8/3 (+3, 4 on the fork). Phone mode needs 8/3 ≈ 2.667 (405x918 logical; in logical layout mode the St scale factor is 1, so `_checkIsPhone` compares the logical size) or 3 (360x816). The UI is 7 % larger than Phosh's 432x979; 2 and 9/4 stay in desktop mode | phoc scale 2.5 |
| Screen off and suspend | The shell's own `powerManager.js` (1179 lines): the power key blanks on a phone, a long press opens a power menu. It takes a `handle-power-key` inhibitor and does its own auto-brightness and proximity handling. The gsd fork disables gsd-power entirely. | Phosh blanks; `rog5-sleep-policy` suspends |
| Performance and memory | No published measurements. Shell issue #70: ~12.5 % idle CPU and battery drain on a OnePlus 6 (48.0); pmOS patch 0006 "keyboard: Avoid spinning idle source" fixes one cause | Phosh: measured idle churn fixed in 598189d9 |

## 2. Feasibility on this phone

### Building for GNOME 50: a trial merge

The trial merges below ran in scratch clones (blob-less clones of the fork
plus the upstream tags), and nothing was pushed:

- **mutter:** `mobile-shell-devel-50` (c99af8f4) and
  `camelCaseNick/mobile-shell-devel-50` (fe00ce86) both **merge 50.5
  cleanly**. The diff is 53-60 files, +3.5k/−0.7k lines (gestures, OSK and
  text-input, window state, "Lower minimum logical monitor size"). The
  camelCaseNick branch also carries Aliendalvik (Sailfish) hacks; they are
  inert here.
- **gnome-shell:** `mobile-shell-devel-50` (d95fe2ac) + 50.5 gives **5
  conflicts**: `js/gdm/authPrompt.js` (1 hunk), `js/ui/unlockDialog.js` (3
  hunks), `js/ui/messageList.js`, `js/ui/workspaceAnimation.js`
  (modify/delete) and `meson.build` (version).
  - The 50.4/50.5 commits in the lock path include "unlockDialog: Escape
    markup in notification titles", "Restrict markup in notification body",
    "Use `should-lock-session` property to block auth", "Wait for
    authPrompt destruction before switching VT" and "gdm/userVerifier:
    Disconnect from settings signals on destroy".
  - The mobile branch removed upstream's `NotificationsBox` from
    `unlockDialog.js` and shows lock-screen notifications its own way. The
    markup fixes therefore have to be ported by hand to the new code, not
    just merged.
  - The code-only diff of the branch is 89 files, +10.7k/−3.8k. It
    rewrites `screenShield.js` (761 lines changed), `unlockDialog.js` (819)
    and `authPrompt.js` (329). 20 commit subjects start with
    WIP/tmp/HACK/FIXME/"am"/"stuff".
  - The shell requires `mutter = 50.mobile.0` (meson `mutter_req`), so the
    two must be built as a pair.
- **For GNOME 51:** the `mobile` heads merged with 51.0 give 9 shell
  conflicts (again `unlockDialog.js`, plus `quickSettings.js`,
  `overviewControls.js`, `messageList.js`, `calendar.js`,
  `workspacesView.js`, `_login-lock.scss`, CI, meson) and 3 mutter
  conflicts (`window.c`, `meta-wayland-xdg-shell.c`, meson). The new
  maintainers plan to do this rebase upstream.
- **gnome-settings-daemon:** the fork is 2 commits on 50.1. One drops the
  power-button and auto-backlight handling; the other is "no gsd-power
  anymore" (literal `return;` in startup and D-Bus registration). It does
  not need a forked package: a drop-in on the user unit
  `org.gnome.SettingsDaemon.Power.service` with
  `ConditionEnvironment=!XDG_SESSION_DESKTOP=gnome-mobile` has the same
  effect for the mobile session only. Phosh and desktop GNOME keep
  gsd-power. The phone already has per-session drop-in directories (`gnome-session@phosh.target.d`), so a `gnome-session@gnome-mobile.target.d` drop-in is the other way. Check how gnome-session 50 starts gsd before relying on either.

Building on the phone is realistic (8 cores, native aarch64; Arch ARM ships
the build dependencies). mutter is the long build. qemu on the Deck would be
very slow.

### The lock screen needs GDM

gnome-shell unlocks through GDM. `js/gdm/util.js` (50.5) calls
`Gdm.Client.open_reauthentication_channel()`, a D-Bus call into the gdm
daemon. The unlock prompt runs with `reauthenticationOnly` (`authPrompt.js`
`UNLOCK_ONLY`), so the `get_user_verifier()` fallback in `util.js:519` is not
used for unlocking. Without the daemon the prompt shows "Authentication
error". This is why `rog5-gnome.service`
says "GNOME's own lock needs GDM" and the switcher hands back to Phosh to
lock.

GDM 50.3 handles a session it did not start: `gdm-manager.c`
`gdm_manager_handle_open_reauthentication_channel` opens a "temporary
reauthentication channel" when the caller is not GDM's login screen. So the
gdm daemon has to run, but the session need not come from GDM. Stock GDM
has no authentication-only mode, though: it always starts its local display
factory and a greeter on seat0 (`daemon/main.c`, `gdm-manager.c`), so in
practice GDM becomes the display manager. A `rog5-phosh`-style unit plus the
gdm daemon would need VT coordination or a GDM patch, and GNOME does not
start locked, so it would skip the PIN at boot.

`gdm` 50.3-1 is in Arch ARM `extra`, and `libgdm` is already installed as a
gnome-shell dependency. Arch's gdm depends on gnome-shell, which the mobile
package provides.

Proposed boot flow for the GNOME Mobile mode:

- GDM greeter without autologin: enter the PIN once at boot.
- The session picker offers "GNOME Mobile" and "Phosh".
- A login through GDM also unlocks the keyring with the PIN, which the
  no-DM boot never did.

Autologin followed by an immediate lock was considered and rejected: it
leaves an unlocked window during startup, which is the same class of bug the
desktop-mode switcher had to fail closed against (00986001, 9129e796).

### What changes in our stack

| Piece | Why it exists | With GNOME Shell Mobile |
|---|---|---|
| `packages/phoc` (0001 inert layer surfaces; embedded wlroots for the 0-height home surface) | phoc crashed on DP unplug | Not needed in the mobile session: mutter has no layer-shell. Kept for the Phosh fallback. |
| `packages/phosh` (0001 lock shields, 0002 LockedHint) | Phosh crashed on hotplug; the switcher needed the lock state in logind | Not needed in the mobile session: gnome-shell sets LockedHint itself (`screenShield.js _setLocked` → `SetLockedHintAsync`). Kept for the fallback. |
| `rog5-desktop-mode` switcher, `rog5-gnome.service`, polkit rule `60-rog5-desktop-mode`, "Desktop mode"/"Phone mode" launchers | Two compositors on one tty; only Phosh could lock | Gone in the mobile session; the shell's own lock is the gate. Kept unchanged for the Phosh fallback. |
| `rog5-phosh.service` (no DM, PAM `phosh`) | Boot straight to the Phosh lock screen | Replaced by `gdm.service` in mobile mode. Stays the fallback boot (see the selector below). |
| `rog5-gnome.service` ExecStartPre `rog5-kms-reset` | mutter after phoc kept a stale plane on the panel CRTC | Probably still needed once (boot splash/simplefb → GDM). Test, and keep it as a `gdm.service` drop-in if so. |
| `MUTTER_DEBUG_DISABLE_HW_CURSORS=1` (environment.d) | DPU underrun with the HW cursor, later traced to the DPU clock | Applies to the mobile session too; re-test with the HW cursor (costs GPU and adds lag) |
| `rog5-touchpad` (BindsTo `rog5-gnome`) | Panel as touchpad in desktop mode | Make it an explicit toggle, or trigger it on "DSI-1 disabled and DP connected" (udev drm event + sysfs `enabled`) |
| `rog5-sleep-policy` | Suspend on battery with the screen off | **Conflict.** It reads DRM sysfs and logind inhibitors, so that part is shell-agnostic. But the mobile `powerManager.js` lights the panel after every resume, including the policy's own wakes (details below the table). |
| `rog5-server-inhibit` (`sleep:handle-power-key` block) | Server workloads never sleep through logind | Unchanged. The shell's power-menu "Suspend" would hit it, and with it the polkit prompt seen in desktop mode. |
| squeekboard | OSK for Phosh | Not used in the mobile session; stays for Phosh |
| `rog5-wayvnc-phone`, `rog5-desktop --phone` (grim/wtype) | Remote mirror and automation via wlroots protocols | Do not work on mutter. Use `gnome-remote-desktop` (RDP; not installed) or accept no phone mirror in the mobile session. The headless sway desktop is independent and stays. |
| `rog5-session-boost` (uclamp for phoc, phosh, ...) | Keep session threads on big cores | Add `gnome-shell`; run after the mobile session too |
| dconf `00-rog5-phosh`, `rog5-mobile-apps` | Phosh defaults | Shared `org.gnome.*` keys stay. `sm.puri.*` keys don't apply. Phoc's scale-to-fit has no mutter equivalent, so non-adaptive apps are cut off on the panel. |
| Brightness (gsd) and auto-brightness (phosh) | — | The mobile shell has its own auto-brightness; gsd-power is off |
| Bootsplash (0107/0108 keep the logo until the first DRM master) | — | Expected to work with GDM's mutter; needs the visual check |

How `powerManager.js` conflicts with `rog5-sleep-policy`:

- **An external suspend is adopted.** On logind `PrepareForSleep(true)`
  the shell enters `suspend-forced`, upgrading a running `blank` or
  `idle-blank` (`pm50.js` 451-478, 685-694). A policy suspend is therefore
  handled as such; only an interrupted preparation reaches the `throw` in
  `_maybeCancelAction('suspend-wakeup')` (Sol, finding 3).
- **The screen lights on every wake.** On resume from `suspend-forced` the
  shell turns the screen back on unless the proximity sensor reports a
  pocket, and with no action in progress it turns it on too ("we were
  probably suspended via the kernel directly"). The policy's 15 s wake
  windows (network, timers) would light the panel on every cycle, which
  costs power and wakes the user.
- **The power-key replay is fine.** The shell ignores the power key for
  500 ms after resume; the policy waits about 2 s (uinput setup) before it
  replays, and it retries.
- **Fix:** keep `rog5-sleep-policy`, which owns external power, remote
  clients, audio, inhibitors and repeated suspends. Patch `powerManager.js`
  to keep the screen blank after a wake it did not cause, and to light it
  only on a user wake (power key or touch). Keep lock-before-suspend and
  the delay inhibitor. Letting the shell own suspend would mean
  re-implementing the policy's rules and the permanent server inhibitor.

### Risks

- **Lock security.**
  - The lock path is the most rewritten part of the fork.
  - On 50.x, the upstream fixes since 50.3 would need a hand port.
  - The fork's own commits include WIP and HACK.
  - A one-time review of the `screenShield.js`/`unlockDialog.js`/
    `authPrompt.js` diff is required before the phone relies on it, and
    again after every merge.
  - GDM adds a new privileged daemon and greeter on the phone.
- **Display regressions.**
  - GNOME has never driven the DSI panel on this phone: `monitors.xml`
    always has DSI-1 disabled, and every desktop-mode session turns the
    panel off.
  - The panel runs in command mode; phoc's atomic commits already hit
    `-EBUSY` 1-8 times per boot (`test-results/2026-09-27-display-gpu-investigation.md`).
  - Panel + DP at the same time under mutter (two CRTCs, GPU composition,
    DPU clock) is untested. It needs the same DPU checks as 0114/0139.
- **Power.**
  - Idle CPU of the mobile shell (issue #70) is unknown on this phone.
  - The OSK idle-source fix is only in pmOS's 48 patches; check whether
    the 51 branch has it.
- **Maintenance.**
  - `gnome-shell`, `mutter` (and `gdm` if needed) go into `IgnorePkg`.
    When Arch moves to GNOME 51, `pacman -Syu` with ignored core packages
    either holds the whole GNOME set or fails dependency checks, so
    `rog5-update` (unattended) would stall. Phosh/phoc already have this
    risk.
  - Every point release needs a merge, rebuild and lock smoke test.
  - Every major release depends on the fork's rebase. The record: one
    release in 18 months.
- **Fallback damage.** Replacing gnome-shell/mutter system-wide also changes
  the GNOME that Phosh's desktop mode runs (expected to behave as a desktop
  when DP is primary, but it must be tested), and phoc depends on `mutter`
  (schemas). A `/opt/gnome-mobile` prefix install avoids this, but needs a
  wrapper for `org.gnome.Shell@wayland.service` and its own typelib and
  schema paths; that is fiddly.

## 3. Packages: what is needed (not prepared yet)

Draft PKGBUILDs are **not** in `packages/`. The right base (50.5 + a hand
port, or 51.x) is not settled, and a 50 package would be outdated by the
GNOME 51 upgrade. When the go conditions hold, `packages/gnome-mobile/`
needs:

1. **`mutter-mobile`:**
   - Arch's `mutter` PKGBUILD for the matching version.
   - Source: `git+https://gitlab.gnome.org/World/MobileShell/mutter-mobile.git#commit=<sha>`
     merged with the Arch upstream tag in `prepare()`, or a pre-merged
     branch in our own fork.
   - `pkgname=mutter-mobile`, `provides=(mutter=<ver> libmutter-<api>.so)`,
     `conflicts=(mutter)`, `options=(debug)`.
   - The meson project version is `<major>.mobile.0`, which gnome-shell
     checks.
2. **`gnome-shell-mobile`:**
   - Arch's `gnome-shell` PKGBUILD; the source is the shell fork (same
     merge rule), plus `libgnome-volume-control` (submodule, as in Arch).
   - `provides=(gnome-shell=1:<ver>)`, `conflicts=(gnome-shell)`.
   - Local patches:
     - **0001** PIN length: no auto-submit, or a length from a GSettings
       key, plus an Enter key on `PinUnlockKeyboard`.
     - **0002** the hand port of the 50.4+ lock-screen fixes (only if
       built on 50.x).
     - pmOS's `0006-keyboard-Avoid-spinning-idle-source`, if not already in
       the branch.
3. **No gsd fork:** a user-unit drop-in disables gsd-power in the
   `gnome-mobile` session only (section 2).
4. **Session files:**
   - `/usr/share/wayland-sessions/gnome-mobile.desktop` with
     `DesktopNames=GNOME` and `XDG_SESSION_DESKTOP=gnome-mobile`.
   - A `gnome-mobile.session` for gnome-session.
   - Defaults: `chassis` is already `handset`. The panel scale 8/3 goes in
     `monitors.xml` (user and GDM greeter). dconf is not session-scoped, so
     settings that must differ from Phosh (`screen-keyboard-enabled`,
     `idle-delay`) need a session-start helper, like `rog5-gnome.service`'s
     ExecStartPre today, or a per-session default from the shell.
   - The fork's `org.gnome.Shell.SensorDaemon` (proximity and
     auto-brightness) needs its D-Bus activation file and must work with
     the SSC sensors through iio-sensor-proxy.
5. **`gdm`** from Arch (not rebuilt), with `/etc/gdm/custom.conf`: Wayland,
   no autologin.
6. **`rog5-shell-select`:** a boot-time selector, described below.

Build on the phone as `phone` (`makepkg -f --nocheck`), like phosh/phoc,
only with the user's OK.

## 4. Migration plan: Phosh stays the fallback

1. **Shell selector.** A mode file `/var/lib/rog5/shell` = `phosh`
   (default) | `gnome-mobile`, read by a oneshot unit before the display
   services:
   - `phosh`: today's boot, unchanged (`rog5-phosh` +
     `rog5-desktop-mode`; gdm not started).
   - `gnome-mobile`: start `gdm.service` instead; `rog5-desktop-mode` and
     `rog5-phosh` stay inactive.
   - **Automatic fallback (a root watchdog, armed before anything stops
     Phosh):** within 90 s the greeter or the user's shell must pass a
     readiness check, not just appear as a logind session:
     - the shell's D-Bus name is owned and answers a ping;
     - DSI-1 is `enabled`, with a `dpms` of On after the boot or after a
       power-key wake;
     - after an unlock, LockedHint changes yes → no.

     If the check fails, or gdm or gnome-shell crash-loops (3 restarts or
     core dumps in 5 min), the selector writes `phosh`, stops gdm, waits
     until DRM master is released and starts `rog5-phosh`. It then checks
     that Phosh comes up locked (LockedHint yes). This is the switcher's
     "never leave the phone without its lock screen" rule.
   - **Mutual exclusion:** `gdm.service` gets `Conflicts=` with
     `rog5-phosh`, `rog5-gnome` and `rog5-desktop-mode`, plus a mode gate
     (`ConditionPathExists`/`ExecCondition` on the mode file). The polkit
     rule and the launchers also refuse `rog5-phosh`/`rog5-gnome` while the
     mode is `gnome-mobile`. Today only Phosh and desktop GNOME exclude each
     other.
   - SSH (key-only) is never affected.
2. **Manual way back:** from SSH,
   `echo phosh > /var/lib/rog5/shell; systemctl stop gdm; systemctl start
   rog5-phosh rog5-desktop-mode`.
3. **Packages:** keep a complete, compatible rollback set of the stock
   `gnome-shell`, `mutter` (and anything rebuilt with them) in a separate
   directory, not just the pacman cache. Rehearse the `pacman -U` rollback
   once before the first real session. Phosh is not isolated from a
   replaced mutter/gnome-shell (shared schemas, user services, dconf), so
   the fallback must be retested on the mobile packages.
4. **Phosh from GDM's session picker** stays possible. It asks the PIN
   twice (GDM, then Phosh's own lock), and desktop mode is not available
   there; full desktop mode is only in the `phosh` mode.
5. **When the mobile session is the default and has passed the tests
   below:**
   - Retire the switcher, `rog5-gnome`, the polkit rule and the launchers
     from the default path.
   - Keep `packages/phoc`, `packages/phosh` and squeekboard for the
     fallback until a major GNOME upgrade has gone through cleanly once.

## 5. Staged test plan

Each stage needs the user's OK for its changes. Stages 0-1 do not touch the
user's session.

| Stage | What | Pass |
|---|---|---|
| 0 | Wait for go: Arch ARM GNOME 51 and a 51.x mobile branch (shell #84/#85). Then build on the phone (OK needed) and keep the stock packages in the cache. | Packages build; `pacman -Qkk` clean |
| 1 | Headless, no DRM: as `phone`, on a private D-Bus, `gnome-shell --headless --virtual-monitor 1080x2448` with a scale of 8/3 (installed to a DESTDIR or `/opt`, so the system GNOME is untouched); screenshots through mutter's ScreenCast D-Bus API (PipeWire) or a test-only extension (the Screenshot API is restricted outside unsafe mode). | `isPhone` true, app grid, quick settings, OSK and the PIN pad render; idle CPU < 1 % for 10 min |
| 2 | Lock review: one Sol review of the `screenShield`/`unlockDialog`/`authPrompt` diff (and of any hand port) before any real session. This is necessary but not enough; stages 3a and 6 test the behaviour. | No open security finding |
| 3 | Supervised real session (user present): stop `rog5-desktop-mode` + `rog5-phosh`, start `gdm`, with a `systemd-run --on-active=15min` revert to Phosh unless `/run/rog5-keep-gnome-mobile` exists. Panel only. | Panel lights at 8/3; touch maps to DSI-1; rotation; OSK; lock on power key; PIN unlock (and 3 wrong PINs → faillock message, not a lockout from auto-submit); `LockedHint` follows the lock |
| 3a | Lock behaviour (supervised, with a second account or root SSH ready to clear faillock with `faillock --reset`). Lock and unlock while gdm is stopped or restarted. Lock, unlock, suspend and hotplug in quick succession. Cancel a prompt, and try a stale one. Try keyboard shortcuts and gestures (overview, quick settings, OSK, notifications) on the lock screen. Check notification markup. Test short, 6-digit and long PINs. | No app frame is visible and no app gets input on either output while locked; gdm down → unlock fails closed (stays locked); PIN pad and faillock behave as documented |
| 4 | Power: on battery, screen off with `rog5-sleep-policy`; power-key wake; a 30 min standby | No `POWERMANAGER` exceptions in the journal; the panel stays dark during policy wakes; the power key always lights it; standby current within 5 mA of the Phosh baseline (~79 mA) |
| 5 | Docking with apps open: plug the MSI, make DP primary (panel on, then off), unplug, 5 cycles; then at 5120x1440@60 and 3840x1080@100 | Apps survive every cycle; the shell flips between desktop and phone UI; no gnome-shell core dump; no DPU underrun (`dmesg`), lock screen on both outputs while locked |
| 6 | Boot path: selector set to `gnome-mobile`, reboot with and without the monitor; then break gdm on purpose (a masked drop-in), and once hang gnome-shell (SIGSTOP) | GDM greeter appears (PIN, then session); the broken and the hung case fall back to a locked Phosh within 90 s |
| 7 | A week of daily use as an opt-in mode, then decide the default | The user's call |

## Alternative: Phosh docked mode (cheap)

The user's actual complaint (irritation 2) is that apps close when docking.
One phoc session with DP as a second output already keeps them:

- Phosh 0.57's docked manager turns off auto-maximise and the OSK when a
  keyboard and pointer are attached.
- phoc and phosh implement `org.gnome.Mutter.DisplayConfig`, so GNOME
  Settings can arrange the outputs.

The costs:

- The desktop is Phosh's mobile shell on the big screen, with no GNOME
  overview, top bar or extensions.
- `phoc.ini` pins the DP mode, which would have to go.
- The DP plug/unplug path is exactly where phoc/phosh crashed before
  (fixed, stress test pending: whats-left test 3).

A one-hour supervised test (monitor attached, Phosh unlocked, docked mode on,
open apps, move a window to DP, unplug and replug) would show whether this
is good enough for now. It needs no new packages, only a manual mode where
the switcher does not start GNOME (`/var/lib/rog5/desktop-mode` = `manual`,
as today).

## Second opinion (GPT-6.1-Sol, read-only)

Full text: [2026-10-01-gpt-6.1-sol-gnome-mobile.md](2026-10-01-gpt-6.1-sol-gnome-mobile.md).
Sol agrees with "not yet" and with trying Phosh docked mode first. What
changed in this document after the review:

| # | Finding | Disposition |
|---|---|---|
| 1 (high) | The `get_user_verifier()` fallback is not used for unlocking (reauthentication only) | Fixed in "The lock screen needs GDM" |
| 2 (medium) | Stock GDM has no daemon-only mode; greeter without autologin is the better choice | Agreed; added |
| 3 (high) | An external suspend is adopted as `suspend-forced`; the "throws" claim was wrong. The wake-lights-screen conflict stands | Rewritten |
| 4 (medium) | Keep `rog5-sleep-policy` and patch the shell's wake handling; the power-key replay is fine | Adopted as the fix |
| 5 (medium) | 72/29 is not a valid mutter scale; use 8/3 (405x918) | Fixed. This had already been corrected from mutter's `meta-monitor.c` before the review came back. |
| 6 (high) | The selector needs real readiness checks, a watchdog armed before Phosh stops, and mutual exclusion of every display unit | Added to section 4 |
| 7 (high) | Lock testing must cover gdm down, races, escape attempts, markup, PIN lengths and faillock recovery | Stage 3a added |
| 8 (medium) | A tested rollback package set; dconf is not session-scoped; SensorDaemon; the greeter's display config | Added to sections 3 and 4 |
| 9 (low) | A 51.x branch should start an evaluation, not acceptance | Agreed (the go conditions only start stage 0) |

## Sources

- Fork: https://gitlab.gnome.org/World/MobileShell/gnome-shell-mobile,
  https://gitlab.gnome.org/World/MobileShell/mutter-mobile,
  https://gitlab.gnome.org/World/MobileShell/gnome-settings-daemon-mobile.
  These are the branch heads in the table, read on 2026-10-01; issues #63,
  #70, #72, #84, #85; mutter-mobile #1.
- Upstream NEWS of gnome-shell and mutter (tags 50.5 and 51.0); upstream
  50.5 sources: `js/gdm/util.js`, `js/ui/screenShield.js`,
  `js/ui/sessionMode.js`, mutter `meta-seat-impl.c`,
  `meta-monitor-manager.c`, `meta-monitor.c`; GDM 50.3
  `daemon/gdm-manager.c`.
- GUADEC 2026 mobile BoF notes: https://pad.gnome.org/6KLdColfQz-2LHVoV32mzQ;
  event https://events.gnome.org/event/306/contributions/1725/.
- C. Garnacho, "On mobile and peer pressure", 2026-09-15:
  https://blogs.gnome.org/carlosg/2026/09/15/on-mobile-and-peer-pressure/.
- pmaports `main` 710e4b87 (`temp/gnome-shell-mobile`, `temp/mutter-mobile`,
  `temp/gnome-settings-daemon-mobile`, `postmarketos-ui-gnome-mobile`);
  wiki "GNOME Mobile" (https://wiki.nura.eco), edited 2026-09-27; rename
  post https://nura.eco/blog/2026/09/27/nura-rename/.
- Fedora COPR https://copr.fedorainfracloud.org/coprs/g/mobility/gnome-mobile/.
- Arch package search (gnome-shell/mutter 51.0 in `gnome-unstable`
  since 2026-09-15); the phone's sync DB (50.5 in `extra`, gdm 50.3).
- Phosh docked mode: `src/docked-manager.c` at tag v0.57.0.
- Second opinion: [2026-10-01-gpt-6.1-sol-gnome-mobile.md](2026-10-01-gpt-6.1-sol-gnome-mobile.md).
