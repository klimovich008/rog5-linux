# First-frame deadline qualification — 2026-09-20

Host and generic ARM64 fixtures only. Phone physical results NOT RUN. No phone,
USB, signing, admission, claim, candidate, or protected-storage operation.
Prior full Denial VM remains FAIL (Foot0/Mousepad137); S06/R01 remain FAIL.
The preceding community recheck was no progress toward runtime qualification.

Starting source `9b82c20a256f37a115f4e4560bab4fde322b3425`, tree
`68b7ee192f4d875425e19fa93814b01f45afdf75`. Frozen corrected source `ffaf75ee12e5e19755b14f704023e0d7e440f02e`,
tree `196bf996bc1d41c2835acc4b0f6523424ec0a3bf`. The evidence-producing pre-fix measurements used starting
source; final tests used corrected source. No installed or signed bytes changed.

## Measured boundary

The actual capture function was exercised with 17, 303 and 559 mappings in small
native ARM64 system VMs. The latter cases load retained GTK dependencies; dense
adds 256 sparse mappings. Original captures and a second instrumented attempt are
separate observations, not equivalent samples. Instrumentation calls the actual
maps/walk/read_frame functions and reports stage wall time plus tracer-thread CPU.
Two owned four-second CPU burners create bounded contention. Each guest command
has a 25s deadline; harness 60s, 512MiB guest,1GiB/no-swap container, no network/GPU.
Read-only runtime/payload, non-root guest target, detach and owned-child cleanup.

| Fixture | vCPUs/load | Duration | Original first-frame result |
|---|---|---:|---|
| r1 | 1 idle, shared process | 11.272s | All three: 2 frames, End |
| r2 | 1 idle, fresh processes | 12.079s | All three: 2 frames, End |
| r3 | 2 idle, same binaries as r2 | 5.592s | All three: 2 frames, End |
| r4 | 2, two CPU burners | 13.509s | Sparse/dense: 0 Deadline; GTK: 2 End |
| r5 | 1, same binaries/load as r4 | 5.642s | Sparse: 2 End; GTK: 1 Deadline; dense: 0 Deadline |

r4 sparse capture wall 27.338ms versus tracer CPU 10.278ms demonstrates scheduling
contribution even with 17 mappings. The instrumented dense attempt performed no
PEEK: maps read 2.536ms, parse completion 16.658ms, total 20.284ms. r5 also misses
frames: reducing vCPUs is not a qualified workaround. All five measurement
harnesses PASS execution/cleanup; the missing-frame outcomes remain explicit.
This does not establish the phase or cause of the original full-VM miss.

## Scoped correction and regression

`tools/qemu-virtio-drm/app-close-stack.rs` now checks the original deadline after
bounded maps I/O and before parsing/allocating. Once expired it returns empty
Deadline. Maps open/read errors still propagate; already-expired malformed text
now intentionally gives Deadline instead of parser error. No expired data is
admitted. The original clock start, limits and post-PEEK check are unchanged.
The guard avoids needless stopped work; it does not make scheduling predictable.

Failing-before regression: expired malformed maps returned maps-range (exit101).
Passing-after covers expired malformed and valid large maps, unexpired malformed
validation, expiry before first read, valid mapped frame, and post-read expiry.
The existing actual-child test covers two real records, all-ones return value,
partial PEEK, detach and child survival with process_vm_readv unavailable.
Read-only independent review found no blocking issue.

Focused host wrapper: 3 suites PASS in 15.903s. Native ARM64: 9 stack tests PASS,
including real owned-child reads; build+VM 8.945s. Initial standalone
invocation omitted the required fixture environment and failed that case; it is
not confused with the successful wrapper or a product regression. A preceding
relative-path compiler setup failed before any test ran. Exact commands, image
identities, input/output hashes and cleanup records are in the qualification JSON.
Active tier: exit 0, 205.713s; counts `{'PASS': 112, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255}`.
Subchecks `{'SKIPPED': 3}`; JSON/JUnit summary retained.
No new full Denial VM, board kernel build or physical test was run.

ARM64 test binary SHA256 `be069ad5024fe6278e17a0c4a70096b7e5857e468504b8730fdbdc04fd2e5568`.
Qualification JSON SHA256 `32dad43387ab94d4fed2cc6362a9cc9f67f89ff9958080aaad454f58476c18e7`.
Private evidence: `rog5-first-frame-20260920-r1` under local state.

## Remaining question

The retained full VM PC is strongly attributed to libgobject handlers_find;
caller, reason for extended teardown and a reproducing component remain unknown.
Next use a bounded native ARM64 GTK/Mousepad close component with the retained libraries and controlled contention to distinguish a component stall from Denial-dependent teardown before another full VM. Preserve 15ms/64KiB/4frame and1200ms outer bounds; no deadline widening, GLib behavior patch, or unchanged compositor rebuild.
