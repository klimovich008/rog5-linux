# XR24 probe recording and service cleanup — 2026-09-13

Fixed a demonstrated interruption bug in the confined runtime runner. Killing
its `systemd-run` client did not kill the independently managed service; an
observation exception bypassed the later service-stop code. Cleanup now attempts
service stop and verifies terminal state on success, failure and interruption,
even if client kill/wait fails. The client receives no stdin.

The original exception is retained with cleanup notes. The CLI preserves those
notes in its failure JSON and exits130 for interruption. Cleanup failures append
to a deadline failure instead of replacing it. A service that cannot be confirmed
terminal cannot produce a successful runner result. Raw logs remain available.

Starting commit `e3d59cf8189579304bedc48a996e94b48f5009fb`, tree
`f81bf87250c67956a4fcb7091f68f532a9affbb5`.
Recording source `f8c2568a5d314f9f8bce32c1b6fdd80187847fc6`, tree
`f855960cec4bf128e5f60d37de04ecf40421f4cd`.
Final report-handler source `e11f5a8a90bb2b3656ae1708d54b0de2801ae79c`, tree
`65885b20acf1222568b7f578131cc45d5b7b5837`. Only two handler lines changed after the
recording run; its bounded service function and ARM64 inputs are unchanged.
The final publication commit changes evidence/status metadata only.

| Personally executed check | Result | Time |
|---|---|---:|
| Initial cleanup regression against old code | Expected FAIL, four failed subcases | 0.079s |
| Focused suite after final report correction | 22 tests PASS | 0.979s |
| Real service: ARM64 XR24 fixture success | PASS, terminal service | 0.124s |
| Real service: returned layout refused | Expected refusal PASS, log retained | 0.121s |
| Real service: observer interrupted after recorded stall | Expected interruption PASS, terminal service | 0.109s |
| Real service: actual800ms service deadline | Expected termination PASS, partial log retained | 0.973s |
| Final frozen-source active tier | 93 PASS; 0 FAIL/BLOCKED/SKIPPED; 255 NOT_SELECTED | 153.424s |

The active tier used two workers, 1GiB maximum, no swap and a600s outer limit;
peak memory284.6MiB. The tests reuse the existing mandatory suite registration.
No existing CI result is represented as personally executed.

Independent source review identified client-wait interruption, lost cleanup
notes and overwritten deadline reasons; all three were reproduced or covered by
focused regressions and corrected before the frozen run. Follow-up read-only
review found no remaining concrete blocker; that review did not execute tests.

The host tests use real, separate client/service process groups with a controlled
service-manager boundary. The integration then uses real systemd user services,
QEMU and the exact retained ARM64 XR24 binary:
`bfb8edc07d91cf487da7abace8175edd5f41a734abacc66c852dec44b4fd2531`.
It binds the matching ABI fixture and authenticated Arch runtime. Its EGL/GBM
and native-fence boundaries remain controlled memfd/eventfd fixtures, with
`/dev/null` as the inherited descriptor. There is no DRM node or phone access.
The interruption is injected in the observer only after its log records the
actual fixture readback stall; the service-deadline case uses a real timer.

The current production Image/DT, module metadata, panel/touch files and their
hashes are **reference inputs**, not the executing kernel. Existing runtime
package hashes were checked before the experiment and bound inputs rechecked
afterward. The unchanged phone trial targets another kernel release and was not
modified. The probe was neither rebuilt nor inserted into any image or trial.

The [qualification JSON](2026-09-13-probe-recording-qualification.json) records
exact commands, per-run results/log hashes, source and reused artifact identities,
negative regressions and integrated JSON/JUnit receipts. The fixture logs remain
private, with their hashes published. A terminal host service state does not
qualify recovery from uninterruptible GPU/kernel work. SIGKILL cannot run Python
cleanup; the independent service deadline remains necessary.

Changed implementation files: `scripts/host/check-denial-runtime-linkage.py`,
`scripts/host/test-denial-runtime-linkage.py`, `docs/development.md`, and
`docs/development-lessons.md`. Publication adds this report/qualification and
updates the artifact inventory/pointer, structured status and generated header.
Historical evidence, accepted contracts and all prior artifact pointers remain.

The pending physical question remains A660 XR24 allocation/fence/readback under
separate authorization. Independent next work is a non-root Denial/native-app
session using the retained binaries/runtime offline; root VM applications have
not qualified the normal mobile privilege model. That work cannot establish
phone graphics or touch acceptance.

No phone/USB operation, candidate, signing, admission, claim, installation or
protected-storage mutation occurred. Physical rows remain **NOT RUN**, S06/R01
remain **FAIL**, and the native-phone goal remains incomplete.

A final opcode-injection regression interrupted actual main immediately after
its tentative success assignment. Before the two-line handler correction it
exited130 while persisting PASS_LINKAGE_ONLY; afterward it exits130 and records
FAIL. Loader operations were mocked. The initial134.376s integrated run is
retained separately; the final run covers the corrected handler. Publication
metadata regressions and status/inventory checks are recorded separately.

Final publication checks PASS: five metadata regressions, eight mobile-status
cases, inventory and generated-header checks. One private metadata-wrapper
filename typo failed before its checker ran; corrected and rerun. All511 prior
artifact sets, old artifact pointers, both acceptance contracts and historical
status body were compared unchanged. Inventory now contains512 sets.
