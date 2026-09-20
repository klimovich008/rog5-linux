# Actual ARM64 GLib signal/observer fixture — 2026-09-20

Four cases **PASS** in11.263476s including build/guest preparation.
All applications exit0; the observer legitimately refuses a completed immediate
target and captures the deliberately delayed shutdown interval. Full UI
Mousepad137 remains unresolved. No phone, full Denial VM, candidate, signing,
admission, claim or protected-storage operation occurred.

Source starts at6c8c72e9/tree4a28f553 and freezes at
`dcdd8eec9f5f5042298ea9e77544172751387c94`, tree`6097f0e2698683a6f26da8e9926fc7176d120d5b`.
Changes are only `tools/qemu-virtio-drm/glib-signal-fixture.c` and
`tools/qemu-virtio-drm/glib-signal-fixture.sh`; publication metadata follows.
The C fixture uses the actual retained ARM64 GLib and g_unix_signal_add(SIGTERM),
holds GApplication, and emits READY from a main-context idle callback. Separate
monotonic markers record callback entry before quit, shutdown and run-return.
It uses the unchanged no-unref DSO and production launcher function/observer.
The script starts the observer asynchronously, then signals packaged timeout,
preserving its two-second kill-after behavior. Observer and application results
are separate. No fixture marker enters the strict DSO lifecycle log.

| Case | Application | Observer | Callback to run-return |
| --- | --- | --- | --- |
| Immediate, no observer |0|Not requested|9.314ms|
| Immediate, observer |0|125/open:NotFound|20.290ms|
| Delayed, no observer |0|Not requested|260.417ms|
| Delayed, observer |0|0/captured|273.024ms|

The deliberate250ms g_usleep occurs after external-sync END and before
SHUTDOWN_AFTER. The capture ends at8.913374768s, inside the fixture's observed
sync-return8.778006s and shutdown-return9.032536s. Its47ms observer run records
four unclipped frame-pointer candidates, stop=Limit, interrupt-to-detach10373us.
PT_LOAD conversion and exact FUNC extents resolve the candidates to
clock_nanosleep, nanosleep, g_usleep and fixture shutdown_app. This is a known
test interval, not a Mousepad stack or a complete unwind.

The fixture executable is72072bytes, SHA-256
`a04987d0b75fc879f6959fe1b6a0cef96fdebbb002b5ef1283fea26ea23e62f8`.
The one-vCPU,512MiB guest used the retained exact kernel, read-only runtime and
payload, no networking or GPU exposure, and bounded container/process cleanup.
Normal guest poweroff and listed input identity checks passed. All owned
containers were absent. One fixed-order matrix is not an overhead benchmark:
it omits GTK, the client FIFO, session bus, renderer and full UI scheduling load.
No generic signal-delivery failure was reproduced, and no GTK repair is claimed.

The frozen active tier passed112 suites in199.529s,
with0FAIL,0BLOCKED,0SKIPPED and255NOT_SELECTED. Three optional historical
subchecks remain SKIPPED. The four manual exact-runtime cases are additional
to that tier, not silently counted as its test coverage. No unmodified full UI
experiment was repeated.

Independent read-only review also found teardown progress in the retained failed
UI log: text-input disable/commit, xdg_toplevel.destroy, xdg_surface.destroy and
wl_surface.destroy precede the recorded137. The shared log stream continues,
is129358bytes (below1MiB), and has no rejection marker. This does not directly
observe TERM callback entry or prove cross-clock timing, but contradicts treating
the absent SHUTDOWN_BEFORE marker as total lack of quit/window progress.
Blocking FIFO writes remain a theoretical backpressure path, not an observed
cause. Do not redesign logging or increase grace on that basis.

The next useful boundary is real Mousepad/GTK window removal and application
lifetime before GApplication shutdown. Use the already retained cheap actual
Mousepad/Weston component fixture to qualify a narrow observation first; its
past PASS is not Denial or phone evidence. Avoid another generic signal test.

Exact commands, hashes, timings and frame attribution are retained in the
[qualification record](2026-09-20-glib-signal-fixture-qualification.json).
All582 historical inventory rows, headless/mobile acceptance contracts and old
FAIL/NOT RUN evidence remain unchanged. Physical rows remain NOT RUN.
