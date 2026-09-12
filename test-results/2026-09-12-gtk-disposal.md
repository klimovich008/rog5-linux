# GTK implicit-view disposal correction

The settings cleanup defect is fixed in a local patch against the exact pinned
Flutter source. The corrected real GTK test fails against the old implementation
and passes after the guard. The actual ARM64 settings application renders the
same image and exits without the invalid implicit-view removal message.

Starting checkout: `706601a5957312cae6bd53834b99b1bc7c03de3d`, tree
`760abd5d7a88b2d8f8908a0929e8f238d80e8a33`.
The frozen implementation is `89745298ca0f69fd7f408192676d1548aad2d9fe`, tree
`1f3c9adf75ad56b0b9584c00bcf67972d3051669`, on
`agent/review-correctness-20260912`. The upstream Flutter base remains
`d728e61e7d835e02c453c70ae9523a40f6c03215`; effective GTK source additionally
includes the local patch. An upstream version string alone does not identify
these patched bytes.

The exact embedder implementation rejects `kFlutterImplicitViewId` in
`FlutterEngineRemoveView`. GTK's `fl_view_dispose` nevertheless called removal
for every view. Its existing `ViewDestroy` test also expected both views to be
removed, masking the API mismatch. The patch guards implicit-view removal and
corrects that real test to expect only the secondary view. It does not suppress
logging or change secondary-view error handling.

The [patch](../patches/flutter-d728e61e/0001-linux-preserve-implicit-view-on-dispose.patch)
changes `engine/src/flutter/shell/platform/linux/fl_view.cc` and
`fl_view_test.cc`. Exact-base `git apply --check` and actual application to
independent source copies pass. The original upstream checkout stays clean.
The completed cache was copied before compilation; old libraries, test output
and the original failing test binary remain retained.

| Executed check/build | Result | Seconds |
| --- | --- | ---: |
| Copy completed cache / actual Ninja dry run | PASS / PASS, 75 steps | 1.818 / 0.716 |
| Compile real GTK tests with corrected expectation, old implementation | PASS | 125.413 |
| `FlViewTest.ViewDestroy`, old implementation | Expected FAIL: 2 removals instead of 1 | 2.677 |
| Exact-base patch check and actual independent application | PASS | 0.009 |
| Patched GTK library and test binary, 4 Ninja steps | PASS | 257.284 |
| `ViewDestroy`, `ViewDestroyError`, `SizedToContent` | 3 PASS | 2.727 |
| Actual settings frame and disposal with only new library overlaid | PASS for frame/disposal | 8.349 |
| ELF/exports/dependencies/source preservation | PASS | 0.255 |
| Stage byte/mode-equivalent tested runtime fixture | PASS | 0.167 |
| Repository active tier on frozen implementation | 86 PASS | 132.880 |

The unit-test binary includes the actual GTK implementation and upstream test
harness; its engine callbacks are mocked. Only the three named lifecycle cases
were selected after the fix. Compiling the full test target does not imply all
GTK unit tests were executed. The separate application run uses the real GTK
engine, settings AOT/assets and application object, with the previously qualified
observer main and GSettings cache. It has no Denial backend. Its image remains
byte-identical to the inspected settings page showing **Settings are unavailable**.
Broadway EGL and accessibility diagnostics remain visible; this is not a clean
complete settings session or Wayland qualification. Historical failed cleanup
and session evidence remain unchanged.

| Artifact | SHA-256 |
| --- | --- |
| Local patch | `4582af8442e207ea4364a19919688e86c8a34cdf662e7a62dece421fea57b851` |
| New ARM64 GTK library, 16,286,240 bytes | `349bfd1d7278290f45e0fb425410288b1d4d1164d21124d7ac215844d43e5959` |
| Preserved old GTK library | `42600a575bee4a753eb075b17e3a85adafcbf3cfa9d8172151277e02fd0db4cb` |
| New 34-file offline settings fixture tree | `658efcd9705f9889fe88ade61a3d65ed5100b4fa3186816dadabec1e25906536` |
| Actual unchanged settings PNG | `4dc8f8e4c0d8656c2b5e576d42fc4eeb97e6c2f16f37e2ecba0481e35e019bbc` |

