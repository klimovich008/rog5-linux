# Focused Pro review: Denial per-frame authorization handoff

Repository: klimovich008/rog5-linux.
Review branch: agent/pro-render-authorization-review-20260912.
The exact publication commit is supplied in the attached handoff; this packet
cannot embed its own Git commit without a hash cycle. Source under test is
ca89dcf7dcf5f1e5b6fde950504c35bdcedd472e (tree
6eda334b934e8ca56b814c2197aa68c479335e99).

Read-only review. No phone, fastboot, SSH, boot, flash, signing, claim or storage
operation is authorized. All runtime evidence below is an ARM64 VirGL VM, not
Adreno/phone proof. This is the next blocker after the earlier modifier review.

## Problem and executed result

The explicit/implicit modifier defect is fixed through selection, Invalid pool
dispatch and returned-descriptor validation. The VM admits XR24/Invalid and
presents frames. Smithay's external-texture guard and native-fence requirements
remain intact. Do not reopen that correction without contradictory evidence.

The complete session still FAILs: eight Flutter backing-store errors plus EGL
BAD_ACCESS during cleanup. The trace records 50 raster frames and 50 page flips.
It contains 278 consecutive records, below the 512 limit: 135 grants, 85 expiries,
50 consumption events, eight missing-authorization refusals and no cancellation.
Seven refusals immediately follow consumption as the last broker transition for
the same view; one follows expiry. The snapshots usually show available slots;
one has a Ready slot. Previous detailed audit showed no missing-pool or
no-free-slot refusals. A timeout-only or pool-size fix is therefore unjustified.

The engine receives asynchronous RenderOutputs work. The broker's one-use
permission may be consumed by another callback or expire before queued work runs.
Current evidence does NOT distinguish stale queued retained-output work from a
fresh unsolicited framework/root frame, nor prove which engine path issued each
second callback. Dirty serial is not necessarily a unique queue-submission ID.

## Exact relevant code

Read the included source-excerpts.md and all three patches under
patches/denial-85b2303e. Key paths:

- Denial output_pipeline.rs: authorization, expiry, target_available, acquire,
  begin_transaction. Calls are broker-mutex protected; admission is one-use.
- Denial output_runtime.rs: render_authorized_outputs, queued RenderOutputs call,
  rebuild_scene decision and OnVsync delivery; with_frame_readiness expires grants.
- Denial renderer/handler/open_gl.rs: make_current, create_backing_store and
  raster_idle. Missing permission becomes None; no dummy FBO is returned.
- Denial compositor/flutter-engine/src/host.rs: None becomes callback false;
  avoid_backing_store_cache=true so the broker chooses each target.
- Flutter shell.cc Shell::RenderOutputs: queues Prepare for rebuild_scene=true,
  otherwise queues DrawDenialRenderOutputs. Returning success is not completion.
- Flutter rasterizer.cc: Prepare/Draw and ExpandDenialRenderOutputTasks. Inspect
  selection_pending and the !selection_pending fallback carefully. Do not assume
  it alone caused these eight callbacks or change it without checking other modes.

## Reproduction

Host regression (no graphics hardware): with Rust 1.98.0 and a retained Denial
Git checkout containing 85b2303e, run:

```sh
RUSTC=rustc python3 scripts/host/test-denial-broker-refusals.py \
  --source /path/to/denial --output /path/to/fresh-output
```

It compiles actual broker/audit functions. Corrected source passes nine cases;
the original passes four and fails four diagnostic expectations. An additional
concurrent case verifies unique trace sequences and the 512-record bound.
The earlier modifier/descriptor regression has 16 corrected passing cases.

Actual VM reproduction needs matching private runtime/container/binary inputs;
the branch does not distribute the whole environment. Use the repository's
scripts/host/test-qemu-virtio-drm.py with the exact inputs in qualification JSON:
ARM64 virtio-DRM kernel, authenticated 326-package Arch runtime, exact Denial
binary, matching ARM64 Flutter engine/AOT/assets, retained QEMU/VirGL container,
Deck renderD128 only. Network disabled, readonly runtime/payload, 1 GiB guest,
1536 MiB container/no swap, 8 MiB serial limit, 120-second harness and 45-second
Denial deadline. DENIA_RENDER_AUDIT=1 enables the diagnostic. The raw serial
hash and relevant trace pairs are in sanitized-vm-evidence.json. Do not claim a
reproduction unless matching inputs actually ran. Payload staging copies may
need reconstruction from their retained originals; see the cleanup receipts.

## Specific questions

1. Trace both paths that can issue a backing-store callback without a remaining
   grant. Which source-level counterexample is established, and what minimal
   additional event (queue mode, generation, caller) would distinguish the seven
   post-consumption cases? Keep observed facts separate from hypotheses.
2. What is the smallest coherent fix that binds queued engine work to its own
   reservation, coalesces or cancels stale work, and avoids deadlock when a
   framework frame produces no raster task? Preserve independent output clocks,
   topology generations, buffer ownership, one-use admission and bounded queues.
3. Can the existing PostRenderThreadTask completion/sentinel API safely acknowledge
   retained-output work? Explain why the Prepare-plus-later-UI-render path may
   need different treatment. Do not replace a missing completion with a larger TTL.
4. Is strict render-selection admission in the engine appropriate only after an
   explicit native frame-clock handshake? Audit nested/legacy behavior before
   recommending that change. Do not discard pending new scene content.
5. Propose focused regressions for delayed queued work, a second callback after
   consumption, skipped framework frames, topology change and teardown. Exercise
   real functions or a narrow extractable seam. Give a minimal patch sketch only
   where the source supports it; identify any missing evidence precisely.

Do not weaken Smithay guards, native fences, the VM failure classifier, or physical
acceptance. EGL cleanup is separate; successful frame admission would not make
this full session PASS. No phone candidate or new vN release is requested.

If repository access fails, the accompanying attachment includes the complete
source excerpts, sanitized evidence and diagnostic patches. No raw credentials
or unit-specific phone identity is included.
