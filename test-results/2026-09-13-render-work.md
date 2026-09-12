# Paired render-work ownership: ARM64 VirGL qualification — 2026-09-13

**The corrected native/engine pair passes the bounded VM rendering gate:**
41 raster frames, 41 page flips and zero reported rendering errors. The previous
VM had 46 frames/page flips and eight backing-store errors. This is one new
45-second guest run in the retained ARM64 VirGL environment, not a new control
run or phone result. The existing modifier correction remains unchanged.

## Corrections and regressions

Denial patch 0006 identifies each reservation batch with a nonzero checked work
ID. Acquisition requires matching admission on the same raster thread. Expiry and
completion cannot cancel an admitted span; completion cancels only unused grants
for its own ID. Engine patch 0004 carries immutable ownership through the exact
vsync callback, committed FrameItems, retained draws and retries. Empty/full
production attempts also release ownership. Stale work is deferred before backing
store allocation and preserves its scene; actual allocation errors remain errors.
Two separately named C exports couple the components without enlarging existing
public structs. Old libraries fail native loading before reservation issuance.

The earlier source counterexamples remain recorded in the
[ordering report](2026-09-13-reservation-order.md). The first new native revision
also failed two completion-during-admission assertions (25 PASS, 2 FAIL); those
failures drove the admitted-span correction. Final actual-method tests pass:
27 broker/handler/FFI cases and 12 engine ownership/queue/admission cases.
Graphics calls, deterministic task runners, framework dispatch and selected data
types are explicit adapters; host tests do not execute real EGL, Dart or KMS.

Independent review found a startup failure-contract gap. Denial patch 0007
constructs EngineHost before callback registration so its existing failed-shutdown
lifetime guard owns the callback/configuration graph. Before: four controls pass,
two injected registration-plus-shutdown failures free reachable state. After:
all six cases pass, preserving the original registration error and publication
order. No sane path to that error pair was established in this matched pinned
engine. It is hardening, **not** the cause of the prior VM failure. Normal ABI,
baton transfer and successful shutdown lifetime review found no further defect.

## Executed checks

| Check | Result | Seconds |
| --- | --- | ---: |
| Final broker/handler/FFI methods | 27 PASS | 0.889 compile + 2.278 cases |
| Final engine ownership/queue methods | 12 PASS | 3.778 total |
| Startup ownership, before/after | 4 PASS + 2 expected FAIL / 6 PASS | 0.667 / 0.675 compile; individual cases in JSON |
| Initial ARM64 native build, before startup hardening | PASS | 219.575 |
| Exact engine dependency closure query | PASS, 52 affected objects | 10.848 |
| Affected ARM64 engine compilation | 52 PASS | 192.529 |
| Complete ARM64 engine link/strip | PASS | 203.602 |
| Final ARM64 native build | PASS | 253.584 |
| Matched ARM64 VirGL guest | PASS rendering gate | 49.186 harness |
| Frozen applicable active tier | 87 PASS suites | 140.053 wrapper |
| Metadata/status regressions | 13 PASS | 1.051 including inventory/status checks |

Final focused behavior total: **45 PASS, 0 FAIL/BLOCKED/SKIPPED**. Historical and
initial expected failures above are separate. The active tier enumerates 255
NOT_SELECTED suites and three declared optional subchecks SKIPPED; zero selected
suite skips, blocks or failures. Manual exact-source tests are outside that tier.
No GitHub CI run was executed or inherited as a new local result.

The complete link records all 3264 inputs. Retained Ninja dependencies identify
52 affected direct objects across 22 files; all six archives/78 member-object
dependencies were checked and none is affected. The other 3212 inputs remain
read-only original cache bytes. All compiled files match an independent replay
of engine patches 0001–0004 at its pinned base; Denial patches 0001–0007 likewise
replay to the final native staged source. Three retained engine toolchain files
were rehashed. Existing engine exports and dependencies are unchanged apart from
the two reviewed new symbols. All 31 other Flutter fixture files are unchanged.

## Runtime evidence and limits

- One native three-buffer pool was imported, with offscreen blitting disabled.
  Forty-one raster/page-flip transactions imply buffer reuse with that fixed
  bounded pool. This is a source-and-log inference, not individual work/FBO tracing.
- Eleven scheduler intervals observe 40 ready-with-fence, fence signal, real
  submission and presentation events, with zero stale-ready drops. These are
  positive synchronization observations, not a per-FD export/readback trace.
- All context cleanup checks pass across 192 contiguous records: the IO owner
  unbinds before main cleanup, the raster context unbinds, and main cleanup binds
  and finally unbinds. No BAD_ACCESS or backing-store error is recorded.
- The 512-entry work log saturates during startup: 256 grants, 255 cancellations,
  one expiry. Admission/consume mappings are **NOT OBSERVED** in that log. The
  trace limit cannot be hidden behind the passing render counters.
