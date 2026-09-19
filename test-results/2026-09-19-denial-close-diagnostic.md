# Denial VM shutdown: settings sync returns before forced kill — 2026-09-19

**Mousepad close remains FAIL (137), but the real settings-sync call returned in
0.209312 ms. This is VM evidence only; phone operation and physical qualification
remain NOT RUN.**

One retained Denial/VirGL ARM64 VM reached owned Mousepad and Foot mapping/focus,
exact host acknowledgement and approved teardown. Foot exited0. Mousepad received
TERM, ran settings synchronization and was subsequently killed by the unchanged
two-second kill-after policy. Its probe emitted loaded/resolved, BEGIN and END
for PID923. An unfinished `g_settings_sync()` at termination is therefore excluded
for this run. The preceding or following shutdown work is not yet localized.

The outer VM observation allowance was420s through an explicit private wrapper;
the standard300s runner was unchanged. Its existing conditional30s cleanup grace
remained available but was not used. App65s, TERM/KILL2s, user120s, PAM140s,
network isolation, read-only runtime, memory/CPU/task limits, owner and ACK guards
were unchanged. **This run is not standard300s qualification; its prior FAIL
remains.** No compositor, kernel, Flutter, package or phone-candidate rebuild.
Only the runner's small Rust/C supervision executables were rebuilt.

## Executed result

| Check | Result |
|---|---|
| Exact prior inputs before execution | PASS,37 hashes matched |
| Owned app mapping/focus sequence | PASS,Mousepad then Foot; no client presentation claim |
| Exact ACK and approved close | PASS |
| Real settings-sync observation | PASS,loaded/BEGIN/END,0.209312ms |
| Required clean app shutdown | FAIL,Mousepad137; Foot0 |
| Guest normal poweroff | PASS,QEMU0,normal power-down,no recorded kernel panic |
| Owned container removal/absence | PASS,also independently rechecked |
| Exact inputs after failed observation | PASS,all37 separately rehashed |
| Full experiment / QEMU runtime | 368.868s /326.516s |
| Text entry,visual semantics,phone hardware | NOT RUN |

Raw close BOOTTIME brackets were310.83→313.33s for Mousepad and310.45→312.13s
for Foot. They include transport/wait overhead and are not exact signal times.
Probe BEGIN312.998475984 and END312.998685296 use CLOCK_MONOTONIC. No subtraction
between these clock domains or the Wayland logger timestamps was used.
The last captured editor messages include pointer enter with a null surface after
surface destruction. A queued event referencing a locally destroyed proxy is
not by itself proof of a malformed server event or of the shutdown cause.

The earlier failing VM had already reported DConf's Type=dbus user service
started approximately27s before close. The new VM likewise reports it started
before close. Cold first activation at shutdown is unsupported; no settings
backend replacement or broker-only substitute is justified by this evidence.
The earlier focused Weston-host pass remains a separate component result.

## Identities and limits

Source commit `b79b6d09e43c3c80f51079b69859ab170c78f19c`, tree
`a43af1710fb4f4ff2470f8035a964332167a2ff6`, clean throughout execution.
Denial upstream revision remains `85b2303e2f09ae7b7b993641f90061a200f03d53`;
the exact composed session archive, overrides, runtime, kernel and tool images
are recorded by hash in the paired qualification JSON. Do not equate upstream
revision alone with the composed runtime bytes.

The private wrapper imports the production runner and changes only the serial
VM dispatch deadline300→420. Its full source, command, hashes and original
production arguments are retained in the qualification. Raw runner status FAIL
and diagnostic status DIAGNOSTIC_FAILED are preserved. The wrapper output is not
release authority. Private raw evidence remains under
`/home/deck/.local/state/rog5-denial-close-diagnostic-20260919-r1`.

Executed command: `python3 /home/deck/.local/state/rog5-denial-close-diagnostic-20260919-r1/run.py`.
Post-run collector separately verified all37 inputs and parsed exact same-PID
records. Existing integrated108-test PASS is inherited for unchanged production
source; it was not rerun or claimed as a fresh result. Fresh publication checks: `python3 scripts/host/test-mobile-status.py`
8/8 PASS,0.021s; `python3 scripts/host/check-artifact-inventory.py` PASS545sets;
`python3 scripts/host/check-mobile-status.py` PASS; `git diff --check` PASS.
An independent semantic comparison preserved all544 earlier artifact sets and
all existing current-artifact pointers, adding only this diagnostic fixture. Historical FAIL/NOT RUN, installed bytes, fallback,
claims and headless acceptance remain unchanged. No phone/USB operation,
signing, admission or protected-storage mutation occurred.

Next instrument the application shutdown callback boundary and run-loop return
using verified exact-package/API semantics. Prepare and check the diagnostic
before another VM. Do not repeat the sync-only observation, lengthen the actual
close grace, or substitute an easier desktop for Denial.

## Run improvement

The longer, explicitly non-qualifying observation envelope answered a question
that two standard-deadline boots could not reach. Keep diagnostic observation
and qualification budgets distinct, preserve original failures, and use actual
function boundaries to choose the next probe. The successful sub-millisecond
sync measurement makes another DConf-only fixture a poor next experiment.
