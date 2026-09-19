# Bounded PC snapshot preparation — 2026-09-20

Offline only: no VM, phone, candidate, claim, signing, admission or protected-storage
operation. ASUS slot A, signed V11 fallback, accepted server/rescue and historical
S06/R01 FAIL remain unchanged. Previous turn was progress: the VM measured main
thread CPU execution during Mousepad137. It did not identify a busy loop.

Starting source `8c3d5101b827b6c6d19f86a32f89a542753f858b`, tree
`9acbb9abdbf6ba844b7b812faf924b510aa0f9b5`. Frozen implementation
`4ad368f845b5b16a669d11b028a429668edbbc0f`, tree
`9b0696fbc77bf6d4af1ab5069d3169a6cb2111be`.

Changes: `tools/qemu-virtio-drm/app-close-ptrace.rs`,
`scripts/host/test-app-close-probe.py`, `configs/repository-tests.json`.
The new component is a library, not an executable or enabled session feature.
The existing read-only proc sampler, normal VM runner, close grace and runtime
are unchanged. Explicit VM-only integration remains required before execution.

One dedicated tracer thread uses SEIZE(options0), INTERRUPT, bounded exact-PID
WNOHANG/__WALL wait, NT_PRSTATUS and DETACH. It reports only PC/SP/frame pointer/
link register and interrupt-to-detach elapsed time. A supplied identity validator
runs before attachment, while stopped and after detach. A failed validation
publishes no registers. Signal-delivery stops are detached with their original
signal; existing group stops are preserved without SIGCONT or reinjection.
All error/panic paths join the tracer thread, letting kernel exit_ptrace release
any remaining relationship. EXITKILL is prohibited. No process memory is read.

The75ms wait-poll policy is not a hard syscall or scheduling bound; a future
caller still needs an independent outer watchdog and bounded validation closure.
Numeric-PID validation cannot make attachment atomic with reuse: stopped checking
prevents attributing another task's registers but cannot prevent that attachment
race. This is suitable only for the guarded disposable VM investigation, not a
claim of race-free arbitrary-process observation or phone authorization.

Review used exact clean Linux7.1.4 source
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`: kernel/ptrace.c cleanup and INTERRUPT,
kernel/exit.c task-exit handling, kernel/signal.c preserved siginfo, and ARM64
user_pt_regs. The actual host execution is on Deck Linux6.16.12-valve24.5,
x86_64. Same-UID owned children are used without changing global ptrace policy.
Retained Mousepad0.7.0 handles external signals via a GLib main-loop callback;
that does not distinguish pre-dispatch execution from earlier quit work.
Exact package/source reconstruction remains incomplete.

Nine Rust snapshot cases and six existing sampler cases pass through two Python
wrappers in3.450s. Coverage executes real host ptrace against owned children:
snapshot/identity, TERM preservation, exactly-once handled USR1, pre-existing
SIGSTOP, deadline, failure after seize/interrupt/stop, panic and target SIGKILL.
Cleanup requires both detached state and continued CPU progress. The deliberate
panic message is expected fault injection, not an uncaught suite failure.

Two mutations fail the actual tests as required: suppressing the pending signal
(exit101; compile/test2.935234230s) and enabling EXITKILL
(exit101; compile/test0.819688469s). Review found the first cleanup assertion
could accept a zombie; the strengthened progress check rejects that mutation.
The first mutation compile attempted an output outside the wrapper's writable
TMPDIR and was refused; only the private fixture output location was corrected.

ARM64 library and test binary compile with warnings as errors in0.515566572s
and13.602469731s. The actual ARM64 register-layout test passes under qemu-user
in0.073878754s; eight real ptrace cases are deliberately filtered out there.
Actual ARM64 kernel ptrace interaction remains NOT RUN.

Library SHA-256:
`0cf370fc2c5e24f0562b1e7fd714bad9de2273497f5168d212f1ca8f4ffee769`.
Test ELF SHA-256:
`1c95ce4b79f1d95d0737870337fd30082e25153f63aa3260a7c6f38534121416`.
The qualification JSON retains commands, exact inputs/outputs and durations;
raw logs remain private under `rog5-close-pc-20260920-r1`.

Next: explicit opt-in integration with VM/UID/parent/starttime guards and the
existing output/time caps, followed by one frozen bounded VM. Preserve the
previous Mousepad137 result and distinguish diagnostic perturbation from a fix.
No unchanged VM rerun, deadline extension or runtime upgrade occurred this turn.

Frozen active tier: {'PASS': 112, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255}; duration194.032158250s. Declared optional historical subchecks: {'SKIPPED': 3}. New VM and phone execution: NOT RUN.
