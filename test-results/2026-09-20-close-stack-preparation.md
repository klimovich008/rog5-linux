# Bounded stopped-task stack preparation — 2026-09-20

Offline/owned host fixtures only; no phone, candidate, signing, admission,
claim consumption, protected-storage mutation or new VM. Physical NOT RUN.
Previous goal turn made progress by resolving and publishing the exact GLib PC
and call-site evidence. Mousepad137 and S06/R01 FAIL remain unchanged.

Starting source04c4197f59d284aa12053edb6abf517936b42ee4;
frozen source `f9bea083c268b67735c98c67c8075b5ae5822e56`, tree `391831c48bb1bb28a832531d22450d2671e91bad`.
Changed files: `tools/qemu-virtio-drm/app-close-ptrace.rs`, new
`tools/qemu-virtio-drm/app-close-stack.rs`, and
`scripts/host/test-app-close-probe.py`.

The tracing helper now exposes a fallible observer after stopped identity
validation and register capture. It publishes results only after detach and
final identity validation. Explicit error and panic tests prove the owned child
survives, detaches and continues CPU progress. The existing capture uses a unit
observer; the VM sampler does not import the new stack component.

The reader bounds maps to64KiB and paths to512 bytes, requires one readable and
writable exact `[stack]` mapping containing SP, and reads at most four16-byte
frame records. Alignment, checked pointer arithmetic, exclusive map bounds,
64KiB SP distance and increasing frame addresses prevent out-of-scope traversal.
Zero FP ends a chain. Short/error reads retain only earlier completed records;
raw PAC return addresses remain unmodified, even without an executable-map match.
Only saved FP/return addresses are read, not a general stack dump. The15ms
budget checks before and after reads are cooperative, not a hard syscall bound.
Other threads can mutate the address space: these are frame-pointer candidates,
not an atomic or complete backtrace. The outer watchdog remains mandatory.

The new stopped-observer regression fails before implementation because the API
is absent. Final focused tests:18 sampler/tracing cases plus6 stack cases
through3 Python wrappers,5.776707131s. The new host C fixture puts a known chain
on its stack and a protected second page next to readable memory; actual tracing
and process_vm_readv recover the chain and return a partial8-byte read. Pure
fixtures exercise partial failure, cycles, overflow, mapping bounds, deadlines,
maximum frame count and raw PAC values. A mutation accepting partial reads is
rejected by the regression (expected nonzero test exit).

ARM64 library/test compilation passes with warnings denied. Five pure traversal
cases and the register ABI test pass under qemu-user (0.114497324s and0.114713557s).
Actual ARM64 ptrace/process_vm_readv, new VM execution and sampler integration
are NOT RUN. Host tests do not promote these rows.

Frozen active tier: `{'PASS': 112, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255}` in193.982488907s.
Optional historical subchecks: `{'SKIPPED': 3}`.
Exact commands, per-command durations, compiled output hashes and source hashes
are in [qualification](2026-09-20-close-stack-preparation-qualification.json).

Next: explicitly gate stack capture, account for worst-case records within the
existing sampler/stream limits, and prove guarded production wiring before one
new VM. Keep one stop, original close grace, signal forwarding and identity
checks. Do not infer a GLib defect or repeat the unchanged old VM. Safe independent
phone display/touch source work remains separate from this application diagnostic.
