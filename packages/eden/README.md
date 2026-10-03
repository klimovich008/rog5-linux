# Eden (Nintendo Switch emulator) for the ROG5

**In use: stable v0.2.1 aarch64 PGO AppImage** (`/opt/eden` -> `/opt/eden-v0.2.1`), pinned to
CPUs 4-7. The nightly below crashes BotW at boot on this phone even pinned (3 more
SIGTRAPs 04:08-04:10); stable v0.2.1 pinned ran BotW 60 s with 361 pipelines and no
asserts. Both are upstream PGO AppImages, not this PKGBUILD.

Nightly (kept in `/opt/eden-nightly-d16735f5b6`):
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

Launch pinned to the big cores: the menu entry runs `taskset -c 4-7 /opt/eden/AppRun %f`
and `/usr/local/bin/eden` does the same. Unpinned, BotW traps at boot (fatal
emulated-scheduler asserts `GetDisableDispatchCount`, also `dynarmic !is_executing`)
in every mode tried (NCE and Dynarmic, PGO and standard, bundled and system
Turnip, with and without DLC; single-core hangs at the same point). Pinned to
CPUs 4-7 (Cortex-A78 x3, X1) it gets past that point with no asserts.
Stable v0.2.1 is unpacked in `/opt/eden-v0.2.1` as a fallback.

Notes:
- The AppImage bundles its own Mesa 26.2.3 (Turnip without our 8-bit storage
  patch, which Eden does not need) and forces X11/Xwayland
  (`05-wayland-is-broken.hook`; `I_WANT_A_BROKEN_WAYLAND_UI=1` overrides).
  It started fine in GNOME desktop mode; Phosh has no Xwayland by default.
- Update: download a newer nightly, unpack next to the old one, repoint `/opt/eden`.
- Games, keys and firmware are the user's own; none are part of this.

The PKGBUILD here (AUR eden 0.2.1-3, cubeb dropped from depends because Arch
Linux ARM lacks it) remains for a source build if ever needed.
