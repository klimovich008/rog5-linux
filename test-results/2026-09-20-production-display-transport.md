# Production display duplex transport — 2026-09-20

**Offline host qualification only. No phone/SSH/USB operation, VM, candidate,
signing, target staging, claim or protected-storage mutation.** The previous turn
repaired worker group cleanup. This turn makes the host duplex protocol agree
with the production supervisor, preserving historical guarded entrypoints.

Start `6518b22c5572bad831b3f93b8afcca0af957dca8`, tree `be56b977249d6a333ca28b37f6e3537d945de00d`.
Frozen implementation `306fbbd08d2dde9be5fd007ec6562e349238efd4`, tree `beae94887bc7736bb272cc546427191f83a87f75`.
Current board artifacts, Linux `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` and artifact pointer
are unchanged. No kernel/DT/module/Denial/Flutter rebuild was required.

## Demonstrated mismatches and implementation

The actual historical exchange rejected a production ready message before start:
the new regression failed with `transport-ready differs` (1 expected FAIL,
0.179s). Historical transport fixture SHA256 is
`3d6f76bb421bf8f40967ac354d49e152248636b2272a1cf2653f8702e2a1a573`.
The source is retained exactly; tests extract the actual protocol functions and
constants, excluding source-loader calls, staging and SSH construction. Those
entrypoints are never imported or executed by these fixtures.

`HostContract` snapshots the six-field admitted target identity, checks the current
production release/DT and descriptor syntax, and uses pinned local sources for
the actual 14-module entry scope and component/blank validators. It does not
discover a target or grant admission. The existing owner supplies device, signing,
health, logging and recovery authority independently.

The transport now uses that contract for entry, acknowledgment and terminal
validation, accepts the 100-second supervisor, and reserves 120 seconds normally:
100 lifetime + 4 action reap + 4 cleanup + 4 cleanup reap + 1 publication + 5 drain
and 2 startup reserve. First failure closes the lease and starts an independent
18-second collection window: 3 lease + 4 action reap + 4 cleanup + 4 cleanup reap
and 1 publication + 2 drain. Two local 2-second reap windows and 1 second reserve
bring initial owner admission to 143 seconds, checked before reservation and
again before process creation. These bounds are conservative contracts, not
proof that every network or uninterruptible kernel operation finishes in time.

The old 78-second budget rejects a valid peer when a controlled host clock moves
past second 78; the repaired 120-second path passes the same case. Restoring the
old `min(existing_deadline, now+closure)` assignment discards delayed cleanup at
timeout; the new independent window retains the real peer's terminal and zero
receipt while the overall outcome stays FAIL. Virtual-clock and shortened-window
tests are not 78/120-second observations.

The local transport child remains waitable until the repaired group-stop routine
finishes; no Popen.poll/wait releases it early. Local group proof is required for
success. An injected absent proof correctly refuses a positive target terminal.
The first timeout, owner failure or interruption remains the host outcome even
if subsequent target cleanup or the complete target action reports success.

Historical staging, source pins, source-boot rejection, fixed SSH construction
and consumed-entry paths remain unchanged. The patch deliberately cannot deploy
using the old pins/context. No production admission or signed composition exists.

## Personally executed tests

`python3 -O scripts/device/test-production-display-transport.py --before`:
one expected readiness FAIL, retained separately. Ordinary transport runs evolved
from 14 PASS/3.202s to 21 PASS/5.857s and 22 PASS/6.062s as timing and ownership
coverage was added; those logs remain retained. Final focused results:

| Command (`python3 -O`) | Cases | unittest seconds | wall seconds |
| --- | ---: | ---: | ---: |
| scripts/device/test-production-display-transport.py | 23 | 6.238 | 6.346 |
| scripts/device/test-display-component.py | 10 | 2.698 | 2.826 |
| scripts/host/test-select-repository-test-tier.py | 37 | 0.729 | 0.837 |

