# Bounded stack read repair and ARM64 qualification — 2026-09-20

Host fixtures and generic ARM64 VMs only. No phone operation, host sudo,
candidate, signing, admission, claim consumption or protected-storage mutation.
Physical tests remain NOT RUN; S06/R01 FAIL remain unchanged. The accepted
server/rescue, ASUS slot A, signed fallback and historical results are retained.

Starting HEAD `415849cd49b4ac9e091ada0a735d3f337dbdbf3f`, tree
`aacc6b57778091675701029af8d10a4df48ff9d9`. The existing integration at that
source gates stack capture behind `--app-close-stack` and `--app-close-ptrace`.
The new source is `bcf3c3368f68cf4e3eab2a9acaa0adbbb6fa65cc`, tree
`74bccc6a896ab4d4616568433741d0e8da5d23e6`. Its parent `2aa81a51` records the
separate community-source follow-up; that documentation does not qualify code.

## Demonstrated preparation error and fix

The previous full VM attempt used `process_vm_readv`, but its retained kernel
configuration has CONFIG_CROSS_MEMORY_ATTACH disabled. The attempt was stopped
through the existing runner's owned cleanup after 276.226455829s. It remains
FAIL, with signal-2 interruption recorded; no stack sample or normal guest
poweroff was observed. Runtime bytes and metadata were verified unchanged.
This is a diagnostic preparation failure, not a newly observed Mousepad failure.

The reader now makes two PTRACE_PEEKDATA reads within the already-owned stop.
The pinned kernel enforces tracer ownership and uses FOLL_FORCE; the actual
ARM64 libc wrapper returns the full native word and differentiates all-ones
valid data from error using errno. A second-word failure yields a short read
that traversal refuses. Mapping, alignment, checked bounds, four-frame limit,
15ms cooperative budget, raw PAC preservation and detach/identity checks remain.
The API is explicitly restricted to 64-bit Linux. There are no tracee writes.
Other threads remain runnable, so these are frame-pointer candidates, not an
atomic or complete backtrace. Existing outer deadlines remain mandatory.

Only `tools/qemu-virtio-drm/app-close-stack.rs` and
`scripts/host/test-app-close-probe.py` changed for this correction. The actual
owned-child fixture now includes UINT64_MAX and an unmapped page boundary:
PROT_NONE alone cannot force a PEEK failure because the kernel uses FOLL_FORCE.
A test-local seccomp wrapper denies process_vm_readv with ENOSYS and verifies
that denial before launching the actual Rust tests. It changes only the owned
test process tree, not host policy. Reinstating just the old reader makes the
new regression fail with ReadFailed instead of End in 1.467633272s.

## Executed offline and API checks

- Focused suite PASS, three Python wrappers in 8.784094513s: 18 ordinary tracing/
  sampler cases, 24 stack-enabled cases and six standalone stack cases. These
  are executions across configurations, not 48 distinct test functions.
- ARM64 test and integrated-release builds PASS with warnings denied, in
  5.327101453s and 3.977230614s. These are user helpers, not a phone kernel build.
- ARM64 user emulation: five pure cases PASS (0.114384493s), one ABI case PASS
  (0.114568386s), and release guard refusal as expected (0.064428052s).
- Frozen active tier PASS: 112 selected suites, zero FAIL/BLOCKED/SKIPPED,
  255 NOT_SELECTED in 195.955345992s. Three optional historical subchecks are
  SKIPPED separately; they are not hidden as executed. Peak 338.8MiB, zero swap.
- A small guest using the retained kernel actually returned ENOSYS/38 for
  process_vm_readv. All six stack tests passed as UID1000, including real owned
  child reads, UINT64_MAX, partial reads, and detach. The guest powered off
  normally and its named container was absent after cleanup. Preparation plus
  VM took 3.103504909s; the QEMU command itself took 1.869819420s.

The small guest's original harness result remains FAIL: a literal-string check
missed ANSI-colored Rust success output. Separate reanalysis normalizes those
escapes, checks each required marker and the existing poweroff validator, and
confirms PASS from the retained bytes in 0.014064016s. No second API VM was run.
The test binary and integrated release binary are separate recorded artifacts;
a successful API fixture is not proof of application teardown.

