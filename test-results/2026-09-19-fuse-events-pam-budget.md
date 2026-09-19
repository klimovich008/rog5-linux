# FUSE event processing diagnostic — 2026-09-19

Generic ARM64 VM investigation only. No phone operation, candidate, signing,
admission, claim consumption or protected-storage operation. Physical NOT RUN.
The accepted server/rescue baseline and historical S06/R01 FAIL remain unchanged.

## Question and source

The preceding VM failed the initialized-device wait; a later database snapshot
contained five consumer entries but lacked FUSE c10:229. Pinned systemd v261.3
3255daee1572366b74fe92f002a3d60ecbb27103 writes a database for character devices
with nonzero devnum even without properties. Empty tty1 is valid. Both tmpfiles
and static-node rules can independently establish FUSE permissions. The packaged
coldplug service runs trigger without settle and ignores its exit failure;
completion of enumeration does not establish successful worker completion.

The source audit also distinguishes trigger settling from initialization:
udev-worker.c broadcasts partially processed failures, and udevadm-trigger.c
settles by UUID. A successful targeted trigger must never replace the actual
initialized-device predicate or retrospectively qualify the failed boot.

Starting source a09307d8337dfcc52dbc238ae43e08f3e0f7c588, tree
8a16691ac2a6a82420deafbfd7fb41845e859213. Implementation 89e6f4b9;
frozen integration a947d956ad09fd29a8021ea4e16b225653b1adb3, tree
369e8aa9a7d73a3fd39c619a81ff1e65842dbcc6. No new Denial/kernel build.

## Changes and offline checks

- logind-session.sh stages a FUSE-only debug rule in the disposable VM's RAM
  /etc before coldplug. On failed readiness only, an encoded ten-second bounded
  diagnostic snapshots the database, requests one three-second bounded add
  retrigger, reruns the one-second initialized reader and extracts matching
  worker journal records. The original failed status remains fatal.
- logind-boot.sh calls the preparation function before starting systemd.
- test-qemu-logind-runner.py executes the production functions with synthetic
  udev tools, testing retrigger success, failed initialization despite settle,
  trigger failure, timeout/reaping and scoped rule staging/no overwrite.
- configs/repository-tests.json raises only this growing host suite's deadline
  from30 to40 seconds. The final132 cases took28.229s alone and31.435s in the
  bounded parallel tier, exceeding the old30s allowance. No VM deadline changed.

Initial new regressions failed on the old source. Development failures from a
shell continuation and a fixture string escape remain retained; both corrected
before freezing. Final22 focused cases PASS12.841s. The packaged ARM64 udevadm
under QEMU user emulation verified the actual rule: one successful file. The
first host-absolute-path invocation failed path chasing; explicit fixture root
succeeded. This is a parser check, not live udev or phone proof.

Initial active tier stopped at the30s suite limit:20PASS,2FAIL,89BLOCKED,
255NOT_SELECTED. The companion suite's SIGTERM followed fail-fast cleanup;
no independent assertion failure was reported. Final tier111PASS,0FAIL/BLOCKED/
SKIPPED,255NOT_SELECTED in182.424839207s;338.3MiB peak,zero swap. Optional
historical subchecks are reported separately in the retained summary.

## VM result

The one VM at a947d956 failed overall in369.213587315s (wrapper369.285675366s).
All six devices initialized in0.64s; therefore the failed-boot FUSE retrigger
was NOT RUN. PAM/logind granted nonroot seat/device access. Portal start passed
in35s (CLOCK_MONOTONIC212.913594912→248.842523184); its separate3s property
snapshot timed out, while mandatory active-service and FUSE-mount checks passed.