- The VM is not a visual, input, performance, A660, phone panel or touch test.
  It retains the same kernel, Mesa/QEMU/VirGL environment, GBM flags, renderer and
  required synchronization policy. No dummy FBO, modifier relabeling, fence bypass,
  increased grant TTL or pool enlargement was used.

VM bounds: no network; only host renderD128; runtime/payload read-only; 1536 MiB
container, 1 GiB guest, two CPUs, 64 PIDs, 120-second outer/45-second guest deadline,
8 MiB serial limit. Engine objects use 1 GiB/one CPU/90 seconds each, complete link
4 GiB/two CPUs/600 seconds, native build 3 GiB/two CPUs/one Cargo job/600 seconds.
All have no swap and preserve at least 3 GiB host disk. Every owned build and VM
container is terminal and removed.

## Identities and reproduction

Starting source: `9ea4fcee44fa3190d0b3c764342e053c59c7c118`, tree
`46178d07990e12bfe5bdffa8f192eb489fa55e9b`.
Native source: `02796f069819b9df2ad11013f69ce3d1ddf39362`, tree
`7df1e33e5711f5f9faf2f31df82d9848595286ce`.
Engine patch source: `66db5ff08065972bf9cf7e3d2c4b845633170052`, tree
`eac6003527f2b051bb783f9a9f3664dd4826ff67`.
Frozen active-tier/harness source: `8ed710f63f5150314f1e7eb008daa6b80e719b81`.
The evidence commit follows these builds; it does not retroactively become their
source identity. Private terminal completion records that ending commit/tree.

| Artifact | SHA256 |
| --- | --- |
| Final deniald | `878ff4c6155279264782523837cf7672273f333a9a45318a7db9cc9fbf7ce19a` |
| Final libflutter_engine.so | `a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418` |
| VM serial log | `e112ab91f58716ec5caa8b293467438690e0270f56819b279adc81ff254807e1` |
| Engine dependency closure | `8b1725ad1116dd7bb61f04d7ba3112442719c1d845978e9e174fd54ec574873b` |

The [qualification JSON](2026-09-13-render-work-qualification.json) contains exact
commands, per-case/object durations, patch/input/toolchain/output hashes, failed
fixture attempts and separate build/runtime results. Private output root is
`/home/deck/.local/state/rog5-render-work-20260913-r1`. Raw logs remain there.
Focused reproduction commands are documented in [development](../docs/development.md).
Run retained `compile-engine-closure.py --execute --closure-sha256` with the hash
above only into a fresh reviewed output; it refuses existing results. Native
commands are locked offline Cargo release builds with one job. The immutable
builder identities and full expanded commands are in the qualification JSON.
This artifact set is a fixture with authority=none, not a candidate or install plan.

Verified lossless debug archives plus one identical duplicate retirement reclaimed
797,878,894 bytes; 60,092,897 bytes of byte-identical VM payload copies were then
removed with restoration mappings. The first archive attempt stopped at the
reserve and left its source intact; only its own partial archive was discarded.
Restore write-kernel A from its archive before using it to restore its identical
B copy. Images, modules, configs, link commands, original caches and signed
recovery inputs were preserved. Historical artifact records remain unchanged.

## Disposition and next question

Confirmed/fixed: work identity isolation, admission lifetime, paired queue
ownership, and injected-error startup ownership. Prior modifier findings are
already addressed; their initial tests were not needlessly repeated. No new
VirGL driver defect or incomplete-FBO cause was demonstrated.

Remaining: visual/readback and synthetic-input VM qualification; individual
work-to-FBO diagnostic coverage; real phone display/touch/A660 and all mobile
physical rows **NOT RUN**. Headless S06/R01 remain **FAIL**. Data-at-rest/mobile
security, sustained interaction, suspend/wake and charging remain separate gates.

Next smallest authorized experiment: retain these exact binaries and add bounded
VM visible-output/readback and synthetic-input evidence. A later exact-artifact
phone scanout/Adreno experiment requires its existing separate authorization and
prepared coordinator process. No phone operation, signing, new candidate,
admission, claim consumption or protected-storage mutation occurred here.

Changed files:

- `configs/project-status.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `docs/development.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `patches/denial-85b2303e/0006-bind-render-work-reservations.patch`
- `patches/denial-85b2303e/0007-own-startup-callback-graph-before-registration.patch`
- `patches/denial-85b2303e/README.md`
- `patches/flutter-engine-d728e61e/0004-bind-render-work-reservations.patch`
- `patches/flutter-engine-d728e61e/README.md`
- `scripts/host/test-engine-registration-ownership.py`
- `scripts/host/test-render-work-broker.py`
- `scripts/host/test-render-work-engine.py`
- `test-results/2026-09-13-render-work-qualification.json`
- `test-results/2026-09-13-render-work.md`
- `tools/denial-engine-tests/render-work.cc`
- `tools/denial-modifier-tests/registration-ownership.rs`
- `tools/denial-modifier-tests/render-work-broker.rs`
