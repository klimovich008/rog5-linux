# Picture-paint diagnostics and bottom-caret selection — 2026-09-13

Scope: offline ARM64 VirGL VM and host tests. This is not phone display,
touch, GPU, suspend, shutdown, or recovery qualification. Physical remains
NOT RUN; headless S06/R01 remain FAIL. No phone operation, signing, admission,
claim use, protected-storage mutation or new phone candidate occurred.

## Source and compiled inputs

The picture diagnostic was compiled from `aae7ee8aeef937a33b6bce8a1fdfb452c9dadd44`,
tree `ff1dc1d3cf815f33f554795c3b9a90cf82e7789d`. The later observer-only repair is
`aab7db8b4dfd007502184f78280f2ed1a7b61f70`, tree
`dce6f3da95d31c4053f625831e4d6486a30821cf`. It does not change the compiled shell.
The separate native compositor remains the retained `daf4b119` build. Metadata
commits do not change any of these evidence-producing identities.

The new vector_graphics 1.2.2 patch instruments actual
`RenderPictureVectorGraphic.paint`, the corresponding widget build and a
bounded shared logger. The default flutter_svg picture strategy is retained.
Records distinguish paint entry, opacity skip, draw begin/end and paint end;
they include monotonic time, Flutter frame timestamp, picture identity, size,
offset, opacity and filter presence. The 96-record cap does not schedule frames
or change canvas operations, image ownership, or exception behavior. Collector
limits remain unchanged; early picture records now survive later frame noise.

`0001-trace-icon-encoding-and-decoding.patch` then
`0002-trace-picture-paint.patch` apply to the exact clean cached package and
reproduce the three modified package files. The earlier private one-shot patch
check is superseded by `patch-series-verification.json`.

38 actual extracted Dart paint/logger checks pass, including comparison with
the prior package's canvas operations and exception identity. This is not a
Flutter layout/raster/GPU test. The old collector fails the new early-record
regression; the corrected collector passes all 11 cases under Python -O in
3.261 seconds. Real shell frontend/AOT builds pass in 23.508/20.007 seconds;
667 workspace/package hashes pass after building. No native or kernel rebuild
was needed. Only `libapp.so` differs from the preceding VM payload file closure.

An initial formatting-tool invocation failed because its telemetry directory
was read-only; a bounded 1 MiB container tmpfs resolved that tool bootstrap
failure. Both results are retained. No package code was changed to bypass it.

## First VM: paint reached, caret probe refused

The first run uses `aae7ee8a`. It fails in 249.492 seconds total, with
235.875 seconds of VM execution, at `pointer did not select a low editor caret`.
Its home screenshot contains app/fallback icons. The diagnostic retains eight
build records and thirteen complete paint/draw sequences across three picture
identities, with opacity 1. This proves that those Dart canvas calls returned
in this run, not why icons were absent in the previous run. Instrumentation
can change timing; historical missing-icon failures remain unresolved.

Both Mousepad and Foot launch/map and become ready. Focus reaches Mousepad,
Foot, then Mousepad; the final return to Foot and OSK typing are not completed.
The editor capture shows the prepared long document. The delivered pointer
(296.4921875, 1075.8828125) agrees with the actual production mapping expectation
(296, 1075) within the existing two-pixel tolerance, including XDG origin
(26, 23). This is pointer mapping evidence, not a successful low-caret test.

A new cursor rectangle request and commit arrive after button down, but still
describe the old top row (x=29, y=90, width=0, height=20). No later qualifying low
rectangle is observed before that run aborts. One bounded optional startup
snapshot times out; that diagnostic failure remains explicit. The named host
container is removed and its absence verified. Normal guest shutdown and
authenticated-session cleanup are not established by host removal.

## Host observer repair

A fresh text-input rectangle is not an acknowledgement that pointer selection
has finished. The original observer refused the first nonlow rectangle
immediately. It also checked its four-second deadline only when fresh evidence
was missing, allowing late qualifying evidence to succeed.

The production observer now verifies surface, geometry and pointer mapping
before allowing a valid nonlow baseline to wait within the original deadline.
Waiting never rearms or extends it. Qualifying updates at or after the deadline
fail. Stale rectangle recommits cannot qualify. The final low-row and height
criteria are unchanged.

Five new regression methods fail against the old source (five failures and two
subcase errors across 18 cases), then all 18 focused cases pass in 0.094 seconds.
They exercise production observer methods. This demonstrates the observer
contract repair, without establishing the cause of the actual client's old-row
update. All 105 active suites pass on the repaired frozen source in 170.374
seconds; zero FAIL/BLOCKED/SKIPPED suites, 255 NOT_SELECTED, three declared
optional subchecks SKIPPED. The earlier 105-suite pass in 157.772 seconds covers
the compiled diagnostic source separately. These are locally executed results,
not newly verified GitHub CI results.

## Runtime comparison

The second VM uses the repaired host source `aab7db8b`. Its 32-input
comparison confirms only the host observer differs from the first VM. Payload,
kernel, engine, native compositor and runtime are reused byte-for-byte; all 32
input hashes verify afterward. The VM fails earlier at launcher tile readiness
in 224.133 seconds total, with 210.369 seconds of VM execution. Eight identical
captures (SHA256 `91644732dda79722309861b412070c675fb78e2abaabb45aa94f37c63c2978e1`)
show wallpaper, labels and widgets but no app/fallback icons. This is the same
image hash as the preceding missing-icon observation. There are no pointer
actions or app launches; runtime caret settling therefore remains NOT RUN.

Crucially, the new diagnostics capture seven complete paint/draw sequences for
all three picture identities at Flutter frame timestamp 20963309 microseconds:
three 128px Foot instances, one 128px Mousepad instance and three 64px fallback
instances, all with opacity 1. Seven matching build records are present. These
records directly disprove the narrow explanation that the icon widgets never
reach picture painting in this failed run. They do not establish successful
rasterization, correct clipping/composition, native submission or presentation.
The remaining boundary must be traced, not guessed from later idle counters.

Two of four bounded startup snapshots report timeout124; the other two succeed.
The diagnostic stream stays bounded. The named host container is removed and
its absence verified; normal guest shutdown/session cleanup remain unproven.
Existing 300-second VM and four-second caret limits were not widened. No third
VM or unchanged rebuild was started after this result.

Next: correlate this picture frame with the actual Flutter raster/output
callbacks, output damage, native submission and presentation. Use bounded early
records, preserve failure returns and do not consume GL errors without recording
them. Keep the existing images as control. Neither a scheduler patch, a rendering
strategy change nor removal of the launcher readiness gate is justified yet.

## Retained evidence

Raw logs, screenshots, package/source inventories, exact commands, result JSON,
and build/VM payloads stay private in `rog5-picture-paint-20260913-r1`.
The final qualification JSON will bind these identities and preserve both VM
outcomes, without promoting diagnostic log lines into protocol success proof.

Machine-readable identities and commands: [qualification JSON](2026-09-13-picture-paint-qualification.json).
