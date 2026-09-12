# Denial allocation contract: Pro review response

The new returned-descriptor finding is reproduced and fixed. This is offline
userspace correctness work; no phone operation, signing, admission, claim,
flashing, candidate creation or protected-storage mutation occurred. Mobile
physical rows remain NOT RUN, and historical headless S06/R01 remain FAIL.

Follow-up started at `472fcfebd1a97409c3df953a3f9b3333ca68894d`, tree `70c7c00ed38976c5b8274d574e45f55454b0d776`.
Executable source is frozen at `1282476b19c61a3efdcc1c00f11b705223c81ad5`, tree `63efcfb25ed8f7c2807e76889fd6c704b4ae837a`.
Later changes record qualification only. Denial remains pinned to
`85b2303e2f09ae7b7b993641f90061a200f03d53`, Smithay to `812bd33259ff58810dadef6086d8385eeac1ca55`.
The published review branch stays frozen at `410b6935526a977ca727359f23ee43fc4ebe45b2`; no new push
or GitHub CI run is claimed. The imported Pro review itself was source-only.

## Confirmed and fixed

The strict explicit intersection and sole-Invalid pool dispatch were already
implemented at e709b1c7; they were retained. The additional allocation regression
failed four cases against that implementation: unexpected explicit return for
an implicit request, unexpected implicit return for an explicit request,
BO/export mismatch, and wrong format/empty request. The new guard compares BO
and exported dma-buf formats, requires XR24 and a requested modifier, and rejects
before either same-device or PRIME framebuffer registration. It preserves the
original export error and resource lifetime ordering. No descriptor is relabeled.

The exact-source runner compiles the actual selector, pool and allocation
functions, with only data and allocation/export/DRM boundary adapters. Sixteen
cases pass after the patch; the original fails ten and passes six. The connected
selector-to-pool case prevents a selector-only fix from passing unnoticed.
The no-XR24 renderer counterexample is now included. These are host regressions,
not a simulated claim of real GBM or EGL behavior.

The active documentation now calls the logged set Smithay's EGL-derived render
format set. Its inserted Invalid entries permit an attempt, not a raw EGL claim.
Successful import does not prove every GL image-target operation was error-free;
Smithay does not check those errors there. The initial external rejection occurs
before its FBO completeness check. Raw EGL query flags and detailed GL stage/error
instrumentation remain NOT RUN. Historical logs and reports are unchanged.

## Executed evidence

| Check | Result | Duration |
| --- | --- | ---: |
| Four new descriptor counterexamples before guard | 4 expected FAIL, 2 PASS | 2.696 s for both units/variants |
| Frozen semantic regression, original and corrected functions | corrected 16 PASS; original 10 expected FAIL | 2.611 s |
| VM harness prerequisites | 5 PASS | 0.003 s |
| Real ARM64 Denial build | PASS | 229.072 s |
| Audited ARM64 VirGL guest | FAIL, 50 frames/page flips | 48.971 s |
| Initial active tier, missing compiler wrapper PATH | 13 PASS, 74 BLOCKED | 9.785 s |
| Corrected-environment active tier | 87 PASS, 0 FAIL/BLOCKED/SKIPPED suites | 126.499 s |

The final tier lists 255 NOT_SELECTED suites and three declared optional
subchecks SKIPPED. JSON/JUnit enumerate per-test commands, durations and source
sections. The missing-PATH receipt remains retained. No source or expectation was
changed for its retry. Missing compiler remains a blocking prerequisite.

Binary SHA-256: `2e58170d826668e7fa34f9949f51657bc3d5894b459fd3a1ae3354acf962eeca`.
Behavior patch SHA-256: `3d05d2d441d32f852c71887bf750aede1a7a5fc959f5a2ac50234a844783b8f1`.
The source inventory verifies 701 files; only kms_state.rs differs from the
previous pool source. The same kernel, Arch tree, Flutter bundle, Smithay, Mesa
and VirGL container were reused. One-crate build: one worker, 3 GiB RAM/no swap,
600-second deadline and >3 GiB free disk. VM: network disabled, readonly payload,
Deck renderD128 only, 1 GiB guest/1536 MiB container, 8 MiB serial bound,
120-second harness/45-second guest deadlines; container removal verified.

The admitted initial descriptor is XR24/Invalid, renderable=true. Initial
rendering proceeds, with 50 raster frames and 50 page flips. Full-session status
remains FAIL: five embedder backing-store errors and EGL BAD_ACCESS during
output-target cleanup. Fourteen audit records total five PoolExhausted and zero
ReadyHandoff. PoolExhausted includes missing matching view/size pool, missing
render authorization, or no free unreferenced slot; the counter alone cannot
choose one. No performance improvement, visual capture, input, standalone fence
trace, error-free GL import or Adreno hardware proof is claimed.

## Remaining questions and next experiment

1. Distinguish those three broker refusal reasons, preserving original errors
   and bounds. A small VM-only diagnostic is the next authorized experiment;
   do not treat denial of a backing store as a successful no-op or dummy FBO.
2. Trace exact engine shutdown and render-context ownership for BAD_ACCESS.
   Do not assume the Rust shutdown comment establishes that every engine thread
   released its EGL binding; do not swallow the cleanup error.
3. Raw EGL/GL stage diagnostics remain available if a later import/FBO failure
   occurs. No evidence currently assigns the initial rejection to a Mesa bug.
4. All phone display/GPU/input and lifecycle qualification remains NOT RUN.

All 484 previous artifact sets and non-VM pointer fields are preserved. The new
set is an offline fixture with authority none. About 60 MB of terminal VM staging
copies were retired after streamed equality checks against retained originals;
the reconstruction map, unique binary, sources and raw logs remain. Cargo's
modified binary freshness marker was archived and invalidated; dependency cache
and original Denial binary were preserved.

[Qualification JSON](2026-09-12-denial-allocation-contract-qualification.json)
contains exact commands, source/artifact hashes, both integrated runs, audit
excerpts and private evidence references. Evidence root:
`/home/deck/.local/state/rog5-modifier-contract-review-20260912-r1`.

Changed files for this follow-up:

- `patches/denial-85b2303e/0001-preserve-implicit-render-modifier-contract.patch`
- `patches/denial-85b2303e/README.md`
- `scripts/host/test-denial-modifier-selection.py`
- `tools/denial-modifier-tests/allocation-fixture.rs`
- `tools/qemu-virtio-drm/guest.sh`
- `configs/project-status.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- this report and its qualification JSON

Final metadata checks: five optimized checker tests PASS in 0.842 seconds and
eight status/identity tests PASS in 0.020 seconds. Inventory, generated status
and whitespace checks PASS; their individual durations were not recorded.
Explicit comparison to the starting commit confirms byte-identical acceptance
contracts and historical current-state body, unchanged non-VM artifact pointers
and all 484 prior artifact entries. The new fixture brings the inventory to 485.