Coverage includes readiness/intent mismatch before ACK, immutable host entry,
start failure, fragmented records, stderr/extra output, corrupt terminal/zero,
owner loss after ACK, interruption followed by positive terminal, late cleanup,
admission margin, local child ownership/group proof and exact identity snapshots.

The complete chain executes the actual host protocol, supervisor, loader,
endpoint and compiled current panel/core callback extracts. All14 insertion
children are real inert processes. Module hashes/bytes and shorter child timing,
sysfs, ownership and identity are explicit fixtures. Production HostContract pins
are checked separately. Peer cleanup/reap limits are shortened to 0.5 seconds;
production 2/4-second constants and budget arithmetic have separate assertions.
No physical scanout, darkness or acceleration is inferred.

Frozen `scripts/host/test-repository-linux.sh active`:
**122 PASS, 0 FAIL, 0 BLOCKED, 0 SKIPPED suites**,
255 NOT_SELECTED, 217.674s.
Three declared optional historical subchecks remain separate. These are local
executions, not imported GitHub CI results. Bounds: 1 GiB/no swap, two CPU quota,
256 tasks, 600 seconds and two test workers; disk-backed scratch. The frozen tier
ran once. No unchanged kernel build was repeated.

[Qualification](2026-09-20-production-display-transport-qualification.json), SHA256
`748a361abe86adccdd15286dacbc320068435147670e564e43568e8270fb689b`, contains exact inputs, per-suite commands/durations and log hashes.
Private evidence is `rog5-display-transport-20260920-r1` under the host state root.

## Remaining integration and next step

The outer historical session remains incompatible. Its entry permits three
insertions and one reprobe, runs a separate GPUCC/provider phase, and expects a
provider-result hash plus GPU-query result. The current loader already includes
GPUCC/provider checkpoints and all14 insertions; the old phase cannot be blindly
prepended. Its display reservation is135 seconds, below the new143-second entry
requirement. Its logger/session/recovery timing and source admission need a
coherent successor, preserving the original no-retry and fallback ownership.
This is source inspection, not execution of the historical session.

Next authorized step: adapt and test that existing session around the integrated
production display operation, with independent logging, health and recovery
closure. Keep the separate GPU-query/accelerated-rendering milestones explicit;
successful display initialization alone does not complete Denial. Firmware
search/root-transition assumptions, actual ARM64/network behavior and exact live
composition remain unqualified.

The smallest later physical question remains whether the exact provider/panel
path prepares and accepts zero brightness after offline composition and explicit
hardware authorization. No Ready requested. All current mobile physical rows are
NOT RUN. S06/R01 and earlier Denial VM failures remain FAIL. Rescue and accepted
server baseline remain unchanged.

Changed implementation files:

- `configs/repository-tests.json`
- `patches/display-controller/0003-production-transport.patch`
- `patches/display-controller/README.md`
- `scripts/device/display-component.py`
- `scripts/device/fixtures/display-loader/transport-before.py`
- `scripts/device/test-production-display-transport.py`
- `scripts/host/test-repository-linux.sh`

## Final metadata and preservation

- `python3 scripts/host/check-mobile-status.py`: PASS, 0.044s.
- `python3 -O scripts/host/test-mobile-status.py`: PASS, 0.086s.
- `python3 scripts/host/check-artifact-inventory.py`: PASS, 0.084s.
- `git diff --check`: PASS, 0.016s.

Eight status regressions passed. Inventory remains595 sets; large/private byte
revalidation remains NOT RUN. Thirteen preservation checks confirm unchanged
artifact pointer/inventory, headless/mobile acceptance, historical state body,
previous loader/supervisor patches and fixtures, and sealed private loader,
backend and transport hashes. The integrated owner exited successfully:319.3 MiB
peak memory, zero swap. No phone operation or protected-storage mutation occurred.

Metadata changes: `configs/project-status.json`, `docs/current-state.md`,
`docs/development-lessons.md`, this report and its qualification JSON. Ending
metadata commit/tree and the complete changed-file list are private in
`rog5-display-transport-20260920-r1/end.json` to avoid a self-hash cycle.
