# Actual local logind session — 2026-09-13

**The generic ARM64 VM passes authenticated local-session and mediated-device checks.**
Actual systemd is PID1; the original packaged login PAM profile authenticates a
public synthetic UID 1000 account on tty1. Its user manager runs, and libseat uses
logind to acquire and release the virtual DRM and input descriptors. PAM logout
succeeds; successful enumeration proves the session and scope are removed.
This run contains no Denial compositor and supplies no phone evidence.

Start: `1ff0b740ba2ee4829fb5d2c7568791a715a35d27`, tree `78d102d7e58ba325afd5d83b9ce65cfc82bffaed`.
Frozen implementation: `f29d7b835a6e7fa62dc62f2748678cf1f7337fa9`, tree `f888ea09fe0d3011d8db7838e4be5ff989c8192d`.
Subsequent commit publishes evidence/status only. All old results are retained.

| Executed check | Result | Duration |
| --- | --- | --- |
| SIGTERM ownership regression before repair | Expected FAIL: live child remained |0.586s |
| Cleanup query regression before repair | Expected FAIL: exit 42 falsely became success |0.002s |
| Default init real VM child-isolation regression | PASS |1.450s |
| Initial actual systemd startup at 512 MiB guest/768 MiB container | PASS startup only |91.439s |
| First frozen public session run | FAIL: PAM 7, then shutdown deadline |193.148s |
| Permit User Sessions correction, 768 MiB container | FAIL: 180s deadline during user manager startup |192.835s |
| Same bytes, 1024 MiB container | PAM/TakeDevice PASS; overall FAIL at openvt cleanup |114.228s |
| Console correction | PAM/devices PASS; overall FAIL: unsupported cleanup argument |127.603s |
| Diagnostic rerun | FAIL: named loginctl exit 1; no cleanup PASS |129.104s |
| Mistyped image identity invocation | FAIL before build/VM; full-hex guard refused it |<0.001s |
| Final frozen public runner | PASS |124.563s total; 111.700s VM |
| Frozen active tier |{'PASS': 97, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255} |136.828s |

The active tier used two workers, peaked at 285.2 MiB, and used zero swap.
All selected suites passed. Three declared optional subchecks were SKIPPED:
retained H03 sealed-archive replay, retained ARM64 trial-state replay, and the
optional ARM64 PMIC rail-reader binary. These are not hardware PASS evidence.

Publication checks then passed: `python3 -O scripts/host/test-review-metadata-checkers.py Checkers`
(5 tests, 0.937s), `python3 scripts/host/test-mobile-status.py` (8 tests, 0.024s),
`python3 scripts/host/check-artifact-inventory.py`,
`python3 scripts/host/check-mobile-status.py`, and `git diff --check`.
Explicit comparison confirms the immutable contracts, historical status body,
previous 516 artifact sets and existing pointer fields are unchanged.

Earlier 256 MiB guest attempts timed out at 60.146,180.740,180.208 and180.202s.
Their diagnostics and raw FAIL receipts remain; startup success never supersedes
later session failure. The prior default-init driver accidentally retained an
overbroad systemd scope label. Its interpretation is explicitly narrowed in the
qualification without editing the original result bytes.

The startup defect was an omitted packaged Permit User Sessions service: the
custom target left `/run/nologin` and PAM correctly refused authentication.
The corrected run observes it present, starts the real packaged service and
verifies absence. No PAM checks, service protections or privilege gates are removed.

