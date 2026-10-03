# Eden (Nintendo Switch emulator) for the ROG5

**Installed: the upstream nightly aarch64 PGO AppImage, not this PKGBUILD.**
Nightly Oct 02 2026 (commit d16735f5b6, `Eden-Linux-d16735f5b6-aarch64-clang-pgo.AppImage`,
SHA-1 79ee68a2f0704f4c133963d206de42dd93493b54 matching its zsync file,
SHA-256 dcb3f072860ebda93262712bb971e24c09964d3e666aa060307d0a27f6a81007).
It is unpacked (`--appimage-extract`, no FUSE needed) to
`/opt/eden-nightly-d16735f5b6`, with `/opt/eden` -> that directory,
`/usr/local/bin/eden` -> `/opt/eden/AppRun` and a menu entry in
`/usr/local/share/applications/dev.eden_emu.eden.desktop`. The download is kept
in `/var/cache/rog5-eden`.

Why not a native build: the emulated CPU runs as JIT- or natively executed
code that compiler flags do not touch, `-mcpu=cortex-x1` gains a few percent
at most on the rest, and the upstream PGO build is 10-30 % faster than a
standard build, which a local build cannot match without a profiling run.

Notes:
- The AppImage bundles its own Mesa 26.2.3 (Turnip without our 8-bit storage
  patch, which Eden does not need) and forces X11/Xwayland
  (`05-wayland-is-broken.hook`; `I_WANT_A_BROKEN_WAYLAND_UI=1` overrides).
  It started fine in GNOME desktop mode; Phosh has no Xwayland by default.
- Update: download a newer nightly, unpack next to the old one, repoint `/opt/eden`.
- Games, keys and firmware are the user's own; none are part of this.

The PKGBUILD here (AUR eden 0.2.1-3, cubeb dropped from depends because Arch
Linux ARM lacks it) remains for a source build if ever needed.
