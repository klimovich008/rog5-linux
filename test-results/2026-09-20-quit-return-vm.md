# Denial VM quit-return observation — 2026-09-20

**FAIL**: Foot exits0; Mousepad exits137. The qualified observer records
WINDOW_REMOVED_ZERO, but neither APP_QUIT_RETURN nor SHUTDOWN_BEFORE appears.
This supplies a more specific observation interval, not a complete backtrace,
a proven deadlock, or proof that the selected interposed quit call was entered.

No phone operation, candidate, signing, admission, claim or protected-storage
mutation occurred. No Denial/Flutter or phone-kernel rebuild occurred. Physical
rows remain NOT RUN; S06/R01 FAIL and previous evidence remain unchanged.

## Exact inputs and execution

Starting/executed source `1b60def8afa1cf075c11a3b6a5f1e4e257640c15`,
tree `1c814ae8f25fb30421bfa9e582f7f3378a7613d9`, clean checkout.
The72368-byte DSO was built frombbfb4a69 and qualified on final source71680178;
its source still matches. SHA-256:
`e6557b7869d3d6f73b20ec25f5239926e178c40fc14c8713712aea046365e002`.
The112-suite active result,33 normal/optimized tests and actual ARM64 GTK/Mousepad
component qualifications are inherited by exact matching inputs, not rerun here.

Only the diagnostic DSO changes from the previous window-observation VM. No
ptrace, stack or stage helper is staged. Kernel, runtime, Denial/engine/shell,
flags, caches and close limits remain unchanged. Both small ARM64 helper builds
pass in6.082s and6.434s and produce byte-identical binaries to the prior run.

All25 harness command steps pass, but the single semantic UI qualification
fails. The QEMU process exits0 after normal poweroff in305.370s; that is not
UI acceptance. Whole harness368.623s; outer service6min29.450s, peak1.5GiB,
zero swap. Full runtime bytes/metadata and input hashes remain unchanged.
Owned containers are absent. `/var` unmount still fails, separately from normal
poweroff. No second VM was run. An initial preparer command used a not-yet-created
working directory and was rejected before execution; no experiment ran from it.

## Recorded boundary

Mousepad PID976, CLOCK_MONOTONIC:

| Stage | Seconds |
| --- | --- |
| loaded |254.871258592|
| APP_RUN_BEGIN |255.666266128|
| WINDOW_REMOVED_ZERO |284.890995632|
| APP_QUIT_RETURN and all later lifecycle stages |not observed|

Timeout records TERM then KILL. Launcher close begin284.17 and return286.84 use
CLOCK_BOOTTIME, so they are not subtracted from MONOTONIC markers or treated as
exact signal timestamps. Both native apps map and receive the requested focus
sequence. Text entry, visual semantics and per-client presentation are NOT RUN
in this close-only test. The retained stream is123810bytes with51563diagnostic
bytes, within its existing bounds. Raw logs and diagnostic payloads stay private;
the qualification publishes selected observations and exact evidence hashes.

The actual-Mousepad component test proves the intended interposition path can
work with these packaged bytes. Marker absence in this VM still does not prove
entry into that call. This distinction rules out claiming a specific synchronous
function is defective without an instruction snapshot. The successful small
fixture does not reproduce the full VM's load, compositor or systemd user bus.

## Next smallest discriminating step

Reuse the existing bounded PC/stack observer with an explicitly selected
last-window mode. Keep its file/PID/clock identity, append-only, size and
partial-record guards. Ready is exactly loaded→APP_RUN_BEGIN→WINDOW_REMOVED_ZERO;
NONZERO does not arm. Any later phase, including quit return or shutdown without
quit return, invalidates the interval. Preserve the old sync mode,1200ms total
budget, asynchronous arming before TERM, no deadline reset, and all checks before
attach, while stopped, after detach and before publishing.

Qualify selection against the actual GTK lifecycle records: the250ms delay
inside quit is eligible, while the250ms hold after return is ineligible despite
a live process. That GTK fixture uses QEMU-user on the x86 host, so it cannot
qualify native ARM64 ptrace registers. Reproduce these boundary patterns in the
existing small ARM64 system-VM/API fixture for capture qualification. Preserve stale/malformed,
partial and during-capture progression refusals. Describe a resulting sample as
“after observed last-window removal, before observed quit return or shutdown.”
It remains one PC and bounded frame candidates, not a stationary-deadlock proof.

Do not repeat the full VM unchanged, widen close grace, add another lifecycle
marker or rebuild Denial. Keep independently authorized native phone graphics
work separate from this VM application issue. Phone access remains outside the
current task's authorization.

[Qualification record](2026-09-20-quit-return-vm-qualification.json):
SHA-256 `fc0f0ccff8819c7a280dc802a97ac212477fc7386e51fcc47ffc08edf1196c26`.
It records commands, inputs, outputs, durations, limits and source review.
All586 earlier inventory rows, acceptance contracts and historical state are
preserved. Publication changes documentation/provenance only.
