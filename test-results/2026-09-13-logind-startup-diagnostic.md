# Logind startup diagnostics and recurring missing icons — 2026-09-13

**Source diagnostic PASS; VM launcher qualification FAIL.** The VM reached the
Denial home screen but all eight captures lacked app/fallback icons. Readiness
correctly refused interaction. Bottom-caret, app switching and text entry remain
NOT RUN in this run. Phone physical qualification remains NOT RUN; S06/R01 FAIL.

## Change and tests

Frozen observer/test source `96e5d19a38a7e9d0abd2951634c9e79b810ba3fd`, tree
`41af3638a7d6ca8ca935c799eedcbbb4560bdd46`. The shell binary is still compiled from `b9d6a5ab`;
native Denial, engine, VM kernel and runtime are unchanged. Metadata commits do
not retroactively change those compiled identities.

`tools/qemu-virtio-drm/logind-observer.sh` now records a 4 KiB PAM-log tail and
up to eight selected process cmdline/status pairs, each capped at 1 KiB. It
reads neither environment nor memory. The entire new collection has a four-second
deadline and one-second kill grace, retaining the four snapshots and 25-second
spacing. Bytes are hex encoded, not mixed into serial success evidence. Optional
absence, refusal, read failure and timeout remain explicit.

The new `scripts/host/test-logind-startup-diagnostic.py` executes the actual shell
function and actual serial validators. Eight cases pass under Python -O in
4.250s: bounded reads, process cap, missing input,
symlink/FIFO refusal, command failure, stalled-reader termination, original
schedule and forged success markers. Unencoded fixture payloads satisfy the
existing validators, while encoded diagnostics cannot. The new mandatory test
is registered in the declarative manifest and existing public selector.

All105 active suites passed in159.171s, with0FAIL/0BLOCKED/
0SKIPPED suites and255NOT_SELECTED. Three declared optional subchecks remained
SKIPPED. This was executed locally; no new GitHub CI result is claimed.

## Bounded runtime result

The unchanged300-second VM limit was not reached: readiness rejected the run
after225.396s of VM execution,239.539s including preparation and host cleanup.
Runtime/PAM/user/device progress is now visible at snapshots110.30,147.11,
180.46 and216.48 guest-uptime seconds. Snapshot0 had no PAM log; snapshot1
reached credential establishment; snapshot2 recorded successful session opening,
active local VT/user manager and mediated device checks, followed by Denial
preparation. The actual captures then establish a rendered home screen.

This run is distinct from the retained prior300-second startup timeout. It
does not identify the reason for that prior timing failure or prove reliable
startup. No kernel, Mesa, QEMU, native compositor or shell binary was rebuilt
or changed for this comparison. Of32 recorded VM inputs, only the startup
observer hash differs. All36 input/reused-binary hash checks passed afterward.

The app evidence stream contains27,192bytes. Eight540×1224captures share SHA256
`91644732dda79722309861b412070c675fb78e2abaabb45aa94f37c63c2978e1`.
Visual inspection shows wallpaper, labels and battery widget, but no application
or fallback icons; the retained reference contains those icons. There were no
pointer actions, app mappings, keys or acknowledgement. Do not update the
reference to accept missing icons.

The existing package diagnostics show successful file reads for Foot and
Mousepad, three encode/decode completions, eleven set-state records and seven
`build-picture` records. The vector sequence reaches43, below its64record cap.
This disproves the narrow explanation that icon loading never reaches widget
rebuilding. `build-picture` is a widget-build marker, not a paint or framebuffer
result. Late frame-audit snapshots show idle requests; they do not establish
that an earlier frame request was lost. Earlier icon-success evidence remains
valid for that run and does not erase this recurrence.

The host removed the exact owned container and verified its absence. This is
host cleanup PASS, not proof of normal guest shutdown or authenticated-session
cleanup. The VM failure remains FAIL.

## Next unresolved boundary

Trace and instrument the actual vector picture paint path and correlate it with
Flutter frame submission and native presentation. The pinned flutter_svg default
is `RenderingStrategy.picture`; inspect that path rather than assuming raster
toImage behavior. Preserve current timing/readiness bounds and the pointer-origin
fix. A source review found no demonstrated dropped-vsync counterexample; do not
patch frame scheduling or change rendering strategy without stronger evidence.

No phone/USB operation, signing, admission, claim use, protected-storage mutation
or new phone candidate occurred. Raw logs/screenshots and decoded diagnostic
bytes remain private under `rog5-bottom-caret-20260913-r1/combined-r2` and
`rog5-startup-diagnostic-20260913-r1`. Machine-readable evidence and exact commands
are in [qualification JSON](2026-09-13-logind-startup-qualification.json).
