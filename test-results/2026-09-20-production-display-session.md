# Production display session integration — 2026-09-20

**Offline host qualification only. No phone/SSH/USB, VM, target staging,
signing, candidate, admission, claim or protected-storage operation.**
The preceding community recheck found unchanged upstream refs and no new
implementation to adopt; it did not advance the hardware goal. This turn
completes the enclosing session adaptation and executable host regressions.

Start `73bc8f71bd9dbd3f0f612dc6d29446a8f88616bf`, tree `0efb6fed0a0cbac8ad28050b66d042dd6d5cfa42`.
Frozen implementation `a9a8b30f6362b4abae6d00c1b80e598b13578837`, tree `cd8d2ddeffe6a0848c4750f4703bb5e943a2dec7`.
Linux remains `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. The board artifact pointer is unchanged
at SHA256 `5d168da495a9af5af842f24ad67631c58967f0b5c9bc8a148fab17c507ebd279`. No kernel, DT, module,
Denial or Flutter build was repeated. This source commit is not installed bytes.

## Confirmed and fixed

- Historical `Owner.base()` checked expiry without retaining the fallback
  reserve on every call. A delayed entry with 1,850 seconds left incorrectly
  permits a 100-second operation despite the required 1,800-second fallback
  allowance. The fix reserves fallback time continuously, in addition to the
  existing 500-second session cap and initial 2,300-second admission.
- The old session separately stages/executes a GPUCC provider before a display
  loader that now owns that provider and all 14 modules. The successor performs
  one integrated dispatch, binds its entry to the six-field identity and exact
  module intent, revalidates before dispatch, and permits no query/reprobe/retry.
- KeyboardInterrupt after logger start previously escaped without a failed
  terminal. The successor records interruption as failure and closes its logger;
  successful health or cleanup cannot overwrite the failed action.
- A failed write of `health-recovery-error.json` previously escaped `finally`
  before recovery. The successor retains the original error and secondary
  diagnostic failure, then invokes the existing recovery owner. Failure to write
  the final result still raises; no persisted result is invented.
- Health collected before a logger's full-lifetime close can be stale afterward.
  The successor collects final health after logger closure. Restoring only the
  historical ordering in the otherwise working successor produces a snapshot
  299.81 seconds old and fails the semantic freshness check.

Four tests against the exact historical session fail for the first four defects
(0.173 seconds, four expected FAIL, no test errors). Fixture SHA256:
`2a2316564977a2839a31f11fb0435859857b6567f38fc5f0752ca27b5f63fa8c`.
The stale-health control is a separate mutation, not a claimed successful
execution of the incompatible historical provider/display flow.

`healthy_target_with_cleanup` now also requires logger-child closure. Display
success alone cannot cover an uncertain logger. The existing recovery callback
must establish selection restoration before returning recovery PASS. No hardware
result is upgraded by either field.

## Personally executed checks

| Command (`python3 -O`) | Cases | Wall seconds |
| --- | ---: | ---: |
| `scripts/device/test-production-display-session.py` | 23 | 3.572 |
| `scripts/device/test-production-display-transport.py` | 23 | 6.428 |
| `scripts/host/test-select-repository-test-tier.py` | 37 | 0.766 |

The 23 session cases exercise admission, boot/owner/descriptor/DT mismatch,
prior recovery, missing physical guards/capture, reserve exhaustion, entry
immutability, contract mutation, interruption, action/transport/logger failure,
post-close health loss, fallback failure and diagnostic disk-full behavior.
The source admission, health, dependency-loader and recovery functions retain their
historical ASTs where unchanged. The actual matched duplex peer receives the
session entry digest instead of a hardcoded fixture digest.

One assembled case executes session → duplex → supervisor → production loader
→ endpoint, including compiled panel/core callback extracts and 14 inert
insertion children. The logger also owns a real inert child, but its 300-second
lifetime is virtual. Health, credentials, source-lock admission, target staging,
identity/sysfs/module effects and logger data are fixtures. Historical imports,
SSH constructors and phone operations never execute. This does not qualify
actual network behavior, kernel logs, regulator state or optical darkness.

Initial fixture runs failed because the substituted evidence writer did not
return the session's expected digest, and because the peer used a hardcoded
monitor digest. Both fixture contracts were corrected; draft logs remain.
A mistyped selector-test filename failed before execution; the actual selector
suite above was subsequently executed. These setup errors are not phone faults.
The independent read-only review identified the diagnostic-write recovery gap;
its regression failed on the draft and passes after the fix.

Frozen `scripts/host/test-repository-linux.sh active` ran once:
**123 PASS, 0 FAIL, 0 BLOCKED, 0 SKIPPED** suites;
255 NOT_SELECTED; 220.314 seconds.
Declared optional historical subchecks remain separately visible in JSON.
These are personally executed local checks, not imported GitHub CI results.
The owner had 1 GiB memory/no swap, two CPU quota, 256 tasks, 600 seconds,
two test workers and disk-backed scratch.

[Qualification](2026-09-20-production-display-session-qualification.json), SHA256
`8909ca6ebf81b4bd52219c74df433c0397849d56b1ac06218f1485afaea4400b`, records exact commands, per-suite durations, source/input hashes
and retained logs. Private evidence: `rog5-display-session-20260920-r1` under
host state. Test-generated temporary peers were cleaned up.

## Remaining integration and qualification

The old pinned logger, full-health validator, target staging and source admission
closure remain unchanged and incompatible with the production cohort. This is
an intentionally non-deployable source patch, not a live successor composition.
Next authorized work is to bind and test those existing components to the
production identity and current firmware/module closure, preserving original
one-use ownership. Firmware search/root-transition lifetime remains unresolved.
No new claim or candidate is needed for that offline work.

The next physical question, only after offline composition and explicit hardware
authorization, is whether the exact provider/panel path prepares and accepts a
zero command. Scanout, touch, GPU rendering and Denial remain separate required
milestones; a successful session fixture does not complete the phone.
Physical tests remain **NOT RUN**. S06/R01 and earlier Denial VM failures remain
**FAIL**. ASUS rescue, signed fallback, accepted server and sealed evidence are
unchanged. No Ready was requested.

Changed implementation files:

- `configs/repository-tests.json`
- `patches/display-controller/0004-production-session.patch`
- `patches/display-controller/README.md`
- `scripts/device/fixtures/display-loader/session-before.py`
- `scripts/device/test-production-display-session.py`
- `scripts/device/test-production-display-transport.py`
- `scripts/host/test-repository-linux.sh`

## Metadata and preservation

- `python3 scripts/host/check-mobile-status.py`: PASS, 0.043 seconds.
- `python3 -O scripts/host/test-mobile-status.py`: PASS, 0.091 seconds.
- `python3 scripts/host/check-artifact-inventory.py`: PASS, 0.078 seconds.
- `git diff --check`: PASS, 0.015 seconds.

Eight status regressions pass. Inventory remains 595 sets; large/private byte
reverification remains NOT RUN. Fifteen preservation comparisons confirm the
artifact pointer/inventory, headless/mobile contracts, historical state body,
previous controller patches/fixtures and sealed private loader/backend/transport/
session bytes are unchanged. The integrated owner exited successfully with
362 MiB peak memory and zero swap.

Metadata files: `configs/project-status.json`, `docs/current-state.md`,
`docs/development-lessons.md`, this report and its qualification JSON.
Ending commit/tree and every changed-file hash are retained in the private
`rog5-display-session-20260920-r1/end.json`, avoiding a self-hash cycle.
No phone operation or protected-storage mutation occurred. The Denial phone
goal remains active and incomplete.
