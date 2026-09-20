# Production kernel logger — 2026-09-20

**Offline host qualification only. No phone, SSH, USB, VM, kernel-log device,
staging, candidate, signing, admission, claim or protected-storage operation.**
Previous turn was progress: enclosing display-session integration. This turn
binds its actual kernel logger and qualifies resource/process closure.

Start `d0790170a1b65276d5a9e13a04254e3c67f07831`, tree `03218a28467c488b7388e9b921ebd6d6a4985e70`.
Frozen implementation `5001f723e76b585c5290ac241bc6693875c1504c`, tree `69f8dc905f092204406634889384a0a7e772f2cf`.
Linux remains `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. Artifact pointer SHA256 remains
`5d168da495a9af5af842f24ad67631c58967f0b5c9bc8a148fab17c507ebd279`. No kernel/DT/module/Denial/Flutter rebuild.
Source qualification does not alter signed candidate or installed phone bytes.

## Demonstrated corrections

Three regressions fail against exact historical kernel-log.py SHA256
`b690ae15bfced9c5cc3c9ab905209dc12dccb909678c31975fe6a32282a18d14`:

- Interrupting pidfd acquisition after Popen leaves the old child/resources
  open. The successor cleans up under BaseException and reraises the original
  startup failure; cleanup errors cannot erase it.
- A stdout fsync failure skips remaining old cleanup and leaves a released pidfd
  number in the object. The successor detaches FD ownership before closing and
  cleans streams independently. Its retry cannot close that numeric FD again.
  Actual unrelated-FD corruption is not claimed; the stale ownership is the
  precise source-level consequence of the reproduced cleanup failure.
- An exited leader can leave a real same-group descendant alive. The successor
  holds the leader with WNOWAIT until the existing supervisor stop function
  proves reap and group absence. The fixture provides PID1-style orphan reaping
  explicitly and cleans every child even when the historical control fails.

The stop helper is reused, not reimplemented. A reaped leader is never signaled
again. Ordinary group closure does not contain a descendant that escapes its
session/group. Output is drained again after stopping the child; trailing records,
stderr, incomplete logs and publication failures cannot produce PASS.

## Production identity and session binding

HostContract exposes the exact endpoint source bytes already hashed and executed
by its dependency reader; consumers do not reopen that source path. The logger
checks that source pin, snapshots all six identity fields and embeds the same
bytes in its bounded script. Remote code calls only Endpoint.identity and opens
kmsg read-only. It checks boot, release, a unique bundle token and descriptor
bytes. Owner and board hash remain admitted bindings, not independently observed
physical identity. No brightness or framebuffer function is called.

The script is bounded to32 KiB. Nonblocking stdin writes share the existing
eight-second readiness deadline, so a peer that never reads cannot hang input
transfer. Four-MiB output,64-KiB frame and128 kernel-record bounds remain; the
reader also checks cumulative bytes. Short remote frame writes fail explicitly.
The session passes the exact contract/owner and actual transport stop callback,
and requires logger group-absence proof for PASS and its healthy-cleanup claim.

Historical SSH construction and source guard ASTs remain unchanged. This still
cannot deploy through the historical staging/admission closure. No new live
composition or authority has been issued.

## Personally executed tests

| Command (`python3 -O`) | Cases | Wall seconds |
| --- | ---: | ---: |
| `scripts/device/test-production-kernel-log.py` | 25 | 3.272 |
| `scripts/device/test-production-display-session.py` | 25 | 4.173 |
| `scripts/device/test-display-component.py` | 10 | 2.770 |
| `scripts/host/test-select-repository-test-tier.py` | 37 | 0.766 |

All97 focused cases pass. The three exact historical controls fail as expected;
logs and full command are retained. The25 logger cases include normal terminal,
startup interruption, fsync failure, live descendant, identity mismatch, missing
terminal, stderr, trailing/partial frames, cancellation, a large record burst,
duration bounds, source integrity, absent group proof, result-write failure and
input backpressure/deadline. The generated remote program executes its real
identity and main-loop code against explicit proc/descriptor/kmsg/clock fixtures,
covering duplicate bundle, descriptor change before open and after heartbeat,
and short-frame failure. It never opens the host or phone kmsg.

The25 session cases include the actual logger plus actual duplex exchange, and
refusal when its group proof is absent. Other assembled component tests retain
the actual driver/core callback extracts. Local children/pipes are real;
SSH, kernel logs, physical guards, source admission and hardware effects remain
fixtures. Short peers advertise synthetic elapsed time for300-second receipts;
this proves protocol handling, not five minutes of physical observation.

Frozen `scripts/host/test-repository-linux.sh active` ran once:
**124 PASS,0 FAIL,0 BLOCKED,0 SKIPPED suites**;
255 NOT_SELECTED; 223.118 seconds.
Declared optional historical subchecks remain visible separately. These are
personally executed local checks, not imported GitHub CI. Owner limits:1 GiB,
no swap,two CPU quota,256 tasks,600 seconds,two workers,disk-backed scratch.

[Qualification](2026-09-20-production-kernel-logger-qualification.json), SHA256
`c7cccc5809d2366833bf6f151fd9db3add753e1581f089019af58330496b2311`, records exact commands, per-suite times and source/log hashes.
Private evidence is `rog5-display-logger-20260920-r1` under host state.

## Remaining and next step

Next: qualify the existing full-health checker against production identity and
retained trial-state semantics, then complete exact target staging/source
admission integration. Firmware search/root-transition lifetime remains open.
Those offline tasks need no candidate generation or hardware operation.

Only after that composition is qualified and physical operations are authorized,
the smallest hardware question is whether the exact provider/panel path prepares
and accepts a zero command. Scanout, calibrated touch, GPU rendering and native
Denial acceptance remain separate. Physical tests remain **NOT RUN**; S06/R01 and
prior Denial VM failures remain **FAIL**. No Ready requested. The full phone goal
remains active and incomplete.

Changed implementation files:

- `configs/repository-tests.json`
- `patches/display-controller/0004-production-session.patch`
- `patches/display-controller/0005-production-kernel-log.patch`
- `patches/display-controller/README.md`
- `scripts/device/display-component.py`
- `scripts/device/fixtures/display-loader/kernel-log-before.py`
- `scripts/device/test-production-display-session.py`
- `scripts/device/test-production-kernel-log.py`
- `scripts/host/test-repository-linux.sh`

## Metadata and preservation

- `python3 scripts/host/check-mobile-status.py`: PASS, 0.043 seconds.
- `python3 -O scripts/host/test-mobile-status.py`: PASS, 0.086 seconds.
- `python3 scripts/host/check-artifact-inventory.py`: PASS, 0.083 seconds.
- `git diff --check`: PASS, 0.013 seconds.

Eight status regressions pass. Inventory remains595 sets; large/private byte
reverification is NOT RUN. Sixteen preservation checks confirm unchanged
artifact pointer/inventory, headless/mobile acceptance, historical state body,
previous untouched controller patches/fixtures and sealed private
loader/backend/transport/session/logger bytes. The integrated owner exited
successfully with305.3 MiB peak memory and zero swap.

Metadata files: `configs/project-status.json`, `docs/current-state.md`,
`docs/development-lessons.md`, this report and its qualification JSON.
Ending commit/tree and every changed-file hash are retained in private
`rog5-display-logger-20260920-r1/end.json` to avoid a self-hash cycle.
No phone operation or protected-storage mutation occurred.
