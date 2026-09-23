# ROG Phone 5 native Linux — Claude Code guide

Native Arch Linux ARM on the ASUS ROG Phone 5 (SM8350). The accepted headless
server boots from local storage through slot B. ASUS WW33 slot A is the
charging/rescue route. Claude Code has been the only coordinator since
2026-09-23. Codex/ChatGPT is retired; see `docs/history/codex-era.md`.

## Goal

Boot the production kernel `7.1.4-rog5-production` on the phone with a coherent
ramdisk, then run one bounded display/GPU (OLED + Adreno 660) trial on it.
Kernel and non-cellular hardware bring-up come before any further Denial/Flutter
or VM UI work.

1. Shared `mdt_loader` ownership (the power stage loads it before PAS; the
   display loader verifies it). WIP: `~/.local/state/rog5-shared-mdt-20260923-r1/`.
2. Verifier profile for production modules (no BTF, 0x4c0 module struct). Check
   against the real config (`CONFIG_DEBUG_INFO_NONE=y`, no MODVERSIONS); don't
   just relax the old check.
3. Bootable unsigned trial ramdisk and boot image from the 64-module production
   tree (`module-root-complete.tar.gz`, `bed63b7b…`). Load modules with
   `modprobe` over a depmod-generated `modules.dep`, as postmarketOS mkinitfs
   does, instead of hand-ordered `insmod` lists. Pin exact bytes once, at
   archive build time.
4. Focused offline tests on the frozen source, including the target busybox
   under qemu.
5. Phone on USB → read-only health → fresh Ready → one headless boot → the
   display/GPU experiment.

Status of each step goes in the generated block of `docs/current-state.md`, not here.

## Orientation (cheap reads only)

- `git status --short`, `git rev-parse HEAD`, then `sed -n 1,8p docs/current-state.md`.
  The rest of that file is a 300 KB historical log; grep it, never load it whole.
- Newest `test-results/2026-09-*.md` and `manifests/current-artifact.json`.
- `grep -n` `docs/development-lessons.md` for the specific issue only.
- Private evidence lives in `~/.local/state/rog5-*`. List it shallowly and never
  `grep -r` across it (hundreds of GB). Registered worktrees: `git worktree list`.
- Phone presence (host-only, read-only): `lsusb | grep -i 0b05`.
- External references (pmOS pdx215, sm8350-mainline OnePlus DT, old i005d DTS):
  see the Claude memory `sm8350-references`.

## Development loop

- Use `scripts/host/rog5-dev` and `docs/development.md`. The project skill
  `rog5-fast-loop` covers kernel/module/DTB/initramfs/boot-chain changes.
  `systematic-debugging` is for repeated or cross-component unknown failures.
- Choose the smallest artifact that answers the question. Freeze source before
  expensive builds/CI. Never repeat a completed check on unchanged inputs.
  Unneeded full kernel builds have cost about 45 min; incremental builds take seconds to minutes.
- Unit suites are standalone (`python3 scripts/device/test-<name>.py`, mostly
  under 10 s). `rog5-dev test active` (about 750 s) runs once on frozen source,
  not per edit. `rog5-dev select BASE HEAD` picks the tier.
- Target shell code must run under the real ARM64 busybox. Extract `bin/busybox`
  and `lib/ld-musl-aarch64.so.1` from the target archive into scratch, then
  `QEMU_LD_PREFIX=<dir> ROG5_TEST_QEMU=/usr/bin/qemu-aarch64-static ROG5_TEST_BUSYBOX=<dir>/bin/busybox python3 <test>`.
- Controller sources are hash-pinned in a chain. Before editing a pinned file,
  find its consumers with `git grep -l $(git show HEAD:<file> | sha256sum | cut -c1-64)`.
  Pins live in sources (`display-component.py` `SOURCE_PINS`), fixtures
  (`scripts/device/fixtures/*/source-pins.json`) and controller patches
  (`patches/display-controller/*.patch`, which are themselves pinned downstream).
  Dated `test-results/` are history: never rewrite them. Re-pin forward, then
  rerun every consumer suite and compare against a clean `git worktree` of HEAD.
- A hardware trial must answer one question that offline tests cannot. VM or
  host results are never phone evidence. Don't merge results across kernels or releases.
- Use bounded subagents for independent research or inventories only. One
  coordinator (this session) owns integration and all phone access.

## Records

After each run: a compact result in the generated block of `current-state.md`,
one dated `test-results/` report, and reusable lessons only in
`development-lessons.md`. Before ending a work session, review repeated failures,
slow stages and unnecessary work against the goal. Apply a scoped improvement
when the results justify it. Don't let process work replace phone progress.

## Human-assisted hardware tests

Prepare everything first: builds, focused checks, review, artifact staging,
device health and actual input/output discovery. Ask for Ready only when a
reviewed session is fully prepared. Don't start any operator countdown without
a fresh Ready. An old or expired reply never counts. On Ready, start immediately.
Only brief current-state guards and runtime arming come after it: no compiling
or debugging. Give one short physical action at a time at the reader's actual
READY and collect events automatically. Never require terminal typing. If a
prerequisite fails, release the user, fix it, and ask again only when ready.

## Safety (non-negotiable)

- Preserve official WW33 slot A (charging/rescue), accepted baseline images,
  signing material, protected storage, unique firmware/backups and raw evidence.
- Keep exact device identity/USB topology checks, signature, storage, power and
  thermal, fallback and post-COMMIT one-use guards. Never replay a consumed
  claim or experiment. Never broaden device discovery to bypass an identity check.
- Destructive storage operations need their own reviewed authorization.
  Packaging never grants boot authority.
- `.claude/settings.json` denies direct fastboot/adb/dd-to-device commands.
  Physical actions go only through the reviewed controllers.
- Check actual free space before large copies (keep a 3 GiB reserve). Don't
  reboot the Deck to simplify setup.
