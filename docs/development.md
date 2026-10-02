# Development loop

Start at [current state](current-state.md). Work on one question and choose the
cheapest artifact that changes its answer. This page covers the live tools:
tests, the fast module loop, kernel rebases, RAM trials, making a kernel the
default, unattended updates, rescue, packaging and target checks. The full
July-September version of this page, with the headless-server, network-root,
recovery-candidate and Denial/QEMU material, is
[history/development-log-2026-07-to-09.md](history/development-log-2026-07-to-09.md).

## Tests and CI

`configs/repository-tests.json` is the only test registry: each row names its
tiers, deadline, prerequisites, resource class and declared optional
subchecks. `bash scripts/host/test-repository-linux.sh --list TIER` prints a
tier; `scripts/host/test-repository-linux.sh TIER` runs it (see CLAUDE.md for
the recorded environment). Every tier first runs
`python3 scripts/host/check-repository-static.py` (context entry points, tracked
test suites and required inputs, local Markdown links in the live docs,
shell/Python syntax, secret scan).

After preparing a public export, run that static check in the exported Git
checkout before publishing. Keep every registered suite and required input,
including extensionless host tools such as `scripts/host/rog5-device-profile`
and the tracked binaries, hashes and metadata in
`artifacts/persistent-trial-state-v{1,2,3}/`. The ignored `artifacts/` parent
does not make those tracked source inputs disposable. Test the clean exported
checkout with the workflow's boot-tool bootstrap and the selected tier;
ignored files in a private worktree must not supply missing publication inputs.

The runner writes per-suite logs plus `summary.json` and JUnit `summary.xml`
under `build/test-reports/` (or a fresh `ROG5_TEST_REPORT_DIR`). Missing
mandatory inputs, unexpected skips, failures and deadlines fail the tier; an
early failure leaves unreached selected suites BLOCKED. Only reviewed isolated
suites run concurrently (two workers by default, bounded by CPU affinity, quota
and `ROG5_TEST_WORKERS`).

After a production source preparation/build, run the exact-source regressions
with the schema tools on PATH:

```sh
ROG5_LINUX_SOURCE="$PWD/build/rog5-production/source" \
  scripts/host/test-repository-linux.sh board
```

The board tier exercises the RPMh binding/PM fixtures, the touch input core
against the pinned Linux files and the panel/touch regulator cases. It does
not rebuild Image/modules or establish physical qualification. The CI
`board-production` job fetches v7.2.7 (`f42acb36`) and builds with
`configs/kernel/rog5-production-build-7.2.7.json`; `panel-driver` compiles the
AMS678 panel on the same base.

Status has one source, `docs/status/components.json` (installed default and
fallback, and every component as ready/partial/untested/missing).
`scripts/host/render-current-state.py` writes the generated block of
[current state](current-state.md) and `tools/status-map/render.py` draws the
status map; `test-render-current-state.py` (active tier) fails when they
disagree. `scripts/host/index-test-results.py` regenerates
`test-results/README.md` after a new dated report.

## Commands and tests

Run these from the repository; `scripts/host/rog5-dev` also works from another
directory. Each command delegates to an existing implementation.

```sh
scripts/host/rog5-dev test active
scripts/host/rog5-dev select --event push BASE HEAD
scripts/host/rog5-dev select --development BASE HEAD
scripts/host/rog5-dev build-initramfs --help
scripts/host/rog5-dev package --help
scripts/host/rog5-dev check-target --help
scripts/host/rog5-dev make-bundle --help
scripts/host/rog5-dev bundles check
```

- Documentation: link/context checks and active tier.
- Observer/userspace: focused behavior tests and active tier; copy only the
  admitted script if no reboot is needed.
- Module: exact `.ko`, ABI/vermagic/BTF and dependency closure; no full kernel
  build unless built-in code or ABI changes. Unsafe unload requires a short boot.
- DT/initramfs: compose only the affected DTB/archive, then test that composition.
- Kernel/recovery/shared lifecycle/trust/storage: focused checks first, one full
  `test ci` on the frozen tree. Historical matrices run `test nightly`.

