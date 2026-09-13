# Render handoff retention and delayed-scene ordering — 2026-09-13

**Host diagnostic regression PASS; VM launcher qualification FAIL.** This is
offline host/ARM64 VirGL VM work, not phone GPU, display or touch qualification.
Physical remains NOT RUN; headless S06/R01 remain FAIL. No phone/USB operation,
signing, admission, claim consumption or protected-storage mutation occurred.

## Source change and checks

Starting metadata/source HEAD was `90814029522539c4667cad693e9968c853d969b6`.
The collector/test change is frozen at `5d9b129dea9965a72f4a704440d4188118c48f1d`,
tree `deb8e883b4a8c021e3829aebc518543d2b39d74b`.
`tools/qemu-virtio-drm/logind-apps.sh` retains compact existing native render
authorization and presentation audit fields. Previously these early records
were lost while the collector preserved icon stages and a recent idle-log tail.
No native renderer, Rust API, GL call, clock, fence or scheduling behavior changed.

The new scan reads at most the first 1 MiB. It keeps the latest four authorization
records and latest two presentation records within that prefix, preserves order
within each category, strips ANSI styling, and limits each selected value to 96
characters with an explicit truncation flag. Its separate 1,792-byte framed
budget sits alongside the unchanged 24,576-byte stage budget. The existing
30,720-byte final snapshot, 4 KiB recent tail, three-second deadline and one-second
kill grace remain. No record is promoted into protocol or success evidence.

Three new regressions in `scripts/host/test-launcher-diagnostics.py` fail against
the previous collector. All 14 focused cases then pass in 3.266 seconds, covering
late damage fields, ordering, ANSI stripping, noise retention and budget
separation, alongside prior timeout/refusal/forged-evidence checks.
All 105 active suites pass on the frozen source in 163.072 seconds: zero
FAIL/BLOCKED/SKIPPED suites, 255 NOT_SELECTED, three declared optional subchecks
SKIPPED. These are local executions, not new GitHub CI claims.

Only the collector differs among the 32 recorded VM inputs. The compiled shell
remains `aae7ee8a`, native compositor `daf4b119`, and the prior kernel, engine and
unsigned VM payload remain unchanged. No AOT, engine, compositor or kernel
rebuild was needed. All 32 input hashes verify afterward.

## VM result and limits

One run fails at launcher readiness in 259.897 seconds total, with 246.321
seconds of VM execution. Eight identical captures show labels, wallpaper and
widgets without app/fallback icons, with the same SHA256
`91644732dda79722309861b412070c675fb78e2abaabb45aa94f37c63c2978e1`
as the prior missing-icon runs. There are no pointer actions or app launches.
Bottom-caret and OSK qualification remain NOT RUN for this run. The exact host
container is removed and absence verified; this does not prove normal guest
shutdown or authenticated-session cleanup.

Seven picture builds and seven complete paint/draw sequences are recorded at
Flutter frame timestamp 21614745 microseconds. The diagnostic stream totals
45,394 bytes and remains under its existing bound. Newly retained fields show:

- Authorization records 508–511 grant/cancel work 255/256 for dirty serial 1;
  the existing 512-record producer cap has been exhausted. These startup records
  do not cover every later icon-frame authorization.
- Two presentation audit intervals report two then one presented outputs,
  zero empty transactions and full-output last frame/buffer damage
  `0,0-540,1224`, at guest wall timestamps 00:03:42.180388 and 00:03:45.755060.

The counter name needs care: `record_present()` increments `presented_outputs`
after rendering/fence export but before broker `mark_ready()`. It is not a KMS
page-flip count. These aggregates cannot be joined to the precise Dart picture
frame merely by timestamp. They do not establish that the newer icon scene
reached scanout, nor prove a driver or framebuffer-completeness failure.

## Separate executable ordering counterexample

A read-only review identified a possible lost update across the existing engine
and native scheduler. Ordinary expiry retains native dirtiness and defers the
engine layer tree; that path has retry support. The distinct ordering is:

1. Framework work W1 for dirty serial S is queued on the UI runner, then expires.
2. A retained-scene retry W2 posts directly to the raster runner and can draw the
   previously successful scene before W1 submits its updated scene.
3. W2's native Ready completion acknowledges S. Delayed W1 subsequently retains
   its newer scene after stale admission, without notifying native dirtiness.

The private `stale-scene-study` adds one mode to the existing engine fixture.
All 19 extracted production sections remain unchanged; independent deterministic
UI/raster queues establish the ordering without manually inserting a LayerTree
or FrameItem. It compiled in 2.748 seconds and reproduced the expected progress
failure in 0.003 seconds: `pending_new_scene=2`, `last_successful_scene=1`, empty
UI/raster runnable queues, and zero new RequestFrame retries. Earlier invariants
pass; this is not a compiler error or timeout.

Admission expiry is still modeled by that fixture's existing newest-work adapter;
GPU output and native dirty acknowledgement are outside the C++ test. Its result
proves an engine-side counterexample, not an integrated real-runtime diagnosis.
The native companion executes 11 exact source sections, including the five
scheduler methods, with only tick/availability inputs adapted. It compiles in
1.066 seconds and passes its five boundary checks in 0.004 seconds: an initial
baton creates S, unavailability preserves S, a retained retry uses S without a
baton, completing S makes the next available tick skip, and S+1 survives stale
completion of S. This confirms the native half of the source interleaving. The
C++ and Rust boundaries are executed separately; a full coupled runtime proof
is not claimed.

The initial companion identity check correctly refused section hashes recorded
without the saved files' final newline. File bytes matched the actual source;
the metadata was corrected and reverified before compilation. Host rustc was
absent, so the existing pinned toolchain container was used with a 512 MiB limit,
no swap/network, one CPU and a 30-second deadline. Cleanup/absence were verified.

Next: turn the coupled counterexample into the smallest production fix that
notifies pending newer scene work without accepting expired reservations or
unconditionally redrawing on every stale work item. Keep exact source/payload
identities, tests for newer-generation protection, and bounded scheduling. Do
not widen deadlines, bypass readiness, or rerun this unchanged VM to infer the
missing frame identity. Historical failures remain unchanged.

All commands, raw logs/captures, test fixtures and retained source-section hashes
are private under `rog5-render-handoff-20260913-r1`. The engine study remains a
source-dependent characterization, separate from the mandatory active tier.

[Qualification JSON](2026-09-13-render-handoff-qualification.json) records exact commands and identities.
