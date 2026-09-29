# Repository restructure plan

Status: proposal, 2026-09-29, written against `1c490e07`. Nothing has been
moved or deleted. Every number below comes from the static inventory in
Appendix A, the test registry, the last test reports and `git` metadata.
Rerun Appendix A before each phase; the numbers drift as work continues.

## 1. Verdict

Yes, the repository needs pruning, but it doesn't need a big reorganisation.

Most of the tree is left over from July to mid-September: the network-root
server, local-image staging generations v1 to v49, storage-layout stages, A660
diagnostic generations v3 to v10, one-use claim runners and the 7.1.4
display-controller stack. What builds, boots and runs the phone today is about
340 files (roughly 27k of the 369k lines in `scripts/`, `tools/` and
`initramfs/`). About 1,060 more files are statically unreachable from anything
live.

What the cleanup buys:

- **Faster, more honest tests.** In the last green `active` run (2026-09-23),
  only 93 s of the 858 s of test time exercised current code. Historical suites
  took 602 s and Denial/QEMU UI suites took 155 s. After the cleanup the
  `active` tier should take about 2 minutes instead of 12 to 14.
- **One place to look for status.** Status currently lives in five places that
  disagree:
  - the `docs/current-state.md` header says r93/r98;
  - `configs/project-status.json` says r120;
  - `manifests/current-artifact.json` describes 7.1.4;
  - `docs/port-status.md` is from the July era;
  - `docs/status/components.json` (r185) is the only current one.
- **CI that checks the real thing.** Public CI is red on every recent push
  because an external download fails. Its board job builds Linux 7.1.4, not
  the 7.2.7 production kernel.
- **Less chance of editing dead code.** The kernel builder still defaults to
  7.1.4. A live unit test reads 7.1.4 patches. Four live tests import
  historical controllers that pull in about 550 more files.

Things to leave alone:

- `test-results/`: 534 Markdown links and 70 code files point into it.
- `scripts/{host,device}` layout for live tools.
- The phone-side file names.
- Git history (see section 5).

## 2. Numbers

### 2.1 How files were classified

Appendix A builds a reference graph over all 3,757 tracked files. An edge
exists when a text file names another tracked path: the full path, a suffix of
it, a path relative to the file's own directory, a unique basename, or a Python
import from the same directory. A reference to a directory counts as a
reference to every file in it. This over-approximates, which is the safe
direction for deciding what is live. Three kinds of file are leaves, meaning
they are kept if referenced but never make what they mention live:

- Fixtures (`*/fixtures/*`, `tests/fixtures/`, `test-fixtures/`).
- Catalogs (`manifests/artifact-sets.json`, `manifests/artifacts.tsv`,
  `manifests/current-artifact.json`, `configs/release-acceptance.json`).
- Markdown, the test registry, the runner, the tier selector and `rog5-dev`.
  These list almost everything, so following them would make everything live.

Live entry points (the "product" seeds) and why each one is live:

| Entry point | Why live |
|---|---|
| `scripts/host/build-rog5-production-kernel.py` + `configs/kernel/rog5-production-build-7.2.7.json`, `rog5-production-warning-policy-7.2.7.json`, `patches/linux-7.2.7/*` | Builds the default kernel. Its closure pulls in fragments, `dts/qcom/*` sources, `check-production-build-diagnostics.py`, `test-mobile-dt-composition.py` and the `verify-*-dtb-delta.py` / `verify-mobile-touch-providers.py` inputs, whose hashes it records. |
| `scripts/device/compose-production-dtb.sh`, `compose-production-display-dtb.sh` | Compose the default DTB from the overlays. |
| `scripts/host/package-production-modules.py` | Module kit. `configs/kernel/rog5-production-modules.json` names the external module sources in `tools/*` (s12_ufs_vote, wifi_activate, ...). |
| `scripts/device/build-persistent-root-standalone-initramfs.sh` | Production initramfs: `initramfs/persistent-root-*`, `production-*`, `rog5-update`, `configs/production/*.list` and the systemd units it installs. |
| `scripts/host/package-production-ram-trial.py`, `production-ram-trial.py` | RAM trials. They use `prepare-recovery-runtime-bundle.py`, `build-persistent-slotb-recovery-initramfs.sh`, `initramfs/recovery-init`, `tools/recovery_control/rog5-bundle-verify.c`, and the boot tools fetched by `fetch-android-boot-tools.sh`. |
| `scripts/host/install-default-kernel.py` + `scripts/device/install-default-kernel-on-target.sh` | Makes a bundle the default. Loads `build-persistent-wifi-selector.py`, which loads `build-native-wifi-boot-initramfs.py` and so `initramfs/native-wifi/*`. |
| `scripts/host/package-slotb-boot-wrapper.py`, `package-stock-capture-wrapper.py`, `tools/persistent_trial_state/`, `configs/persistent-trial-helper.path` | Rebuild the boot_b wrapper and the stock capture wrapper. |
| `scripts/host/module-loop.py`, `rebase-kernel-series.py`, `rog5-dev` | Development loop and kernel rebase. |
| `scripts/device/bench/*`, `tools/rog5-kms-*.c`, `tools/standby_probe/*`, `tools/status-map/*`, `docs/status/*` | Trials, benches, the status map. |
| `configs/{systemd,polkit,tmpfiles,drirc,environment.d,phosh,applications,udev,wireplumber,firewall,NetworkManager,dconf,journald,production}` | Phone configuration. Some of it is installed by the initramfs kit; the rest is copied to the phone by hand. No script deploys it. |
| `scripts/device/rog5-*`, `third_party/hexagonrpc/*`, `packaging/arch/phoc/*`, `packages/resources/*` | Phone daemons (sleep policy, desktop mode, touchpad, USB sleep, perf mode, powerd, healthd, charge limit, bottom USB, sensors), hexagonrpcd, patched phoc, Resources. |

Registered tests were sorted into four groups:

- **live:** the test references product code and its name doesn't match a
  historical family.
- **review:** it references product code but its name matches a historical
  family (network-root, headless, storage-layout, generation, consume,
  retention, a660, qmp-ufs, ...).
- **retarget-7.2.7:** it tests a 7.1.4 patch that the 7.2.7 series still
  carries under the same name.
- **archive:** it references no product code.

