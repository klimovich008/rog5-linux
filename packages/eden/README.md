# Eden (Nintendo Switch emulator) for the ROG5

**In use since 2026-10-03 07:50: `eden 0.2.1-3.5`, built natively on the phone from
this PKGBUILD** (-O3, `armv8.2-a+crypto+crc+lse+rcpc+fp16+dotprod`, `-mtune=cortex-x1`,
LTO, `-g1` kept for crash reports, no libstdc++ assertions, Qt WebEngine off) with two
Eden fixes: `0001-nce-refresh-host-thread-id.patch` and
`0002-kernel-tls-accessors-out-of-line.patch`. Settings: v-sync Mailbox
(`use_vsync=1`; FIFO stalls on Phosh). Packages kept in `/var/cache/rog5-eden/pkgs`
(also the working -O2 debug build `eden-dbg 0.2.1-3.1` as fallback).

BotW 1.6.0, unattended 5-minute run (virtual keyboard: title, New Game, intro,
shrine, walking; Mesa overlay frame log; first minute excluded; 30 fps game cap):

| Build | avg fps | median | 1% low | time <25 fps | time <20 fps | temp |
|---|---|---|---|---|---|---|
| -O2 debug (eden-dbg 3.1) | 24.6 | 23.2 | 17.4 | 58% | 9% | 47->78 C |
| -O3+LTO+tuning+fixes (3.5) | 26.2 | 28.5 | 20.0 | 41% | 3% | 48->73 C |

Without the two fixes every -O3/LTO build (ours and the upstream clang PGO AppImages)
crashed BotW at boot. Screenshots at 80 s show the "Wake up, Link." intro.

History:

**In use (2026-10-03 05:00): a native build of v0.2.1 from this PKGBUILD**
(`eden-dbg 0.2.1-3.1`: gcc -O2 -g1, not stripped, no LTO, Qt WebEngine off),
started as `eden` from the system menu entry, with **v-sync = Mailbox**
(`use_vsync=1` in `~/.config/eden/qt-config.ini`).

Why: the upstream AppImages (stable v0.2.1 and nightly d16735f5b6, PGO and
standard) crash BotW at boot on this phone in every configuration, also on
Wayland (SIGTRAP/SIGSEGV after NS GetApplicationDesiredLanguage; emulated
scheduler asserts). The native build against the system glibc/libstdc++/Boost
never crashed (5 runs). Its remaining problem was a stall with FIFO v-sync on
Phosh: the GPU thread waited forever in Turnip's Wayland WSI
(`wl_display_dispatch_queue`). With Mailbox v-sync BotW ran 95 s, game running,
438 pipelines, no asserts. The AppImage crash therefore comes with its bundled
runtime (sharun loader/glibc/Boost), which NCE's TLS/signal handling meets.
Analyses by GPT-6.1-Sol and GPT-6-Astra: `~/.local/state/rog5-eden-src/report-*.md`.

Earlier (superseded): stable v0.2.1 aarch64 PGO AppImage** (`/opt/eden` -> `/opt/eden-v0.2.1`), pinned to
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

## Crash root cause (2026-10-03 06:40) and patch

A -O3+LTO build with symbols (`-g1`) trapped in `Core::ArmNce::ReturnToRunCodeByExceptionLevelChange`
at `brk #1000`, right after `svc #0` with x8=130 (`tkill`) and x1=12 (SIGUSR2), called from
`ArmNce::RunThread` (arm_nce.cpp:231) on `CPUCore_2`. NCE enters guest code by sending
SIGUSR2 to `m_thread_id`, which `ArmNce::Initialize` caches only on the first call; when
that core's guest work later runs on another host thread, the signal goes to the old
thread, tkill returns and execution reaches the brk. The signal stack is likewise set up
only for the first thread. `0001-nce-refresh-host-thread-id.patch` refreshes the id on
every `Initialize` (called before each RunThread) and keeps one sigaltstack per host
thread. -O2 builds happened not to trigger it in our runs; -O3/LTO builds and the
upstream AppImages (clang -O3+LTO+PGO) did, every time.

Round 2 (07:30): with 0001 alone the brk #1000 was gone, but the game then aborted
(svcBreak 0xE401) and NCE's fault fallback called the null previous SIGSEGV handler
(PC 0). The underlying fault: `KernelCore::CurrentPhysicalCoreIndex`,
`GetCurrentHostThreadID`, `Get/SetCurrentEmuThread` read `Impl::tls_data`
(`thread_local`); inlined by LTO into scheduler/CPU-manager code, the thread-local
address of the previous host thread is reused after `Fiber::YieldTo` resumes on
another host thread. `0002-kernel-tls-accessors-out-of-line.patch` marks them
`[[gnu::noinline]]`. Testing pkgrel 3.5 (-O3 LTO + 0001 + 0002).
