# phoc for the ROG Phone 5

Arch's phoc 0.57.0 packaging rebuilt with phoc's embedded, patched wlroots
(see the PKGBUILD header: stock wlroots 0.20 rejects Phosh's 0-height home
layer surface), plus ROG5 patches:

- 0001 (1.2): the get_alpha/draggable/stacked_layer_surface handlers hand out
  an inert surface when the layer surface was already destroyed (its output
  went away) instead of dereferencing NULL. Phosh requests an alpha surface
  right after DP-1 turns off; phoc crashed at phoc+0x4446c twice (2026-09-29
  12:40, 2026-09-30 00:27), ending the session. The requests and destroy paths
  of those objects already handle `layer_surface == NULL`.

Build on the phone as the desktop user and install:

    makepkg -f --nocheck
    sudo pacman -U phoc-0.57.0-1.2-aarch64.pkg.tar.xz

`/etc/pacman.conf` has `phoc` in `IgnorePkg`.