Files touched since 2026-09-15 are held back as "recent", whatever their
class, so a human looks at them first. So are unregistered `test-rog5-*`
scripts (for example `test-rog5-perf-mode.sh`, which tests a live daemon but
isn't registered) and the post-wipe restoration files.

Two caveats:

- Paths built at runtime (f-strings, `$var/name`) aren't seen. The runner and
  `--prepare-only` checks in section 4 catch those.
- "Live test or CI" is an upper bound. Four live-looking tests import the
  historical S12/live-cycle, display-controller and startup-observer chains:
  - `test-production-display-health.py`
  - `test-startup-observer.py`
  - `test-source-teardown-observation.py`
  - `test-persistent-power-readiness.py`

  Three server-era evidence tests do the same (`test-repeated-boot-evidence.py`,
  `test-powered-off-start-evidence.py`, `test-current-persistent-root-storage-profile.sh`).
  Together they pull in about 530 files, including all 178 in
  `configs/recovery-candidates`. With those seven decoupled and the 7.1.4
  default removed (Phase 2), the live set is about 570 files: 341 product plus
  231 tests, CI and dependencies.

### 2.2 Per-directory result (HEAD `1c490e07`)

| Path | Files | product | tests/CI | retarget | Denial | recent | review | archive | evidence | docs |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `test-results` | 1163 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1163 | 0 |
| `scripts/device` | 804 | 52 | 197 | 34 | 0 | 65 | 7 | 449 | 0 | 0 |
| `scripts/host` | 675 | 17 | 178 | 4 | 3 | 27 | 33 | 413 | 0 | 0 |
| `configs` | 296 | 78 | 199 | 3 | 1 | 4 | 1 | 10 | 0 | 0 |
| `manifests` | 171 | 0 | 9 | 0 | 0 | 0 | 32 | 130 | 0 | 0 |
| `tools` | 143 | 40 | 15 | 0 | 53 | 5 | 8 | 22 | 0 | 0 |
| `patches/` (userspace, 5.4, other) | 85 | 0 | 19 | 0 | 51 | 14 | 0 | 1 | 0 | 0 |
| `patches/linux-7.2.7` | 81 | 81 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `docs` | 76 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 76 |
| `initramfs` | 53 | 34 | 7 | 0 | 0 | 1 | 2 | 9 | 0 | 0 |
| `patches/linux-7.1.4` | 46 | 0 | 46 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| root files, dot-dirs, `containers`, `third_party`, `packages`, `artifacts` | 44 | 9 | 27 | 0 | 0 | 1 | 0 | 4 | 0 | 3 |
| `tests` | 43 | 0 | 32 | 0 | 0 | 0 | 0 | 11 | 0 | 0 |
| `dts` | 40 | 24 | 5 | 0 | 0 | 0 | 0 | 11 | 0 | 0 |
| `packaging` | 37 | 6 | 29 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| **Total** | **3757** | **341** | **763** | **41** | **108** | **117** | **83** | **1062** | **1163** | **79** |

`patches/linux-7.1.4` is live today only because `test-production-kernel-build.py`
reads its 0040 patch and the 7.1.4 policy through the builder's defaults.
Phase 2 removes that.

Archive and review candidates by family (archive / review):

| Family | archive | review |
|---|--:|--:|
| A660 / GPUCC / CCF / GMU / SMMU diagnostic generations | 186 | 1 |
| local-image-* staging v1-v49 (+ initramfs `local-image-stage-*-init`, `manifests/local-image-*`) | 140 | 0 |
| network-root era | 108 | 1 |
| storage-layout stage 1/2 | 43 | 39 |
| generation-N / `consume-*-claim` | 55 | 1 |
| stable-recovery / wrapper / recovery-control | 53 | 6 |
| Wi-Fi bring-up probes | 43 | 0 |
| qmp-ufs / UFS discovery stage patches | 29 | 0 |
| minimal headless server acceptance, soak, durability | 28 | 6 |
| display controller (7.1.4 era) | 14 | 4 |
| watchdog / softdog probes | 13 | 1 |
| persistent-root v9-v17 / power-usb | 12 | 0 |
| charging / Alpine / stock | 11 | 6 |
| Windows host era (`*.ps1`) | 11 | 0 |
| retention-cycle | 9 | 1 |
| early-target diagnostics | 8 | 2 |
| other (`arch-successor`, `vpn-hotspot`, `key-indicator`, old DT candidates, `sources.tsv`, ...) | about 300 | about 20 |

### 2.3 Sizes

| Item | Size |
|---|---|
| `test-results/` | 28 MB. 1,034 flat reports (205 from July, 448 from August, 381 from September) plus 5 subdirectories with 129 files. |
| `scripts/` | 14.6 MB tracked (23 MB on disk with caches). `run-stable-recovery-live-gate.sh` alone is 521 KB. |
| `manifests/` | 4.4 MB. `artifact-sets.json` is 3.4 MB. |
| `docs/` | 4.2 MB, including a 2.4 MB PNG. `current-state.md` is 318 KB; `development-lessons.md` is 282 KB. |
| `artifacts/` (ignored, local only) | 2.8 GB on disk. 3 tracked files (5.8 MB `network-root-v3` initramfs used by the CI qemu job). |
| Git | 1.72 GiB packs; 1.9 GB gitdir (see section 5). `/home` is 96% full with 39 GB free. |

### 2.4 Test tiers

- 405 registered tests: `active` 146, `ci` 373, `quick` 384, `nightly` 389,
  `probe` 59, `board` 9.
- In `active`, 44 tests exercise current code, 31 are Denial/QEMU UI and 71
  are historical or review.
- Last green `active` run (2026-09-23, 140 PASS): the three slowest tests are
  all 7.1.4 display-controller tests.
  - `test-production-display-health-binding.py` took 249 s.
  - `test-production-cold-boot.py` took 181 s.
  - `test-production-display-worker.py` took 67 s.
- Last local `active` attempt (2026-09-26): 11 PASS, 2 FAIL (both QEMU/Denial:
  `test-qemu-mobile-observer.py`, `test-qemu-screencopy.py`), 131 BLOCKED.
- Registration is written three times and must agree:
  - the rows in `configs/repository-tests.json`;
  - the shell arrays in `scripts/host/test-repository-linux.sh`
    (`repository-test-report.py init` fails if they differ);
  - the special-case path lists in `select-repository-test-tier.py`.

### 2.5 Stale or misleading files

| File | Problem | Proposed fix |
|---|---|---|
| `docs/current-state.md` header | Says 7.2.7 r93/r98 with fallback safe-r2. The rest is a 318 KB log from July to September. | Phase 5: short, generated. The log moves to `docs/history/`. |
| `configs/project-status.json`, `configs/mobile/{acceptance,session-policy,trial-plans}.json`, `scripts/host/check-mobile-status.py`, `test-mobile-status.py` | Generate the stale header and enforce headless S06/R01 rows from September 10. | Retire. `docs/status/components.json` is the source. |
| `manifests/current-artifact.json` | Last observed runtime 7.1.4 (2026-09-20). Nothing in product reads it. | Retire with `manifests/` (Phase 6). |
| `manifests/*` (171) | Generation manifests and artifact catalogs for the July/August artifacts. Only historical tests and one CI job read them. | Archive. Keep a redacted "current bundle" block in `docs/current-state.md`. |
| `docs/port-status.md` | Table from July (7.1 base, "GPU v9 consumed", Wi-Fi "no radio evidence"). CLAUDE.md milestone 8 points at it. | Replace with components.json and archive the doc. |
| `docs/builds-and-artifacts.md` | "Development follows Linux 7.1.4"; 84 KB of generation records. | Rewrite as one page for 7.2.7; the old one goes to history. |
| `ROADMAP.md` | Written 2026-09-12; Denial is the selected compositor. | Rewrite from `docs/whats-left.md`. |
| `CLAUDE.md` | Goal and milestones still Denial-centred; fallback given as `production-7.2.7-safe-r2` (current is safe-r6); points at `manifests/current-artifact.json` and `sed -n 1,8p docs/current-state.md`. | Update in Phase 5 together with the entry points. |
| `docs/test-plan.md`, `release-acceptance.md`, `network-root.md`, `minimal-headless-live-cycle.md`, `recovery-control-plane.md`, `kernel-port.md`, `arch-linux.md`, `core-compatibility-oracle.md`, `core-source-dtb-contract.md`, `thermal-policy-static-oracle.md`, `reusable-recovery-claim-model.md`, `dedicated-linux-layout-v1.md`, `host-storage-cleanup.md`, `artifact-retention.md`, `repository-governance.md`, `mobile-power-policy.md`, `mobile-trial-plans.md`, `godshell.md` | No mention of 7.2.7; they describe superseded flows. | `docs/history/` (Phase 5). |
| `.github/workflows/offline-smoke.yml` | `board-production` fetches v7.1.4 and its path filter watches `patches/linux-7.1.4/`. `candidate-publication` verifies the historical power-usb lock. `qemu-system` boots the network-root NFS image. | Phase 1c and Phase 3. |
| The archive checkout's `CLAUDE.md` (outside this repo) | Names `rog5-review-correctness-20260912-r1` as the active project. Work happens in `rog5-prod-boot-20260923`. | Tell the user; it's outside this repo. |

## 3. Target layout

Keep the top level. Shrink what's inside it:

```text
README.md  ROADMAP.md  CLAUDE.md
configs/          phone and build configuration (kernel/ keeps 7.2.7 only)
dts/qcom/         production DT + overlays actually composed
initramfs/        production, slot-B loader, recovery-init, stock capture, native-wifi
patches/
  linux-7.2.7/    production series (the only kernel series in the tree)
  asus-5.4.210/   provenance of the pinned wrapper kernel (6 files, kept)
  denial/ ...     only if Denial stays (Phase 4)
scripts/host/     live host tools, their tests, test runner
scripts/device/   live phone tools, daemons, bench/, their tests
tools/            live helpers (module sources named by rog5-production-modules.json, kms, probes)
packaging/ packages/ third_party/ containers/   as today, minus Alpine/historical
tests/fixtures/   only fixtures of live tests
test-results/     unchanged + generated README.md index
docs/
  README.md                 index
  current-state.md          short, generated (default, fallback, open items)
  development.md            how to build, trial, install, rescue (+ curated pitfalls)
  status/                   components.json, whats-left.md
  hardware/                 stock-comparison, audio, sensors, touch, bootloader assessment
  reviews/                  unchanged
  history/                  codex-era, current-state log, lessons log, archived docs, archived-files index
```

Decisions:

- **Historical code: archive tag plus `git rm`, not a `git mv` into
  `archive/`.** Archived scripts refer to themselves by repo-relative paths
  (`REPO/'scripts/host/...'`), and hash pins (`source-pins.json`,
  `display-component.py` `SOURCE_PINS`, `patches/display-controller`) are keyed
  by path. Moved copies would be broken. They would still inflate `git grep`
  and still pass through the runner's syntax checks. An annotated tag keeps
  them runnable at their original paths:
  `git worktree add --detach /tmp/x archive/pre-restructure-20261001`.
  This follows the existing precedent `archive/pre-stable-recovery-2026-07-28`
  (see [archive-index.md](archive-index.md)). A generated
  `docs/history/archived-files.tsv` records every removed path with its
  family, so later readers can find it.
- **`test-results/`: don't move files.** 534 Markdown links in
  README/ROADMAP/docs and 70 code files use exact paths, and dated results
  must not be rewritten. Add a generated `test-results/README.md` index by
  month instead, with each report's first heading. Keep the flat date-prefixed
  naming for new reports; it already sorts by month.
- **7.1.4 trees** (`patches/linux-7.1.4`, `configs/kernel/rog5-production-build.json`,
  `rog5-production-warning-policy.json` and the 7.1.4-only fragments
  `rog5-display-60hz`, `rog5-ufs-discovery`, `rog5-ufs-local-write`,
  `rog5-a660-registration`, `rog5-stable-wrapper-slim-v1*`,
  `rog5-network-root`, `rog5-suspend-pm-test`, `rog5-tailscale-netfilter`):
  archive them after Phase 2. `rebase-kernel-series.py` rebuilds any series
  from the tag if ever needed.
- **Userspace patch sets.**
  - `patches/runtime/` (A660 v6-v10 probes): archive.
  - `patches/display-controller/`: archive with the display-controller family.
    It is pinned downstream only by archived tests.
  - `patches/linux/{device,diagnostic}` (3 files): archive. The ath11k WCN6851
    patch is in the 7.2.7 series.
  - Denial, Flutter, GTK, Wayland, `vector_graphics`, `flutter_svg`,
    `denial-engine`: Phase 4 decision.
- **`manifests/`: retire the directory.** Its only remaining job, "what is
  installed", belongs in a redacted block of `docs/current-state.md`, written
  from the private install descriptor.
- **Docs: few moves, stable entry points.** `docs/current-state.md`,
  `docs/development.md` and `docs/active-context.md` must exist (the runner
  checks them), and CLAUDE.md, skills and 5 code files name them. Keep those
  paths and shrink the contents. Only 25 links from `test-results/` point into
  `docs/`, and several are already broken, so moving other docs costs little.
  No redirect stubs are needed.

## 4. Migration, step by step

### 4.0 Ground rules

- Work in a separate worktree so the production worktree stays clean
  (`install-default-kernel.py` refuses to stage from a dirty repo) and phone
  work continues:
  `git -C ~/.local/state/rog5-prod-boot-20260923 worktree add -b agent/repo-restructure-20261001 ~/.local/state/rog5-restructure-20261001 HEAD`.
  Rebase onto `agent/production-boot-20260923` before each phase. Merge each
  phase as soon as its checks pass; no long-lived divergence.
- One family or one mechanism per commit, so any commit can be reverted
  alone (`git revert <sha>`). Never mix a deletion with a behaviour change.
- No moves of live files, no content edits to dated `test-results/`, no
  history rewriting, no pushes. Publishing stays the filter-repo flow (see
  "Risks").
- Don't run `git gc`, `git prune`, `git repack -a -d` or `git worktree prune`
  in any of the shared gitdirs.

### 4.1 Standard checks (referenced as K1-K7)

- **K1 clean tree.** `git status --short` is empty after the commit, and
  `git show --stat HEAD` lists only the intended files.
- **K2 no dangling references.** For every path the commit deleted or renamed,
  there must be no mention left outside history:

  ```sh
  git diff --name-status HEAD~1 HEAD | awk '$1 ~ /^[DR]/ {print $2}' |
  while read -r p; do
    git grep -n -F -e "$p" -e "$(basename "$p")" -- . \
      ':!test-results' ':!docs/history' ':!docs/archive' ':!docs/repo-restructure-plan.md' |
      grep -v -F 'archived-files.tsv' && echo "DANGLING $p"
  done
  ```

  Any `DANGLING` line fails the step unless it is an intended textual mention.
  Rerun Appendix A and confirm no `live-*` file changed class.
- **K3 product unit suites** (each standalone, seconds):

  ```sh
  for t in scripts/host/test-production-kernel-build.py scripts/host/test-package-production-modules.py \
    scripts/host/test-production-ram-trial.py scripts/host/test-install-default-kernel.py \
    scripts/host/test-module-loop.py scripts/host/test-rebase-kernel-series.py \
    scripts/host/test-build-persistent-wifi-selector.py scripts/host/test-persistent-trial-state.py \
    scripts/host/test-recovery-init-policy.py scripts/device/test-production-platform-kit.py \
    scripts/device/test-production-wifi.py scripts/device/test-rog5-update.py \
    scripts/device/test-standalone-production-tree.py scripts/device/test-production-trial-commit.py \
    scripts/device/test-slotb-ram-bundle.py scripts/device/test-usb-storage-scope.py \
    scripts/device/test-rog5-healthd.py scripts/device/test-rog5-powerd.py \
    scripts/device/test-mobile-dt-guards.py scripts/device/test-mobile-touch-providers.py; do
    python3 "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done
  ```

  Shell suites (`test-persistent-slotb-loader.sh`, `test-persistent-slotb-recovery-loader.sh`,
  `test-rog5-sleep-policy.sh`, `test-rog5-perf-mode.sh`, `test-rog5-hotspot-uplink.sh`)
  run under the real ARM64 busybox, as CLAUDE.md describes.
- **K4 runner, `active` tier,** in the recorded environment from CLAUDE.md,
  with a new report directory. It passes when `summary.json` shows every
  selected test PASS, and when the selected set equals the previous run's set
  minus the tests this step intentionally removed (compare `selection.json`).
- **K5 static preflight** (Markdown links, shell and Python syntax, secret
  scan). Today these run only inside the runner, and the syntax check runs
  only in non-`active` tiers. Phase 1b makes them one command:
  `python3 scripts/host/check-repository-static.py`.
- **K6 kernel dry run** (any step touching `configs/kernel`, `patches/`,
  `dts/`, the builder or its recorded inputs):

  ```sh
  out=~/.local/state/rog5-restructure-prep-$(git rev-parse --short HEAD)
  PATH=~/.local/state/rog5-host-tools/dtschema-2026.6/bin:$PATH \
  python3 scripts/host/build-rog5-production-kernel.py \
    --config configs/kernel/rog5-production-build-7.2.7.json \
    --linux-git ~/.local/state/rog5-linux-stable-git --output "$out" --jobs 2 --prepare-only
  python3 - "$out/result.json" ~/.local/state/rog5-restructure-prep-baseline/result.json <<'PY'
  import json, sys
  a, b = (json.load(open(p)) for p in sys.argv[1:])
  keys = ('status', 'production_series_binding_sha256', 'config_sha256', 'base_archive_sha256', 'patch_dir')
  assert all(a[k] == b[k] for k in keys), {k: (a[k], b[k]) for k in keys if a[k] != b[k]}
  assert a['inputs'] == b['inputs'], set(a['inputs']) ^ set(b['inputs'])
  print('K6 PASS', a['status'], a['config_sha256'][:12])
  PY
  rm -rf "$out"   # the extracted source tree is large; keep the 3 GiB reserve
  ```

  `status` must be `PREPARED`. The series binding, config hash and every
  recorded input hash must be identical to the baseline (Phase 0). A step that
  intentionally changes a recorded input must list it in its commit message.
- **K7 CI tiers** (end of each phase, not per commit): run the runner's `ci`
  tier locally, and `probe` and `board` where their inputs exist. GitHub CI
  sees the change only at the next public publish.

### 4.2 Phases

**Phase 0: freeze and baseline** (no content change).

1. `git tag -a archive/pre-restructure-20261001 -m "before repository restructure" HEAD`.
   Keep the tag local only; see Risks.
2. Refresh the backup bundle. It takes about 1.9 GB, so check `df` first:
   `git bundle create ~/rog5-git-backup/rog5-all-refs-20261001.bundle --all`,
   then `git bundle verify` it.
3. Record the baselines:
   - K6 into `~/.local/state/rog5-restructure-prep-baseline/`;
   - a K4 report;
   - the runner's per-tier selection lists;
   - Appendix A's output, committed as `docs/history/restructure-inventory-20261001.tsv`.

Rollback: nothing to roll back.

**Phase 1: make the safety net single-source and green.** Three commits. No
files are removed.

- **1a.** `test-repository-linux.sh` derives each tier's test list from
  `configs/repository-tests.json`, and the shell arrays go. Add
  `--list TIER`. Update the tokens `test-repository-linux-runner-contract.sh`
  greps for (`shared_tests=(`, `tier_tests=()`).
  Check: for every tier, `--list` output equals the Phase 0 selection
  (`diff`); K3; K4.
- **1b.** Factor the two inline Python preflights (syntax, links) and the
  secret grep into `scripts/host/check-repository-static.py`, and have the
  runner call it. Check: K5 passes; a deliberately broken link in a scratch
  copy fails.
- **1c.** CI:
  - Make `fetch-android-boot-tools.sh` resilient. Either cache its pinned
    output with `actions/cache` keyed by the pinned commits, or vendor the two
    pinned Apache-2.0 tools under `third_party/` with their notices. This is
    what failed in the last two runs (HTTP 503 from
    android.googlesource.com).
  - Switch `board-production` to the 7.2.7 base: fetch `v7.2.7`, verify
    `f42acb3678424d1e08f6ed27c0d8ba8a125e14d6` (the local stable Git confirms
    it is the `v7.2.7` tag), and pass
    `--config configs/kernel/rog5-production-build-7.2.7.json`.
  - Set its path filter to `patches/linux-7.2.7/`.

  Check: `test-github-exact-head-workflow.sh` (update it), K5, `actionlint` if
  available. CI itself is confirmed at the next publish.

**Phase 2: decouple live code from history.** Small code edits, no deletions.

- **2a.** In `build-rog5-production-kernel.py`, change the defaults `CONFIG`,
  `PATCHES`, `WARNING_POLICY` and `policy.get('patch_dir', ...)` to 7.2.7.
  Update the example in `rebase-kernel-series.py`'s help text.
  Check: K3; K6 with `--config` (identical except the builder's own recorded
  hash, which is expected to change); K6 without `--config` (must now give
  the same series binding and config hash as the 7.2.7 baseline).
- **2b.** Retarget `test-production-kernel-build.py` to the 7.2.7 policy and
  patch (`0040-drm-msm-adreno-defer-until-iommu-attachment.patch` exists in
  7.2.7), and check `test-package-production-modules.py` and
  `test-rebase-kernel-series.py` the same way.
  Check: K3; K4.
- **2c.** Retarget the 41-file `retarget-7.2.7` group. For example:
  - `test-ncm-tx-timer.py`, `test-qcom-battmgr-charge-units.py`;
  - `test-ams678-*`, `test-asus-s12-oem-point.py`, `test-rpmh-readback.py`;
  - `test-clk-orphan-runtime-pm-current-source-patch.sh`;
  - `test-rog5-rpmh-binding.py`, `test-ufs-storage-trust-boundary.py`,
    `test-qcom-battmgr-asus-cell-voltage-patch.sh`.

  Each one points at the 7.2.7 copy of its patch; fixtures named `*-v7.1.4.c`
  are refreshed from the 7.2.7 tree.

  Where the 7.2.7 patch differs, the test either passes against it or is
  consciously retired. Coverage of a production patch is never dropped
  silently. Check: each test standalone; K4.
- **2d.** Decouple the seven entangling tests from section 2.1. Where one
  tests a live file (for example `initramfs/persistent-startup-observer`),
  extract the few helpers it imports from the historical controller into the
  test or a small live helper. Otherwise reclassify it as review.
  Check: rerun Appendix A; "live-test-or-ci" should fall to about 230; K3; K4.

**Phase 3: archive the unreachable families.** About 15 commits. Each commit:

1. Take the family's files from the current Appendix A output (`archive`
   class only; `recent` and `review` files are excluded until a human clears
   them).
