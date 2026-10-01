# GNOME Shell Mobile: host build, headless smoke test, phone read-only checks

Date: 2026-10-01. Branch `agent/gnome-mobile-261001`. Not run on the phone's
display; the phone was only read (SSH, no package or session change).

## Build (host, aarch64 under qemu-user)

The rehearsal's aarch64 Arch root (copied to
`~/.local/state/rog5-gnome-mobile-build/root`, then `pacman -Syu`;
mutter/gnome-shell still 50.5-1 in Arch ARM), `makepkg -f --nocheck` of
`packages/gnome-mobile/{mutter-mobile,gnome-shell-mobile}` (8 threads,
qemu-aarch64-static):

| Package | Build time | Result |
|---|---|---|
| mutter-mobile 50.5-1 | ~50 min of compile (674 ninja steps; the official fork head failed in clutter, base moved to camelCaseNick's branch, tree then resumed incrementally) | built |
| gnome-shell-mobile 50.5-1 | 12-18 min | built (all 11 patches) |

Both build trees were checked against the committed patch series: the
gnome-shell source tree hash equals the series' tree; mutter's differs only
by the empty `subprojects/.wraplock` meson writes. Packages and SHA256SUMS:
`~/.local/state/rog5-gnome-mobile-build/packages/` (private):

    d0e9d9fd3b010da6c6def551342ad791e18bd4c046e166b3568a6d02fc967c19  mutter-mobile-50.5-1-aarch64.pkg.tar.xz
    02cdbb006650fb08ea8119f7dbf21059647159d97f7961527ccec15b2bbedbd2  mutter-mobile-debug-50.5-1-aarch64.pkg.tar.xz
    28c97cd8cddcb680c7394ad1ef402f2bd7389008d46776a09df3cfe89b739e30  gnome-shell-mobile-50.5-1-aarch64.pkg.tar.xz
    7e7d6dbbd1315f76d0c5a2e78c2985711b63051e58ef7598b11923088dca1dad  gnome-shell-mobile-debug-50.5-1-aarch64.pkg.tar.xz

Estimate on the phone (native, 8 cores): a small fraction of the qemu time,
roughly 10-20 min for mutter and 5 min for gnome-shell.

## Headless smoke test (host chroot, llvmpipe)

`gnome-shell --headless --unsafe-mode --virtual-monitor 405x918 --mode=user`
(405x918 = the panel at scale 8/3) on a private session bus, a system bus
without logind/GDM, as an unprivileged user
(`~/.local/state/rog5-gnome-mobile-build/headless.sh`):

| Check | Result |
|---|---|
| Starts on mutter `50.mobile.0` | PASS |
| `Main.layoutManager.isPhone` | `true` |
| `Main.powerManager` loaded | `true` |
| Home, quick settings | mobile layouts render (screenshots) |
| `screenShield.lock(false)` | `locked,active,unlock-dialog` |
| PIN pad | 6 dots, digits, keyboard toggle, delete; no Emergency button (patch 0005: `visible=false`) |
| Unlock without GDM | "Authentication error" (reauthentication channel refused): fails closed, as expected |
| JS errors during use | none; one at shutdown (`popModal: incorrect pop` while tearing down the unlock dialog) |

Not covered: OSK (headless has no touch device; `Main.keyboard.open()`
showed nothing), real DRM/DSI, input, GDM, suspend. Without GDM the shell
retries the reauthentication channel every ~2 s while the PIN pad is up.

## Phone read-only checks (k112, main-k112-d13-261001a, over Wi-Fi)

- `mutter 50.5-1`, `gnome-shell 1:50.5-1`; `gdm` not installed, repository
  has `gdm 50.3-1`; `gnome-remote-desktop`, `pacman-contrib` not installed.
- The stock mutter/gnome-shell package files are **not** in
  `/var/cache/pacman/pkg`; the repository still has exactly 50.5-1, so the
  installer's rollback set is downloaded with `pacman -Sw`.
- `/proc/interrupts`: `189: pmic_arb 1302618 Edge pmic_pwrkey` (the format
  patch 0008 parses); `/sys/power/pm_wakeup_irq` readable (no data before
  the first suspend of this boot: 0008 then keeps the upstream behaviour).
- `card1-DSI-1` enabled/dpms present; touchscreen `ASUS ROG5 MP2 front
  FTS3658U` (event1), `pmic_pwrkey` (event3).
- seat0 active session = Phosh on tty7 (Service phosh); `phone`'s
  `monitors.xml` has DSI-1 as `unknown/unknown/unknown` (disabled in the
  desktop-mode configurations).
- `setpriv`, `busctl`, `python3` present; `/etc/rog5` exists; `IgnorePkg =
  phoc resources phosh gtk2 vulkan-freedreno`; 39 GB free on `/`.
