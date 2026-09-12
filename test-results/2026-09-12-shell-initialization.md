# Offline ARM64 shell initialization and GTK library

The real Denial shell creates its root Dart isolate, renders the portrait lock
screen and shuts down cleanly under ARM64 QEMU. This is software rendering of the
actual shell AOT/assets, not a reconstructed UI or physical phone observation.
The exact GTK engine affected target also compiled successfully. Its public
exports and dynamic loader dependency resolution pass in the authenticated Arch
runtime; the settings native runner and GTK initialization remain **NOT RUN**.

Starting source: `1bb6c03d839cb36db6cf41f33abdbc85bf89f9ba`, tree
`f67cb86bee8a9c6e614861f7ac4f3d4d4e8e446d`, clean branch
`agent/review-correctness-20260912`. The earlier audit's boot-health, panel,
screen-power and board-build source repairs are already in this branch; they
were not restored from the obsolete audited revision or rebuilt this checkpoint.

| Executed stage | Result | Seconds |
| --- | --- | ---: |
| First harness compile | PASS | 3.225 |
| First namespace invocation | FAIL before engine startup | 0.064 |
| Corrected harness compile / initialization | PASS / PASS | 2.421 / 3.875 |
| Exact namespace preflight without engine | PASS | 0.060 |
| Later-frame harness compile / initialization | PASS / PASS | 2.421 / 8.189 |
| Invalid ICU rejection / unchanged valid restart | 2 PASS | 1.117 / 8.195 |
| Black, later, restarted and truncated frame checks | 4 PASS | 0.030 |
| Cached GTK graph preflight | PASS, 97 steps | 0.866 |
| `ninja -C /work/out -j2 flutter_linux_gtk` | PASS | 252.279 |
| GTK ELF/public exports/dependency resolution and hashes | PASS | 0.443 |

The first mount layout attempted to create `/bundle` under a read-only root and
failed. The corrected namespace uses `/tmp/bundle` and `/tmp/result`. Both runs
remain recorded. The first successful run produced an all-black initial capture;
it proves a callback, not visible UI. The later eight-second run captured nine
frames, one root isolate, 39 tasks and 16 platform messages, with no invalid
callback and successful engine shutdown. The actual later PNG was inspected and
shows Denial wallpaper, clock and date. A nonuniform check alone does not identify
a UI. The invalid-ICU case intentionally exits 134 at the real ICU validation;
core dumps are disabled. A new process using the unchanged valid fixture then
renders and shuts down successfully. No fabricated backend service replies were
used: unsupported platform messages receive empty responses.

A first GTK export check incorrectly demanded private `fl_engine_start` as a
public symbol. Inspecting the exact public header corrected the fixture to use
`fl_engine_new`; the failure remains recorded. No engine change was needed.
The loader check resolves dependencies; it does not invoke GTK or establish a
working settings window. The compile owner is terminal and absent, confirmed
from the actual container ID after the successful terminal result.

| Artifact | SHA-256 |
| --- | --- |
| Private 32-file runtime fixture tree, unchanged | `e2cfdd7c25fbd00c6a705c0084f0d1a9fb806c00ea2ec3d4c808f93386d6f9de` |
| Actual later software frame, 819,200 bytes | `88743af2bda75f7376a45302e32195aeda59109d94c868370dde98abfce39aee` |
| Lossless later PNG | `d989813b0eb8a70666c1667b250e4a9916cd3f7496aa988517afbee1f49720f3` |
| ARM64 `libflutter_linux_gtk.so`, 16,286,240 bytes | `42600a575bee4a753eb075b17e3a85adafcbf3cfa9d8172151277e02fd0db4cb` |

The existing `libflutter_engine.so` and `gen_snapshot` hashes remain unchanged.
Denial source is `85b2303e2f09ae7b7b993641f90061a200f03d53`; Flutter source is
`d728e61e7d835e02c453c70ae9523a40f6c03215`. The GTK build reuses the pinned
compiler, GN arguments and completed object cache, with 4 GiB memory/no extra
swap, two CPUs/workers and a 580-second container deadline. Software shell runs
use at most 1.5 GiB, one CPU, a 60-second runtime limit, isolated namespaces,
read-only source/runtime inputs, no host devices and no network. High-memory
phases run sequentially. No complete SDK or kernel rebuild was needed.

Private evidence directories:

- `/home/deck/.local/state/rog5-shell-init-evidence-20260912-r1` (I).
- `/home/deck/.local/state/rog5-settings-native-evidence-20260912-r1` (N).

The [qualification JSON](2026-09-12-shell-initialization-qualification.json)
contains exact commands, durations, results, script/input/output hashes and both
retained failure records. I retains `run.py`, `run-r2.py`, `run-r3.py`, Rust harness
versions, `test-icu.py`, `check-visible-frame.py` and `export-frame.py`. N retains
`preflight.py`, `compile.py`, `qualify.py` and corrected `qualify-r2.py`. The PNG is
a lossless export of the engine's opaque RGBA buffer. These are private offline
fixtures, with no candidate, signing, admission or installation authority.

Next: compile and qualify the settings native runner, then exercise a complete
offline Wayland session with its real services. Phone scanout, calibrated touch,
Adreno acceleration, lock-screen security and physical lifecycle remain open.
No phone operation, claim operation, signing, new boot candidate or protected
storage mutation occurred. Signed/installed/fallback artifacts and headless
S06/R01 **FAIL** remain unchanged; physical rows **NOT RUN**. The next physical
experiment remains the separately reviewed provider/display question; this task
grants no authority to run it.

Changed files: this report and its qualification JSON, `configs/project-status.json`,
generated `docs/current-state.md`, `docs/development-lessons.md`,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`. All 477 prior
parsed artifact sets remain unchanged; two offline fixture records bring the
inventory to 479. I/completion.json records ending commit/tree and file hashes.

Final metadata checks, executed locally after the checkpoint edits:

| Command | Result | Seconds |
| --- | --- | ---: |
| `python3 -O scripts/host/test-review-metadata-checkers.py` | 19 PASS | 2.026 |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.040 |
| `python3 scripts/host/check-artifact-inventory.py` | PASS | 0.091 |
| `git diff --check` | PASS | 0.026 |

The metadata suite has 19 PASS, zero FAIL/BLOCKED/SKIPPED. The other three
checks pass. Six ICU/frame cases pass; the earlier namespace execution failure
and mistaken export assertion remain retained. No new remote CI run is claimed.
Exact metadata commands/timings are in I/metadata-final-results.json. Full phone
kernel and unrelated integrated tiers were not rerun for these evidence/status
changes; their existing results apply only to their recorded inputs.