The console fixture originally used `openvt -s -w`, whose exit path attempts
to deallocate the console after switching back. Its starting and target console
were both tty1. The real test therefore succeeded but openvt returned 8. The
correction uses `setsid --wait openvt -e` and preserves the existing foreground
console. Successful process enumeration checks no attached processes before and
after; query failures are failures. Actual PAM command status is retained.
The authenticated runtime openvt manual documents direct exec; the
[upstream source](https://github.com/legionus/kbd/blob/master/src/openvt.c)
was also inspected as a cross-check, not used as proof of exact package bytes.

The exact ARM64 loginctl parser independently reproduced the unsupported
`--no-footer` argument in under 1s. Removing it preserved `--no-legend`, which
already suppresses the footer. The shared real query functions now run with
`--help` before costly systemd startup; this checks the actual packaged parser
while the host fixtures verify both paths use the same argument lists.

Six focused host test methods cover real process-group interruption, timeout
and background-descendant reaping, plus 15 query-boundary subcases. The actual
shell functions distinguish absent, present and unavailable state; no duplicate
behavior model stands in for the implementation. The unchanged default init
mode also executed in its real VM; only the explicit compile-time fixture mode
executes packaged systemd as PID1.

With the same 512 MiB guest, the 1024 MiB container sampled peak 1,035,280,384 bytes,
zero max/OOM events and zero swap. The 768 MiB run was observed near its limit,
but its event counters were missed before teardown. This supports the larger
host budget without claiming a proven OOM kill. No kernel/Mesa/QEMU version
or guest-RAM change was made. All owned containers were removed.

The VM has read-only 9P runtime/payload, no network or host render node, 180s
host deadline and 8 MiB serial cap. Account, shadow, helper metadata and writable
configuration exist only in guest RAM. PAM uses its original login profile;
this fixture is not the packaged login executable or a lock-screen UI.
Missing generic-kernel namespaces/BPF/audit/tmpfs ACL remain recorded limits.
Logind functionality does not establish complete service sandbox enforcement.
Earlier failed runs logged /var unmount errors before final unmount/poweroff;
the final run did not. All logs remain; this does not qualify phone shutdown.

The supplied framebuffer review was already addressed by the unchanged strict
selector, Invalid pool dispatch and returned-descriptor guard. Retained 16
corrected PASS and 10 original expected FAIL were not repeated. Prior non-root
rendering, 210 frames/page flips and text entry remain separate VM evidence.

Changed implementation files:

- `configs/repository-tests.json`
- `docs/development-lessons.md`
- `docs/development.md`
- `scripts/host/test-qemu-logind-runner.py`
- `scripts/host/test-qemu-logind.py`
- `scripts/host/test-repository-linux.sh`
- `tools/qemu-virtio-drm/init.c`
- `tools/qemu-virtio-drm/logind-boot.sh`
- `tools/qemu-virtio-drm/logind-observer.sh`
- `tools/qemu-virtio-drm/logind-pam-session.rs`
- `tools/qemu-virtio-drm/logind-seat-probe.rs`
- `tools/qemu-virtio-drm/logind-session.sh`
- `tools/qemu-virtio-drm/logind-user.sh`

Publication files:

- `test-results/2026-09-13-logind-session.md`
- `test-results/2026-09-13-logind-session-qualification.json`
- `configs/project-status.json`
- `docs/current-state.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`

Publication adds this report and qualification, appends one fixture artifact
set, and updates the existing pointer/status/generated header. The previous 516
sets, existing pointer fields and historical current-state body remain unchanged.
The immutable headless/mobile contracts and historical S06/R01 FAIL are preserved.

Next smallest authorized experiment: launch the prepared Denial entry/native
applications through this actual local PAM/logind route in one bounded VM.
Do not infer graphics/session integration from the two separate prior proofs.
A real-phone A660 modifier/fence/readback test still requires new physical
authorization; no phone test starts under this task.

[Qualification JSON](2026-09-13-logind-session-qualification.json) contains
exact commands, per-step deadlines/durations, input/output and provenance hashes,
earlier failures, terminal cleanup receipts and integrated JSON/JUnit identities.
Rust compilation with `-Dwarnings` passed; rustfmt was unavailable (BLOCKED).
No new GitHub CI result is claimed. Mobile physical rows are all NOT RUN.
No phone operation, signing/admission/claim, candidate generation or protected
storage mutation occurred. This turn advanced the local-session boundary;
the long-term native-phone goal remains incomplete.
Private evidence: `/home/deck/.local/state/rog5-logind-boundary-20260913-r1`.
