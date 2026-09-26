# phoc with phoc's embedded, patched wlroots

Arch's phoc 0.57.0-1 is built with `-D embed-wlroots=disabled` against the
stock `wlroots0.20`. Phoc's wlroots wrap carries
`0001-Revert-layer-shell-error-on-0-dimension-without-anch.patch` because phosh
maps its "phosh home" layer surface with height 0, anchored only
bottom|left|right. Stock wlroots rejects that with "height 0 requested without
setting top and bottom anchors". Phosh then dies with Wayland error 71 right
after "Phosh ready", and the session ends.

This PKGBUILD is Arch's with only the build options changed. It builds natively
on the phone in about two minutes:

    # as root: pacman -S --needed --asdeps base-devel meson ninja glib2-devel
    install -d -o phone /home/phone/build/phoc && cp PKGBUILD /home/phone/build/phoc/
    cd /home/phone/build/phoc && runuser -u phone -- makepkg -f --noconfirm
    pacman -U phoc-0.57.0-1.1-aarch64.pkg.tar.xz

`/etc/pacman.conf` on the phone has `IgnorePkg = phoc`, so unattended updates
don't bring back the unpatched build. When Arch ships a new phoc (or phosh
starts requiring a newer one), bump `pkgver`, check that the wrap still
carries the revert (`prepare()` fails if it doesn't), and rebuild.