2. `git rm` them.
3. Drop their rows from `configs/repository-tests.json`.
4. Drop their entries in `select-repository-test-tier.py` and its test.
5. Drop `rog5-dev` actions that call them (for example `accept`,
   `check-deployed-server`, `check-standalone-*`, `durability-phase`,
   `check-server-runtime`, `check-rescue-*` belong to the headless-server
   family).
6. Drop CI steps that use them.
7. Rewrite Markdown links in live docs into plain text: "archived in
   `archive/pre-restructure-20261001`: path".
8. Append the family to `docs/history/archived-files.tsv`.

Checks: K1, K2, K3, K4, K5. Add K6 when the family touches `dts/`,
`configs/kernel/` or `patches/`. K7 after the last family.

Suggested order (least coupled first):

1. `*.ps1` Windows host tools (11 files).
2. local-image staging, including `initramfs/local-image-stage-*-init` and
   `manifests/local-image-*` (about 190).
3. qmp-ufs stage patches and their tests (about 30).
4. generation-N and `consume-*-claim` (about 55).
5. retention-cycle and early-target diagnostics (about 20).
6. A660/GPUCC/CCF/GMU/SMMU generations, plus `patches/runtime`,
   `tools/a660` and the `dts` diagnostic overlays (about 200).
7. network-root era, plus the CI `qemu-system` job,
   `tools/qemu-network-root-nfs`, `tools/qemu-smoke` and the 3 tracked
   `artifacts/network-root-v3` files. The last only after the job is gone,
   and adjust the publish filename-callback note.
