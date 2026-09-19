# Device readiness diagnostics — 2026-09-19

**Offline diagnostics pass; the controlled VM fails at user-service startup.**
The six-device wait passed on this run. The previous wait failure remains
unexplained. No phone operations or new candidate, signing, admission, claims,
protected-storage mutations or persistent installation occurred.

Starting source `b400791f84673411aae4dfcfe51edd10b807535a`, tree
`ef72ae5386f30ab32a9c709d4a648dae9e8df040`; implementation `b438b9005d96de42f8c432a5086118681fd93641`.
Frozen qualification source `4beee9a27b2136c01a7aab400e97d3d9a29c07b5`, tree `d6385d69a38726f66320942eedcc1e8e80b89f5b`.
Production changes: `tools/qemu-virtio-drm/logind-session.sh`,
`scripts/host/test-qemu-logind-runner.py`, `configs/repository-tests.json`.
Evidence-producing source is distinct from this later publication commit.

## Behavior and host regressions

The helper runs exactly one `udevadm wait --timeout=8 --initialized=yes` for the
same mode-specific devices. It preserves the wait result, brackets it with
/proc/uptime samples, captures explicit debug output, drains excess beyond a
16KiB publication cap, and encodes output so it cannot inject serial markers.
Only failure triggers a separately bounded three-second device/property/journal
snapshot. Failure of that snapshot never replaces the primary wait result.
Failure to retain diagnostics after a successful wait refuses qualification.
Later port identity, permissions, seat, PAM and cleanup guards are unchanged.

Four new regressions fail against the former helper (0.125s). Final checks:
13 focused cases PASS in 7.932s; nine diagnostic cases under Python -O PASS
in 4.625s; all 107 runner cases PASS in 23.067s. These include oversize drain,
exact 16384/16385-byte boundary, partial snapshot timeout, failed queries,
capture/encoder failures, primary-status preservation, success without another
query, and whole-process-group interruption with no retained waiter/scratch.
Single-PID signal forwarding is not claimed: Bash may defer traps while waiting
on a foreground pipeline. Shell syntax and whitespace passed.

The first frozen active tier failed its 20s runner deadline after 33.200s:
20 PASS,2 FAIL,87 BLOCKED,0 SKIPPED,255 NOT_SELECTED. This result is retained.
The test manifest now allows 30s for the measured expanded host suite and names
its additional tools; the 37 selector checks pass. No guest deadline changed.
The new frozen active tier passed 109 suites in 180.943s: 0 FAIL,0 BLOCKED,
0 SKIPPED,255 NOT_SELECTED. Three declared optional historical subchecks remain
SKIPPED (charging archive, trial-state ARM replay, rail-reader ARM binary).
These are personally executed local checks, not imported CI results.

## Actual ARM64 VM result

The wait began at guest boottime 161.09 and returned 0 at 164.91 (3.82s).
All 152 captured bytes decoded completely; the message describes an ignored
network-namespace lookup error. It is nonfatal in this run and is not proven to
explain the earlier failure. No after-failure snapshot ran because wait succeeded.
The actual ARM64 capture/encoding path ran; failure branches remain host fixtures.

PAM opened the mobile user session. Denial ran and its terminal counters record
four raster frames, four output page flips and six delivered vsyncs. These are
VM observations, not a qualified interactive session or phone acceleration proof.
The user-service start returned 124 under its unchanged 25s bound; clock samples
bracket it at 226.931979360 and255.117533280. The line-buffered 3s state query also
returned 124 with no properties. The journal records accessibility and document
portal startup, then GTK/main portal activation late in startup. Its coarse
wall timestamps do not establish exact readiness against the cutoff.

No applications mapped; app-release observation, text entry and final rendering
qualification were NOT RUN. The host reported application transport closed
before approved teardown. QEMU's container command ended -9 after 276.478s;
the harness took 318.417s and wrapper 318.484s. Guest Power down was recorded,
with a retained /var unmount failure. No RCU stall report was recorded.
Compositor logs also retain inactive-libseat/atomic-restore-skipped teardown;
normal poweroff and observed frames do not make cleanup/session PASS.

Only the diagnostics script changed among 38 VM inputs; 37 match the previous
readiness run. Same kernel, Denial/Flutter, payload, release probe, two guest
CPUs, 1 GiB guest memory, 2 GiB/no-swap host cap, 2 CPU quota, network disabled,
read-only runtime and single-TCG policy. Runtime bytes/mapped metadata and all
input hashes passed post-run verification. The owned container is absent.
No unchanged VM retry was performed.

[Qualification JSON](2026-09-19-device-readiness-diagnostics-qualification.json) retains exact commands,
source identities, durations, counts, raw-evidence hashes and the one-use VM
recipe. Private logs: `rog5-device-diagnostics-20260919-r1` under local state.

## Next step and efficiency

Device diagnostics are qualified; this VM passed the six-device wait and opened PAM, but the 25-second user-service start and three-second state query returned 124. Denial recorded four raster frames/four page flips; app mapping, release and text entry were NOT RUN. Correlate individual portal lifecycle events with the CLOCK_MONOTONIC start bracket using the existing bounded journal capture, then prepare one discriminating control; do not increase service/VM deadlines or drop required services. The earlier device-wait failure remains unexplained. Preserve local modifier/work-ID/caret fixes when reviewing upstream v0.4.3. S06/R01 remain FAIL; phone physical NOT RUN and no phone authority.

The preceding turn was progress: it verified upstream fixes and reusable kernel
references. This turn implemented and qualified a missing diagnostic boundary,
then retained a single controlled VM failure with new stage-specific evidence.
No kernel, Denial or Flutter rebuild was needed. Source review was bounded and
read-only; the next service observation should reuse the existing journal path.

Device diagnostics (2026-09-19): preserve the producer status while capping and draining debug output, and label later snapshots separately. This VM passed the same initialized-device wait; instrumentation and scheduling changed timing, so this does not explain the preceding failure. An aborted qualification can still contain useful compositor counters: inspect retained logs before calling rendering unexecuted. The live service query timed out with no properties despite line buffering; use already captured individual service journal events with monotonic timestamps to distinguish late readiness from a stuck start transaction. Bound new fault-injection tests using measured runtime: 107 runner cases took 23.067s, exceeding the former20s host-test limit. Raising only that test limit to30s allowed the active tier to pass; production deadlines remain unchanged.
