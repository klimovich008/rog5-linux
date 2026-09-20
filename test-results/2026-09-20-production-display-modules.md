# Production display module subset — 2026-09-20

**Offline inert packaging only; no phone operation or new boot candidate.**
Previous turn was progress (loader ordering regression/repair); this turn is
progress (validated current production module input for its successor).

Start `33ef860ad9552fc32c61b127bd941d66590075ac`, tree `7df82f6acd47435817c14f39323bb821bf85f355`.
Frozen implementation `2fdd26fc07a9977d6bdaad24af3240306064be23`, tree `dedb20de81a332794513e67c320eb3c8ae96670d`.
Kernel inputs remain the existing qualified board source
`8f7b2f83b59b37c8a7cd53b78610d0b1db0896fc` and Linux `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`.
No kernel/module/DT rebuild or device test was performed.

## Implemented

`build-production-display-modules.py` reads the current-artifact pointer and
validates the bound qualification, module provenance and dependency-index hashes.
It selects only the fixed REFGEN/GPUCC/panel/MSM roots and their declared symbol
dependencies, preserving legitimate transitive depmod edges. It validates actual
ARM64 relocatable ELF bytes, full vermagic, name/depends/firmware metadata and the
qualified default-dark panel hash. Selected soft/weak dependencies require review
instead of implicit expansion. Symlinks, changed bytes and existing outputs fail.

The deterministic tar embeds its manifest with exact input identities and
builder/checker hashes. An exclusive atomic publication cannot replace another
writer. It contains modules and metadata only: no helper, service, autoload,
firmware, boot image, signature or claim. The historical loader is unchanged.
No active builder selects this fixture by its directory name.

Review demonstrated two defects in the initial new implementation. An extra
modules.dep edge could add an unrelated module; selection now follows declared
ELF dependencies and rejects edges outside their transitive closure. Firmware
normalization also accepted null/false/zero/objects; only a list or the historical
empty string is now accepted. Failing-before logs are preserved. The first falsy
subcase test left its unexpected output behind; fixture cleanup was corrected
before repeating the control, which independently failed for all four values.
These were new packager defects, not evidence of current-cohort corruption.

## Personally executed results

- Initial22 semantic tests PASS,0.916s; after bounds/canonical firmware update,
  22PASS,0.916s.
- Review counterexamples before fix:2test methods,5expected failures,0.599s.
- Final25 semantic tests PASS,1.213s. They compile inert ARM64 .modinfo ELF fixtures
  with clang and inspect them with real modinfo; no module is inserted.
- Selector/workflow regression:37PASS,0.642s. Native CI explicitly installs kmod;
  environment receipts include modinfo/depmod. GitHub CI was not run here.
- Two real production subset archives PASS: 0.332s
  and 0.320s; 0.665s total.
  Every archived member matched its source pin.14modules;3,010,560bytes each.
- Frozen integrated active tier: 114PASS/0FAIL/0BLOCKED/
  0SKIPPED suites,255NOT_SELECTED; 207.887s. Three declared
  optional historical subchecks are separately skipped.

Archive SHA256: `37835ca7455c3f654b5f1de432cf91992550ef1767ed89b641bd3b15f26c87a1`.
Embedded manifest SHA256: `ec9e258cce646d6f0981adf6e7d08a3b7817260f2563acbc1f326a14c5e1b2f8`.
Qualification SHA256: `6bf0e36e208fc37c13b3ba0c3495a00ea34be540dc6bd7e4bc1d2a0a95b63d3f`.

The private twin archives live under `rog5-production-display-modules-20260920-r1`
in the host state directory and are registered as one **fixture** set. No generated
binary was added to Git. The [qualification record](2026-09-20-production-display-modules-qualification.json)
contains commands, tool hashes/versions, selected test durations, archive/module
identities and JSON/JUnit/log hashes. Build owner:512MiB/no swap,1CPU,64tasks,120s;
actual peak31.2MiB. Integrated owner:1GiB/no swap,2CPUs,256tasks,600s; two workers.
Scratch and outputs are disk-backed; initial free disk219GiB.

Focused commands: `python3 -O scripts/device/test-production-display-modules.py`,
its two named review controls, and `python3 -O scripts/host/test-select-repository-test-tier.py`.
Production command: `python3 -O scripts/device/build-production-display-modules.py
--output /absolute/new.tar` (exact twin paths retained in qualification).
Integration: `scripts/host/test-repository-linux.sh active` on frozen source.

## Remaining activation boundaries

The14-module result is **symbol dependency closure, not hardware load order**.
DT/provider edges include REFGEN supplying the DSI PHY, GPUCC supplying GMU/SMMU
clock/power, panel supplies/GPIOs and the MSM DSI host. Exact GPUCC probe configures
two PLLs; MSM client/fbcon registration can trigger panel preparation. `msm_open()`
calls `load_gpu()`, so opening a DRM node is an activation boundary too.

All14 modules have empty modinfo firmware metadata. The exact A660 catalog still
names `a660_sqe.fw` and `a660_gmu.bin`; the active GPU overlay names
`qcom/sm8350/a660_zap.mbn`. This archive packages or qualifies none of them.
Empty metadata must not become a firmware-complete claim.

Next offline step: consume this exact inert subset in a successor that verifies
members before staging, binds current board/firmware/endpoint identity, and
qualifies provider-before-consumer activation with the default-dark ordering
repair, one-use insertion and independently owned cleanup. No automatic modprobe
or retry should be derived from this graph. This is not an armed physical trial.
The next eventual physical question remains whether the exact production provider/
panel path can prepare and accept zero brightness under existing recovery guards;
no execution authorization is inferred here.

Current-artifact pointer, Image/DT/module bytes, accepted server/rescue, signed
fallback and consumed claims remain unchanged. S06/R01 and prior Denial VM failures
remain FAIL. New physical, VM, firmware and activation-order qualification: NOT RUN.

Implementation files:

- `.github/workflows/offline-smoke.yml`
- `configs/repository-tests.json`
- `patches/display-controller/README.md`
- `scripts/device/build-production-display-modules.py`
- `scripts/device/test-production-display-modules.py`
- `scripts/host/record-ci-environment.sh`
- `scripts/host/test-repository-linux.sh`

Metadata updates this report/qualification, existing artifact inventory, structured
project status, generated current-state header and one development lesson.

Final metadata checks: `check-mobile-status.py --write`,
`check-mobile-status.py`, `python3 -O scripts/host/test-mobile-status.py` (8PASS,
0.021s), `check-artifact-inventory.py` (594sets,68small tracked hashes) and
`git diff --check` passed. The inventory checker did not hash large/private
artifacts; twin packaging separately verified all14 archive member hashes.
The prior593 inventory rows, current artifact pointer, headless/mobile contracts,
trial plans, draft controller patch, sealed historical loader and historical
current-state body are unchanged. Final active service terminated successfully,
207.954s runtime,295.6MiB peak,0swap. Both owned services are terminal.

Exact metadata files:

- `test-results/2026-09-20-production-display-modules.md`
- `test-results/2026-09-20-production-display-modules-qualification.json`
- `manifests/artifact-sets.json`
- `configs/project-status.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