Do not rerun full local tests without changed code or a new failure. The runner
prints per-suite duration. It runs at most two explicitly isolated suites by
default, further limited by CPU affinity and inherited CPU quotas.
`ROG5_TEST_WORKERS=1` serializes those suites; values 1–32 request another cap
without exceeding detected CPU capacity. Unknown quota hierarchies serialize
conservatively. Completed suite logs print as slots are reclaimed, and any ready
failure is handled before refilling the queue. Shared-state tests remain sequential. CI uses this same runner. PR head and
merge validation remain separate; main pushes now select from before/head.
Unknown or unavailable diffs broaden validation. Scheduled/manual validation
runs nightly and QEMU. Required job names are retained, with explicit skipped
merge handling for non-PR runs.
The single reviewed current narrative report is documentation in both the
development and CI selectors. Other `test-results` paths remain potentially
executable inputs and select broader checks; mixed critical changes still win.
PR merge checks continue to cover their full relevant branch delta.

Before full CI in a new worktree, materialize the tracked test fixtures; a sparse
checkout prepared for hardware observation may omit required historical inputs.
Provide the pinned Android boot tools and canonical boot-v3 template using the
bootstrap steps in `.github/workflows/offline-smoke.yml`, or reuse local copies
after verifying their exact pinned hashes. These ignored dependencies are not
created by `git worktree add`. Keep temporary checkout copies on disk, preserve
at least 3 GiB free, and restore the sparse checkout after validation if needed.
The active composition suite also uses the pinned Android unpacker, so active
checks need boot-tool bootstrap or verified local copies. Only the canonical
boot-v3 template remains unnecessary for the active tier.

Batch related fixes into one frozen integration checkpoint; record the exact
source/dirty-input identity tested. Run focused checks during edits, one full
local CI for relevant shared changes, then publish with existing exact-head
and merge requirements. Documentation-only follow-up gets its link/active
checks; it does not retroactively change the source covered by earlier CI.
No repeated full CI for unchanged inputs. While remote checks run, do useful
independent work without modifying their frozen inputs or starting a second
device coordinator. This policy changes iteration cadence, not release gates.

### Fast module loop (running production kernel)

Use `rog5-dev module` to change a loadable module and test it on the phone in
seconds, with no ramdisk, packaging, reboot or flashing. The phone must be
running a production boot whose vmlinux matches the object tree.

- Dev trees, one per running kernel build: `~/.local/state/rog5-kdev/7.2.7-rog5-production-build-r2/`
  (current) and `…/7.1.4-rog5-production-build-r2/`. `source/` is a
  git copy of the exact source; edit it there, and `git diff` exports the
  change as a patch. `env` exports `ROG5_KDEV_SOURCE` and
  `ROG5_KDEV_OBJECTS`, the read-only build-r2 objects.
- Build: `set -a; . <dev tree>/env; set +a; rog5-dev module build --dir
  drivers/power/supply --ccache ~/.local/state/rog5-host-tools/ccache-4.14/ccache`
  compiles that directory as an external module against the pristine objects,
  so kernel headers always match the running vmlinux. Edits to `include/`,
  `arch/` or a header outside the directory are refused, because they need a
  full kernel build.
- Deliver: `rog5-dev module deliver --build <build dir> --only qcom_battmgr
  --test '<command>'` checks the USB port, the release and the GNU build ID
  from `/sys/kernel/notes`. It then streams the module into
  `/run/rog5-dev-modules` (RAM), loads its dependencies from
  `/run/rog5-modules`, runs `rmmod` + `insmod` (or `--mode load|oneshot`), runs
  the test and keeps the kernel log since its marker. An oops, BUG, WARNING or
  lost SSH makes the run FAIL.
- Measured on 2026-09-23: `qcom_battmgr` edited, built in 9 s, delivered and
  tested in 5 s.
- Modules that cannot be unloaded while in use (msm, the panel) need a clean
  boot first. The RAM-trial launcher gives one in about a minute, after which
  `deliver --mode load` applies.

### Upgrading the kernel base

Every kernel-source change belongs in the base's `series.production`.
Side patches applied by other builders get lost on upgrade: the WCN6851
hw1.1 ath11k patch in `patches/linux/device/` is one, to be folded in as
0044. The upgrade is one scripted rebase, one build, one module package and
one RAM trial:

1. `rebase-kernel-series.py start --linux-git ~/.local/state/rog5-linux-stable-git
   --tag v7.2.8 --fetch --from patches/linux-7.2.7 --work <new dir>` fetches the
   tag and requires a valid signature from Greg Kroah-Hartman
   (`647F…693E`) or Linus Torvalds (`ABAF…1886`); the keyring is
   `~/.local/state/rog5-host-tools/gnupg`. It then applies the series one commit
   per patch. On a conflict, fix the listed `.rej` hunks in `<work>/tree`,
   delete the `.rej`/`.orig` files and run `continue --work <dir>`.
