# Denial VM last-window observation — 2026-09-20

**FAIL**: Foot exits0; Mousepad exits137. The new observer records an empty
GTK window list, but GApplication shutdown is never observed. This narrows
this run's failure to after the last-window removal class closure and before
SHUTDOWN_BEFORE. It does not identify a defective GTK/Denial function.

No phone operation, candidate, signing, admission, claim or protected-storage
mutation occurred. No Denial/Flutter or phone kernel rebuild occurred. Physical
rows remain NOT RUN; S06/R01 FAIL and all earlier evidence remain unchanged.

## Inputs and executed checks

Starting/executed source: `b96ffdecd0d8c1fd357ee13d7298a56f204f5c12`,
tree `f536673cf1999f030e1177e65db4adbe607c335b`, clean checkout.
The DSO was compiled from617c4e78; its source still matches exactly. Its hash is
`4d9817c6bba700a8d2ea4b73b79ca53a0e58317571939e7b5f7b426529b86614`.
The112-suite active tier and24 normal/optimized DSO cases from that source are
inherited by matching inputs, not rerun or counted as tests executed this turn.

The qualified window/no-unref DSO replaces the previous no-unref DSO. All four
app-close sampling options are removed: no ptrace, stack or stage waiter is
built or staged. Independent review checked the fresh payload and streamed
88-member session archive; neither can supply an old helper. The existing
supervisor forwards the bounded1536-byte lifecycle log unchanged and preserves
nonzero child exits. The new markers never enter the incompatible stage reader.

Kernel, runtime, Denial/engine/shell, graphics flags, caches and application close
deadlines remain unchanged. The retained kernel is Linux
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` in the generic ARM64 VM profile.
This is VirGL/host-render-node testing, not Adreno or ROG5 scanout evidence.
Two small ARM64 helper builds pass in6.032s and6.382s; both outputs are
byte-identical to the previous run. The underlying QEMU command exits0 after
normal guest poweroff in330.145s. All25 harness command steps pass, while the
single final UI qualification fails. These are different result scopes.

The whole harness takes393.923s; outer service6min55.327s, peak1.7GiB, zero swap.
Complete runtime bytes/metadata and all recorded input hashes pass final checks.
Owned containers are removed and absent. `/var` unmount still fails as before;
normal poweroff does not erase that result. No second VM was run.

## New evidence

Mousepad PID987 records these CLOCK_MONOTONIC stages:

| Stage | Seconds |
| --- | --- |
| loaded |279.742479088|
| APP_RUN_BEGIN |280.686151296|
| WINDOW_REMOVED_ZERO |310.355080400|
| SHUTDOWN_BEFORE and all later lifecycle stages |not observed|

Both native apps map and receive the requested focus sequence. This close-only
run does not qualify text entry, visual semantics or per-client presentation.
Timeout records TERM then KILL. The launcher records close begin309.28 and
return312.30 in CLOCK_BOOTTIME; these are not exact signal timestamps and are
not subtracted from the MONOTONIC markers. No sampling helper is present, so
this run proves that helper is not necessary to reproduce a close failure.
It does not quantify the DSO's own overhead or establish why older runs stopped
at different stages. Final retained logs supersede interim empty-log snapshots.

GTK's retained RUN_FIRST window-removed class closure releases the window's
application hold before removing it from the public list. The AFTER observation
therefore follows that closure, but total application holds may remain, and
window destruction can still be on the current callback stack. Retained Mousepad
source contains holds for preferences and asynchronous autosave save/delete.
The source has no explicit inactivity timeout, and retained GLib defaults to0;
the component fixture's550ms gap is not evidence of a configured500ms delay.
These are matching upstream-source leads, not exact packaged debug attribution.

## Next bounded step and improvement

Qualify one optional APP_QUIT_RETURN marker after the real external
`g_action_group_activate_action(application, "quit", NULL)` returns, only for
the observed application after WINDOW_REMOVED_ZERO. The retained Unix-signal
callback returns immediately after this action. One additional record keeps
the normal single-window path at12 records and within the existing byte cap.
Prove original-call-once and errno behavior, then compare a small actual ARM64
fixture's delay inside quit against an outstanding hold released later. This
separates synchronous destruction return from later dispatch/holds without
private object-layout assumptions. Prove actual Mousepad interposition too.

Readelf confirms the exact packaged libmousepad imports the action function.
An initial executable-only assertion found no import because implementation is
in its NEEDED libmousepad.so.0; the dependency inspection corrected that scope.
An imported symbol alone is not proof of the runtime callback path.

Do not repeat this VM unchanged, widen grace, rebuild the compositor, or guess a
settings-sync fix from marker absence. The small qualified component fixture
can validate the next seam first. This unresolved VM application issue must not
be promoted into a prerequisite that blocks independently authorized native
phone graphics work. Phone access remains outside this task's authorization.

Exact commands, source/tool/artifact identities, timings, source review, logs and
results are in the [qualification record](2026-09-20-gtk-window-vm-qualification.json).
Its SHA-256 is `f47a9ab49be5cb592b9a12f2fc131a1f43137b64abdd5488183ca4f40664c95e`.
All584 earlier artifact rows, both acceptance contracts and the historical
current-state tail are preserved. Publication changes documentation/provenance
only; the executed source identity above does not become the publication commit.
