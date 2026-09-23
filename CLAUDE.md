# ROG Phone 5 native Linux — Claude Code guide

Native Arch Linux ARM on the ASUS ROG Phone 5 (SM8350). The accepted headless
server boots from local storage through slot B. ASUS WW33 slot A is the
charging/rescue route. Claude Code has been the only coordinator since
2026-09-23. Codex/ChatGPT is retired; see `docs/history/codex-era.md`.

## Goal

Set 2026-09-23 after the display/GPU goal passed: **fast, safe module
iteration on the phone and a kernel base that is easy to upgrade.** Kernel and
non-cellular hardware work still come before Denial/Flutter or VM UI work.

1. Fast module loop: `rog5-dev module build|deliver`, build-ID-checked and RAM
   only. Done: about 15 s from edit to tested module.
2. Module package reproducible in the repo (`package-production-modules.py`). Done.
3. Signed-tag upgrade tooling (`rebase-kernel-series.py`). Done.
4. Production moves to stable 7.2.7: build, module package, ramdisk, then a
   RAM trial with headless and display/GPU regression. In progress.
5. Fold side patches into the series. The ath11k WCN6851 hw1.1 patch becomes 0044.
6. Build speed: trim the defconfig base (6810 objects, about 50 min at -j6) to
   what SM8350 needs, proven by a phone regression trial.
7. Self-recovery for unattended updates: ramoops, a watchdog kept armed across
   kexec, and the RTC time.
8. Production as the phone's default kernel (selector try-once plus fallback).
   **Needs explicit user approval**, because it writes boot storage.

Status of each step goes in the generated block of `docs/current-state.md`, not here.

## Where things live (don't break these)

- This checkout is a git worktree. Its git dir is
  `~/.local/state/rog5-haven-clean-ci-20260810/.git`, which borrows objects from
  `~/Projects/rog-phone-linux-migration/repo/.git/objects` (alternates). Never
  delete or move either directory. About 600 commits are not on GitHub. Backup
  bundle of all refs: `~/rog5-git-backup/rog5-all-refs-20260923.bundle`.
- Boot chain: slot A is stock ASUS (rescue/charging). boot_b holds a 96 MiB ASUS 5.4
  wrapper whose recovery initramfs mounts p24 `arch_root_a`, reads
  `/boot/rog5-linux/selector`, verifies an Ed25519-signed inner bundle (Image, DTB,
  initramfs, manifest) and kexecs it. The root is p24 (ro lower) with an overlay
  on `userdata:/rog5/root/root-overlay-v1.ext4`. Trials RAM-boot a 128 MiB wrapper
  that embeds the signed bundle via `fastboot boot` (no flashing). The signing
  key stays outside Git.
- Observation: SSH over USB NCM 10.77.0.2 (host 10.77.0.1), early progress on USB
  ACM `/dev/ttyGS0`, and TCP stage records (busybox nc) to 169.254.77.1:8079, which
  `production-ram-trial.py boot --stage-receiver` collects without root. There's no pstore
  yet, so a hard hang needs a manual forced reboot.
- Detailed map: `~/.local/state/rog5-wf-scratch-20260923/BOOT-CHAIN.md`.

## Orientation (cheap reads only)

- `git status --short`, `git rev-parse HEAD`, then `sed -n 1,8p docs/current-state.md`.
  The rest of that file is a 300 KB historical log; grep it, never load it whole.
- Newest `test-results/2026-09-*.md` and `manifests/current-artifact.json`.
- `grep -n` `docs/development-lessons.md` for the specific issue only.
- Private evidence lives in `~/.local/state/rog5-*`. List it shallowly and never
  `grep -r` across it (hundreds of GB). Registered worktrees: `git worktree list`.
- Phone presence (host-only, read-only): `cat /sys/bus/usb/devices/1-1.2/{idVendor,idProduct,product}`.
  Linux reports `1d6b 0104 "ROG5 persistent root"`; fastboot reports `0b05 4daf`;
  `05c6 900e` is the Qualcomm crashdump screen. `lsusb | grep 0b05` cannot see
  Linux. Host NCM interface: `enp4s0f3u1u2` with 10.77.0.1/30. Any ordinary
  reboot lands on V11: userdata still holds a GPU-trial record the selector
  doesn't recognise. Manual rescue runbook: docs/development.md.
- External references (pmOS pdx215, sm8350-mainline OnePlus DT, old i005d DTS):
  see the Claude memory `sm8350-references`.

## Development loop

- Module changes: `rog5-dev module build|deliver` builds a module directory against the running
  kernel's objects and loads it on the phone after a build-ID check (seconds, RAM only). See
  "Fast module loop" in `docs/development.md`.
- Use `scripts/host/rog5-dev` and `docs/development.md`. The project skill
  `rog5-fast-loop` covers kernel/module/DTB/initramfs/boot-chain changes.
  `systematic-debugging` is for repeated or cross-component unknown failures.
- Choose the smallest artifact that answers the question. Freeze source before
  expensive builds/CI. Never repeat a completed check on unchanged inputs.
  Unneeded full kernel builds have cost about 45 min; incremental builds take seconds to minutes.
- Unit suites are standalone (`python3 scripts/device/test-<name>.py`, mostly
  under 10 s). `rog5-dev test active` (about 750 s) runs once on frozen source,
  not per edit. `rog5-dev select BASE HEAD` picks the tier.
- The integrated tiers need the environment of the last passing run. The
  runner fails fast and marks every remaining suite BLOCKED, and the report
  dir must not exist yet:
  `systemd-run --user --wait --pipe --collect -p MemoryMax=1G -p MemorySwapMax=0 -p CPUQuota=200% --working-directory=$PWD env PATH=$HOME/.local/state/rog5-gbm-sync-evidence-20260912-r1:$PATH ROG5_WAYLAND_INCLUDE=$HOME/.local/state/rog5-xwayland-runtime-evidence-20260912-r1/materialize/root/usr/include ROG5_TEST_WORKERS=2 ROG5_TEST_REPORT_DIR=<new dir> TMPDIR=<scratch> bash scripts/host/test-repository-linux.sh <tier>`.
- New tests: register in both `configs/repository-tests.json` and the shell
  arrays in `scripts/host/test-repository-linux.sh`. Tests that need private
  inputs declare them as `optional_subchecks`, with the exact skip message and
  test ids, so CI reports PASS with declared skips.
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

Standing user authorization (2026-09-23): phone tests that need no physical
action from the user may run without asking for Ready. Examples are SSH
probes, to-fastboot, RAM-only trials via `production-ram-trial.py`, and a
normal `fastboot-reboot` to V11. Keep RAM-only, identity checks, one claim per
image and evidence capture. Flashing, partition or slot changes still need
explicit approval. Ask for Ready only when the user's hands are needed, and
tell the user at once if a rescue press becomes necessary.

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
