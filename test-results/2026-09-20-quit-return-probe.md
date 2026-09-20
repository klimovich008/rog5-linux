# Quit-return observation qualification — 2026-09-20

**PASS in host-only component scope.** The new optional observer distinguishes
return from the synchronous quit action from a later outstanding application
hold. Packaged ARM64 Mousepad also reaches the marker and exits0 under headless
Weston. The full Denial VM Mousepad137 remains unresolved; no full VM was run.
No phone, signing, candidate, admission, claim or protected-storage operation.

Starting source08165029/tree58f24c51. Probe and initial fixture source
`bbfb4a691b0be964e459ed9b96d496e22c4bd79f`. Final fixture/source freezes at
`7168017877a04a83ab196a88119c0b72c961c498`, tree`ea46ccae908d91afdf7d10d1992524c59ba4a330`. Source changes are only
`tools/qemu-virtio-drm/settings-sync-diagnostic.c`, new
`tools/qemu-virtio-drm/gtk-quit-fixture.c`, and
`scripts/host/test-settings-sync-diagnostic.py`; publication metadata follows.

ROG5_QUIT_PROBE requires WINDOW_PROBE and NO_UNREF_PROBE. The public action
wrapper forwards exactly once, preserves entry/result errno, and records only
the outer matching quit for the running application after an empty-window event
during that call. Generation checks reject stale notifications; nested/duplicate
calls cannot consume another return record. No reference or private object-layout
inspection is introduced. Previous default/no-unref/window DSOs remain
byte-identical. The normal single-window path is12records within1536bytes; extra
window/sync events can exhaust that bound and must not be silently accepted.

Nine new semantic cases give5FAIL/4PASS on previous C and9PASS on new C.
All33 tests pass normally and with Python -O,1.117s each; six inherited private
harness checks pass in0.115s. Coverage includes wrong object/action, calls outside
run, errno/parameter forwarding, blocked return, nested/duplicate actions, missing
symbol and compile prerequisites. All four ARM64 DSO builds and both fixture
builds pass; exact commands/times are in the qualification record.

## Actual ARM64 discrimination

Final GTK fixture uses the actual retained GTK/GIO libraries, QEMU user emulation,
private D-Bus and Weston headless Pixman, with no GPU/input/network access.
Its shutdown sync is an after-handler, unlike Mousepad's class-vfunc placement.
Both cases destroy the window and use the same public quit-action path.

| Case | Empty window to quit return | Quit return to shutdown observer |
| --- | --- | --- |
|250ms delay inside quit|255.561ms|0.281ms|
|250ms outstanding hold|5.001ms|250.703ms|

Both exit0 and produce the exact12-phase sequence. Total final fixture8.683s.
These are discriminating fixture intervals, not performance measurements of the
phone or full VM. Initial fixture8.580s also distinguished the delays, but its
normal shutdown handler was connected before the observer and logged sync before
SHUTDOWN_BEFORE. Review caught this; source switched to an after-handler and the
validator now requires the complete phase order. Old evidence remains retained.

Actual packaged Mousepad passes in9.134s with mapped frame and clean exit,
DConf mapped/owned and document unchanged. It records WINDOW_REMOVED_ZERO at
411999.232135061, APP_QUIT_RETURN at411999.726271502 and SHUTDOWN_BEFORE at
411999.726434935 (CLOCK_MONOTONIC). This verifies actual symbol interposition and
places this component run's roughly494ms gap inside the synchronous quit action;
it does not identify a slow function or explain the failed full VM.

All owned containers are absent after cleanup. Each component service uses
512MiB/no swap, TasksMax256 and the existing90-second outer bound. App close
keeps its65-second timeout/two-second kill-after. The fixture processes have
15-second deadlines; its session has40seconds. No production guard was weakened.

The frozen active tier passes112 suites in202.304s.
Counts: {'PASS': 112, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255}. Optional historical subchecks: {'SKIPPED': 3}.
This is personally executed host evidence, distinct from imported CI/phone proof.

New72368-byte probe SHA-256:
`e6557b7869d3d6f73b20ec25f5239926e178c40fc14c8713712aea046365e002`.
The [qualification record](2026-09-20-quit-return-probe-qualification.json) binds
source, build inputs, outputs, commands, logs, timing, review and fixture revisions.
All585 older artifact rows, acceptance contracts and historical state are unchanged.

Next one bounded full Denial observation can use this qualified variant without
the incompatible stage reader/ptrace helper. ZERO without QUIT_RETURN leaves the
synchronous action unobserved returning; QUIT_RETURN without SHUTDOWN_BEFORE moves
the boundary to subsequent dispatch/holds. Preserve exact stages and close limits.
No Denial/Flutter rebuild is needed. Phone physical rows remain NOT RUN.
