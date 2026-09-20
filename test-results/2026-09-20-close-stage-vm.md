# Stage-triggered VM close observation — 2026-09-20

**FAIL**: Foot exits0, Mousepad exits137. The requested observer returns125
with `open:NotFound`; no PC or stack was captured. Only loaded and APP_RUN_BEGIN
markers appear, so this run does not locate the earlier unfinished shutdown.
No phone operation, candidate, signing, admission, claim or protected-storage
mutation occurred. Physical rows remain NOT RUN; S06/R01 FAIL remain unchanged.

## Exact comparison

Executed source `b113edde0b56c49dbde2157b37b9e77402fbf61f`, tree
`2dd962af37999424c43612b7afc65b496190ba01`, clean checkout. Publication follows
as metadata only. The prior no-unref control's kernel/runtime/Denial/engine,
diagnostic DSO, caches, flags and deadlines were verified unchanged. Changes are
the qualified stage-aware runner, launcher and helper plus the new reader module
and explicit `--app-close-after-sync` option. The112-suite active result and13-case
ARM64 API fixture are inherited by matching source bytes, not rerun this turn.

Three ARM64 helper compilations passed in6.182s,6.432s and7.637s. The underlying
QEMU command exited0 in317.227s after normal poweroff; this is process completion,
not UI acceptance. All28 harness command steps passed while the final semantic
UI check failed. Overall run390.287790s; outer service6min51.623s, peak1.8GiB,
zero swap. Full runtime bytes/metadata and input hashes remained unchanged;
all owned containers were absent after cleanup. No second full VM was run.

## Observations and limits

Mousepad PID1005 logs loaded264.712899232 and APP_RUN_BEGIN265.641001072 in
CLOCK_MONOTONIC. SHUTDOWN_BEFORE, external sync BEGIN/END, SHUTDOWN_AFTER and
run-return are absent. The probe arms for that PID, reports `open:NotFound`,
then finishes with3records, truncated=false and elapsed1318ms. The1200ms budget
is cooperatively checked around bounded operations; an operation/scheduling delay
can return later. No late capture was accepted. The error lacks the identity-read
path, so it does not establish whether the parent or application disappeared.
There is no evidence here of ptrace attachment or a render-thread instruction.

The launcher records close begin295.18 and return298.20 for timeout PID1003
using CLOCK_BOOTTIME. These are not an exact TERM-delivery timestamp and must
not be subtracted from MONOTONIC markers without a clock correlation. Timeout
records TERM then KILL. Device readiness passes in17.21s versus0.68s in the
prior control. Scheduling variation and polling overhead remain hypotheses;
this single comparison is not an overhead measurement or proof of causation.
Guest poweroff passes, while `/var` unmount fails as before.

## Next discriminating check and improvement

Do not repeat an unchanged full UI run or lengthen grace to obtain a capture.
The previous real GLib API fixture quits immediately from activate; it never
tests Unix-signal delivery through the main loop while the new waiter polls.
Use a small owned ARM64 GLib/timeout fixture for that boundary, comparing the
same application with and without the stage waiter under unchanged limits.
Reuse the existing exact signal-forwarding cases; distinguish callback entry,
shutdown entry and observer refusal. Mousepad's retained0.7.0 history source
registers SIGHUP/SIGINT/SIGTERM through g_unix_signal_add when session restore is
enabled, then activates the quit action. That source lead is not exact-package
debug attribution or proof that this run entered its callback.

Commands, inputs, outputs, durations and private log hashes are in the
[qualification record](2026-09-20-close-stage-vm-qualification.json). The prior
581 inventory rows and both acceptance contracts are preserved. This is a VM
fixture with no admission authority; no ROG5 panel/GPU/touch result is inferred.
