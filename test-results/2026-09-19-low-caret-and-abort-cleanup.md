# Low-caret VM interaction and abort cleanup — 2026-09-19

**Low-caret input/visibility passed in the retained ARM64 VirGL VM; the overall
session failed.** A separate source fix now detaches busy temporary executable
mounts on abort without turning failure into success. Phone tests remain NOT RUN.

VM evidence-producing source: `9b1a18bc064e0e4ee74e287681fb8b1fd313b4c2`, tree
`dcba1a78aafb400a9ddd37b0627347511296fe02`. Cleanup-fix source: `f5c8acfd3ac1942c23975d47fc87f375eed80d8b`,
tree `efcba7749932badd0316a093e18855f0a6d25b79`. The fix was made after the VM result; it has
not been tested in a guest. No installed phone bytes or signed candidate changed.

## Interaction evidence

The prepared `run-bottom-caret.py` ran once with the retained GTK caret module,
Denial/native shell, engine, kernel and runtime. The observer passed a64-line RAM
document's low-caret retap: client surface25 remained at x92,y1070, with a fresh
rectangle and commit after the translated pointer press. Expected viewport
translation was266.2px. The actual surface pointer was approximately296.492,
1079.859, matching the translated mapping within the existing tolerance.

Four original captures were visually inspected: the caret is at the end of
line-50 above the keyboard; subsequent images show line-50test, line-50tes,
line-50test. The native editor protocol records all12 matching press/release
events with no unfocused keys. Mousepad and Foot mapped and focused in the
expected Mousepad/Foot/Mousepad/Foot sequence. Keyboard reveal used a synthetic
pointer gesture; this is not automatic physical-touch activation. Per-client
presentation feedback is NOT RUN. Visual captures and protocol proof have
separate scopes; neither is phone OLED/touch/Adreno evidence.

All38 original input identities were revalidated:37 still match retained paths;
the changed cleanup script matches its evidence-producing Git blob and staged
VM copy. All47 staged output hashes also match.15 original PNG identities are
retained in the paired JSON. No kernel, Denial, Flutter or GTK rebuild was needed.

## Overall failure remains

VM result FAIL: total399.603s, QEMU347.543s. The diagnostic allowance was420s;
standard300s acceptance was not granted. App65s, user120s, PAM140s and existing
cleanup deadlines were unchanged. The120-second user session timed out with124
as controlled app close began. ACK and approved teardown arrived, but final
client exit records and normal poweroff did not. Do not infer another Mousepad137
or settings-sync hang from missing records.

Serial evidence records stage2 executable-view cleanup failure32; the alias
survived into late shutdown, followed by PID1 panic exitcode7. This is consistent
with the retained shared-9P teardown hazard. Actual late unmount flags were not
traced, so panic causation and prevention are not established. QEMU exit0 does
not override this failure. The owned container is confirmed absent.

## Source correction and executed checks

Changed `tools/qemu-virtio-drm/logind-session.sh` and its existing Python suite.
Normal restoration still requires ordinary `/usr/bin` unmount before lazy alias
release. An already-nonzero EXIT uses lazy overlay detach and then lazy alias
release, retaining the original status. Failure at either stage remains visible;
completed stages are not repeated, and a failed overlay detach cannot release
the alias. No forced unmount, deadline change or relaxed session-success check.

| Check | Result / elapsed |
|---|---|
| New regression against old source | Expected FAIL; retained prior log |
| Six production-function cases | PASS, 0.164s |
| Same cases under Python-O | PASS, 0.265s |
| Real isolated mounts, old abort | Expected FAIL, 0.065s; mounts remain |
| Real isolated mounts, fixed abort | PASS, 0.032s; mounts gone,124 retained |
| Strict busy unmount then abort cleanup | PASS, 0.064s; mounts gone,32 retained |
| Normal real-mount cleanup | PASS, 0.032s |
| Frozen integrated active tier | 108PASS,0FAIL/BLOCKED/SKIPPED suites; 173.601s |
| Unselected / optional subchecks | 255NOT_SELECTED;3optional SKIPPED |

The real-mount fixture uses unprivileged user/mount namespaces with private
propagation and tmpfs/run. A live child holds the bind mount busy; the actual
production functions perform unmounts. This proves host mount behavior and
status preservation, not ARM64/9P/PID1 shutdown. Guest treatment remains NOT RUN.
No new VM was run to repeat the already-observed text-entry flow.

The paired JSON includes exact commands, fixture source, source/artifact hashes,
recorded VM steps, focused and integrated durations, capture identities and
failure markers. Raw logs/images remain private under
`rog5-app-shutdown-probe-20260919-r1/bottom-caret-r1`; cleanup evidence is under
`rog5-vm-abort-cleanup-20260919-r1`. Existing historical records are unchanged.

## Next unresolved check and efficiency

A narrowly bounded VM abort test can check whether the fixed release reaches
normal guest poweroff after a deliberately failed user session; it must retain
that original failure. Prepare that independently of the full UI interaction.
The full mobile session still must fit its unchanged lifecycle deadlines;
measure startup/action/close stages before changing workload or proposing policy.
Do not repeat low-caret typing merely to test shutdown.

Real-phone graphics/touch/session, suspend/wake and installed integration remain
NOT RUN. S06/R01 remain FAIL. No phone/USB, signing, admission, claim, flashing or
protected-storage operation occurred. The prior cleanup turn and this correction
are progress; neither completes the phone goal.

The scoped improvement was a subsecond real-mount reproducer instead of another
six-minute UI run. Its scope is explicit, and its old/fixed outcomes are retained.
The existing development guide now records the abort-versus-success distinction.

Publication checks:8mobile-status cases PASS(0.022s),547-set artifact inventory
and generated status PASS; whitespace PASS. All546 earlier sets and existing
current-artifact pointers are semantically unchanged.
