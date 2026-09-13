# Release icon stages and clean no-pan VM session — 2026-09-13

The ARM64 VirGL VM **passed** with visible launcher icons, Mousepad/Foot
switching, visible **test → tes → test** using the OSK without manual panning,
clean exits for both clients, authenticated session/scope removal and normal
VM poweroff. The coordinator inspected the five retained captures. This is
VM software qualification, not ROG5 touch, OLED or Adreno qualification.

The previous icon failures and Mousepad137 **did not reproduce**. Their causes
remain unresolved. Diagnostic instrumentation may alter timing; this result is
not a proven fix for either historical failure. Keep the prior
[missing-icon failure](2026-09-13-close-diagnostics.md) and
[successful typing with failed cleanup](2026-09-13-launcher-diagnostics.md).

## Implemented and built

Source `e95c425bd94fcf7135d92af0caec906103474deb`, tree `57dd53275108269df61c304e91968f409d86c2e7`, follows
starting commit `95f8d66622832e9c2bc130a262d602de2596c713`. Denial patch0018 instruments the actual direct
HomeAppTile → AppIconImage path. Private copies of flutter_svg2.3.0 and
vector_graphics1.2.2 add stages around existing preparation, release encoding,
decoding, cache/pending results, mounted errors, setState and widget builds.
No cache key, returned widget, Future chain, retries or frame requests changed.
The original mounted guard and rethrow semantics remain intact.

The shell logger caps48 records per isolate and two per stage/path; each package
caps64 records per isolate. These are per-isolate limits, not a global worker
count. Labels contain sanitized identifiers/type names, never SVG contents or
exception messages. Worker creation still follows the original load path.

The existing guest snapshot now scans at most the first1MiB for icon stages,
retains at most24KiB of framed stages plus a4KiB recent tail, and enforces the
existing30KiB snapshot/64KiB host budgets and3-second producer deadline. A new
semantic regression failed on the old tail-only snapshot, then passed after the
change. This prevents later frame logs from displacing the early failure stage.

The actual release frontend passed in23.509s
and ARM64 AOT in20.007s, using explicit read-only
mount overrides for the two copied packages. No native Denial, engine or kernel
rebuild was required. All385 workspace and281 copied package file hashes remained
unchanged after build. All three patches applied to matching fresh source copies;
the resulting bytes matched the instrumented trees. Shared package caches remain
unchanged. The ordinary VM runner rebuilt only its existing small PAM/seat/init
fixtures; no phone candidate or release was produced.

AOT SHA256: `e9eb0af00f9a1d56eb4eede850074d23253e56c8c760e073eeb9c7d198dd37d7`.
Unsigned VM archive SHA256: `3c10a80355ee445485f523b2f231dbbecb1b44907f6edc2cb0397fc86c2ac67e`.
The existing native compositor, kernel and engine identities are retained in the
VM input record. Packaging grants no installation or execution authority.

## Personally executed checks

| Check | Result |
| --- | --- |
| Old snapshot with early icon stage followed by frame noise | expected FAIL |
| Snapshot bounds, early-stage retention, failures/deadline, Python-O | 9 PASS,3.151s |
| Actual supervisor host fixtures, Python-O | 27 PASS,7.977s |
| Pure Dart logger limits and sanitized identifiers | 4 PASS |
| Actual SvgLoader._load with real host Dart isolates/compiler adapters | 4 PASS |
| Patch application and resulting source equality | 3 PASS |
| Real frontend and ARM64 AOT compilation | PASS,43.516s combined |
| Bounded VM | PASS,290.357s |
| Frozen integrated active tier | {'PASS': 103, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255},156.412s |

The SVG method test verifies byte/error propagation through the real Future and
isolate path with an adapted compiler. It does not execute real SVG compilation
or Flutter drawing. The four logger tests are pure Dart, not widget tests. The
real release VM separately exercised the pinned encoder and vector decoder.
Three declared optional subchecks were SKIPPED; no mandatory suite skipped or
blocked. No new remote GitHub CI result is claimed. Initial formatter failure
against a read-only analytics home is retained privately; only its scratch
environment was corrected. It did not change source or runtime behavior.

## Observed stages and session

The observer retained28,099 diagnostic bytes. After removing duplicate snapshot
records,75 distinct records include three encode and decode completions: the
bundled fallback, Foot SVG and Mousepad SVG. Four stale-picture observations
also occurred during widget replacement; no cause is inferred from them.
Encoding/decode completion and build-picture are separate from actual display;
the visible captures and independent terminal counter oracle provide that VM
evidence. The real home path bypasses DeferredAppIcon's load queue.

All12 required key press/release events and Mousepad → Foot → Mousepad → Foot
focus transitions passed. The compositor reported188 raster frames and188 page
flips with no recorded rendering errors. The exact observer ACK preceded approved
teardown; Foot and Mousepad both exited0. Session/scope removal and VM poweroff
passed. All31 declared VM inputs passed post-run streaming hash verification.

Timeout's own diagnostic records TERM, with no KILL message in this run.
The Mousepad boot-clock samples bracket262.37–264.78s, including evidence
transport; that2.41s is not an exact TERM-to-reap measurement. The historical137
sender remains unproven. Original65-second lifetime and2-second kill grace were
not changed or treated as successful on a nonzero exit.

This qualifies top-line text visibility with the OSK; actual bottom-edge caret
displacement and rotation remain untested in the VM. Reuse this exact payload
for the next distinct usability question: a prepared bottom-edge text fixture
with actual text-input caret reports and matched paint/input coordinates. Keep
these diagnostics armed so a recurrent icon/close failure can be localized.
Do not run an unchanged VM merely to accumulate a green result, weaken launcher
readiness, or change loading/close policy based on non-reproduction.

No phone, USB, signing, admission, claim consumption, phone installation or
protected-storage operation occurred. Physical rows remain NOT RUN; S06/R01
remain FAIL. The native-phone goal remains active and incomplete.

[Commands, identities, stages and results](2026-09-13-icon-stage-qualification.json).
