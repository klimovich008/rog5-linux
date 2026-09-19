# Explicit VM readiness budget experiment — 2026-09-19

Generic ARM64 VM/offline work only. No phone operation, candidate, signing,
admission, claim consumption or protected-storage mutation. Physical NOT RUN;
ASUS slot A, signed V11 fallback, server/rescue and historical S06/R01 FAIL preserved.

Starting commit83c95c678fea10fabad7c9ac43355dd0a8362fd5,
tree8d2bf0eb94dedcb5909186b8d352ffbc65bd713d. Previous turn made progress:
late virtual input worker completion was observed after the8s admission wait.
The independently prepared read-only close sampler remained runtime NOT RUN.

Source1784e75b8b238dde44af8f17d5d87b8a86a3a53c,
tree5f2ca2ac93a864b57275e4f862c2691216f80f03. Changes are limited to
`scripts/host/test-qemu-logind.py`, `tools/qemu-virtio-drm/logind-session.sh`
and `scripts/host/test-qemu-logind-runner.py`.

The explicit `--device-readiness-20s` combined-VM option stages an exclusive
recorded marker. Guest validation selects one20s shared initialized-device wait;
normal behavior remains8s. Basic/malformed selection fails before device effects.
The exact six consumers, original rules, initialization predicate, permissions,
identity/VT/seat/PAM checks and original failure result remain mandatory.
No retry or global settle is added. Extra12s consumes existing setup reserve;
PAM190/225/230, unit260 and host440 limits remain unchanged. The outer deadline
can still expire first; full worst-case inner budgets are not guaranteed.

Three new regression methods fail against retained old source in0.821s. Final
18 focused cases pass2.550s, including real runner marker staging/identity and
unchanged compiled Rust budget expressions. Initial fixture snapshot re-sourcing
bypassed a parent-shell stub; the final fixture appends its inert snapshot seam
to the file sourced by both shells, avoiding reads of host device/journal data.
Early private logs remain retained and are not included as public evidence.

One VM at the frozen source completed in382.146982498s; wrapper382.218997869s.
Readiness20s PASS:141.86→158.31 BOOTTIME,16.45s. This exceeds the old8s limit
and establishes the usefulness of the explicit arm for this run. It does not
establish repeated-start reliability or erase historical8s failures. No retry
or original-rule replacement occurred; failure-only snapshot/retrigger NOT RUN.

PAM authentication, nonroot active VT/seat and mediated device access passed.
Both Mousepad and Foot visibly launched; their screenshots were personally
inspected. Mapping/focus protocol and observer PASS, approved teardown true.
No text-entry or phone-touch claim. Foot exited0; Mousepad again exited137 after
TERM/KILL. Close-begin292.91 and close-returned296.07 include preparation,
transport and reaping, so neither is an exact signal-delivery timestamp.

The sampler ran successfully:39 records,1039ms,invalidated=false,truncated=true.
First sample295.021760480 is2.112s after the pre-close marker; this is not proof
that TERM had already been delivered2.112s earlier. Main-thread PID1001 is
reported as syscall=running and State:R in rounds0–4. Exact pinned Linux
fs/proc/base.c and lib/syscall.c show this means no stable blocked-task snapshot
was obtained; it does not prove uninterrupted execution or a spin loop. No
main-thread PC was available. Timeout PID1000 waits in ARM64rt_sigsuspend133;
one worker waits in futex98/WAIT_PRIVATE and two workers in ppoll73. These
worker states do not locate the main-thread failure.

Round5 reports syscall PermissionDenied with shared pendingSIGKILL0x100.
The0400 proc syscall inode can become root-owned when a task loses its mm;
this is consistent with teardown, not proof of an earlier permission blocker.
Exact cause is unobserved. Truncation means omitted FD/worker records are not
proof of absence. The settings probe again has loaded/APP_RUN_BEGIN without
shutdown, sync, run-end, unref or destructor markers. Do not generalize an older
late-unref observation to this run.

The corrected PAM helper reaches close-session0, delete-credentials0 and end0,
then preserves child failure1. This is observed cleanup on the failure path,
not a successful app/session lifecycle. The prior alarm142 incident remains
historical; this observation alone does not isolate timing causality.
Journal reports session c1 removal. Normal VM poweroff passes; /var unmount
FAIL remains. Input hashes and original runtime bytes/metadata verify unchanged;
no owned containers remain. Phone physical results remain NOT RUN.

Next: add raw main-thread utime/stime and voluntary/nonvoluntary context-switch
counters to the existing six-round sampler, recording clock-tick scale and
keeping its byte/time bounds. Use /proc/PID/task/PID/stat, since /proc/PID/stat
aggregates the thread group. This distinguishes measured execution from absent
accounted progress without ptrace, signals, interposers or a kernel rebuild.
PERF_EVENTS/SCHEDSTATS are disabled; ordinary stat/status counters are available.
No unchanged VM repeat is justified. Increased CPU use alone would not prove a spin.


Frozen active tier112PASS,0FAIL/BLOCKED/SKIPPED,255NOT_SELECTED in190.876051168s; three declared optional historical subchecks SKIPPED. Resource totals are retained in active.log. Full commands, source/artifact identities and per-step durations are retained in the qualification JSON and private records. No new kernel/Denial/Flutter build.
