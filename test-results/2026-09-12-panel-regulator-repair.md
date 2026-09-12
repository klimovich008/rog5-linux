# Panel regulator ownership repair — 2026-09-12

The panel now stops ambiguous regulator retries. Actual Linux 7.1.4 accounting
proved that a parent-disable error can follow consumption of the child vote, and
that failed enable unwind can leave a parent vote behind. The previous panel
flags either retried a consumed vote or permitted another power cycle with a
leaked parent. These paths are relevant to the L13C/BOB and L12C/S1C supplies.

The driver now records NONE, HELD or UNKNOWN per supply. It releases other known
votes after one fails, preserves the original error, and returns `-EUCLEAN` on
later uncertain cleanup. New preparation is refused. DRM may retain prepared
state after uncertain power-off, but initialization is false and enable/backlight
transactions remain blocked. Ordinary DSI-off errors still permit a clean next
prepare when regulator release succeeds. Reset, Iris, DSI command sequences,
brightness byte order and mode-flag handling are byte-unchanged.

This does not restore uncertain hardware or preserve inhibition across reprobe.
No rebind/reload is qualified after such a fault. All mobile physical rows remain
**NOT RUN**; headless S06/R01 remain **FAIL**. No phone operation, signing, claim,
candidate creation, installation or protected-storage mutation occurred.

## Identity and execution

The worktree started clean on `agent/review-correctness-20260912` at
`06034292096bb8e3bf7d92baef74dc14fbab1564`, tree
`e3c8d3b503b6fc83453d7e60b5ea31b2ce4cecc4`. Earlier review repairs were retained;
no old audited files or historical failures were restored or overwritten.

Frozen build/test source: `fce7a9892df3e69a170015699aad3f3f13e13aea`, tree
`2ff259f1feec407ac87b38036960c6b35b9ab288`. Later changes are documentation and
artifact/status metadata. Final commit/tree and every changed-file hash are in
private `completion.json`, recorded after the metadata commit.

- Pinned Linux: `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` / v7.1.4.
- Patch 0037 SHA256: `a3fcff9b884facfa5628aff9623428c074eb4146926efd1c3dd9c53b4bd083ae`.
- Driver SHA256: `f29ecb3bd574615c20e800da810f892a54975703d63bec88051656b694d884a6`.
- New production-series SHA256: `6ecab1592d1293be2dbb2d48792f4de889a5db5d2418738b56e8f3c394af62ee`.
- Merged configuration remains `277bc74e104bcdec8e6eda8a345e2a4e7bb15be5118bb829741742e97d8a174c`.
- Identical 23,128-byte panel twins: `e7a5ac14d92ded53ca480272f0272d8fe236a38b671c5deabb17ff44ba2a6191`.
- Vermagic: `7.1.4-rog5-production SMP preempt mod_unload aarch64`.
- New 1,031-module metadata SHA256: `bfa19931ebdad5975d581efa85ee41e0d84ce85e14f3b20d04fdea79203db973`.

The [qualification receipt](2026-09-12-panel-regulator-qualification.json) binds
exact commands, sources, tools, artifacts and retained evidence. The
[current artifact pointer](../manifests/current-artifact.json) identifies the new
panel module and module root explicitly. The accepted/signed/runtime/fallback
pointers and original dirty checkout remain unchanged. No new phone image was
created. The old Q6 schema FAIL and previous qualifications remain historical.

## Failing-before and passing-after checks

| Executed check | Result | Seconds |
|---|---|---:|
| New core-coupled regression against old panel patch | Expected FAIL: normal cycles pass; seven fault cases fail | 0.282343 |
| Frozen regulator regression, exact-source comparison, Python `-O` | PASS: eight cases and three mutations | 1.166619 |
| Frozen lifecycle/DRM/brightness regression, Python `-O` | PASS: 16 cases, one mutation, 20 normal cycles | 0.865942 |
| Complete 16-patch production preparation/merged config | PREPARED; applicability/config PASS, compilation separate | 59.630074 |
| Panel twin B, W=1/modpost | PASS | 2.962 |
| Panel twin C, W=1/modpost | PASS | 2.811 |
| Full module cohort copy/hash/depmod command | Depmod PASS; subsequent ad hoc name check FAIL | 0.775069 overall |
| Existing production dependency checker and cohort byte verification | PASS | 0.111173 |
| Source/artifact inheritance checks | PASS: 65 inputs, only 0037 driver content changed | 0.208918 |
| Frozen repository CI tier | 305 PASS, 0 FAIL, 0 BLOCKED, 3 optional SKIPPED, 30 NOT_SELECTED | 616.595203 |
| Final metadata/status tests, links, inventory and preservation checks | PASS | 0.365722 |

