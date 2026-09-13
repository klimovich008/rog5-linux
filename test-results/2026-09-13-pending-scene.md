# Pending-scene progress repair — September 13, 2026

**Source fix and ARM64 build PASS. The engine-only VM comparison reaches visible launcher icons and Mousepad → Foot → Mousepad, then FAILS the lower-caret baseline.** No phone execution, signing, admission or claim consumption occurred. S06/R01 remain FAIL; phone physical qualification is NOT RUN.

## Correctness change

The previously reproduced ordering leaves a newer scene pending after an old-scene retained retry has already cleared the native dirty serial. Patch0005 requests fresh retained work through the existing raster→UI weak-engine→ScheduleFrame(false)→Animator scheduling route. It preserves admission/expiry refusal and the public embedder ABI. The request is limited to configured outputs in render-work mode, genuinely newer pending scenes and one notification watermark per view. Duplicate/older/already-drawn tasks do not notify; structural output changes reset the watermark.

Source review found an additional edge before compilation: a retained retry moves the last-successful task out of its owner. An empty owner therefore does not prove an unseen scene. The final guard also checks the existing reused-layer-tree marker; the regression executes this stale retained path. The independent final review reported no concrete blocker.

Implementation source: `0d055f4c942bfba624d83e7fd505b67c52352020`, tree `bfebe2afe05e0229a07ff2b91ffe63a01e0fe11c`. Initial checkout HEAD was `ccb939efc66fce97d51d847387384dacac15c2fe`; a separate documentation commit records the completed storage cleanup. Engine base remains `d728e61e7d835e02c453c70ae9523a40f6c03215`, with patches0001–0005. No Rust/native or shell rebuild was required for this internal engine correction.

Changed files:
- `patches/flutter-engine-d728e61e/0005-request-work-for-newer-pending-scenes.patch`
- `scripts/host/test-render-work-engine.py`
- `tools/denial-engine-tests/render-work.cc`
- `docs/development.md`

## Failing-before / passing-after

The same progress regression applies exactly patches0001–0004 for its negative control. Compilation succeeds, then the process returns1 with `FAIL progress obligation: newer deferred scene has no runnable engine continuation`. This is a behavioral failure, not a compiler error or timeout.

The fixed fixture executes20 cases including real RequestFrame/CanReuseLastLayerTrees, Engine/Shell notification, retained drawing, output equality and topology transitions. The positive progress case requires pending N to become the last successful scene after a fresh grant, with no additional Dart build and no runnable notification loop. Native grant expiry/regrant, GPU presentation, deterministic queue/weak-lifetime implementations and the cache tail of CollectView remain explicit adapters.

| Check | Result | Seconds |
|---|---|---:|
| Old-source negative control (compile then one case) | Expected FAIL | 3.596 |
| Fixed actual-method suite |20 PASS | 5.290 |
| Same suite under Python `-O` |20 PASS | 5.081 |
| Complete affected ARM64 object compilation |10 PASS | 58.164 |
| Link |PASS | 222.106 |
| Integrated active tier |105 PASS;0 FAIL/BLOCKED/SKIPPED;255 NOT_SELECTED |174.932 |
| VM comparison, including owned cleanup |FAIL lower-caret baseline |308.414 |

The active tier separately records3 optional skipped subchecks; no mandatory selected suite silently skipped. These are personally executed local results, not imported GitHub CI. The negative control is an expected FAIL retained as evidence, not counted as a passing runtime test.

Exact source commands used `scripts/host/test-render-work-engine.py --source /home/deck/.local/state/rog5-denial-20260910-r1/engine-build-r1/checkout`, fresh outputs under `rog5-pending-scene-20260913-r1`, and `--without-pending-scene-fix --case queued-ui-stale-scene-progress` only for the negative control. The optimized run used `python3 -O`. Private compilation/link drivers and exact expanded commands are retained alongside hashed receipts. Only10 of3264 link inputs were newly compiled; the other3254 are verified control inputs, including earlier patched objects. All22 staged patched files match the test replay. The original engine remains unchanged.

## Artifact identities

- New ARM64 engine SHA-256: `e4a182f7a4cd0cb3f3a1361678f9f1268d195f3772800d906758ef6c81bc8cf0` (16003096 bytes).
- Control engine SHA-256: `a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`.
- Unsigned VM archive SHA-256: `6e1968e98c5892a686b696467375506589f9492858cb40a8006b96599cc9aac0` (26699314 bytes).
- Native Denial remains `b3bc17099f666ef920412183c59f179160fb28033a38d79f61f18e17e3f0dcf5`.
- Shell remains `06634d7ae6f4f54d3e6184306201547aa185a5411811ffea089f39bd7dde48b2`.

Thirty VM input identities, tool identities, container images and runtime-view metadata match the retained control run. Within the session payload, only libflutter_engine.so and generated provenance change. This is a VM development fixture, not a new phone candidate or installed update.

## Runtime result and remaining blocker

Both launcher tile checks matched on the first capture. Screenshots were inspected: colored icons are visible, Mousepad shows the long text document, and Foot shows its controlled terminal. Native client protocol records mapping/readiness for both applications and focus Mousepad→Foot→Mousepad. The fourth focus visit and text-entry sequence were not reached; overall launcher/editor qualification remains FAIL.

The low pointer press reached Mousepad surface25 at(296.4921875,1075.8828125), sequence86. A subsequent text-input rectangle still reported(29,90,0,20), rectangle sequence91. Later geometry was(26,23,540,1176). The baseline timed out; no OSK keys were sent, bottom-caret result is NOT RUN, ACK was not sent, and graceful client teardown was not qualified. The held pointer was released; the named VM container was forcibly removed by the bounded harness and verified absent. Host cleanup PASS does not turn guest/session failure into PASS.

Read-only follow-up narrows the next question: client protocol after the press publishes surrounding text `line-01` and the old caret rectangle, while subsequent surface damage covers the lower row around y1070. Confirm exact GTK input-method spot-location update behavior; do not assume incorrect pointer mapping, extend the deadline or weaken the low-caret requirement. Detailed raw traces remain private.

The positive icon observation is consistent with the proven source repair. Earlier icon readiness was intermittent, so one treatment run does not establish reliability or prove this was the exclusive cause of every historical icon failure. The new engine is not phone GPU evidence. Next work is the precise caret-publication boundary using retained logs and exact source, followed by one changed-input VM check.

[Qualification JSON](2026-09-13-pending-scene-qualification.json) retains commands, source/artifact hashes and detailed results.