8. storage-layout stages 1/2 (archive part only).
9. stable-recovery, wrapper and recovery-control candidates, plus
   `configs/recovery-candidates` once Phase 2d has freed them, and the CI
   `candidate-publication` job with `manifests/power-usb-active.lock.json`.
10. minimal headless server acceptance, soak and durability (after 2d).
11. display controller (7.1.4 era), with `patches/display-controller`, its
    pins and fixtures.
12. watchdog/softdog, charging/Alpine/stock (keep `stock-capture-5.4`; it is
    live) and Wi-Fi bring-up probes.
13. `patches/linux-7.1.4` and the 7.1.4 kernel configs (after Phase 2).
14. The remaining "other" files, reviewed by listing.

Rollback: `git revert` the family commit, or restore single files with
`git checkout archive/pre-restructure-20261001 -- <path>`.

**Phase 4: Denial decision** (108 files, 31 `active` tests, about 155 s).

- **Now:** move the Denial/QEMU UI tests from `active` to a new opt-in tier
  `denial`. This is a one-line change per row after Phase 1a. Keep
  `rog5-denial.service` and the sources.
- **Later, once the user confirms Denial is abandoned** (it is still installed
  but not the boot shell; upstream PRs weren't accepted):
  1. Archive `patches/denial*`, `flutter*`, `gtk-*`, `wayland-*`,
     `vector_graphics*`, `flutter_svg*`, `denial-engine`,
     `tools/denial-*`, `tools/qemu-virtio-drm`, `tools/gtk-caret`,
     `tools/wayland-debug`, `configs/denial`, `configs/rog5-desktop`
     (Sway), `configs/systemd-user`, `scripts/host/denial/` and the tier.
  2. Uninstall from the phone separately.
- **If Denial is kept:** move those paths under `patches/denial/` and
  `tools/denial/`, still in the opt-in tier.

Check: K4; the `denial` tier on its own.

**Phase 5: docs and status.** Several commits.

- **5a.** `tools/status-map/render.py` also emits a Markdown status block.
  `docs/current-state.md` becomes a short file (about 80 lines) with a
  generated block: default and fallback bundle, kernel rN, components
  summary, open items. `git mv` the old body to
  `docs/history/current-state-log-2026-07-to-09.md`.
  Retire `check-mobile-status.py`, `test-mobile-status.py`,
  `configs/project-status.json` and `configs/mobile/*.json`.
- **5b.** Curate `development-lessons.md`: keep the checklists and the lessons
  still applicable to 7.2.7 (target 30 KB or less). `git mv` the full file to
  `docs/history/development-lessons-log.md`.
- **5c.** `git mv` the stale documents from the table in 2.5 into
  `docs/history/`, and merge `docs/archive/` into `docs/history/archive/`.
  Move hardware notes (`stock-comparison-plan.md`, `audio-plan.md`,
  `vcnl36866-als-proximity.md`, `front-touch-prototype.md`,
  `hardware-contract.md`, `stock-image-analysis.md`,
  `bootloader-assessment.md`) into `docs/hardware/`. Rewrite
  `docs/README.md` as a short index.
- **5d.** Rewrite `docs/builds-and-artifacts.md` for 7.2.7 (one page).
  Rewrite `ROADMAP.md` from `whats-left.md`. Update CLAUDE.md: goal,
  fallback safe-r6, orientation commands, the status source, and the new
  single-registration rule for tests. Also update the `rog5-fast-loop` skill
  paths.

Checks: K5 (link check), K1, K2, K4 (the runner checks the entry points).

**Phase 6: `manifests/`.** Once Phase 3 has removed the generation
manifests, archive the rest. Change the three remaining readers in the same
commit: `check-artifact-inventory.py`, `build-production-display-modules.py`
(historical) and `test-review-metadata-checkers.py`.
Checks: K2, K4, K7.

**Phase 7: `test-results/` index.** Add a small generator
(`scripts/host/index-test-results.py`) and a generated
`test-results/README.md`, grouped by month, one line per report with its
first heading. No existing file changes.
Check: K5.

**Phase 8: verify and close.**

- Rerun Appendix A.
- Full K6. Then a full kernel build with the documented command into a new
  directory. It must reproduce the installed default's Image and module
  hashes, since the build is deterministic at the same inputs.
- K7 `ci`, `nightly` and `board` tiers.
- At the next planned trial, one RAM trial of an unchanged bundle, to prove
  that packaging and the trial path still work. This is a hardware step; it
  needs the usual preparation.

Expected end state: about 1,200 to 1,400 tracked files. That is 1,163
evidence, about 80 docs and about 570 live files, less whatever the review
buckets clear. The `active` tier would run about 50 tests in 2 minutes or
less.

### 4.3 Risks

| Risk | Where | Mitigation |
|---|---|---|
| Hash pins break | `scripts/device/fixtures/*/source-pins.json`, `display-component.py` `SOURCE_PINS`, `patches/display-controller/*` (pinned downstream), recorded input hashes in kernel build results | Live files are never edited or moved. Families are removed together with their pinned consumers. K4 catches a missed consumer. K6 proves the recorded kernel inputs are unchanged. |
| Hardcoded paths | Runner arrays, registry, `select-repository-test-tier.py` special cases, CI path regexes, `rog5-dev` actions, `configs/kernel/rog5-production-modules.json` (`tools/*` sources), `configs/persistent-trial-helper.path`, `importlib` loads by path in tests | Phase 1a makes the registry the single list. K2 greps every removed path and basename. The runner fails fast on a missing registered test. |
| Dynamic paths the static graph can't see | f-strings and `$repo/$name` in shell | K4 and K6 on every step. `recent` and `review` files are excluded until a human clears them. |
| A deleted file was actually used by hand on the phone or host | Phone-side scripts are copies (`/usr/local/...`), and the phone updater doesn't read the repo. No host systemd user unit or cron job references the repo. | Anything touched since 2026-09-15 is held back. `scripts/device/rog5-*` and `bench/` are product and never move. Restore from the tag in seconds. |
| The production install is blocked | `install-default-kernel.py` requires a clean repo | Do the restructure in a separate worktree and merge per phase. |
| Public publish flow breaks | Publishing re-filters `pubbase..pub` from the untouched `refs/remotes/github/main` with a deterministic filter, drops `artifacts/` except `network-root-v3`, and scans new blobs | Deletions are ordinary commits, and the filter handles them unchanged. Don't push `archive/pre-restructure-20261001`: it points at unfiltered history. If a public archive tag is wanted, create it in the filtered clone on the mapped commit (`.git/filter-repo/commit-map`) and push that one tag explicitly, after user approval. Once `artifacts/network-root-v3` is gone (Phase 3 step 7), the callback's exception becomes a no-op. Update the memory note then. |
| CI is red, so there is no independent check | GitHub `head-exact` fails before tests | Phase 1c comes first. Until CI is green, K4 and K7 locally are the gate. |
| Registration drift | Adding tests after Phase 1a | CLAUDE.md is updated in Phase 5d. The runner-contract test asserts the arrays are gone. |
| Private evidence names repo paths | `~/.local/state/rog5-*` records and the wf-scratch `BOOT-CHAIN.md` cite script paths | Those are records, not code. The tag keeps every cited path reachable. |

## 5. Local Git history: recommendation, not action

Facts:

- The shared gitdir `~/.local/state/rog5-haven-clean-ci-20260810/.git` is
  1.9 GB (1.72 GiB packs). It serves 5 worktrees and borrows from
  `~/Projects/rog-phone-linux-migration/repo/.git/objects` through alternates
  (96 MB).
- 79 blobs over 10 MiB make up 1.76 GiB. All of them are July/August
  `artifacts/*/initramfs.cpio.gz` files (storage-layout stage 2,
  persistent-native-root). 84 large artifact blobs are reachable from the
  current branch's HEAD history, so no `gc` can drop them. Only a history
  rewrite could.
- The backup bundle `~/rog5-git-backup/rog5-all-refs-20260923.bundle` is
  1.88 GB. `/home` has 39 GB free.
- GitHub reports about 1.8 GB for the public repository as well.

Recommendation: **don't compact now.** A rewrite would:

- change every commit ID on shared branches, and break the other four
  worktrees' branches;
- break the public publish flow, which depends on the untouched
  `refs/remotes/github/main` (`3cc3f443`) and on re-filtering `pubbase..pub`
  deterministically, so the next push would stop being a fast-forward;
- invalidate the commit IDs cited in `docs/`, `test-results/` and the
  private evidence;
- risk the alternates relationship. Repacking one repo can drop or duplicate
  objects the other relies on.

The payoff (about 1.7 GB, 4% of free space) doesn't justify that. The file
pruning above doesn't reduce Git size at all; it makes the working tree and
the tests smaller.

If disk becomes the bottleneck later, the only safe route is a cut-over to a
new repository. The old gitdir, worktrees, alternates and bundle stay
untouched as the cold archive:

1. `git clone --no-local` the current branch into a new directory.
2. `git filter-repo --path artifacts/ --invert-paths`, keeping only
   `artifacts/network-root-v3` if it still exists.
3. Make the new clone the working repo. Its publish flow needs a new
   `pubbase` mapping, documented before the first push.

Do this only as its own reviewed task with user approval.

## Appendix A: inventory script

Run from the repository root:
`python3 inventory.py . > inventory.tsv`, then
`cut -f1 inventory.tsv | sort | uniq -c`. It has no side effects and takes
about 2 s.

```python
#!/usr/bin/env python3
"""Classify every tracked file of the ROG5 repo as live or historical (static, conservative).

Usage: inventory.py REPO > inventory.tsv   (columns: category, path)
Edges: any token in a text file that names another tracked path (full, suffix,
own-directory relative, or a unique basename), plus same-directory Python imports.
Fixture files, catalogs, Markdown and the test registry/runner are leaves: they
are kept if referenced but never make what they mention live.
"""
import collections, fnmatch, json, os, re, subprocess, sys

repo = sys.argv[1]; os.chdir(repo)
files = [f for f in subprocess.run(['git', 'ls-files', '-z'], capture_output=True, check=True).stdout.decode().split('\0') if f]
fileset = set(files)
dirfiles = collections.defaultdict(list)
for f in files:
    p = f.split('/')
    for i in range(1, len(p)): dirfiles['/'.join(p[:i])].append(f)
GENERIC_DIRS = {'scripts', 'scripts/host', 'scripts/device', 'configs', 'docs', 'test-results', 'patches', 'manifests', 'tools', 'dts',
                'initramfs', 'packaging', 'tests', 'third_party', 'containers', 'artifacts', 'build', '.github', 'tests/fixtures',
                'docs/archive', 'configs/kernel', 'dts/qcom', 'scripts/device/fixtures', 'scripts/host/fixtures'}
GENERIC_NAMES = {'README.md', 'Makefile', 'COPYING', 'cpio', 'gzip', 'init', 'failure', 'healthy', 'radio', 'runtime', 'timing', 'user',
                 'Dockerfile', 'PKGBUILD', 'LICENSE', 'cases.c', 'stubs.h', 'source-pins.json', 'init.c'}
byname = collections.defaultdict(list)
for f in files: byname[f.rsplit('/', 1)[-1]].append(f)
TOK = re.compile(r'[A-Za-z0-9_.@+\-/]+')
IMP = re.compile(r'^\s*(?:from\s+([A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z0-9_\., ]+))', re.M)

def edges_of(f):
    out = set()
    if f.startswith(('test-results/', 'docs/')): return out
    try: raw = open(f, 'rb').read()
    except OSError: return out
    if b'\0' in raw[:8192]: return out
    text = raw.decode('utf-8', 'replace'); fdir = f.rsplit('/', 1)[0] if '/' in f else ''
    for t in set(TOK.findall(text)):
        t = t[2:] if t.startswith('./') else t
        t = t.rstrip('/.,'); hit = False
        for i in [0] + [m.start() + 1 for m in re.finditer('/', t)]:
            for s in (t[i:], (fdir + '/' + t[i:]) if fdir else t[i:]):
                if s in fileset: out.add(s); hit = True; break
                if s in dirfiles and s not in GENERIC_DIRS and '/' in s: out.update(dirfiles[s]); hit = True; break
            if hit: break
        if hit: continue
        b = t.rsplit('/', 1)[-1]
        if b in byname and b not in GENERIC_NAMES:
            c = byname[b]; same = [x for x in c if x.rsplit('/', 1)[0] == fdir]
            out.update(c if len(c) == 1 else (same or c))
    if f.endswith('.py'):
        for m in IMP.finditer(text):
            for n in re.split(r'[ ,]+', m.group(1) or m.group(2) or ''):
                c = fdir + '/' + n.split('.')[0].strip() + '.py'
                if c in fileset: out.add(c)
    out.discard(f); return out

E = {f: edges_of(f) for f in files}
# The 7.2.7 build names 7.1.4 only as argparse defaults and in help text; that is a coupling to fix, not a dependency.
for b in ('scripts/host/build-rog5-production-kernel.py', 'scripts/host/rebase-kernel-series.py'):
    E[b] = {t for t in E[b] if not t.startswith('patches/linux-7.1.4/') and t not in (
        'configs/kernel/rog5-production-build.json', 'configs/kernel/rog5-production-warning-policy.json')}
LEAVES = {'configs/repository-tests.json', 'scripts/host/test-repository-linux.sh', 'scripts/host/rog5-dev', 'CLAUDE.md', 'README.md',
          'ROADMAP.md', '.github/workflows/offline-smoke.yml', 'scripts/host/select-repository-test-tier.py',
          'scripts/host/test-select-repository-test-tier.py', 'manifests/artifact-sets.json', 'configs/release-acceptance.json',
          'manifests/artifacts.tsv', 'manifests/current-artifact.json'}
def leaf(f): return f in LEAVES or f.endswith('.md') or '/fixtures/' in f or f.startswith(('test-fixtures/', 'tests/fixtures/'))
def closure(seeds):
    seen = set(seeds); st = list(seeds)
    while st:
        f = st.pop()
        if leaf(f): continue
        for t in E[f]:
            if t not in seen: seen.add(t); st.append(t)
    return seen
def glob(pats): return {f for p in pats for f in files if fnmatch.fnmatch(f, p)}

PRODUCT = glob([
    'scripts/host/build-rog5-production-kernel.py', 'configs/kernel/rog5-production-build-7.2.7.json',
    'configs/kernel/rog5-production-warning-policy-7.2.7.json', 'patches/linux-7.2.7/*',
    'scripts/device/compose-production-dtb.sh', 'scripts/device/compose-production-display-dtb.sh',
    'scripts/host/package-production-modules.py', 'scripts/device/build-persistent-root-standalone-initramfs.sh',
    'scripts/host/package-production-ram-trial.py', 'scripts/host/production-ram-trial.py',
    'scripts/host/install-default-kernel.py', 'scripts/device/install-default-kernel-on-target.sh',
    'scripts/host/rebase-kernel-series.py', 'scripts/host/module-loop.py', 'scripts/host/rog5-dev',
    'scripts/host/package-slotb-boot-wrapper.py', 'scripts/host/package-stock-capture-wrapper.py',
    'scripts/host/fetch-android-boot-tools.sh', 'scripts/host/build-canonical-boot-v3-template.sh',
    'tools/persistent_trial_state/*', 'configs/persistent-trial-helper.path',
    'scripts/device/bench/*', 'tools/rog5-kms-*.c', 'tools/standby_probe/*', 'tools/status-map/*', 'docs/status/*',
    'configs/systemd/*', 'configs/systemd/*/*', 'configs/polkit/*', 'configs/tmpfiles/*', 'configs/drirc/*',
    'configs/environment.d/*', 'configs/phosh/*', 'configs/applications/*', 'configs/udev/*', 'configs/wireplumber/*',
    'configs/firewall/*', 'configs/NetworkManager/**', 'configs/dconf/**', 'configs/journald/*', 'configs/production/*',
    'scripts/device/rog5-*', 'third_party/hexagonrpc/*', 'packaging/arch/phoc/*', 'packages/resources/*'])
product = closure(PRODUCT)
CI = glob(['scripts/host/test-repository-linux.sh', 'scripts/host/repository-test-report.py', 'scripts/host/select-repository-test-tier.py',
           'scripts/host/repository-test-workers.py', 'scripts/host/record-ci-environment.sh', '.github/*', '.github/*/*',
           'configs/repository-tests.json', 'scripts/host/test-repository-linux-runner-contract.sh',
           'scripts/host/test-repository-test-report.py', 'scripts/host/test-select-repository-test-tier.py',
           '.agents/**', '.claude/**', '.gitignore', '.gitattributes', '.dockerignore', 'skills-lock.json',
           'patches/asus-5.4.210/*'])  # provenance of the pinned ASUS 5.4 wrapper kernel
registry = [t['path'] for t in json.load(open('configs/repository-tests.json'))['tests']]
HIST = re.compile(r'network-root|headless|storage-layout|retention|generation|charging|alpine|minimal|recovery-profile|local-image|'
                  r'power-usb|early-target|candidate|stable-recovery|stable-wrapper|deployment|live-cycle|admission|dual-cell|a660|'
                  r'qmp-ufs|gpucc|ccf|soak|release-|rescue|durability|stock-|timeout-lattice|recovery-(control|fetch|host|progress)|'
                  r'podman|host-storage|isolated-recovery|verified-|check-(deployed|standalone)|server-runtime|github-exact|qemu-|'
                  r'logind|denial|launcher|caret|mobile-status|buttons-indicator|core-(compat|source)|collect-|observe-|prepare-|'
                  r'consume-|sequence|transaction|executor|descriptor|package-closure|native-kexec|mainline-|qcom-wdt|thermal|suspend-pm')
code_product = {f for f in product if not f.startswith(('configs/kernel', 'dts/', 'patches/', 'test-results', 'docs'))} - {'scripts/host/rog5-dev'}
live_tests = {t for t in registry if (E[t] & code_product) and not HIST.search(t.rsplit('/', 1)[-1])}
review_tests = {t for t in registry if (E[t] & code_product) and t not in live_tests}
recent = set(subprocess.run(['git', 'log', '--since=2026-09-15', '--name-only', '--format='], capture_output=True, text=True).stdout.split())
DENIAL = glob(['patches/denial*/**', 'patches/flutter*/**', 'patches/gtk-*/**', 'patches/wayland-*/**', 'patches/vector_graphics*/**',
               'tools/denial-*/**', 'tools/qemu-virtio-drm/**', 'tools/gtk-caret/**', 'tools/wayland-debug/**',
               'configs/denial/**', 'configs/rog5-desktop/**', 'configs/systemd-user/**', 'scripts/host/denial/**'])
keep = product | closure(live_tests) | CI
review = closure(review_tests) - keep
# Tests of a 7.1.4 patch that the 7.2.7 series still carries (same name after the number): retarget, don't archive.
ported = {n[5:] for n in os.listdir('patches/linux-7.2.7')}
retarget_tests = {t for t in registry if any(r.startswith('patches/linux-7.1.4/') and r.rsplit('/', 1)[-1][5:] in ported for r in E[t])}
retarget = closure(retarget_tests) - keep - {f for f in files if f.startswith('patches/linux-7.1.4/')}
for f in files:
    if f.startswith('test-results/'): c = 'evidence'
    elif f.startswith('docs/') or f in ('README.md', 'ROADMAP.md', 'CLAUDE.md'): c = 'docs'
    elif f in product: c = 'live-product'
    elif f in keep: c = 'live-test-or-ci'
    elif f in DENIAL: c = 'denial-dormant'
    elif f in retarget: c = 'retarget-7.2.7'
    elif f in recent or re.search(r'scripts/[^/]+/test-rog5-|post-wipe', f): c = 'recent-review'
    elif f in review: c = 'review'
    else: c = 'archive'
    print(c + '\t' + f)
```
