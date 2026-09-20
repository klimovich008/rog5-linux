# Mousepad close control without object-unref interception — 2026-09-20

Host fixtures and a generic ARM64 VM only. No phone access, host sudo, signing,
candidate, admission, claim consumption or protected-storage mutation. Physical
qualification remains NOT RUN; S06/R01 FAIL and accepted rescue/server remain.

Starting source `af46e35c826c0cccfb7eb1b1075eb3791dd7e1ed`, tree
`13645015fd31892f6dd6674f7da15bb73a82c16e`. Frozen implementation
`b9da8f712e6c14344cc2988e5719862c12124000`, tree
`fb650b3c96be14b7dadd6bde8f93436e20539345`. Evidence metadata is recorded
separately afterward. The community recheck found unchanged upstream refs and
no additional qualification; this turn resumes the pending executable control.

## Question and implementation

The previous run sampled GTK finalization through the diagnostic DSO's
`g_object_unref` wrapper. That was insufficient to establish a GTK defect or
instrumentation overhead. The new compile-time `ROG5_NO_UNREF_PROBE` control
omits the exported symbol and its resolver/state entirely. It retains actual
application run/shutdown/settings markers, errno handling, secure bounded logs,
and child-exec environment cleanup. APP_UNREF markers are DISABLED in this
variant, not missing proof of an attempted observation.

Changed implementation files:

- `tools/qemu-virtio-drm/settings-sync-diagnostic.c`: explicit control mode.
- `scripts/host/test-settings-sync-diagnostic.py`: actual compiled-library
  symbol/forwarding, marker order, errno, blocked-child and cleanup tests.
- `configs/repository-tests.json`: declare the new test's `nm` prerequisite.

The new symbol-absence regression fails against the old source: the old library
still exports `g_object_unref`. The retained unittest log reports one failure
in0.389s; the surrounding historical shell ended with successful log printing,
so its overall exit code is not presented as the failing unittest exit code.
Final focused runs each pass19 tests, in0.515395274s normally and0.515663497s
with Python `-O` (including process startup). `git diff --check` passes.

## ARM64 and integrated qualification

The normal diagnostic rebuild is byte-identical to the previous artifact:
SHA256 `7a3cac369e1bd0d35b3af53b4b6c91ecbd6d199efd669fddeb7a871eb2edef38`,
71784bytes. The control is SHA256
`fcf35e0285b79c14223bb89737939d86b7c0940a18e30fd303e374739b113e5f`,
71136bytes. No default-mode behavior change is inferred from source alone;
actual binary equality was checked. Builds use the retained ARM64 compiler
container, warnings as errors,256MiB/no-swap,one CPU,network disabled and40s caps.
Default/control/fixture compile commands take0.566864881s/0.466871258s/0.567018443s.

A real ARM64 GLib application subclass runs under user emulation in isolated
namespaces against the exact retained libraries. Both default and control
pass application finalization exactly once and expected lifecycle/DSO-fini
marker ordering. Runs take0.214717216s and0.164582024s. These tiny runs qualify
the API, not GTK/Denial closure or performance. Their duration difference is not
an interposer-overhead benchmark. Fixture source, binary, commands and logs are
retained with hashes. No new API kernel guest was needed: the stack-reader
sources are identical to the previously qualified exact-kernel fixture.

Frozen active tier:112PASS,0FAIL/BLOCKED/SKIPPED,255NOT_SELECTED in198.360103721s.
Three optional historical subchecks remain separately SKIPPED. Service peak
348.8MiB,zero swap,two workers. A read-only review found no actionable issue in
the control, actual DSO exports, or the exact-input comparison wrapper.

## Bounded VM comparison

Only the explicit diagnostic DSO differs from the previous full VM's execution
inputs. Output directory changes for evidence isolation. The control retains
the kernel, runtime, engine, caches, MOPS policy, single TCG thread,20s readiness,
225s PAM budget,2s application-close acceptance, and bounded single stack stop.
The old source identity and all unchanged inputs are checked before execution;
full runtime bytes/metadata and current input identities are checked afterward.
No source edit is made while the frozen VM is running.

## Observed outcome and limits

The single full control VM remains **FAIL** in384.249973216s: Foot0, Mousepad137,
with the original incomplete-UI observation error. Readiness passes in0.68s.
Normal guest poweroff passes the existing checker; initial `/var` unmount still
fails. All owned containers are absent, and full runtime bytes/metadata and
current input hashes verify unchanged. Service peak1.6GiB,zero swap. No retry.

Same-PID994 CLOCK_MONOTONIC records reach SHUTDOWN_BEFORE294.215183136,
external settings-sync BEGIN294.223343184 and END294.223536800 (0.193616ms).
No SHUTDOWN_AFTER, APP_RUN_END, or DSO_FINI follows. This is an unfinished
observed shutdown interval, not proof of a stationary deadlock or failed sync.
It does not cover GLib's internally bound later settings-sync invocation.
APP_UNREF markers are intentionally disabled and are not scored as missing.

The sampled PC and LR both map to exact GObject ELF offset0x33340, a `cbz w0`
following an indirect call. No exported function extent covers it; objdump's
nearest-symbol label is not attribution. Stack collection returns zero
candidates, stop=Deadline. Interrupt-to-detach32,665us includes the tracer's
bounded work and scheduling; it is not a pure-read latency measurement. The
sampler emits40 records in1015ms with truncated=true and invalidated=false.

Crucially, sample-end293.399750320 is0.815432816s before SHUTDOWN_BEFORE in
the same monotonic clock domain. The process subsequently progresses into
shutdown. This PC cannot identify the later unfinished stage, and no stack
frame was captured. Earlier runs' GTK frame candidates and application-unref
boundaries must not be merged into this run.

Removing per-object interception alone was insufficient to meet acceptance.
The single comparison cannot quantify its cost or exclude effects of remaining
lifecycle hooks, scheduling, GTK cleanup, or the observer. It justifies keeping
this simpler control available; it does not justify patching GTK or raising the
close grace. Earlier passing/failed observations remain historical evidence.

The next smallest useful experiment is one stage-triggered observation after
external-sync END, using the existing bounded tracer rather than another early
snapshot. Pre-arm the marker waiter asynchronously before sending TERM; synchronous
waiting would prevent the shutdown it waits for. Require ordered same-PID
SHUTDOWN_BEFORE/BEGIN/END, refuse if shutdown-after/run-return/exit already
arrived, and never extend kill grace for missing or late markers. The existing
probe starts before TERM, and this run has no exact TERM timestamp; the sample
is not a time-since-TERM measurement. First test trigger ordering, absent markers,
wrong identity, child exit and cleanup offline. Preserve all existing time, output, ownership and
signal protections. No second full VM was run this turn. Independent phone
kernel/display/touch work remains separate from this VM application issue.

Exact commands, source and generated artifact hashes, test/build durations,
review scope, raw-log identities and retained results are in the matching
[qualification](2026-09-20-no-unref-control-qualification.json). Publication
adds this report/qualification, one fixture inventory row and current pointer,
structured status/generated current-state summary, and a development lesson.
No prior inventory row or acceptance contract is rewritten.
