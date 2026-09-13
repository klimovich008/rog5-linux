# Logical content sizing and complete VM text entry — 2026-09-13

**The corrected shell shows the complete `test` → `tes` → `test` sequence in
native Mousepad, including the formerly clipped leading character.** The same
OSK pointer sequence and supported manual viewport pan were used. One bounded
ARM64 VirGL VM run produced 127 raster frames/page flips, all 12 expected key
events and no reported rendering errors. Phone physical qualification remains
NOT RUN. Automatic caret tracking and launcher-based app switching are not
established by this test.

## Demonstrated defect and correction

The native surface pipeline publishes both root-buffer dimensions and logical
content geometry. Mousepad's observed backing buffer is 592×1228; its logical
content is 540×1176. `WindowSurfaceTree` already maps logical content into its
requested rectangle. The old `WindowTextureRect` nevertheless sized that outer
rectangle using backing-buffer pixels, then used `BoxFit.cover`. This stretched
the logical content and cropped its horizontal edges to fill the output.

The regression executes Denial's actual `_buildTexture`, status/frame metrics,
preview aspect, content-rectangle and surface-mapping methods with small value
and widget-construction adapters, plus the matching Flutter `applyBoxFit`.
With the old code, a glyph at logical x=4 maps to screen x=−9.2663. With the
correction, the body is 540×1176, the complete frame is 540×1224, and that glyph
maps to x=4. The original fails six of thirteen assertions and exits nonzero;
the patched code passes all thirteen.

Patch `0008-use-logical-window-content-size.patch` changes four Denial files:

- `dart_shell/lib/src/widgets/window_texture_rect.dart`: use logical content size.
- `dart_shell/lib/src/input/input_layout.dart`: keep status/frame metrics in the
  same logical units, independently of backing-buffer scale.
- `dart_shell/lib/src/widgets/window_geometry.dart`: use the matching logical
  size for preview aspect.
- `dart_shell/lib/src/widgets/window_content_rect.dart`: explicitly supply the
  local Flutter app's existing logical layout size to the shared metric.

Buffer upload, texture-source cropping, `mapSurfaceRect` and native input routing
are unchanged. The regression covers scaled buffers, status-bar height, local
layout override, fallback/empty/system windows and unchanged surface mapping.
It does not execute a Flutter renderer or qualify desktop/local-app interaction.
The subsequent real AOT build and VM observation provide separate evidence.

## Source, artifact and execution identities

Starting commit `154912792d470816263b95bc5d291e7716c0f3fa`, tree
`a46c3f0adc0f56be9cf267f6a4f428950a67a6cf`; executed source
`5fd94e97995eb882f33f99e0ae217dc80b1f34ec`, tree
`c6b4649d16171c18c511d09492cfee21728c1627`. The later evidence commit is separate.
Patch SHA256: `6b96371155c3e1bb3bba3581116a7901c08bdb19a9f782c2030bcefbf317bb52`.

The isolated build workspace's 300 Dart library files matched the retained
source before patching. Its 380-file inventory records exactly four changed
files. The matching package graph, Dart frontend, patched SDK and AOT generator
were verified against retained hashes. New ARM64 `libapp.so` SHA256:
`85567c81c52a375d8fa424aaaa54a152440b2fd02d73632301b857da6b230b19`.
Its deterministic build command is recorded; this turn built it once and does
not claim a new two-build reproducibility comparison.

Only `lib/libapp.so` changed in the 32-file runtime fixture. Native Denial,
engine, assets/ICU, package root, generic kernel, Mesa, capture client and
graphics/synchronization policy remain identical to the prior run. No kernel,
native compositor or engine rebuild was needed. The runtime is an offline VM
fixture with no admission authority, not a new phone candidate.

| Executed check | Result | Seconds |
| --- | --- | ---: |
| Final original production sizing unit | 7 PASS / 6 expected FAIL; exit 1 | 0.553 |
| Corrected production sizing unit | 13 PASS; exit 0 | 0.622 |
| Shell frontend compilation | PASS | 23.508 |
| ARM64 shell AOT generation | PASS | 20.007 |
| One corrected VM | Protocol/capture and complete visible text PASS | 102.627 |
| Frozen active tier | 90 PASS; 0 FAIL/BLOCKED/SKIPPED; 255 NOT_SELECTED | 139.487 |

Three declared optional subchecks remain SKIPPED separately from suite counts.
The integrated tier used two workers, 1 GiB/no swap, a 600-second bound and
346.3 MiB peak memory. The manual sizing test is explicitly outside that tier;
its exact-source/tool command and thirteen results are separately recorded.
The initial regression harness expected an already-proportional scaling case
to fail; that expectation was corrected and the failed run retained. Later
wrapper tightening changed only diagnostic containment. All attempts remain
in private evidence; no historical result was relabeled.

After the evidence/status update, five metadata-checker cases pass in 1.007
seconds and eight status cases in 0.080 seconds (wall time). Inventory validation
passes for 500 sets in 0.068 seconds; generated status validation passes in
0.041 seconds. Whitespace checks and explicit comparison of both acceptance
contracts, the historical current-state body and all 499 previous sets pass.
Exact commands/durations are retained in private `metadata-result.json`.

The VM retained the existing network-none, read-only runtime/payload, private
capture share, host render-node-only exposure, CPU/memory/process/log limits and
120-second outer deadline. The build containers and VM container were removed.
Direct inspection of the three text captures confirmed complete words; the
native final capture also shows restored `test`. Capture transport alone is
not the basis of the visual PASS. Manual viewport panning remains necessary.

The [qualification JSON](2026-09-13-mobile-content-sizing-qualification.json)
records commands, source/tool/patch/runtime hashes, build results, all regression
attempts, per-suite timing/status, protocol results and visual findings.
SHA256: `47ac6bb3e30768a7a61db27808f8652eebf2ca0abaa0af4467563cff3857f627`.
Raw logs and captures remain private under
`/home/deck/.local/state/rog5-mobile-sizing-20260913-r1`.

## Retention, limits and next action

Streaming comparison verified 136 duplicate payload files from four completed
VMs against durable originals before reclaiming 240,667,268 bytes. Container
absence and unchanged file identity were checked. The restoration map is
`duplicate-payload-retention.json`; unique logs, initramfs bytes and captures
were retained. Builds maintained the 3 GiB disk reserve, with a recorded minimum
of 3,787,919,360 free bytes. No protected storage was involved.

Repository source files changed: patch0008, its README and
`scripts/host/test-mobile-content-sizing.py`. Evidence/status files changed:
this report and qualification JSON, `docs/development-lessons.md`,
`configs/project-status.json`, the generated current-state header,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`. The current
pointer now explicitly selects `mobile_content_sizing_observation`; earlier
native/engine and failed mobile observations remain retained. Prior 499 artifact
sets and both acceptance contracts remain unchanged.

Next: exercise the actual mobile launcher and switch between Mousepad and Foot,
both already present in the authenticated runtime. First give UI-launched
children explicit guest cleanup ownership: they use separate process groups
and are not owned by the fixture's existing automatic-editor PID trap. Existing
native INFO launch records provide PID/executable attribution. Capture the
launcher before selecting tile coordinates; do not substitute guest-side
automatic launches for launcher proof. This next experiment has not run.

Non-root mobile-session security, automatic caret visibility, two-app switching
and daily operation remain open. Phone OLED/touch/A660, suspend/wake, charging
and all mobile physical rows remain NOT RUN; S06/R01 remain FAIL. No phone
contact, signing, candidate creation, admission, claim operation or
protected-storage mutation occurred. Installed bytes were not queried or changed.
