# Denial authorization history: consumption and expiry are separate failures

Previous goal turn: progress. This turn adds a bounded real-function trace and
executes it in ARM64 VirGL. Seven failures follow a consumed reservation; only
one follows expiry. A timeout-only fix would miss most observed failures.
Denial's reservation is internal per-frame admission, not missing user approval.
No phone operation, signing, claim, candidate creation or protected-storage
mutation occurred. Physical rows remain NOT RUN; S06/R01 remain FAIL.

Starting commit `801f7e4e626d2b6b5a44b0738b3e4f24ddbc2fbb`, tree `c02c38c4db76f969af15e6fec522ba1e559e1fcc`.
Source frozen at `ca89dcf7dcf5f1e5b6fde950504c35bdcedd472e`, tree `6eda334b934e8ca56b814c2197aa68c479335e99`.
Denial `85b2303e2f09ae7b7b993641f90061a200f03d53`, Smithay `812bd33259ff58810dadef6086d8385eeac1ca55` and Flutter
`d728e61e7d835e02c453c70ae9523a40f6c03215` remain pinned. Later commits record evidence/review packaging.

## Implemented and observed

Patch 0003 records at most 512 ordered grant/consume/expire/cancel/refusal events,
only under the existing render audit. Each includes the view, request dirty
serial, reservation age and slot states/reference counts. The last permitted
record marks the cap explicitly. Admission logic, expiry, pool/descriptor guards,
flags and native fences are unchanged. Actual functions are compiled by the
extended broker regression, including a contended sequence-cap case and explicit
regrant after expiry. Corrected source passes nine tests; the original passes
four and fails four diagnostic expectations (the new trace-cap test is after-only).

| Executed check | Result | Duration |
| --- | --- | ---: |
| Exact-source broker/trace regression | 9 corrected PASS; original expected failures | 1.206 s |
| One-crate ARM64 build | PASS | 211.070 s |
| Bounded VirGL VM | FAIL: 50 frames/page flips, eight backing-store errors | 48.769 s |
| Frozen active tier | 87 PASS, 0 FAIL/BLOCKED/SKIPPED suites | 133.734 s |

The active tier records 255 NOT_SELECTED suites and three declared optional
subchecks SKIPPED. Exact per-suite commands/times are in JSON/JUnit. No new
GitHub CI result is claimed. The binary SHA-256 is
`6b4f86ae95648f97ba1191da9fcf1bd014fb1e80f16794086d86f1de173a6ec5`.
Patch 0003 SHA-256: `448b00598c86134a4bd56e496dda6a8daf8952297e1cb92fff084840bb267025`.
Only output_pipeline.rs differs from the previous 701-file diagnostic source.
Kernel, Arch runtime, Flutter engine/AOT/assets, Mesa and VirGL are unchanged.

The trace has 278 contiguous records, below its 512 cap: 135 grants, 85 expiries,
50 consumes and eight refused callbacks. Seven have consumption as their last
broker transition, one expiry; no cancellation occurs. Most refused snapshots
have reusable slots; one also has a Ready slot. This does not imply the callbacks
belong to the same engine frame: dirty serial is not a unique submission nonce.
The trace does not record RenderOutputs rebuild/retained mode per grant or the
native C++ caller stack. Those limitations matter when distinguishing stale
queued retained work from unsolicited/new framework rendering. The full session
still fails, including EGL BAD_ACCESS cleanup. No screenshot, input, standalone
fence trace, performance or phone GPU proof is inferred from frame counters.

## Focused review and independent work

The [review packet](render-authorization-review-20260912/README.md) contains exact
trace pairs, pinned source excerpts and upstream notices. Review branch:
`agent/pro-render-authorization-review-20260912`. Its exact publication commit
is supplied in the external handoff to avoid embedding a self-referential hash.
It asks how to bind queued engine work to a reservation, coalesce/cancel stale
work and acknowledge framework frames that produce no raster task, preserving
independent output clocks, one-use admission and bounded ownership. A larger TTL,
larger pool or dummy FBO is not justified by the data. The earlier framebuffer
review branch stays frozen at 410b6935.

Independent next work is a bounded two-thread EGL release probe in the same VM.
The engine source proves its managed thread join path, but that does not prove
release of the current EGL binding. EGL 1.5 section 3.12 specifies explicit
thread-state release; this API fact is not evidence of the retained runtime's
thread-exit behavior. [Khronos EGL 1.5](https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf).

## Resource and evidence preservation

Build: one worker, 3 GiB RAM/no swap, 600-second deadline and >3 GiB disk reserve.
VM: network disabled, readonly runtime/payload, Deck renderD128 only, 1 GiB guest,
1536 MiB container, 8 MiB serial bound, 120-second harness/45-second guest bounds.
Both owned containers were removed. The original Denial binary and dependency
cache remain; the modified binary freshness marker was archived/invalidated.

Four completed source trees (2,804 files) and 12 completed host test executables
were archived and verified byte-for-byte before retiring unpacked copies.
Restoration commands, file hashes and source modes are retained. This recovered
about 102 MB; another roughly 60 MB of terminal VM payload duplicates was removed
after streamed comparison with retained originals. No unique source, binary or
raw result was discarded. Restore the historical source/executable paths before
replaying commands that refer to those now-archived copies. The latest source,
standalone Denial binaries, raw logs and current build inputs remain unpacked.
All 486 prior artifact entries and all non-VM pointers are preserved; five new
historical archives are registered with the new offline fixture set.

[Qualification and commands](2026-09-12-denial-authorization-history-qualification.json)
record exact sources, artifacts, tests and restoration receipts. Evidence root:
`/home/deck/.local/state/rog5-authorization-history-20260912-r1`.

Changed files: patch 0003/README; broker test runner and fixture; project status,
current state and development lessons; artifact pointer/inventory; this report
and its qualification JSON; focused review README, source excerpts, sanitized
VM evidence and upstream notices. No accepted phone artifact changed.

Final metadata: five optimized checker tests and eight status tests PASS;
process durations 0.916 and 0.114 seconds.
Inventory, generated status, whitespace, review-packet JSON and secret-pattern
checks also PASS. Explicit comparisons preserve both acceptance contracts,
historical current-state body, all 486 prior sets and non-VM pointers.
