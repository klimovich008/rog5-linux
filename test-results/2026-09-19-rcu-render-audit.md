# RCU qualification gate and render-audit startup control — 2026-09-19

**Host fixes PASS; generic ARM64 VM FAIL; audit-off comparison INCONCLUSIVE.**
No phone operation, candidate, signing, admission, claim or protected-storage
mutation. Physical results remain NOT RUN; S06/R01 FAIL and prior VM failures
remain unchanged. This is preparation for native Denial, not phone qualification.

Starting source was `2d13d4f028f2382a0c1e479af69bbdee65e6d6d8`, tree
`12ec7da5d89800d58c91cc9d4898eae651278750`. Tested and VM-executed source is
`8bf3985d9fef54c66422e4c89383dd15a22a1f3e`, tree
`a231fcfc250c3d44ea7dcc27910b73511bebf22a`. Both integration and VM started
with a clean checkout. Later documentation does not change those identities.
The original dirty project checkout and other source worktrees were preserved.

## Demonstrated fixes

- `scripts/host/test-qemu-logind.py`: an RCU CPU stall now invalidates normal
  VM poweroff qualification. Previously a stall followed by success/poweroff
  markers passed. The regression executes the production function with both
  observed stall messages, timestamp prefixes and ANSI colouring: six old-code
  counterexamples fail. Ordinary RCU boot notices remain accepted. The first
  draft missed coloured messages; those two fixture failures were corrected.
- `tools/qemu-virtio-drm/logind-denial.sh`: diagnostic rendering mode defaults
  to0 instead of being forced to1. The runner's explicit `--render-audit` option
  stages1 for a combined Denial VM session; its absence stages0. A private policy
  controls the actual exported child environment, ignoring inherited settings.
  Invalid policy stops before launch; staging refuses an existing output.
- `scripts/host/test-qemu-logind-runner.py`: executes the actual shell bootstrap
  and staging function for default/0/1, malformed policy, child inheritance,
  output refusal and CLI scope. The previous bootstrap fails six subcases.

Seven focused cases pass under Python `-O` (0.190s including startup). The frozen
active tier passes **111 suites,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED** in
182.194s. Three declared optional historical subchecks are SKIPPED separately.
The119-case runner suite passes in25.020s (25.311s including startup); peak
active-test memory521.3MiB, swap0. Syntax and diff checks pass. These were local
executions, not imported GitHub CI results. Subsequent publication checks pass
eight status tests and the558-set inventory check; all557 historical rows and
the historical current-state body compare unchanged. Exact commands, timings and hashes:
[qualification record](2026-09-19-rcu-render-audit-qualification.json).

## Source deductions before the control

The exact retained GTK portal backend clears `GTK_USE_PORTAL` before `gtk_init`,
and calls `g_bus_own_name` afterward. This disproves that particular recursive
portal hypothesis. Missing GTK/main `Started` events do not identify the exact
blocking call, and no activation dependency cycle was demonstrated. Existing
service requests, environment publication and deadlines were preserved.

The matching patched Denial source emits terminal raster/page-flip/vsync counters
independently of auditing, after successful orderly engine shutdown at INFO
level. Their increments and required EGL fence creation/flush/export are also
independent. Audit0 disables **optional GPU timestamp queries as well as trace
formatting/output**. This is therefore a diagnostic-mode comparison, not an
isolated measurement of logging cost. Remaining instrumentation is not removed.
The review matched all703 native source files to the retained inventory and
matched source/build receipts and native/engine archive members. It did not
rehash every one of the3264 historical engine linker inputs or rebuild either
binary. Detailed source bindings remain in the private review.

The previous stall's exact ELF reproduces the executed Image. Its sampled
`prep_new_page+132` is just after `clear_page`; registers show order0, one4KiB
page. Neither that instruction nor the stack proves how long clearing took.

## One bounded VM result

Retained kernel, Denial/Flutter, session archive, runtime/cache inputs, guest
SMP, single-thread TCG mode, container limits, services and deadlines stayed
fixed. Two consumed source files changed: the runner and Denial fixture.
The staged audit policy is exactly `0\n`. No Denial, Flutter or kernel rebuild
was performed; only the existing small VM helper assembly ran.

| Boundary | Observed result |
| --- | --- |
| Cache preparation | PASS |
| Initialized devices | PASS, boottime215.98→223.08, unchanged8s command deadline |
| PAM/logind | Authentication/account/credentials/open-session PASS; active tty1 and mediated-device probe PASS |
| Session entry | Guest snapshot reaches the mobile-session configuration check |
| Denial rendering/portal start | No completed result or terminal render counters captured |
| Mousepad/Foot mapping, text entry | NOT RUN; no pointer actions or screenshots |
| Kernel | RCU self-detected stall in PID1/systemd before its banner and before Denial |
| VM | FAIL_TIMEOUT at300.011s; QEMU killed with-9; harness357.144s, wrapper357.215s |
| Cleanup | Host container removal and absence verified; normal guest poweroff/PAM close NOT OBSERVED |

The new stall maps to `copy_user_highpage+56` → `handle_mm_fault` →
`do_page_fault`. Its sampled PC is the instruction after `copy_page` returns.
This differs from the earlier bash page-allocation sample and does not prove
either helper consumed the stall interval. The guest advertises MOPS and the
ELF contains MOPS alternatives; runtime-patched instruction bytes were not
captured. MOPS remains an investigation lead, not an established cause or fix.

A bounded host sample measured2.439CPU-seconds over2.001wall-seconds, no new CPU
throttling and zero memory events. It describes that window only, not scheduling
throughout the stall. All41 consumed input hashes and full original/mapped
runtime bytes and metadata passed post-run verification. Initramfs218769bytes:
`68ef8623ad1e60e949cb4fbe38ea07c9989c8ae6d27e9d7bacfb064b9ce47a8e`.

The VM fails before answering the intended portal comparison; it neither proves
nor disproves a startup benefit from audit0. The RCU gate's new rejection path
is host-regression tested; this VM already failed at the earlier outer timeout.

## Next action and feedback

Review the recurring exact-kernel page-fault/TCG boundary, including MOPS feature
and alternative selection, before choosing a smaller startup control. Preserve
the current kernel and resource bounds while establishing what a proposed
control actually changes. Do not raise deadlines or repeat a full Denial run
unchanged. Later portal/app-release problems and real-phone display/touch/GPU
qualification remain independent open work.

The intervening community follow-up did not change this startup dependency:
no progress toward this acceptance boundary. This turn is progress: the
qualification defect is repaired, an explicit diagnostic control is tested,
integrated tests pass, and the new
retained VM trace changes the next investigation. The reuse lesson is to make
costly diagnostic modes explicit while keeping required observation counters,
and never allow a recovered kernel stall to become a qualification PASS.

Private evidence: `rog5-rcu-portal-audit-20260919-r1` under the local state root.
The authoritative current pointer registers this as a fixture with authority
none. All older artifact rows and failure evidence remain intact.