The CI summary records 39 optional skipped subchecks across the selected suites,
including skips within optional suites. Every skipped suite is declared optional.
Both JSON and JUnit summaries are retained. `ROG5_LINUX_SOURCE` was unset for this
host CI; its unexecuted source checks remain NOT RUN. The explicit frozen checks
above used the freshly prepared exact source. No remote GitHub run was invoked.

The final metadata check verified all 17 trial test hashes, all 18 qualification
proof hashes, all 28 unchanged physical rows and all 450 unchanged historical
artifact sets. Eight mobile-status regression cases passed. The two new artifact
sets are offline fixtures. An independent read-only metadata review found no
material concerns; its scope excluded hardware. Exact final check commands and
durations are retained in private `metadata-checks/result.json`.

The external module was compiled using the real merged board configuration and
read-only retained objects. All 37 imported symbols resolve. Its dependencies are
`drm_display_helper`, `drm_kms_helper` and transitively `cec`; no direct firmware
request was added. 726 kit files stayed unchanged; 681 source/header/control files
matched the fresh production source. 714 files were consumed by the final builds.
The complete cohort has only one changed module; the other 1,030 module byte hashes
match the retained build. `depmod -ae` produced no diagnostics. Its individual
step duration was not retained separately from the 0.775069-second initial command.

Private preparation failures remain recorded: a retained/PATH Python mismatch,
then an incomplete pre-build inventory of generated module-common inputs. Twin A
compiled but failed that input-coverage qualification; final B/C passed. Tool
records distinguish actual resolution from merely verified retained executables;
exec tracing was NOT RUN. A later ad hoc dependency spelling check was corrected
by reusing the existing production checker, including modules.dep coverage/cycles.
These were host qualification errors, not observed panel failures.

Commands were run from this worktree. Full argument lists and durations are in
`prepare-r1-execution.json`, `frozen-panel-checks/result.json`,
`module-build/result.json`, `module-cohort-qualification-r2.json`, and
`ci-r1-execution.json` under the private root below. CI used two workers,
MemoryMax=3GiB, MemorySwapMax=0 and disk-backed scratch:

```sh
systemd-run --user --scope --quiet -pMemoryMax=3G -pMemorySwapMax=0 \
  bash scripts/host/test-repository-linux.sh ci
```

The Image and composed DT bytes were rechecked unchanged. Their existing schema
and compilation evidence is inherited for verified unchanged inputs; neither a
cold Image build nor DT/schema execution was repeated. Generic QEMU evidence
inside repository tests covers its declared userspace/fixture scope, not SM8350
panel, GPU, touch or PMIC behavior.

## Unresolved work and next experiment

Confirmed/fixed: unsafe panel regulator retries and missing actual-accounting
regressions. Disproved: a regulator error always means its child vote remains
held. No extra classifier or broad readback controller was added.

The provider survey found that GENI protocol/FIFO observation needs clock and
pinctrl setup and a QUP-version-dependent decode. Existing passive snapshots
cannot establish mode or DMA ownership. Historical RPMh/PMIC readers concern
other rails and report votes/programmed values, not physical voltage or L8C's
upstream feed. Reusing their names would not supply the missing evidence.

Physical regulator recovery, OLED/A660 operation on the current exact artifacts,
L8C supply, touch events, suspend/wake and idle drain remain unresolved. Reset
assertion, 28 ms/DSC TODOs and vendor provenance concerns were not guess-fixed.
No source result explains or closes S06/R01.

The next smallest hardware experiment is one bounded 60 Hz scanout/blank cycle,
with fresh power telemetry and independent return-to-known-good checks, **only
after separate exact-artifact composition and execution authorization**. It must
answer whether this corrected panel can complete that lifecycle. Touch stays
disabled; raw GENI reads must not be smuggled in as passive setup. No test was
armed and no Ready prompt was requested.

Private evidence root:
`/home/deck/.local/state/rog5-provider-readiness-evidence-20260912-r1/`.

## Changed files

- `.github/workflows/offline-smoke.yml`
- `configs/mobile/acceptance.json`
- `configs/mobile/trial-plans.json`
- `configs/project-status.json`
- `configs/repository-tests.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `docs/front-touch-prototype.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `patches/linux-7.1.4/0037-drm-panel-add-ASUS-ROG-Phone-5-AMS678-ER2.patch`
- `scripts/device/fixtures/ams678-regulator/cases.c`
- `scripts/device/fixtures/ams678/cases.c`
- `scripts/device/fixtures/ams678/stubs.h`
- `scripts/device/test-ams678-lifecycle.py`
- `scripts/device/test-ams678-panel-patch.sh`
- `scripts/device/test-ams678-regulator-errors.py`
- `scripts/host/build-ams678-panel-check.sh`
- `scripts/host/test-repository-linux.sh`
- `test-results/2026-09-12-panel-regulator-qualification.json`
- `test-results/2026-09-12-panel-regulator-repair.md`