Public exported symbol names and declared dependencies remain unchanged. All 72
resolved runtime library hashes match the authenticated Arch payload. Generic
`libflutter_engine.so`, host snapshot tool, settings runner/AOT/assets and source
pins are unchanged. The current artifact pointer selects the patched GTK
library and equivalent fixture explicitly; old bundles are retained independently.
This is a private offline fixture, not a boot image, signed candidate or install.

Private evidence is
`/home/deck/.local/state/rog5-gtk-disposal-evidence-20260912-r1` (E).
The [qualification JSON](2026-09-12-gtk-disposal-qualification.json) records exact
commands, source/patch/effective-file identities, durations and artifact hashes,
with references to retained raw results, logs and JUnit. Executed private
drivers are `prepare.py`, `build-before.py`, `test-before.py`, `build-after.py`,
`test-after.py`, `test-settings.py`, `qualify.py`, `stage.py` and `run-active.py`.
`run-inner-unit.sh` and `run-inner-unit-after.sh` own their isolated display
servers. E/completion.json records ending commit/tree and changed-file hashes.

Builds use the pinned compiler/container, two workers, a 4 GiB memory/no-extra-swap
limit and 580-second container deadline. The paired link build peaked at
4,224,507,904 bytes with no OOM/max event. Future paired LTO links should use one
worker; reduced peak memory has not yet been measured. No unchanged rebuild was
run to test that scheduling choice. Runtime tests use a 1.5 GiB/one-CPU,
45-second isolated scope without host devices or network. Heavy phases run
sequentially. Scratch is disk-backed and remains above the 3 GiB free reserve.

The active tier reports **86 PASS, 0 FAIL, 0 BLOCKED, 0 SKIPPED,
255 NOT_SELECTED**. This is a local execution, not a new remote CI result.
No phone-kernel rebuild or unrelated full GTK test suite was performed.

Next: inspect the retained generic ARM64 QEMU/kernel stack for virtual DRM,
then qualify the actual `deniald` backend and Wayland clients offline. Source
inspection shows `denial-nested` is a topology demo with no full shell/backend;
its success would not answer this question. Availability of a virtual DRM setup
and full compositor startup are **NOT RUN**, not assumed. Phone scanout,
calibrated touch, Adreno acceleration and lifecycle remain **NOT RUN**. The
separately reviewed provider/display trial remains the next physical experiment,
requiring the existing authorized process; this task authorizes no phone action.

No phone contact/operation, signing, candidate creation, claim operation or
protected-storage mutation occurred. ASUS slot A, signed fallback/candidate,
installed observations, consumed claims, historical current-state paragraphs and
headless acceptance remain unchanged. S06/R01 remain **FAIL**. All 480 previous
parsed artifact records are preserved; the inventory now has 481 sets.

Changed files: the Flutter patch, `docs/development.md`,
`docs/development-lessons.md`, `configs/project-status.json`, generated
`docs/current-state.md`, `manifests/current-artifact.json`,
`manifests/artifact-sets.json`, this report and its qualification JSON.

Final metadata checks after the evidence/status edits:

| Command | Result | Seconds |
| --- | --- | ---: |
| `python3 -O scripts/host/test-review-metadata-checkers.py` | 19 PASS | 1.921 |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.040 |
| `python3 scripts/host/check-artifact-inventory.py` | PASS | 0.090 |
| `git diff --check` | PASS | 0.028 |

Metadata regressions: 19 PASS, zero FAIL/BLOCKED/SKIPPED; the other three
checks pass. Exact commands/timings are in E/metadata-final-results.json.
The active tier was not repeated for these metadata-only edits.
