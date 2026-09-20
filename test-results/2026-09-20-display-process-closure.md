# Display worker process closure — 2026-09-20

**Offline host qualification only. No phone or VM operation, candidate, signing,
claim creation/consumption, target staging or protected-storage mutation.**
The previous goal turn was progress: production endpoint and supervised assembly.
This turn repairs its demonstrated same-group child cleanup defect, retaining
the sealed historical backend and all one-use barriers.

Starting commit `c3b77fb0b6bbd7c2ca6cf2562ba91af0ed528145`, tree `08ac306e0ddf98106e99924b5681be789e7a0baf`.
Frozen implementation `fc15d61e0ad5e09e68c10e0a89f09613fdd8d687`, tree `9fc8f132ad62ef8813ff33629e66508a217e640c`.
No kernel/DT/module/Denial/Flutter rebuild. Current board artifacts, Linux
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` and artifact pointer are unchanged.

## Demonstrated failure and repair

The prior stop routine reaped its worker before checking the process group. A
same-group descendant could remain alive, while callers cleared their PID and
therefore omitted forced cleanup. The real inert-process regression reproduced
this. A second regression showed that a repeated stop after reaping attempted
SIGKILL using released numeric identities. Signals in that second control were
mocked; no unrelated host process was signaled.

The corrected routine establishes direct-child ownership with waitid/WNOWAIT
before every signaling attempt, including retries. It retains the child until
group signaling completes. Forced stop also targets the direct child in case it
has not called setsid yet. When the leader becomes waitable it signals the group
again before reaping, closing a setsid/fork race around the first forced signal.
After reaping, all remaining group operations are signal-zero observations.
ECHILD refuses signals and reports unresolved closure; lost exit status never
becomes inferred success. All waits preserve the existing REAP bound.

The [Linux wait manual](https://man7.org/linux/man-pages/man2/waitpid.2.html)
documents WNOWAIT's retained waitable state and ECHILD. The repo's host test runner
already uses this ownership pattern. The new regression additionally checks
ownership at the exact group-signal call, rather than trusting source markers.

Review identified the initial force/setsid race in the first repair. Its added
test failed before the final-at-exit group signal: the first killpg call returns
controlled ESRCH, the actual directly killed leader exits, and its real child
survives without the second group signal. The final repair passes. This is a
controlled syscall-boundary regression, not a naturally timed race observation.

The actual production loader's Popen preserves the worker group; the pinned
module-once C helper neither forks nor changes sessions/groups. Tests retain
real workers and descendants. A fixture-only subreaper deterministically adopts
and reaps orphans in place of PID1, using real waitpid/group lookup. Production
still requires init to reap zombies inside the existing observation bound.
Fixture failure cleanup closes the anchored leader before its adopted child.

## Personally executed tests

Commands below use `python3 -O scripts/device/test-production-display-supervisor.py`:

| Selection / phase | Result | unittest seconds |
| --- | --- | ---: |
| `ProcessClosure`, prior implementation | 1 PASS, 2 expected FAIL | 0.408 |
| `ProcessClosure`, initial repair | 3 PASS | 0.076 |
| Complete suite, extended coverage | 30 PASS | 3.261 |
| `ProcessClosure.test_group_appearing_after_initial_force_signal_is_closed`, before final signal | 1 expected FAIL | 0.376 |
| Complete final suite | 31 PASS | 3.303 |

Final supervisor wall time was 3.435s. Coverage includes a normal exited leader
with a live child, a live leader and child, pre-setsid termination, a group that
appears after the first signal, invalid/unowned/reaped PIDs, interruption before
and after reap, normal timeout followed by forced cleanup, and group-observation
timeout remaining a failure. Existing durable-entry/ACK, one-use, lease, action
error and independent cleanup regressions also pass.

`python3 -O scripts/device/test-display-component.py`: 10 PASS, 3.016s unittest /
3.153s wall. This retains the real assembled supervisor/loader/endpoint test with
14 inert insertion children and actual compiled panel/core callback extracts.
All module, sysfs, identity and physical effects remain explicit fixtures.

Frozen `scripts/host/test-repository-linux.sh active`:
**121 PASS, 0 FAIL, 0 BLOCKED, 0 SKIPPED suites**,
255 NOT_SELECTED; 229.453s.
Three declared optional historical subchecks remain separately skipped. This is
personally executed local evidence, not a new GitHub CI result. Resource bounds:
1 GiB/no swap, two CPU quota, 256 tasks, 600 seconds, two test workers. Disk-backed
scratch; 219 GiB free observed before work. The frozen suite ran once.

[Qualification](2026-09-20-display-process-closure-qualification.json), SHA256
`7ec7e3c7f204b0c6c1d815dd21332f8c2a3495421bde8714ec2047c6465a96ed`, records per-suite commands/times, source identities and log hashes.
Private evidence is in `rog5-display-process-closure-20260920-r1`. Intentional
before-fix failures and the intermediate race failure are preserved.

## Remaining boundaries

Same-group userspace cleanup is covered; arbitrary setsid escape and
uninterruptible kernel tasks are not. A group that fails to disappear still
produces failure. Killing userspace does not reverse completed module actions.
The owner is single-threaded with no competing SIGCHLD reaper; the future exact
composition must preserve that assumption. These tests are host-native, not an
ARM64 supervisor execution or physical recovery test.

The draft production backend is still deliberately undeployable using historical
context/pins. Outer transport/admission must be qualified for the 100-second
supervisor and 14-insertion scope; the old 60/78-second contract remains too short.
Firmware root-transition assumptions also remain unqualified. A read-only trace
of historical transport.py confirms that exchange rejects a 100-second ready
message before start. It calls the removed B.intent, validates the historical
success status/three-field target identity and old component validator signature.
Its failure path uses min(existing deadline, now+14), so hitting the original
normal deadline adds no cleanup-collection time. Session display_result also
expects the historical provider-result handoff; current integrated checkpoints
have a different shape. These findings are source counterexamples, not runtime
executions. Private transport-source-audit.json pins the inspected sources.
Next authorized work is an actual offline duplex regression with an inert peer,
then adaptation of timing, entry and result contracts together while preserving
all consumed-entry and recovery protections.

The smallest later hardware question is whether the exact provider/panel path
prepares and accepts zero brightness after those offline prerequisites and
explicit hardware authorization. No Ready requested. Physical rows remain NOT
RUN; S06/R01 and historical Denial VM failures remain FAIL. Signed rescue/fallback
and accepted server baseline are unchanged.

Changed implementation files:

- `patches/display-controller/0002-production-supervisor.patch`
- `patches/display-controller/README.md`
- `scripts/device/test-production-display-supervisor.py`

## Final metadata and preservation

- `python3 scripts/host/check-mobile-status.py`: PASS, 0.050s.
- `python3 -O scripts/host/test-mobile-status.py`: PASS, 0.098s.
- `python3 scripts/host/check-artifact-inventory.py`: PASS, 0.091s.
- `git diff --check`: PASS, 0.071s.

Eight status regressions passed. Inventory remains 595 sets; large/private byte
revalidation remains NOT RUN. Eleven preservation checks confirm the unchanged
artifact pointer/inventory, headless/mobile acceptance, historical state body,
original loader patch/fixtures and sealed private loader/backend hashes.
The integrated service exited successfully, with peak memory 320.2 MiB and zero
swap. No device coordinator, phone session, candidate or claim was started.

Metadata changes: `configs/project-status.json`, `docs/current-state.md`,
`docs/development-lessons.md`, this report and its qualification JSON. The ending
metadata commit/tree and complete changed-file list are retained privately in
`rog5-display-process-closure-20260920-r1/end.json`, avoiding a self-hash cycle.
