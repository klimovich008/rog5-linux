# Impeller IO context release — 2026-09-12

**The corrected engine and Denial now release the distinct IO resource EGL
context on its owning thread in the ARM64 VirGL VM.** Raster release and
main-thread cleanup still pass. The full VM session remains **FAIL**, with
47 raster frames, 47 page flips and
7 backing-store errors. Frame admission has not
changed. No phone result follows from this virtual experiment.

## Source counterexample and correction

Start: `237d5a62c90bebf73f1b1cd3b9e830e6513f2c44`. Frozen tested source: `5c960b5bd1ff043c543a3614df9cb56c450d76bd`,
tree `8df0e373a6242bf5a5684818e56c57cd74c510fb`. Engine base: `d728e61e7d835e02c453c70ae9523a40f6c03215`; Denial base: `85b2303e2f09ae7b7b993641f90061a200f03d53`.
The prior corrected engine only released the render context. In the pinned
engine, Shell destroys its final IO manager and calls ReleaseResourceContext
on the IO thread. PlatformViewEmbedder inherited PlatformView's empty release
method, while EmbedderSurfaceGLImpeller::CreateResourceContext bound the resource
context. The retained trace showed that separate context bound on ThreadId(11)
with no matching unbind. Denial's clear callback also selected only the render
context. With a foreign render owner it would reject an IO caller; after raster
release it could instead report success while leaving the IO context current,
because Smithay unbind is a no-op for a context that is not current here.

Engine patch 0002 forwards the existing release hook to the surface. Impeller
tracks successful IO binding, disables reactor work before release, reports a
failed clear and retains the binding flag on failure. Failed initial binds and
repeated successful release do not clear unnecessarily. Denial patch 0005 routes
the shared clear callback to the resource context only when that context is
actually current on the caller. Existing ownership and EGL failure guards remain.
The two patches are a coordinated change; neither alone qualifies shutdown.
Other engine backends retain their existing behavior and are not newly qualified.

## Executed checks

- Actual-method fixtures: **PASS**, 2.444
  seconds for compilation/execution. Old code has five expected failures and four
  passing controls; corrected code passes all nine cases. Cases cover normal and
  repeated binding/release, null surface, initial bind failure, clear failure with
  retained ownership and retry, correct render dispatch and wrong-owner refusal.
  An initial Rust fixture compilation failed because pub(super) was placed at
  crate root; removing only that adapter visibility corrected it. Initial logs
  remain retained. EGL/reactor effects in these fixtures are adapters.
- Real ARM64 engine dependency closure: **PASS**, 38.729
  seconds. Ninja reports 16 header dependents; all eight linked into this engine
  are recompiled using the exact retained commands. The eight internal-library
  duplicates are not linked. Rebuilding only the directly edited .cc files would
  miss changed derived-class vtables and allocation sizes.
- Real ARM64 Denial: **PASS**, 211.569 seconds; one crate,
  dependencies reused, 3 GiB/no swap, two CPUs, one Cargo job.
- Complete separate engine link: **PASS**, 202.103 seconds;
  4 GiB/no swap, two CPUs, 600-second and 8 MiB bounds. Nine objects are substituted:
  eight new IO/header dependents and the previously qualified raster destructor.
  Original engine/cache/source remain read-only. Minimum free disk during link:
  3340926976 bytes. The ARM64 export/SONAME/NEEDED comparison
  passes; only the engine changes in the 32-file Flutter bundle.
- VM: context release **PASS**, complete session **FAIL**;
  48.769 seconds. 238 trace records are
  contiguous and below the cap. IO unbind precedes main cleanup, occurs on the
  previously recorded owning thread, and is followed by no IO rebind. Raster and
  final main unbinds remain visible; no BAD_ACCESS or cleanup error is recorded.
- Harness prerequisite/error-classifier tests: six cases **PASS**, including the
  new IO failure message. Frozen active tier: 87 PASS,
  zero FAIL/BLOCKED/SKIPPED suites, 255 NOT_SELECTED,
  three declared optional subchecks SKIPPED; 126.558 seconds.

VM isolation is unchanged: no network, read-only runtime/payload, host render
node only, 1536 MiB/no-swap container, 1 GiB guest, 120-second harness, 45-second
session and 8 MiB serial bounds. No phone/USB, power, signing, admission, claim,
installation or protected-storage operation occurred. This is not visual, touch,
A660, scanout or physical power qualification. S06/R01 historical FAIL and mobile
physical NOT RUN remain unchanged. No new candidate or review-branch push.

## Artifact identity and next step

| Artifact | SHA-256 |
| --- | --- |
| Denial | `aa00de38f46ee44d85b3bc2fcc2104575d13d4e040ba60b6f73279311d436711` |
| Engine | `8b57bc22ac3613e5da3af08965443c5706b0fa064c71a419a6af0ead13337291` |
| Serial | `2f53c3fdc2f518df3b44b3741a4ad35448156cc53b2cb75ee842196298a42c8e` |

Exact build/test commands, durations, input/output hashes, source bindings and
bounded observations are in the [qualification record](2026-09-12-impeller-io-context-qualification.json).
Raw private evidence: `/home/deck/.local/state/rog5-io-context-release-20260912-r1`. Verified duplicate payload staging was removed only
after comparing every file with retained originals; restoration paths/hashes
remain recorded. The original render-only engine and all historical evidence
are retained. New artifacts are manual VM fixtures with authority=none.

Next: resolve queued-render generation/reservation and callback provenance using
the pending focused review. Reuse these corrected cleanup artifacts and retain
the frame-admission guards. Do not infer an expiry-only fix from the remaining
errors. A phone trial still requires its separate authorized process; none ran.

## Changed files and final metadata checks

- `configs/project-status.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `patches/denial-85b2303e/0005-clear-current-io-resource-context.patch`
- `patches/denial-85b2303e/README.md`
- `patches/flutter-engine-d728e61e/0002-release-impeller-io-context.patch`
- `patches/flutter-engine-d728e61e/README.md`
- `scripts/host/test-io-context-release.py`
- `scripts/host/test-qemu-virtio-drm-prerequisites.py`
- `scripts/host/test-qemu-virtio-drm.py`
- `test-results/2026-09-12-impeller-io-context-qualification.json`
- `test-results/2026-09-12-impeller-io-context.md`
- `tools/denial-engine-tests/io-release.cc`
- `tools/denial-modifier-tests/io-clear.rs`

Final metadata validation passed 13 cases, artifact coverage (491 retained sets)
and generated status. The active tier used 318.6 MiB peak and no swap.
Its source remains the frozen build commit above; final evidence-only edits were
checked separately, without repeating unchanged builds or the active tier.