The observer reports PASS for synthetic-pointer delivery and captures. Both
Mousepad and Foot were visibly inspected in retained screenshots; the original
observer visual_semantics NOT RUN field is unchanged, with supplemental image
inspection in qualification JSON. This is two initial focus visits, no text-entry
or phone-touch proof. Teardown was requested; Foot close began at boottime288.92,
but no successful normal-close receipt or terminal compositor counters followed.
PAM recorded child exit124, then successful close-session/delete-credentials/end.
Normal guest poweroff passed the existing RCU-aware gate. The /var unmount failure
remains recorded. Host containers closed; full runtime bytes/metadata and locked
input hashes passed post-run verification.

Source inspection then found the fourth nested deadline: the Rust PAM helper
still used120s for every Denial child. This is a demonstrated budget defect and
is consistent with the observed close interruption; it does not prove a Foot or
Mousepad application defect. The executable regression compiles the actual Rust
child.args expression using cfg flags selected by the actual Python runner.
Old source fails120>=190; basic20 and startup-only120 remain unchanged.

Correction28c98531 adds startup-only cfg dispatch and budgets full190s child
(60 setup+40 portals+60 flow+30 cleanup),230s PAM (40 authentication/teardown
reserve),260s fixture and440s host. The actual helper cross-compiles ARM64 with
-Dwarnings in6.780451095s, SHA256
`e19a41da1a425ffdd434f84d0f222c3fb8b805e127aaba6a4e252265538cb004` (564224B).
This is a VM helper, not a phone candidate. Final20 focused cases PASS2.045s.
The corrected helper has not run in a system VM. No second VM was launched.


Final frozen active tier at 28c985314f63769d554eea0cd924386f406c6ea1:111PASS,0FAIL/BLOCKED/SKIPPED,
255NOT_SELECTED in185.513329358s; three declared optional
historical subchecks SKIPPED. Exact command, source/tree, retained logs, build
inputs/output and VM identities are in the qualification JSON and private
`rog5-fuse-events-20260919-r1` / `rog5-pam-child-budget-20260919-r1` records.

Next: one bounded same-input close-only VM using the repaired helper; preserve
all guards and capture actual app closure plus compositor termination. Original
FUSE event absence remains open. No phone operation or protected-storage mutation
occurred; physical rows stay NOT RUN and S06/R01 remain FAIL.

## Executed commands and changed files

The retained command arrays bind full paths, resource limits and compiler inputs.
Focused invocations were `python3 scripts/host/test-qemu-logind-runner.py
FuseEventDiagnostics DeviceReadiness DeviceReadinessDiagnostics SessionBudgets`
and, after the child repair, `python3 scripts/host/test-qemu-logind-runner.py
SessionBudgets CleanupGrace TcgMode`. The standalone measurement used Python -O
for the complete runner suite. Integrated invocations used
`scripts/host/test-repository-linux.sh active` in the recorded bounded services.
The ARM64 parser invocation was `udevadm verify --root=FIXTURE
/etc/udev/rules.d/00-rog5-vm-fuse-diagnostic.rules` through the pinned runtime's
binary and QEMU user emulation. Exact build and VM commands are in qualification.

Post-publication `check-mobile-status.py --write`, `check-mobile-status.py`,
`check-artifact-inventory.py`, `test-mobile-status.py` (8 cases), and
`git diff --check` pass. Inventory validation initially rejected a shared proof
listed twice as an output; the VM row now owns its distinct result, while both
rows reference the common proof as evidence. All567 sets validate. Prior rows,
headless acceptance bytes and historical current-state body were compared to
the starting commit and are unchanged.

Changed files:

- configs/repository-tests.json
- scripts/host/test-qemu-logind-runner.py
- scripts/host/test-qemu-logind.py
- tools/qemu-virtio-drm/logind-boot.sh
- tools/qemu-virtio-drm/logind-session.sh
- tools/qemu-virtio-drm/logind-pam-session.rs
- configs/project-status.json
- docs/current-state.md
- docs/development-lessons.md
- manifests/artifact-sets.json
- manifests/current-artifact.json
- test-results/2026-09-19-fuse-events-pam-budget.md
- test-results/2026-09-19-fuse-events-pam-budget-qualification.json
