# Mobile editor viewport investigation — 2026-09-13

**The supported right-edge viewport pan restores Mousepad while the OSK stays
open.** The previous white area was consistent with the document's blank middle
after its header and first line moved offscreen. No renderer change or rebuild
was needed. Text insertion, deletion and restoration now visibly change the
line, but the expected leading `t` is not visible at the left edge: the captures
show `est`, `es`, then `est`. Complete visible text remains **FAIL** pending
clipping/content verification. This is ARM64 VirGL VM evidence, not phone proof.

## Source explanation and change

The retained Denial source is pinned to upstream
`85b2303e2f09ae7b7b993641f90061a200f03d53`. In
`dart_shell/lib/src/widgets/edge_panel_layer.dart`, `MobileKeyboardViewport`
translates the whole application by `-(keyboardOffset - viewportScroll)`.
`ShellMetrics.edgePanelHeight` returns `min(368, height * .30)`, or 367.2 pixels
for this 1224-pixel output. Initial viewport scroll is zero. Mousepad's header
and first line therefore move above the output when the OSK opens. The previous
observer never used the existing panning control.

The observer now preserves the unpanned capture, then drags downward from
(531,240) to (531,640) in the stationary 18-pixel right-edge strip. The production
controller multiplies movement by 1.15 and clamps it to keyboard height. This
restores the app's original vertical position before the same OSK key sequence.
The new sixth capture records that restoration separately. Pointer cleanup,
protocol key validation, capture bounds and deadlines remain in force.

This is a test-flow correction, not an implementation of automatic caret
visibility. The Dart text-input state exposes active/panel/purpose fields but
no caret rectangle; the viewport consumes manual scroll and panel progress.
Native cursor rectangles currently serve input-method popup placement.

## Exact execution

Starting commit `e33ce9b6645531b2c5d278f580b614cdb8ad1919`, tree
`7026222097eddf0f35b3f697ef07d80f2176bd01`; executed source
`21e5dd7ef6b353f31a6a0a2711952ef9c28345aa`, tree
`8ca9f289999c9359e010e729d267f4abe4aef786`. The later evidence commit is separate.
Native/engine/AOT/runtime/kernel/capture-client bytes are unchanged from the
[native capture comparison](2026-09-13-mobile-vm-native-capture.md).

| Check | Result | Seconds |
| --- | --- | ---: |
| New pan/capture expectations against old observer | 5 expected FAIL in 6 cases | 1.175 unittest |
| Focused observer/transport/protocol cases, Python -O | 40 PASS | 1.639 wall |
| Final motion-coordinate and cleanup cases | 6 PASS | 1.127 unittest |
| One bounded VM run | Protocol/capture PASS; pan restores app; full text FAIL | 102.345 |
| Frozen integrated active tier | 90 PASS; 0 FAIL/BLOCKED/SKIPPED; 255 NOT_SELECTED | 138.243 |

Three declared optional subchecks remain SKIPPED separately from suite counts.
The active run used two workers, 1 GiB/no swap, a 600-second bound and 345.6 MiB
peak memory. Tests independently decode pointer coordinates, verify the full
downward pan and capture order, reject every capture failure and release the
pointer after interruption at all 43 stage boundaries. No CI result is claimed
as a newly executed local test.

After the status/evidence update, five metadata-checker cases pass in 0.933
seconds and eight status cases in 0.080 seconds (wall time). Inventory validation
passes for 499 sets in 0.065 seconds; generated status validation passes in
0.040 seconds. Whitespace and explicit historical-preservation checks pass.
Commands and timings are retained in private `metadata-result.json`.

The VM produced 124 raster frames/page flips and all 12 expected focused key
events, with no reported rendering errors or RCU stall. Its container was
removed. Existing network-none, read-only runtime/payload, private capture
share, host render-node-only exposure, memory/CPU/process/log limits and
120-second harness deadline were preserved. No additional guest was started.

Initial native/VNC images are identical. The final sequential pair differs at
only 40 pixels in rectangle x27–28, y141–160, consistent with the visible caret
blink. Both show the restored application and the same text suffix. This is
not a same-frame timestamp claim. Initial/panned/text/deleted/restored captures
remain private; raw logs are not copied into Git.

The [qualification JSON](2026-09-13-mobile-vm-editor-pan-qualification.json)
contains exact commands, per-suite timing/status, source and artifact hashes,
reviewed production-source identities, protocol evidence and visual findings.
SHA256: `ce675a5569eac4d8d2d05eb65f4b1225f4ee783616bc84a2b35c73fdcdc9b684`.
Private evidence: `/home/deck/.local/state/rog5-vm-editor-pan-20260913-r1`.

## Remaining boundary and preservation

The next source-level suspect is aspect fitting. The native surface pipeline
publishes root-buffer dimensions as `window.width/height`, while separately
publishing logical content dimensions. `WindowSurfaceTree` maps logical content
into its requested size, but `WindowTextureRect` uses the root-buffer dimensions
for that size and `BoxFit.cover`. Mousepad's observed buffer is 592×1228 and its
content geometry is 540×1176. This difference can crop content horizontally;
it is not yet a verified root cause of the missing leading glyph. Test the
actual layout functions and/or save the RAM document through the native UI to
distinguish clipped rendering from missing text before changing the shell.

Changed source files: `scripts/host/qemu-mobile-observer.py`,
`scripts/host/test-qemu-mobile-observer.py`, `docs/development.md`.
Evidence/status files: this report and its qualification JSON,
`docs/development-lessons.md`, `configs/project-status.json`, generated header
in `docs/current-state.md`, `manifests/current-artifact.json` and one appended
fixture in `manifests/artifact-sets.json`. Prior 498 sets and historical evidence
remain unchanged. Both headless and mobile acceptance contracts are preserved.

Launcher/app switching, automatic caret visibility and complete unclipped text
entry remain unqualified here. All mobile physical rows remain NOT RUN; S06/R01
remain FAIL. No phone contact, signing, candidate creation, admission, claim
operation or protected-storage mutation occurred. Installed bytes were not
queried or changed.
