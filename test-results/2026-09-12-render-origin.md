# Denial frame authorization: both raster paths are involved — 2026-09-12

**The VM trace resolves the previously unknown callback origins.** Three rejected
backing-store requests came from retained-output draws; five came from the
framework pipeline. Seven refusals followed consumption by the other path, and
one followed expiry. All five rejected framework draws had explicit selection
pending. Disabling the default select-all fallback would therefore not fix these
observed failures. This does not prove that fallback is correct in every mode.

The complete VM remains **FAIL**: 46 raster frames, 46 page flips, eight
backing-store errors. Render, IO and main-thread context cleanup still **PASS**.
No phone result or hardware operation is implied.

## What the new evidence establishes

The trace contains 729 contiguous engine events and 294 contiguous broker events,
below their 4096/512 limits. All 54 surface attempts have matching end records:
46 success and eight failure (pinned DrawSurfaceStatus::kFailed = 2). Every
backing-store error and refusal is enclosed by an identified surface attempt.

| Rejected raster call | Origin | Prior broker mutation | Prior consumer | Explicit selection pending |
| --- | --- | --- | --- | --- |
| 78 | retained-output | consume | framework-pipeline 77 | retained task |
| 97 | framework-pipeline | consume | retained-output 96 | yes |
| 100 | framework-pipeline | consume | retained-output 98 | yes |
| 103 | framework-pipeline | consume | retained-output 102 | yes |
| 106 | framework-pipeline | consume | retained-output 105 | yes |
| 138 | framework-pipeline | expire | —  | yes |
| 168 | retained-output | consume | framework-pipeline 167 | retained task |
| 171 | retained-output | consume | framework-pipeline 170 | retained task |

These IDs identify executed raster calls, **not** queued submissions or native
reservation tokens. The logs do not identify the precise framework producer of
each FrameItem. Source and trace together establish a shared per-view permission
being consumed across the two asynchronous paths without a matching work identity.
They do not establish which original native request each queued call should own.
A timeout-only repair would leave the seven post-consumption cases unresolved.

The KMS frame-clock enable method currently sets only a Rust-side boolean. Its
false path retains legacy timed-vsync behavior. Do not impose a global engine
selection policy without accounting for this mode distinction. The next repair
needs a bounded work/reservation handshake that preserves scene content and
handles stale queued work, no-raster framework frames, topology change and
shutdown. No admission, selection, queue, framebuffer or fence policy changed
in this diagnostic. The focused external protocol review remains pending.

## Executed checks and identities

Start: `5e8f2ecb60d2119618c380f20aefa4a0ca7bb545`.
Initial INFO diagnostic source: `7e1abd4e621ef811a8f72dfb0a56f1f770b665fa`.
Final frozen source: `bf0458a1737c99ae284edc5805751318730771b3`, tree `cc8f930b67cc500db0fd4e75cf8358075752a70e`.
Engine base: `d728e61e7d835e02c453c70ae9523a40f6c03215`. Denial remains the qualified
`5c960b5bd1ff043c543a3614df9cb56c450d76bd` executable, SHA-256
`aa00de38f46ee44d85b3bc2fcc2104575d13d4e040ba60b6f73279311d436711`.

- Initial diagnostic: actual ARM64 object and separate link **PASS**, but origin
  observation **FAIL** (zero records). Normal Shell startup sets the threshold to
  ERROR, suppressing INFO. That VM remains recorded: 54 frames/page flips and
  eight errors, 48.777 seconds. Do not use it
  as callback-origin evidence.
- Actual log-threshold regression: the original INFO helper fails nested and
  concurrent-cap cases; disabled operation passes. IMPORTANT passes all three
  cases, including the exact pinned normal-startup severity assignment. New test
  children disable core dumps for assertion failures. The initial assertion
  failures and logs remain retained.
- Both ARM64 object builds **PASS**, 5.983
  and 5.983 seconds. Both full links **PASS**,
  201.101 and 201.102
  seconds, using the established 4 GiB/no-swap and two-CPU bounds. Only the
  rasterizer object is newly compiled per attempt; nine qualified cleanup objects
  are reused against the read-only original cache. Ten of 3264 link inputs are
  substitutions. Compiler/linker/objcopy file hashes remain unchanged.
- The final engine is `4ca08d258a4f60ad8f3238cf066422354675fe17ef2b0fd043b4cf6f9a8335cf`. AArch64 ABI exports, SONAME,
  dependencies and the 32-file bundle comparison pass; only the engine changes.
  Kernel, Mesa, QEMU/VirGL, Denial, AOT/assets, usage flags and fence policy are
  unchanged. Logging perturbs timing; frame counts are not a performance comparison.
- Final VM: origin correlation and context cleanup **PASS**, session **FAIL**;
  48.787 seconds. Serial SHA-256:
  `24a7c2528c9d8220e4c9352b8052abeacc3f9f0dd0ed27a1cb8ec12b8c59a477`.
- Frozen active tier: 87 PASS, zero FAIL/BLOCKED/SKIPPED
  suites, 255 NOT_SELECTED and three declared optional
  subchecks SKIPPED; 126.405 seconds. The three new manual
  exact-engine helper cases are separately executed, not silently included in the
  ordinary tier. Exact commands, durations, patches and hashes are in the
  [qualification JSON](2026-09-12-render-origin-qualification.json).

Both guests retain no-network, read-only runtime/payload, host render node only,
1536 MiB/no-swap container, 1 GiB guest, 120-second harness, 45-second session and
8 MiB serial bounds. Containers are removed. Phone, USB, signing, claims,
installation and protected storage were not operated. Historical S06/R01 FAIL,
accepted server/rescue, signed fallback and mobile physical NOT RUN are unchanged.
No new phone candidate or review-branch push occurred.

## Retention and next action

Lossless archives retain 17 completed host-test executables and two historical
unstripped engine outputs, saving 59541907 and
48783921 bytes. Every archived member was
stream-verified before removal; restoration paths and commands are in the linked
record. Runnable stripped libraries, sources and logs remain. The accepted
original engine is unchanged. Duplicate VM payload staging was retired only after
matching all 33 files to retained originals. No historical evidence was relabelled.

Private roots: `/home/deck/.local/state/rog5-render-origin-20260912-r1` and `/home/deck/.local/state/rog5-render-origin-20260912-r2`. Next: implement the smallest reviewed reservation
handoff, using these cross-path cases as regressions. Reuse the corrected cleanup
objects and existing runtime; no kernel rebuild or phone experiment is required
to investigate this software boundary.

## Changed files and final validation

- `configs/project-status.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `docs/development.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `patches/flutter-engine-d728e61e/0003-trace-raster-call-origin.patch`
- `patches/flutter-engine-d728e61e/README.md`
- `scripts/host/test-render-origin-audit.py`
- `test-results/2026-09-12-render-origin-qualification.json`
- `test-results/2026-09-12-render-origin.md`
- `tools/denial-engine-tests/render-origin.cc`

Final metadata validation passed all 13 cases, retained artifact coverage and
generated status. The active tier peaked at 317.2 MiB, with zero swap.
