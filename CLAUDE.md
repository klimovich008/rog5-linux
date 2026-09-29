# ROG Phone 5 native Linux — Claude Code guide

Native Arch Linux ARM on the ASUS ROG Phone 5 (SM8350). The accepted headless
server boots from local storage through slot B. ASUS WW33 slot A is the
charging/rescue route. Claude Code has been the only coordinator since
2026-09-23. Codex/ChatGPT is retired; see `docs/history/codex-era.md`.

## Goal

Set 2026-09-23, after `production-7.2.7-r3` became the slot-B default: **make
the default kernel a usable native Linux phone, meaning every non-cellular hardware
block works or is explicitly marked unsupported, then run a Denial touch
session on the OLED.** Cellular is excluded. The previous goal (fast module
loop, signed-tag upgrades, 7.2.7 as the default) is done. Its leftover config trim
continues only when a build blocks work.

Each milestone ends with a new default bundle. First a RAM trial of the
image, then `install-default-kernel.py` with a fresh descriptor, then two
ordinary boots that commit healthy (see "Making a production kernel the
default" in `docs/development.md`). Driver iteration uses `rog5-dev module`.
Ask the user only for what needs eyes, ears or fingers, and batch those checks.

1. **Clock and self-recovery.** Correct time after a reboot without network
   (PM8350 RTC, or NTP over the USB link), ramoops/pstore at the stock
   debug region `0x9b800000`, and a watchdog that survives kexec. Pass: time
   is right after a cold boot, and a forced panic leaves a pstore record that the
   next boot reads.
2. **Display and GPU at boot, without manual steps.** The default DT enables
   MDSS/DSI/panel/gpucc/refgen, and modules autoload in the right order. Fix
   the GPU SMMU deferred probe instead of the `drivers_probe` workaround.
   Pass: three boots each show `/dev/dri/card*` and `renderD*` and the A660
   initialized, with no new WARN. The user sees the panel lit once.
3. **Wi-Fi.** Enable PCIe0 in the DT, add the WCN6851 firmware and
   `regulatory.db`, and keep the radio off until it's configured. Pass: scan,
   associate, DHCP, then 10 minutes of traffic with no firmware crash. The
   network name and password come from the user.
4. **Touch and buttons.** Autoload the FocalTech touch driver, and map evdev
   coordinates to the panel. Keep the three keys and LED from the buttons
   milestone. Pass: `libinput debug-events` shows the four corners the user
   touches, plus power/volume events.
5. **Graphics stack.** Mesa freedreno/turnip on Arch ARM, then a
   hardware-rendered test such as kmscube or weston on the panel. Pass:
   GPU-rendered frames at the panel refresh rate, with no GPU faults or hangs
   over 10 minutes.
6. **Denial session.** Build the pinned ARM64 compositor, engine and AOT shell
   from `configs/denial/source-lock-v1.json`, then run it on the OLED with
   touch. Pass: the completion criteria in `ROADMAP.md`: GPU acceleration, two
   native Wayland apps and text entry, three starts, a 60-minute
   interactive/idle run, screen off and wake, compositor recovery, and
   update/rollback.
7. **Audio.** Speaker, earpiece, microphones and headset through the
   q6/LPASS path. Pass: the user hears a test tone on each output, and a
   recording plays back.
8. **The rest, as a tracked table.** Bluetooth, sensors (VCNL36866 first),
   charging control, suspend/resume and cameras. Each one is qualified or marked
   unsupported or untested in `docs/port-status.md`.

Order is 1 → 2 → 3/4 → 5 → 6, with 7 and 8 fitted in where they don't block.
Status of each step goes in the generated block of `docs/current-state.md`,
not here.

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
  Linux. Host NCM interface: `enp4s0f3u1u2` with 10.77.0.1/30 (after a replug
  run `nmcli con up rog5-standalone-shared`). An ordinary reboot boots the
  selector's primary, or its fallback `production-7.2.7-safe-r2` after an
  uncommitted boot (V11 was the fallback until 2026-09-26 and stays on p24).
  Manual rescue runbook: docs/development.md.
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
- New tests: add one row to `configs/repository-tests.json` (its `tiers` field
  is the only tier list; `bash scripts/host/test-repository-linux.sh --list TIER`
  prints a tier). Tests that need private inputs declare them as
  `optional_subchecks`, with the exact skip message and test ids, so CI reports
  PASS with declared skips.
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
normal `fastboot-reboot` back to the installed chain. Keep RAM-only, identity checks, one claim per
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
