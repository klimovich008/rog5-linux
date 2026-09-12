# Denial broker refusal isolation

Previous goal turn: progress (checked allocation, actual ARM64 build and VM
frames). This turn also made progress: the observed render-target refusal is
now specifically missing authorization. It is not pool capacity exhaustion in
this run. Full session remains FAIL; no phone operation, signing, admission,
claim, candidate creation or protected-storage mutation occurred. Physical rows
remain NOT RUN, and historical headless S06/R01 remain FAIL.

Starting commit `c1beb871d45503e9894a8731dcdf2fd59d538eaf`, tree `b31c00a442dcaf18fb7a78a5671fdc749eac5a96`.
Diagnostic source frozen at `a3534e51769ef694045e2095485fc440fbd34481`, tree `8ead532c95f321ff292523db1a09032dbcd96581`.
Later changes record results only. The published review branch remains frozen
at `410b6935526a977ca727359f23ee43fc4ebe45b2`. No new push or CI result is claimed.

## Change and executable checks

Separate patch 0002 replaces the ambiguous internal PoolExhausted reason with
MissingPool, MissingAuthorization and NoFreeSlot. ReadyHandoff is unchanged.
Existing INFO audit keeps the old aggregate counter while reporting the three
components, initialized and reset with each interval. Existing authorization
expiry is additionally logged at INFO only with DENIA_RENDER_AUDIT enabled.
Allocation, one-use consumption, deadlines, flags, fences and refusal decisions
are unchanged. Patch 0001's descriptor validation remains unchanged.

The exact-source test compiles actual acquire, expire_authorizations and
record_target_blocked methods and actual enums, with data adapters. Seven cases
cover view/size mismatch, missing authorization, referenced/busy slots, Ready,
successful acquisition/field handoff, expiry boundary and aggregate accounting.
The old source passes three and fails four diagnostic expectations; the new
source passes all seven. No unrelated duplicate broker model is used. This
manual source-dependent test does not run implicitly in ordinary repository tiers.

| Personally executed check | Result | Duration |
| --- | --- | ---: |
| Final exact-source regression, original and diagnostic variants | 7 corrected PASS; 4 expected original FAIL | 1.138 s |
| ARM64 Denial diagnostic build | PASS | 213.070 s |
| Bounded VirGL VM | FAIL: 53 frames/page flips, errors remain | 48.779 s |
| Frozen active tier | 87 PASS, 0 FAIL/BLOCKED/SKIPPED suites | 128.556 s |

The integrated tier enumerates 255 NOT_SELECTED suites and three declared optional
subchecks SKIPPED. Exact commands and per-suite times are retained in JSON/JUnit.
The previously corrected compiler-wrapper PATH is explicit in the recorded
service command; no missing-compiler retry was needed this turn.

Denial binary SHA-256: `1fa170f899fb77c2dadc6c32c1087f5b7e8e2aa507de37d7f8aec791c745054c`.
Diagnostic patch SHA-256: `593e74d6d5fde9f41fdff210296d82c4d4617d206b6a2c368805a0d344fea269`.
The 701-file source inventory differs from the retained allocation-guard source
in three diagnostic files only. Denial/Smithay pins, Flutter engine and bundle,
Arch runtime, kernel, Mesa, QEMU and VirGL remain unchanged. One-crate build:
one Cargo worker, 3 GiB RAM/no swap and live >3 GiB disk reserve guard. VM:
readonly runtime/payload, network disabled, Deck renderD128 only, 1 GiB guest,
1536 MiB container, 8 MiB log limit, 120-second harness/45-second guest bounds.
Both owned containers were removed after terminal results.

## Observed boundary and unresolved cause

Sixteen audit intervals total nine MissingAuthorization refusals and zero
MissingPool, NoFreeSlot or ReadyHandoff refusals. The log contains exactly nine
backing-store errors, 104 authorization expiry events, 53 raster frames and
53 page flips. EGL cleanup still reports BAD_ACCESS. None of those positive
counters promotes the failed session; no visual, input, performance, separate
fence trace or phone GPU proof is claimed.

Pinned engine source inspection confirms that returning None from Denial's
backing-store handler becomes false in the Rust callback, which causes the
observed embedder error. Shell::RenderOutputs queues Prepare/Draw work on the
raster thread and returns before it runs. Meanwhile the broker can expire an
unclaimed authorization after two output intervals. A delayed queued request
can outlive that permission. The audit does not attach an authorization ID or
its last transition to each rejection, so it does not prove expiry rather than
prior consumption/cancellation for each of the nine failures. Do not enlarge
the buffer pool, admit an unauthorized target, or increase deadlines on this
aggregate evidence.

A separate exact-source trace establishes that this configuration uses an
engine-managed raster thread. FlutterEngineShutdown collects the shell/thread
host; owned fml::Thread destructors join. This does not establish EGL release
at thread termination, so the cleanup BAD_ACCESS cause remains unresolved.
Eight relevant engine files match the retained d728e61e Git objects, and the
runtime engine bytes match their existing qualified artifact identity.

## Next smallest authorized experiment

Record the last grant/consume/expire/cancel transition for the first few rejected
render requests, alongside engine queue/callback order. Test that instrumentation
against actual broker methods before one bounded VM run. Use the resulting
handoff evidence to fix the protocol; preserve one-use authorization, queue and
buffer bounds. Separately isolate whether EGL thread termination leaves the
context current in the retained runtime. Phone operations remain unauthorized.

The build reused the dependency cache; no kernel/engine rebuild was needed.
About 60 MB of terminal VM staging copies were retired only after streamed
comparison against retained originals. The reconstruction map, binary, source,
serial log and original failures remain. The modified Cargo binary freshness
marker was archived/invalidated; all dependency cache and original binary bytes
were preserved. All 485 previous artifact sets and every non-VM pointer field
remain unchanged. The new set is an offline fixture with no admission authority.

[Qualification and exact commands](2026-09-12-denial-broker-refusals-qualification.json)
retain all results and hashes. Private evidence root: `/home/deck/.local/state/rog5-broker-refusal-20260912-r1`.

Changed files: patch 0002 and patch README; `test-denial-broker-refusals.py`;
`tools/denial-modifier-tests/broker-fixture.rs`; project-status/current-state;
development-lessons; current-artifact/artifact-sets; this report and its JSON.

Final metadata verification: five optimized checker cases and eight status
cases PASS; complete checker process durations 0.916 and
0.114 seconds. Inventory, generated status and whitespace
checks also PASS. Explicit preservation checks passed against the starting
commit. Exact commands/durations are included in the qualification JSON.
