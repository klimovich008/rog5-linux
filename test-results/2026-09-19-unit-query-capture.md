# Bounded startup-query capture and app-close retry — 2026-09-19

**Collector defects fixed; 108 integrated checks PASS. Startup timing remains FAIL with 8/9 units observed. Cache dispatch and authenticated startup/cleanup are verified. Separate app-close VM times out before controlled shutdown. Phone tests NOT RUN.**

## Source and demonstrated regressions

Source `9169523db92784828e55214965eca5d71cbb5f5e`, tree `c53b7121e8de83da59b09b7cd4ae70a5e0da256f`. Only the timing function in `tools/qemu-virtio-drm/logind-session.sh`, its actual-function cases in `scripts/host/test-qemu-logind-runner.py`, and required tools in `configs/repository-tests.json` changed.

A real C stdio writer emits a property then waits. The old collector loses that buffered row on a real timeout. Separate fixtures demonstrate unbounded stderr and raw stderr containing the exact serial session-success marker. The before run has 3 failed assertions across 2 test methods. These prove collector defects, not that every earlier VM timeout had the same root cause.

The collector now line-buffers systemctl stdout, enables bounded debug stderr, applies a 16 KiB per-file limit before reading output into shell memory, and hex-encodes both streams. It retains the 8-second query and 1-second kill-after limits, all 9 required units and the existing mandatory parser. Exact output bytes, including trailing newlines, are retained. Overflow is failure; partial data never becomes full timing PASS. Query failure status is preserved when transport succeeds; encoder failures propagate. Private scratch is removed on ordinary completion and handled signals.

An intermediate fixture failed because its intentionally minimal environment omitted the new scratch directory; the fixture now supplies TMPDIR. Final 12 startup-only cases PASS1.500s, full runner 88 PASS13.907s, selector 37 PASS (exact timing in receipt); syntax and diff checks PASS. Commands: Python `-O` for both test scripts, `bash -n tools/qemu-virtio-drm/logind-session.sh`, `git diff --check`.

Independent interruption fixture: 7.988s, child absent and scratch removed. Cancellation waits for the original timeout process group; it is bounded, not immediate. Source review found no demonstrated blocker. Host stdio coverage uses a synthetic C writer; exact target behavior is separate below.

Frozen integrated `scripts/host/test-repository-linux.sh active`: 108 PASS, 0 FAIL/BLOCKED/SKIPPED, 255 NOT_SELECTED; 3 declared optional subchecks skipped.173.015s, peak546.1MiB, no swap. This is local execution, not GitHub CI. No kernel/Denial/Flutter rebuild or new cache generation was needed.

## Startup-only VM: useful partial evidence, overall FAIL

Same retained kernel, package runtime, container images and admitted linker cache. Overall command227.045s, QEMU180.847s, exit0, authenticated local session/device/scope cleanup and normal poweroff. Container absence verified.

The timing command returned 124, now preserving 2,535 stdout bytes and 4,827 debug bytes. Eight unit property blocks and their matching GetAll replies are observed. The last request is GetAll for sysinit.target; its reply is not observed before timeout. This distinguishes sequential query progress from total lack of a response. It does not prove a target-specific manager stall, or by itself establish the exact cause of the earlier zero-byte records.

The retained ldconfig record is loaded/inactive, ConditionResult=no, with zero ExecMain start/exit timestamps. Together with verified staged cache bytes, this observes the intended skip. Hardware-database generation has ConditionResult=yes, Result=success and ExecMainStatus=0; its execution lasted12.518s from same-clock timestamps. Other first-boot work was not globally suppressed with an /etc/.updated stamp. Missing sysinit.target still prevents the complete timing inventory from passing; no overall critical-path speedup is claimed.

## Independent app-close VM: FAIL before observation

Observed cache dispatch and authenticated cleanup supplied the prerequisite for a separate app-close run. The nine-unit timing FAIL remains unchanged; it was not relabelled to permit that independent experiment. Existing app ownership, exact ACK, clean exits, 300-second VM deadline and conditional cleanup grace remained unchanged.

Overall command345.062s, QEMU timeout300.012s. Mousepad owner900/start28186 is observed near guest 281.86s, but neither app mapping/focus nor ACK/approved teardown completed. No settings-sync loaded/BEGIN/END record reached the observer. Normal guest poweroff did not occur; owned container cleanup/absence passed. The old Mousepad137 failure remains unresolved, not reproduced or fixed by this earlier timeout.

The latest PAM snapshot places the Denial service-start stage near monotonic 251.322s. This identifies late session activation, not its cause. Startup variability again consumed the app-close observation window. No third VM was run. Do not repeat this full boot unchanged; prepare a focused exact-ARM64 app-close environment to isolate shutdown, then retain full-session qualification separately. A suitable headless compositor was not found in the host PATH during the bounded tool check; its dependency must be established before that experiment is ready.

## Evidence and scope

[Qualification record](2026-09-19-unit-query-capture-qualification.json) contains exact commands, code/cache/kernel inputs, output identities, raw-log hashes, partial properties, test records and both failure results. Raw serial/debug logs remain private under `/home/deck/.local/state/rog5-unit-query-20260919-r1`. Historical FAIL/NOT RUN evidence and consumed claims remain intact. S06/R01 stay FAIL. No phone/USB/SSH/fastboot, production signing, admission, claim consumption or protected-storage mutation occurred. Native phone OLED/touch/Adreno Denial acceptance remains NOT RUN.
