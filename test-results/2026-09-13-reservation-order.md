# Render reservation ordering: executable counterexamples — 2026-09-13

**The modifier review is already incorporated; the later reservation problem is
not fixed.** Current source retains strict explicit intersection, Invalid-only
pool dispatch and returned-descriptor validation. The
[allocation response](2026-09-12-denial-allocation-contract.md) records sixteen
passing corrected semantic cases and the initial ARM64 VM rendering progress.
Those unchanged tests were not repeated this turn. The review branch remains
frozen at `410b6935526a977ca727359f23ee43fc4ebe45b2`.

This turn implements executable counterexamples against the actual queue and
broker methods, closing a gap before a cross-thread completion change. It changes
no engine/compositor production policy, admission, pool size, TTL, framebuffer,
fence, scene selection or cleanup behavior. No source fix is claimed for the
reservation protocol. Both stale-work assertions remain visibly **FAIL**.

## New results

| Check | Result | Seconds |
| --- | --- | ---: |
| Frozen engine ordering, seven cases | PASS characterization | 2.571 |
| Frozen broker desired properties and controls | 2 FAIL, 2 PASS | 1.117 |
| Applicable frozen active tier | 87 PASS suites | 126.505 |

The tier separately enumerates 255 NOT_SELECTED suites and three declared optional
subchecks SKIPPED; zero suite failures, blocks or skips. The new manual exact-source
checks are separate. Their intentional broker failures are not hidden in the tier
PASS or reclassified as successful rendering. No GitHub CI run is claimed.

The engine fixture extracts unchanged `Pipeline`, `FrameItem`,
`Animator::BeginFrame/Render/EndFrame/OnAllViewsRendered`, `Shell::OnAnimatorDraw`
and `Rasterizer::Draw/ShouldResubmitFrame` from engine
`d728e61e7d835e02c453c70ae9523a40f6c03215`. Deterministic FIFO runners, timing,
semaphore counting, synchronous framework dispatch and draw results are adapters.
It does not execute Dart, GPU surfaces, physical threads, presentation or the real
decision to resubmit. The actual queue/dispatch/resubmission code executes.

- One item draws before a post-EndFrame barrier (control).
- Two queued items execute `draw:1 → barrier → draw:2`: EndFrame does not post
  a second draw, and the first Draw reposts its continuation behind the barrier.
- A BeginFrame-return barrier executes before partial-view EndFrame's draw.
- A zero-render frame posts no raster work, preserves its continuation, and the
  next frame renders through the fixture successfully.
- Early all-views EndFrame followed by outer EndFrame commits exactly once.
- A full pipeline requests retry without invoking the third framework callback
  or committing a third item. A requested frame was not necessarily serviced.
- An injected resubmission executes the actual queue handling and produces
  `draw:1 → barrier → draw:1`; a barrier is not proof of terminal work.

The broker fixture executes actual authorize/acquire/expiry/cancel/availability
methods from Denial `85b2303e2f09ae7b7b993641f90061a200f03d53` plus existing patches
0002/0003. The entire replayed output_pipeline.rs byte-matches the current retained
Denial executable source (`f34b77805c0c9bf2ceb61a62e9c60fd432c4e52673d02248ea453201709a9c10`).
An old queued acquire, identified only by view/size, can consume a replacement
grant after expiry. Canceling an old view can likewise clear a new grant. The
latter is a counterexample to using that API for a proposed asynchronous completion;
it is **not** evidence that such a cancellation callback ran in the VM.
Expiry without replacement and current one-use acquisition pass their controls.

## Identities, bounds and limitations

Starting commit: `0c5c980ab5d9c0cba2dd22d24e6fe036f530bd51`, tree `57374ddfc44874ba7d4aa152613618ce563b1dbf`.
Frozen source: `3e1a2f0f38c4ea3a0d72a8802322ed199d09d982`, tree `8f2b5f60f0a21e197f8cdc144738e9069dd8cb3b`.
Denial/Smithay source pins and all existing engine patches are unchanged. The
[qualification JSON](2026-09-13-reservation-order-qualification.json) retains exact
commands, section/translation-unit hashes, tool identities, per-case durations,
initial attempts, output identities and changed files. Private final output:
`/home/deck/.local/state/rog5-render-reservation-order-20260913-r1`.

Both focused runners use the existing repository executor's process-group cleanup,
30-second compile and ten-second case limits, and disabled core dumps. Final tests
run under Python -O; placeholder integrity is not assertion-dependent. The Rust
compiler uses the retained network-disabled 512 MiB/no-swap container wrapper.
The active tier uses 1 GiB/no-swap, two workers and a 600-second scope limit.

An initial fixture extractor mistook upstream `/// @note` for an unresolved
placeholder and failed before compilation (0.014 s). The exact placeholder check
was corrected, with that failure retained. Subsequent development runs and the
frozen checks are separate records. No production error is inferred from it.

The unchanged latest VM still has **46 raster frames, 46 page flips, eight
backing-store errors: full session FAIL**. Context cleanup remains PASS. Streaming
hash checks matched its retained engine, Denial executable and serial log; this
rechecks identity, not runtime behavior. No engine link, VM rerun, phone contact,
root operation, signing, claim, candidate, installation or protected-storage
mutation occurred. Headless S06/R01 FAIL, accepted rescue/server and mobile
physical NOT RUN remain unchanged. All existing artifact pointers remain intact;
the new pointer subsection references host tests only, with authority none.

## Next smallest step

Implement work-specific acquisition and cancellation, carried with the actual
queued frame through terminal raster handling. UI production completion and raster
completion are separate; account for zero-item, deferred and resubmitted work.
Preserve scene content and reject stale work before attempting backing-store
allocation. The new counterexamples constrain that repair; they do not implement it.
Only after source regressions pass should a matched ARM64 build and one bounded
VM test answer whether rendering progresses through reuse without errors. Phone
qualification remains a separate, currently unauthorized display/touch/GPU trial.

Final metadata validation: all 13 cases PASS; inventory, generated status and
whitespace checks PASS. Exact commands and timings are in the qualification JSON.
Both acceptance contracts, the historical current-state body, all 493 prior
artifact sets, all previous pointer fields and production patches are unchanged.