2. `export --work <dir> --policy-from configs/kernel/rog5-production-build-7.2.7.json`
   writes `patches/linux-<version>/` and `configs/kernel/rog5-production-build-<version>.json`
   (new base commit and base-archive hash). Export fails unless the new patch
   set reproduces the work tree on a fresh extract.
3. Build with the dtschema environment on PATH:
   `~/.local/state/rog5-host-tools/dtschema-2026.6/bin/python3 scripts/host/build-rog5-production-kernel.py
   --config <new policy> --linux-git ~/.local/state/rog5-linux-stable-git
   --output ~/.local/state/rog5-kernel-<version>-build-rNNN --jobs 6 --ccache
   ~/.local/state/rog5-host-tools/ccache-4.14/ccache`. The output name makes
   this build kNNN and `uname -r` `<version>-rog5-kNNN` (see "Bundle names and
   the bundle tool"). Run `--prepare-only` first: in under a minute it shows
   whether the patches apply and the merged config still meets the policy.
   A new base prints upstream W=1 diagnostics that the old hash-pinned warning
   policy cannot match, so the build ends FAIL with only those left. Run
   `draft-warning-policy.py --build <build> --build-policy <new policy> --previous
   <old warning policy> --output configs/kernel/rog5-production-warning-policy-<version>.json`.
   It keeps the old entries whose files are unchanged, pins the rest by file
   hash and exact message, and refuses any diagnostic in a series-modified
   file, schema message or depmod line. Set `warning_policy_file` in the
   new build policy, then confirm with `check-production-build-diagnostics.py
   --build <build> --policy <that file> --output <new json>`. 7.2.7: 7 of 21
   reviewed files and both initializer pins carried over; 317 messages in 28
   upstream files were drafted; the checker reports PASS.
4. Add the new base's `X.Y.Z-rog5-k[1-9]` ... `k[1-9][0-9][0-9][0-9]` patterns
   to `production_release()` in `build-persistent-root-standalone-initramfs.sh`,
   an exact allowlist so no other release name (and no unlabelled k0 build)
   gets through.
   `package-production-modules.py --build <build> --output <new dir>` builds the
   64-module ramdisk package, including the `tools/` externals, from that build.
5. Then `rog5-make-bundle.py` (ramdisk, signed package) and the RAM trial as
   in the production trial flow. After a PASS, create a new `rog5-kdev` dev tree from the build for the
   fast module loop.

Measured on 2026-09-23 (7.1.4 → 7.2.7): 15 of 17 patches applied
unchanged; 0003 and 0018 needed context-only fixes. Replaying with the tool
reproduced the manual result byte for byte. The host tools are pinned under
`~/.local/state/rog5-host-tools`: ccache 4.14 (minisign-verified), CPython
3.12.14 (release SHA256SUMS) and the dtschema 2026.6 environment. The old
dtschema venv died with the removed Codex runtime.

### Bundle names and the bundle tool

Every signed bundle comes from one command, run from this repository. It
builds from a clean `git archive` of HEAD, so commit first: uncommitted
changes are not in the bundle (the tool says so).

```sh
scripts/host/rog5-make-bundle.py --role main --kernel k111 --dtb d9        # next default
scripts/host/rog5-make-bundle.py --role safe --kernel k69 --dtb d3 \
    --boot-modules-from 4980520d                                            # the safe-r8 recipe
scripts/host/rog5-make-bundle.py --role main --kernel k111 --dtb d9 --plan  # name and inputs only
```

- **Kernel builds** are `kNNN`: the builder output
  `~/.local/state/rog5-kernel-7.2.7-build-rNNN` is kNNN. From k111 on,
  `uname -r` is `7.2.7-rog5-kNNN`: the build policy's `release_localversion`
  with the label from the output name or `--label`. Any other output name
  gives k0, which the production ramdisk builder refuses. k110 and older
  report `7.2.7-rog5-production`.
- **DTBs** are `dN` in `configs/production/dtbs.json` (path, sha256, compose
  features, base, needed patches). A `features` file with the same id and
  hash sits next to each `board.dtb`. d2/d3 (fallback line) and d7-d9
  (default line) keep the rN of their directory. Register a new composition
  with `scripts/host/rog5-bundle-registry.py add-dtb --dtb <state>/<dir>/board.dtb
  --features <list> --base d9`; it takes the next free id, from d10.
- **Bundles** are `<role>-k<kernel>-d<dtb>-<YYMMDD><letter>`, for example
  `main-k111-d9-261001a`. `main` is built with a fresh try-once descriptor,
  `safe` (a fallback) without one. The letter is the first free one of the
  day. A failed attempt burns its name, so a trial id is never reused.
  Bundles made before 2026-10-01 keep their names (`production-7.2.7-r208`,
  `production-7.2.7-safe-r8`). RAM trials boot the main bundle's own
  wrapper, so there is no trial role. The names pass the loader's
  `valid_bundle_name` (`^[a-z0-9][a-z0-9._-]{0,63}$`, no `..`).
- **Steps.** The kernel build must be PASS, its Image must match
  `result.json` and a labelled build must report its label. The DTB must match
  its hash and features file. A module package the tool made
  (`modules-kNNN`, with a digest of the packager, the module selection and
  the `tools/` sources of the external modules) is reused only while that
  digest matches the snapshot; otherwise a new one is packaged from the
  snapshot (`--fresh-modules` forces that). A legacy `modules-7.2.7-rNNN`
  is used only when the build's objects are gone (k69), and the registry
  notes it. Build steps get no inherited `PRODUCTION_*`, `EXPECTED_*`,
  `ROG5_*` or `PYTHON*` variables. The ramdisk is built with the pinned inputs of
  `configs/production/bundle-inputs.json` and must carry exactly the new
  descriptor (main) or none (safe), plus the current init. Then
  `package-production-ram-trial.py` signs and wraps it. The signing key path
  comes from bundle-inputs.json, `$ROG5_SIGNING_KEY` or `--private-key`;
  only the packager reads the key. A pruned kernel build (objects deleted,
  like k69) takes its Image from a registered bundle with the same hash.
  `--boot-modules-from REV` (safe only) takes `boot-modules.list` from an
  older commit, for a kernel that lacks newer modules.
- **Outputs** in `~/.local/state/rog5-production-boot-20260923`:
  `trial-<name>/descriptor`, `ramdisk-<name>/`, `package-<name>/` (with
  `make-bundle.json`, the full input record) and `bundle-work-<name>/` (step
  logs). Measured on 2026-09-30: about 2 minutes for a main bundle with a new
  module package. The k110 module package and the ramdisk member lists came
  out identical to r208's and safe-r8's, and a copy of the r110 modules
  relabelled 7.2.7-rog5-k111 built a ramdisk with only that tree
  (`test-standalone-production-tree.py`, private inputs).
- **Registry.** The tool appends the bundle (status `built`) and any new
  kernel to `configs/production/bundles.json` and renders
  [bundles.md](bundles.md). Record each outcome with
  `rog5-bundle-registry.py set <name> --status installed-main|installed-fallback|retired|ram-trial-fail|...
  --healthy yes|no --installed '<date time>'`. Marking a bundle installed
  retires the previous one of that role. Commit both files.
  `rog5-bundle-registry.py describe k111 '<changes>'` fills a kernel's
  change note. `test-rog5-make-bundle.py` fails when bundles.md is stale.
- **Releases and modules.** Every bundle carries its own modules. The
  ramdisk holds that kernel's depmod tree and publishes it at
  `/run/rog5-modules/lib/modules/<release>`. The root filesystem has no tree
  for any production release (only an old 7.1.4 directory), and the init
  compares `uname -r` with the release its ramdisk was built for. So a k111
  default next to a k69 fallback needs nothing from the root, and installing
  a k111 bundle from a k110 system or from the fallback works as before.
  `install-default-kernel.py` only logs the running release. `rog5-dev module
  deliver` still needs a kdev tree from the running kernel's build; its
  release check now also tells builds apart.

### Device profile (per-phone boot values)

The boot sources accept exactly one phone and one root. Their per-phone
values (UFS geometry and node count, userdata/p24/overlay/state UUIDs, the
overlay size limit, the sealed root's hashes and pinned binaries) live only in
the `# BEGIN ROG5 DEVICE PROFILE` block at the top of
`initramfs/persistent-root-init`, `persistent-root-attest`,
`persistent-service-state`, `persistent-slotb-loader-init`, `recovery-init`,
`scripts/device/stage-persistent-root-overlay.sh` and
`stage-persistent-service-state.sh`; the rest of each script uses the
`rog5_*` names. The blocks carry the reference phone's values
(`configs/device-profiles/reference.env`). `scripts/host/rog5-device-profile
render` rewrites a block from another profile, and
`build-persistent-root-standalone-initramfs.sh` does it for the init,
attestor and state helper when `ROG5_DEVICE_PROFILE` is set.
`scripts/host/test-rog5-device-profile.py` fails when a block and
`reference.env` disagree or a reference value appears outside a block, so
change both together. The overlay limit (`rog5_overlay_max_bytes`) is derived:
userdata - 4 GiB - max(2 GiB, userdata / 32), in whole MiB (184.9 GiB on the
reference phone, was a fixed 192 GiB).

### Making a production kernel the default

The slot-B loader boots the selector's primary bundle while the p23 try-once
record (`/rog5/boot/wifi-trial-state`) is absent or healthy, and re-arms it
to pending on each primary boot. A boot that does not mark itself healthy
sends the next boot to the selector's fallback, currently
`production-7.2.7-safe-r8` since r205 (k69 + d3, no trial descriptor;
[bundles.md](bundles.md) and the `bundles` entry of
`docs/status/components.json` name the installed pair). Older fallbacks, down to V11, stay on p24 for a manual
rollback. The production ramdisk commits itself when it is built with a
trial descriptor:

1. `rog5-make-bundle.py --role main --kernel kNNN --dtb dN` writes a fresh
   descriptor (`format=rog5-persistent-wifi-health-v1`, `trial_id=<64 random
   hex>`, `primary_bundle=<new bundle>`, `mode=try-once`; never reuse a trial
   id or bundle name), builds the ramdisk with
   `PRODUCTION_TRIAL_DESCRIPTOR=<file> PRODUCTION_TRIAL_DESCRIPTOR_SHA256=<sha>`
   and packages it with `--bundle <new bundle>`.
2. RAM-trial that wrapper. `rog5-production-trial-commit.service` must log
   `rog5-production-trial: SKIP …` (the record belongs to another trial) and
   leave the record unchanged.
3. `install-default-kernel.py --bundle-dir <package>/bundles/<bundle>
   --descriptor <file> --trust-key <raw loader key> --evidence <new dir>`
   from any booted ROG5 system. It verifies both bundles with the trust key
   (the fallback the current selector names is fetched from the phone),
   checks that the ramdisk carries this
   descriptor, generates the selector, backs up the old selector and record,
   and runs the target script's `--inspect` and `--preflight` against a RAM
   copy. Add `--stage` (clean repository) for the single write window: the
   bundle goes to p24, a read-only remount is proven before activation, the
   new selector is exchanged in atomically (`exch`; the old one keeps its
   inode as `selector.rollback-<bundle>`), p24 is relocked, and the old
   record is archived as `wifi-trial-state.archived-before-<bundle>-<sha>`.
   Nothing on p24 is unlinked: `/` is an overlay over the same p24
   superblock, a cached overlay dentry keeps a replaced inode alive, and
   ext4 then refuses every read-only remount (the r206 install failed that
   way on 2026-09-30). A 180 s timer relocks p24 if the script dies. If p24
   cannot be relocked after activation, the script still archives the record
   (once the selector and bundles re-verify) and prints a `STATE … next_boot=…`
   line, kept in `INSTALL-RESULT.json` as `phone_state`. Never retry a failed
   `--stage`: inspect the phone first. `--fallback-bundle-dir <package>/bundles/<name>`
   also installs a new fallback bundle in the same window. The bundle must
   be new on p24 and carry no trial descriptor, and the new selector names
   it.
4. Reboot normally. The first boot writes a pending record and boots the
   bundle, and the unit logs `PASS <bundle> committed healthy`. The next
   reboot must land on the same bundle. Record it:
   `rog5-bundle-registry.py set <bundle> --status installed-main --healthy yes
   --installed '<date time>'` (and `installed-fallback` for a new fallback).
   Persistent boots answer SSH on `10.77.0.2` (the RAM-trial address is
   `169.254.77.2`), about 60 s after the reboot. 7.2.7 (`production-7.2.7-r3`) became the default this way on
   2026-09-23.

Going back is a selector change: `selector.rollback-<bundle>` is the
previous selector, which boots its fallback while the new record is foreign
to it. To test the fallback: persistently mask
`rog5-production-trial-commit.service` (`/etc/systemd/system` → /dev/null)
for one boot. That boot stays pending, the next one boots the fallback, and
you then unmask and install a fresh default (tested 2026-09-26 with the
safe-r2 fallback, which came up with Wi-Fi).

A fallback bundle keeps a well-tested kernel but must carry the current
init, since both bundles boot the same upper and its update snapshots (see
rog5-update below). `rog5-make-bundle.py --role safe` builds its ramdisk like
a default one without `PRODUCTION_TRIAL_DESCRIPTOR`, from the current source,
with that kernel's module package. `configs/production/boot-modules.list`
must name only modules that kernel has: the build fails otherwise (k69 lacks
`tcpci_rt1711h`, which 0144 kernels load, so `--boot-modules-from 4980520d`
takes the list safe-r8 used). A DTB change for the fallback goes on top of
its own DTB (d3 = d2 `platform-usbbtm-dtb-r2` + the memx overlay, a dts diff
of exactly that node); register it with `add-dtb`. The installer puts a fallback on p24 only together with
a new primary (`--fallback-bundle-dir` next to `--bundle-dir` and a fresh
descriptor). safe-r7 and older predate the v2 seal: on a v2 `pending`
record they write `restore-refused`, drop `pending`/`attempt` and boot the
updated upper, and a `restoring-v2` journal fails their overlay stage.

### Unattended package updates (rog5-update)

pacman owns only userspace. Kernel, modules and firmware come from the
signed bundle. The primary and the fallback boot the same persistent upper,
so a bad upgrade breaks both. `rog5-update` guards upgrades with a copy of
that upper without user data:

- **Build.** The init's snapshot restore is always compiled in. It does
  nothing until a pending record exists. `PRODUCTION_UPDATE_KIT=1` (with
  `PERSISTENT_ROOT_OVERLAY=1`) adds the `/rog5-update` kit: the tool, the
  hourly `rog5-update.timer` and the per-boot `rog5-update-commit.service`.
  The init publishes the kit to `/run`, like the trial kit. Build both the
  primary and the fallback bundle from this init. A fallback without it
  cannot restore a snapshot.
- **run** (hourly, at most one attempt per `ROG5_UPDATE_INTERVAL`). It needs
  a default route, `rog5-package-keyring` active, the battery below 45 °C,
  and either external power or battery above `ROG5_UPDATE_MIN_BATTERY`. The
  current root must pass `verify-root`. Then it does `pacman -Sy` and plans
  `-Su --print`. A plan that pulls in a package from `ROG5_UPDATE_HOLD` is
  skipped. Next it takes a snapshot: it holds `db.lck`, runs `sync`, and
  copies upper with GNU tar (owners, modes, times, hard links, sparse files,
  ACLs, all xattrs incl. `trusted.overlay.*`) into
  `/.rog5/state/snapshots/<id>/upper`, leaving out the user data in
  `snapshot_excludes` (`home`, `usr/share/guestos`, `var/lib/flatpak`,
  `var/lib/systemd/coredump`, `var/log/journal`, `var/cache/pacman/pkg`;
  20.8 of 27.0 GB on 2026-09-30, so a snapshot is about 6 GB). The v2 seal
  holds an entry count, a hash of the name list and `excluded=`. The space
  check counts upper without those paths. It writes `pending
  action=restore`, upgrades the
  keyring first, then `pacman -Su`, then runs `verify-root`. On a pass it
  rewrites pending to `action=verify` and reboots once the backlight is
  off (`ROG5_UPDATE_REBOOT=idle|now|never`). On a failure the restore stays
  armed and the phone reboots at once. A transaction that changed nothing is
  discarded without a reboot.
- **Init.** Before the overlay mounts, the first boot with a `verify` pending
  record writes `attempt`. A second boot without a commit, or any `restore`
  record, renames the sealed snapshot into place. It keeps the old upper as
  `snapshots/<id>/failed-upper`, then moves each path of the seal's
  `excluded=` list from `failed-upper` into the restored upper, so a rollback
  keeps the newest `/home`, Flatpaks, FEX rootfs and journal. Every parent
  of such a path that exists in the root being replaced must be a real
  directory there and in the snapshot; otherwise the restore is refused
  before anything moves (`restore-refused`, the updated root boots). Then
  it writes `rog5-update/last-result`. The renames and moves are journaled
  (`restoring-v2` for a v2 snapshot), and a later boot finishes an
  interrupted restore. The init accepts only paths of its own
  `update_snapshot_excludable` list; a v1 seal (full copy) restores
  everything. An init without v2 support refuses a v2 snapshot (the updated
  root boots) and stops at a `restoring-v2` journal instead of finishing
  without `/home`, so build the fallback from this init too.
  The init acts only on exact records (0:0 0444, fixed grammar) and on a
  snapshot that matches its seal. Anything else leaves upper as it is. All
  the existing checks then run on the result.
- **commit** runs after the trial commit and after `systemd-update-done`. It
  waits for the trial commit's health gate, then reruns `verify-root`. On a
  pass it records `committed`, keeps only this update's snapshot as the last
  good root, and empties the package cache. A root that fails is armed for
  restore and rebooted.
- **Operate:** `/run/rog5-update/rog5-update status|verify-root|resume|rollback`.
  After two failed updates in a row, the same plan waits for new package
  versions. After three, updates pause until `resume`. `rollback` arms a
  manual restore to the kept snapshot.

`verify-root` checks the merged-root conditions that the next boot enforces.
A package can trip them:

- **`filesystem`, `shadow`, `systemd` (sysusers):** `/etc/shadow` must be
  0:0 600 with one hard link and exactly `root:x:<n>::::::` (P2). A root
  crypt hash passes the init but fails P2.
- **`openssh`:** the effective `sshd -T` policy must still be key-only root
  with `usepam no`. `ssh-keygen -y` and `-lf` must work. `/usr/bin/sshd`
  must stay the listener. The `10-rog5-server.conf` drop-in is unowned and
  must stay the pinned 201/211-byte file.
- **`systemd`:** both `/etc/.updated` and `/var/.updated` must use the exact
  `systemd-update-done` template. A new wording breaks the second boot after
  the upgrade, so `verify-root` greps the installed binary for the template.
  `/sbin/init` must still resolve.
- **`glibc`:** `/etc/ld.so.cache` must be 0:0 644, 1 B–1 MiB.
- **`archlinuxarm-keyring`:** its three keyring files must be 0:0 644.
- **`coreutils`, `util-linux`, `iproute2`, `gawk`, `grep`, `sed`, `gnupg`,
  `pacman`, `systemd`:** the attestor and helpers run these from the root, so
  each is smoke-tested.

The lower's hash pins (sshd, systemd, sshdgenkeys, `authorized_keys`) are on
read-only p24, and pacman cannot change them.

Limits:

- A boot that fails inside the init restarts into fastboot. Someone must
  press START (or run `fastboot reboot`). The loader then boots the
  fallback, which restores the snapshot. The fallback stays selected until
  the default is installed again.
- `/persist` (keyring, SSH identity, Tailscale, clock) is not in the snapshot.
- Sockets are not copied (tar skips them; gpg-agent and services recreate
  theirs). Hard links between user data and the system become two files.
- A rollback moves the excluded subtrees as they are, but does not reconcile
  their parents' `trusted.overlay.*` opaque/redirect/impure xattrs between
  the two roots (the snapshot keeps upper's own parents). Changed ancestry
  (e.g. an opaque `/var/lib` made after the snapshot) can change what the
  lower shows below it.
- User data (`snapshot_excludes`) is not rolled back. A package's files there
  (e.g. under `/var/lib/flatpak`) keep their updated state after a rollback.
- Files that services rewrite during the copy can be torn. pacman's own
  files are consistent.

### Human-assisted hardware sessions

Complete the builds, focused tests, review, staging and no-press runtime checks
before asking the user to be available. The
local-root physical-key reader (`scripts/device/observe-local-root-physical-key.sh`, archived 2026-09-29)
supports `--preflight`: it checks the actual input FD, driver, device tree and
inhibitor, then exits without a READY prompt or event reads. Run the relevant
key preflights before the handoff; keep the existing NFS-specific gate separate.

Prepare the full launch and cleanup recipe in advance. Wait for a fresh explicit
Ready before starting any operator countdown. After the reply, perform only the
brief current-state guards and runtime arming, then immediately present the
actual reader READY prompt. Ask for one short press/release at a time and collect
events automatically; the user should not have to type terminal commands.

If preparation fails or availability expires, close the session and resolve the
problem independently before asking again. Keep partial valid component evidence
and every raw failure; avoid repeating a completed physical step solely because
a later independent validator failed. Explicitly distinguish a strict test-case
FAIL from separately verified component behavior.

### Manual rescue (hard hang, no USB, dark screen)

The production kernel has no lockup detector. The ASUS Haven watchdog is
disabled before kexec, and the trial's rollback timers are userspace. A hang
that doesn't panic (`panic=10` covers panics) therefore stays hung until someone
resets the phone by hand. Declare a hang when nothing new appears for the
controller's deadline after kexec: no stage frame, USB enumeration or SSH. Then
prompt the operator one step at a time:

- **R1 (force reboot to fastboot):** hold Power + Volume Up for about 20 s. When
  it vibrates or the logo appears, release Power but keep holding Volume Up
  until fastboot shows. This comes from the Codex-era archive and worked after
  a kexec'd kernel hung.
- **R2 (Qualcomm crashdump screen, "waiting for flashing full ramdump", USB
  05c6:900e):** hold Volume Down + Power for 8–12 s, then immediately do R1.
  Proven on 2026-08-16 (commit 411dc6fe, since removed from the charging doc).
- If R1 gets no response within 25 s, do R2, then R1.
- Never pick Recovery or Power off in the menus, and never press anything on the
  ramdump screen. Replugging USB does not reset a hung kernel.

Landing: a forced reset without Volume Up boots the flashed boot_b wrapper. A RAM
trial image is gone after any reset. The slot-B loader then picks the primary
or its fallback (production-7.2.7-safe-r2 since 2026-09-26; V11 before). A loader failure returns to fastboot. With USB connected, power-off is
not a stable state: the phone restarted into slot B by itself (S06 on 2026-09-09
and on 2026-09-03). Record which landing occurred and the hold time the operator
reports.

## Packaging without identity-copy scripts

The runtime packager accepts one JSON `--config` containing its non-credential
Configuration fields. Run `package --help` for field names (JSON uses underscores).
All values are strings. Artifact paths resolve relative to the JSON file.
The recipe cannot contain signing-key/output paths, admission authority or
unknown fields; CLI recipe overrides are rejected. Supply the key and a fresh
private output directory separately. The original CLI remains supported.

The packager computes sizes, hashes and the signed manifest from the actual
input bytes and publishes atomically. Do not copy derived hashes into a second
manual signing script. Keep per-cycle private recipes and receipts outside Git.
`build-initramfs` delegates to the qualified base/radio composer; later layer
builders retain their own explicit input contracts.

For a packaging rehearsal, use an ephemeral test key and the retained accepted
Image/DTB/archive. Compare twin outputs and run the native bundle verifier with
that test public key. Such an output is **not trusted by the phone**. Testing
with a test key must never replace production signature verification.

## Exact target filesystem checks

Host QEMU without filesystem isolation previously exposed host `modules.dep`
and hid a real BusyBox failure. The following command extracts the archive into
a disposable root and runs its own BusyBox, using bubblewrap plus static
`qemu-aarch64-static`. No host `/lib`, network or physical device is exposed.

```sh
scripts/host/rog5-dev check-target --release TARGET_RELEASE INITRAMFS -- \
  sh -n /rog5-native-wifi/runtime
scripts/host/rog5-dev check-target --release TARGET_RELEASE \
  --empty-module-index INITRAMFS -- \
  modinfo -F vermagic /rog5-native-wifi/qcom-pon.ko
```

`--empty-module-index` explicitly simulates the trusted pre-switch runtime's
empty mode-0444 index **inside the disposable extraction**. Omit it to test the
original archive. Check expected output as well as status: BusyBox `modinfo`
can exit zero for a missing module. Archive paths precede runtime relocation;
`/rog5-native-wifi` becomes `/run/rog5-native-wifi` during boot. This runner
does not execute init, load modules, emulate hardware or prove systemd behavior.

## Builds, trials and publication

Reuse the retained kernel/DT/modules for host, documentation and userspace
changes. `kernel-build-contract.sh` already enforces locked exact-state
incremental reuse through `INCREMENTAL_BUILD=1`, optional `KBUILD_CCACHE=1`
and bounded `JOBS`. A changed kernel input must invalidate reuse. The existing
ASUS wrapper cache binds actual source, toolchain, config, initramfs and repack
inputs; host docs and target bundle names are not wrapper-kernel inputs.
Keep clean twins when changed recovery/kernel inputs need release reproduction.

Local development path: freeze source; run the appropriate local tests;
compose/package without remote access; validate exact archive, signature,
payload identity and output inventory; retain source SHA and timings. This
path now uses the shared recipe CLI instead of copied scripts requiring a
fresh remote run merely to package unchanged payloads.

Live admission is separate. Existing reviewed device/topology/slot, power,
fallback, artifact and one-use claim checks still apply. This consolidation
does not add a local-CI waiver to a live gate that requires remote evidence.
Publication/release still requires successful CI for the exact commit plus
merge validation where applicable. A shared trust/runtime change receives full
validation. Admission-only generated data need isolated artifact/claim checks,
not another complete run when the already verified source is unchanged.

Do not invoke historical Alpine/NFS live gates for the installed native server.
The native RAM loader and transaction are
`scripts/device/load-native-ram-bundle.sh` and
`scripts/device/execute-native-ram-bundle-transaction.sh`; host admission must
precede them. Neither this command front door nor packaging consumes a claim.
Never retry an ambiguous or post-COMMIT experimental target.
