# Denial modifier contract: real virtual frames, incomplete session

This turn made offline progress. No phone operation, signing, admission, claim,
flashing or protected-storage mutation occurred. Physical rows remain NOT RUN;
S06/R01 remain FAIL. No screenshot or input/usability proof was captured.

Starting source: `ab5789b16f88733a25c2ff62b324f2fa6a39f757`, tree
`cb47d94e05e1174be06804d68168ff6990ae15e7`. Executable fix frozen at
`e709b1c7` (full commit/tree in the qualification JSON). Later changes only
record provenance/documentation. Signed candidate, observed-runtime, fallback,
board qualification and authenticated Arch runtime pointers remain unchanged.
All 483 prior artifact sets are preserved; the new fixture set is number 484.

## Focused external review

The requested review branch was pushed and read back from the remote:
[agent/pro-framebuffer-review-20260912](https://github.com/klimovich008/rog5-linux/tree/agent/pro-framebuffer-review-20260912),
exact commit `410b6935526a977ca727359f23ee43fc4ebe45b2`, tree
`e6e6d261dc2ec33212334f8b6a363bb15b32b99e`.
It remains frozen. No PR, merge to main or remote development-branch update was
performed. The packet includes pinned source excerpts, diagnostic patch,
sanitized VM evidence, exact artifact identities, reproduction prerequisites,
rejected hypotheses and focused questions. JSON, secret-pattern screening,
whitespace and exact upstream patch application checks passed before publishing.

The self-contained private attachment is
`/home/deck/.local/state/rog5-framebuffer-diagnostic-20260912-r1/pro-review-prompt.md`.
It includes later independent findings and source excerpts for the pool allocator,
backing-store callback and cleanup path. Those addenda are explicitly separate
from the frozen review commit. The exact runtime/container binaries are private;
repository access alone cannot reproduce a binary run. Pro can inspect the
included source and request missing engine evidence without operating hardware.

## Demonstrated defects and correction

The logging-only build observed XR24/Linear, stride 2560, one plane, 640x480,
while EGL advertised XR24/Invalid and no explicit modifiers. `renderable=false`.
The exact Smithay import predicate marks this external-only and its bind path
rejects it as a render target. TRACE could not diagnose this because the release
build compiles it out; one INFO diagnostic in Denial exposed the actual format.

The selector inferred explicit Linear support from implicit EGL support. Strict
explicit intersection plus a shared Invalid request fixes that mismatch. A first
real VM test of the selector-only change failed earlier because
`allocate_scanout_pool` discarded Invalid requests. That failed build/run remains
retained. The complete correction carries a sole Invalid request through the
pool after the unchanged extent/length/memory checks. Explicit modifier ordering,
Linear fallback, error propagation and partial-allocation destruction remain.
It does not relabel an allocated buffer or weaken native fences.

The executable regression compiles the actual pinned selector, pool and validation
functions before/after applying the patch. Data and allocator-boundary adapters
are explicit; GBM/EGL/DRM behavior is tested separately in the VM. The original
fails five of nine cases. The selector-only patch passes seven and fails two pool
cases. The combined patch passes all nine. This manual exact-source test is not
implicitly included in ordinary repository tiers.

## Personally executed results

| Stage | Result | Duration |
| --- | --- | ---: |
| Logging-only ARM64 build | PASS | 214.570 s |
| Initial format VM diagnostic | FAIL: explicit/implicit mismatch | 9.777 s |
| Selector-only ARM64 build | PASS | 245.575 s |
| Selector-only VM | FAIL: Invalid filtered by pool | 11.934 s |
| Combined selector/pool ARM64 build | PASS | 213.069 s |
| Combined VM | FAIL: 33 frames/page flips, errors remain | 48.760 s |
| Frozen active repository tier | 87 PASS, 0 FAIL/BLOCKED/SKIPPED suites | 135.070 s |

The active tier reports 255 NOT_SELECTED suites and three declared optional
subchecks SKIPPED. Peak memory: 368 MiB, no swap. Per-suite times/commands and
JSON/JUnit are bound by the qualification receipt; no new GitHub CI result is
claimed. The final nine-case compile/run takes about 1.2 seconds across both
variants; exact sub-run timings are retained.

Only the Denial crate was rebuilt, using the exact Rust 1.98.0 ARM64 toolchain,
thin LTO and one codegen unit. Builds used one Cargo worker, a 3 GiB container
memory bound, no swap and a live disk-reserve/deadline guard. The original
retained Denial binary is still byte-identical. After completion the mutable
bin-deniald Cargo freshness marker was archived and invalidated, so a future
source remapping cannot rely on freshness from this modified binary. Dependency
cache and exact standalone outputs were preserved.

The same kernel, Arch tree, Flutter bundle and VirGL container were used in all
three comparisons. Final output: XR24/Invalid, `renderable=true`, initial atomic
scanout reached, Flutter initialized, 33 raster frames and 33 output page flips.
The complete session still FAILs: four backing-store creation errors and
EGL BAD_ACCESS when binding the context for output-target cleanup. Positive
counters do not override these diagnostics. Native-fence requirements remained;
no separate fence trace/readback, visual capture or Adreno qualification occurred.

## Retention and remaining work

About 180 MB of terminal VM staging copies were removed only after every file
was streamed against an identical retained binary or Flutter bundle. All source
binaries, runtime/bundle originals, source copies, raw logs and receipts remain.
The cleanup receipt maps every retired path to its durable identical source;
reconstruct the payload copies before attempting any replay. These were private
VM fixtures, not phone candidates. Host disk remained above the 3 GiB reserve.

The next authorized question is whether the backing-store messages correspond
to bounded broker exhaustion, a request mismatch or a lifecycle defect. The exact
source supports `DENIA_RENDER_AUDIT=1` with INFO-level reports; enable it in a
bounded guest run before another binary rebuild. Independently inspect the
post-engine-shutdown EGL context ownership assertion. Neither cause is proven.
Do not grant more host privileges for the retained AMD file-description warning.
Do not weaken the test classifier or native-fence/ownership guards.

The source patch is not selected by a phone image builder. Pro review is pending.
A real phone touch session, OLED/A660 behavior, two apps/text input, ordinary
starts, long observation, screen-off/wake and recovery/update qualification all
remain incomplete and unauthorized in this offline task.

[Qualification and exact identities](2026-09-12-denial-modifiers-qualification.json)
records every build/run command, source/patch hashes, output hashes and original
failure receipts. Private evidence root:
`/home/deck/.local/state/rog5-framebuffer-diagnostic-20260912-r1`.

After the metadata update, 19 optimized metadata tests passed in 1.895 seconds.
The artifact/current-state validators and whitespace check also passed.

Changed files in this checkpoint:

- `configs/project-status.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `docs/licensing-provenance.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `patches/denial-85b2303e/0001-preserve-implicit-render-modifier-contract.patch`
- `patches/denial-85b2303e/README.md`
- `scripts/host/test-denial-modifier-selection.py`
- `test-results/2026-09-12-denial-modifiers-qualification.json`
- `test-results/2026-09-12-denial-modifiers.md`
- `test-results/framebuffer-review-20260912/README.md`
- `test-results/framebuffer-review-20260912/diagnostic-build.json`
- `test-results/framebuffer-review-20260912/initial-format-diagnostic.patch`
- `test-results/framebuffer-review-20260912/qemu-container-packages.tsv`
- `test-results/framebuffer-review-20260912/qemu-gl-loader-hashes.txt`
- `test-results/framebuffer-review-20260912/sanitized-vm-evidence.json`
- `test-results/framebuffer-review-20260912/source-excerpts.md`