Review found no PEEKDATA implementation blocker. Before the small guest ran,
review also caught unnamed compiler-container cleanup and a fixed VM-name
collision risk; both private harness issues were corrected using unique names
and the existing cleanup owner. Neither fix changes device authority.

Exact commands, source/build identities, durations, logs and artifact hashes are
in [qualification](2026-09-20-close-stack-peek-qualification.json). The new
metadata changes are this report/qualification, the current artifact pointer,
artifact inventory, structured project status, its generated human summary and
the existing development-lessons file. Historical inventory rows are preserved.

## Full Denial VM result

One new full run used the corrected source while retaining the kernel, runtime,
engine, graphics flags, caches,20s readiness allowance and2s close grace. It
remains FAIL in383.696946133s. Foot exits0; Mousepad exits137 after TERM/KILL.
Readiness succeeds in1.21s. Normal guest poweroff passes; initial /var unmount
fails. Named-container cleanup completes, and full runtime byte/metadata and
input-hash verification passes afterward. No unchanged retry followed.

The reader returns four unclipped frame candidates, stop=Limit. The complete
probe emits29 records in642ms with truncated=true; this is not a complete
process snapshot. Interrupt-to-detach takes26,464us. Recorded frames resolve
through exact ELF PT_LOAD segments to GTK offsets0x199010 and0x337594,
GObject g_object_unref return offset0x225d0, and the interposed g_object_unref
return offset0x1180. Call attribution uses saved LR minus4 for AArch64.

The current PC is diagnostic DSO+0xb10, the start of __errno_location@plt; live
LR is DSO+0x10c4, matching its caller inside the interposed g_object_unref.
This does not prove errno lookup is blocked. Two nested unref wrappers are
consistent with ordinary object finalization; they do not prove recursion is
unbounded. The main thread gains19 user CPU ticks over0.402601024s. No allocator
lock, deadlock, infinite loop or upstream GTK defect is established.

Crucially, this run's only lifecycle markers are loaded and APP_RUN_BEGIN. There
is no SHUTDOWN_BEFORE/AFTER, APP_RUN_END or APP_UNREF_BEGIN. Do not inherit the
previous run's later application-unref boundary or combine PCs from different
runs into a single stack. The new result narrows this observation to GTK object
lifecycle work while the recorded application-run interval remains open.

Next: prepare and qualify a diagnostic DSO variant without g_object_unref
interposition, preserving run/shutdown/settings markers. Then one bounded
comparison can test sensitivity to the per-unref probe, with the same runtime
and close grace; timing variability limits any single positive comparison. Keep the existing close acceptance deadline unchanged;
a diagnostic sample is insufficient justification for a GTK/GLib patch. This
VM investigation does not block safe independent phone display/touch source
work, and provides no phone GPU, OLED, input, charging or suspend evidence.

## Source attribution, with limits

GTK3.24.52 tag peels to commit
`6a0b360d473f7c546314738c0c8dd9829eb9d3c2`. Ordered operations and member offsets
strongly match frame3 to [gtk_style_context_finalize](https://github.com/GNOME/gtk/blob/6a0b360d473f7c546314738c0c8dd9829eb9d3c2/gtk/gtkstylecontext.c#L369),
unrefing its CSS node, and frame0 to [gtk_css_widget_node_finalize](https://github.com/GNOME/gtk/blob/6a0b360d473f7c546314738c0c8dd9829eb9d3c2/gtk/gtkcsswidgetnode.c#L33),
unrefing last_updated_style before the parent finalizer. The intervening exact
GObject call loads the class finalize slot. These names are inferences, not
matching package debug symbols. Nearest exported symbols in objdump output
are not used as function names. Exact source-file hashes and the private review
identity are included in qualification; no upstream implementation was imported.

The API guest's UID1000 follows from its successful hashed setpriv invocation,
not a separately printed getuid measurement. Its ten other ptrace tests were
filtered out; error/panic coverage comes from host tests, not that guest.
