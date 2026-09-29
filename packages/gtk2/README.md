# gtk2 for the ROG Phone 5 (native aarch64 Steam)

Valve's aarch64 Steam client loads `steamui.so`, which links
`libgtk-x11-2.0.so.0`. Arch Linux ARM no longer ships GTK 2 (it moved to the
AUR), and the runtime Steam downloads carries only x86 copies, so the client
stopped with "Failed to load steamui.so" until this was installed.

`PKGBUILD` is the AUR/Arch `gtk2` 2.24.33-5 packaging (heftig, jgc) with:

- `aarch64` added to `arch`, `pkgrel=5.1`;
- the GNOME release tarball instead of a git clone of the whole GTK
  repository (sha256 `ac2ac757…6cc6da` from download.gnome.org's
  `gtk+-2.24.33.sha256sum`, pinned here as b2sum); the two Arch patches are
  applied with `patch` instead of `git apply`.

Build and install on the phone (about 5 minutes; needs `gtk-doc` for
`autoreconf`):

    sudo pacman -S --needed --asdeps gtk-doc
    makepkg -f --nocheck
    sudo pacman -U gtk2-2.24.33-5.1-aarch64.pkg.tar.xz

`/etc/pacman.conf` has `gtk2` in `IgnorePkg`. Steam also needs `lsof`
(`GetIPCConnectionDetails`), from the normal repository.
