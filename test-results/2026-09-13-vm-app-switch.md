# Native VM app launch and focus discrepancy — 2026-09-13

**Mousepad and Foot launch visibly through the mobile UI, but the app-switch
qualification fails.** After a rightward switch, the capture shows Mousepad
again while the native keyboard focus log still identifies Foot. The observer
correctly stops there; the second switch is NOT RUN. This is ARM64 VirGL VM
evidence, not phone touch, Adreno or physical display qualification.

## Executed evidence

| Run/check | Result | Wall seconds |
| --- | --- | ---: |
| VM r1 |FAIL: observer waited for an audit that an idle scene need not emit |102.656 |
| VM r2 |FAIL: upward flick opened Overview; home tile gate stopped further input |75.766 |
| VM r3 |FAIL: visual return to Mousepad without native keyboard focus transfer |102.435 |
| Final mobile-observer suite, Python -O |48 PASS |2.670 |
| Final native-client parser suite, Python -O |22 PASS |0.114 |
| Runtime prerequisite suite, Python -O |25 PASS |0.215 |
| Unchanged actual guest helper suite, Python -O |10 PASS |2.321 |
| Frozen active tier |92 PASS; 0 FAIL/BLOCKED/SKIPPED; 255 NOT_SELECTED |137.988 |

Three declared optional subchecks remain SKIPPED separately. The integrated tier
ran once on the final source, with two workers, 1 GiB/no swap and a 600-second bound;
peak memory was 338.8 MiB. Its PASS does not replace the three VM FAIL results.
All exact commands and per-run source/input hashes are in the
[qualification JSON](2026-09-13-vm-app-switch-qualification.json). The complete
JSON/JUnit tier reports are retained privately and referenced by hash.
Final evidence validation also passed: metadata checker cases (0.912 s), mobile-status cases (0.094 s), artifact inventory (0.071 s), generated status (0.046 s), and diff whitespace (0.035 s). Exact commands and results are retained in the private `metadata-result.json`. No new GitHub CI execution is claimed.

The final run produced 79 raster frames and 79 page flips, with no reported
rendering errors. Direct inspection shows Mousepad, Overview, home, Foot's shell
prompt, then the original Mousepad document again. Native protocol evidence has
only these three keyboard focus events:

- Mousepad enter at 59.750838 seconds.
- Mousepad leave at 67.864027 seconds.
- Foot enter at 68.061955 seconds.

There is no later enter/leave event, including in an unprefixed search. All 618
client records have intact prefixes; the parser reports no malformed/ownership
error or log-limit failure. Both linked native surfaces remain mapped. This
establishes the visible/native-focus discrepancy; it does not establish where
the focus request was lost or delayed. No test key was injected into the hidden
client to demonstrate the consequence.

The final observer capture `04-mousepad-restored-waiting.png` deliberately records
what is visible during failed native readiness without advancing input. Final
guest cleanup and container removal pass. Run r2 was aborted by its home gate:
container removal passed, while graceful guest cleanup was not established.
All failures retain their original result bytes.

## Demonstrated harness defects repaired

The first parser required two later positive output-audit intervals. The pinned
`OutputSchedulerAudit.maybe_report()` only runs during ready/fence/submission/
presentation activity and suppresses output until one second has elapsed.
A scene that finishes drawing inside that interval can become idle with positive
counts buffered indefinitely. Foot mapped at 68.798 seconds after the last report
at 68.614, matching this source counterexample. Extending the deadline would not
repair it. The new no-later-audit regression fails against the original parser
(exit 1, 0.060 seconds) and passes after the correction.

Capture readiness now requires an owned native app with the right app ID/title,
linked toplevel, configure/ack, committed buffer and fresh keyboard focus, followed
by 1.5 seconds of settling. Optional global audit reports remain separate; they
are not attributed per-client presentation feedback. Terminal frame counts and
direct captured pixels are independently assessed. `wl_surface.frame.done` is
not substituted for KMS presentation evidence. Identity, failure, teardown,
bounds and fresh-focus checks remain intact.

The same velocity-dependent up-flick went home in r1 and opened Overview in r2.
The final route deliberately pulls up, captures Overview, and taps the observed
exposed background at (25, 1080). Source confirms that this scrim calls
`closeOverview()`, clearing foreground selection without closing the app. A
reference-image check then requires the previously inspected Foot and Mousepad
icon regions before another tile click. No compositor gesture thresholds changed.

## Source and artifact identity

Starting commit `658d6423de22aac3aa3b666f9a9177ccb44ffcc4`, tree
`21e06466e60a46bb51d3b9b8d8308000ad72c79c`.

- r1 source `a984b605f594c9e616e52e097ae2cab961001df9`, tree
  `7d61d929fad5bc6c4fab63ef09df8610b926f146`.
- r2 source `31332c7110c974beeb714dd75300ff61fd728f41`, tree
  `20168e90817d5c5256d6f03fb832acf12fdca06c`.
- Final source `efb9af269d4ee4508d3de012244c4add6d1a9e15`, tree
  `7ddb06c538412c091332140009ad632bc10fa029`.

Native Denial, engine, corrected shell AOT, assets and generic kernel match all 34
inputs from the preceding launcher discovery. No native, engine, shell or kernel
rebuild occurred. Each run generated its own small VM initramfs. Native Denial
SHA256 remains `878ff4c6155279264782523837cf7672273f333a9a45318a7db9cc9fbf7ce19a`;
shell AOT remains `85567c81c52a375d8fa424aaaa54a152440b2fd02d73632301b857da6b230b19`.
Final serial SHA256:
`931c94a9e0ce272d90fc9c2fa76e220f1a8fde4bef3caf3d7554ed17e5178b46`.
Final initramfs SHA256:
`c222d076366667321a58af1b03dc86fc11a172b4920fad02f4cc6b9a831ba7d6`.

Changed source files are `scripts/host/qemu-launcher-protocol.py`,
`test-qemu-launcher-protocol.py`, `qemu-mobile-observer.py`,
`test-qemu-mobile-observer.py`, `test-qemu-virtio-drm.py`,
`test-repository-linux.sh`, `tools/qemu-virtio-drm/guest.sh`,
`configs/repository-tests.json`, `docs/development.md` and
`docs/development-lessons.md`. Evidence changes add this report and qualification
JSON, append one fixture to `manifests/artifact-sets.json`, update
`manifests/current-artifact.json` and `configs/project-status.json`, and regenerate
only the current header of `docs/current-state.md`.

Private evidence is `/home/deck/.local/state/rog5-vm-app-switch-20260913-r1`.
After verifying identical durable copies and terminated containers, 99 duplicate
payload files from earlier runs were removed, reclaiming 180,278,691 bytes.
Every removal has a path/hash/size/durable-source restoration record. Unique
initramfs images, logs and captures remain. The accepted artifacts, prior 501
inventory entries, headless/mobile contracts and historical current-state body
are preserved. No phone operation, signing, admission, claim, new phone candidate,
protected-storage mutation or history rewrite occurred.

## Unresolved focus boundary and next experiment

Source review found a real scheduling weakness: the service cadence advances
before work; a platform message can queue a window command, then either 2 ms
background-slice check can skip the sole window-command drain. The pending-work
predicate omits that runtime queue. Repeated expensive earlier work can therefore
starve a queued focus command. Existing logs do not prove that this happened in
r3, or that a focus command reached the queue at all. Settings cost is not an
established cause. No speculative native fix was applied.

The next smallest offline experiment should correlate the shell's target window
ID, wire enqueue, command drain and native activation. First establish an
executable regression against the actual scheduling/dispatch code where possible;
use bounded stage diagnostics if runtime attribution remains missing. Preserve
both visible selection and native focus requirements rather than accepting one
as the other. Do not repeat the unchanged VM or increase deadlines blindly.

The wrapper/app-ID mismatch hypothesis is disproved: Foot remains an expected
app ID independently of the Exec wrapper. A reversed second gesture was also
corrected during preparation: activation raises each window in Smithay's
back-to-front list, and Dart preserves that ordering, so both return switches
use a right drag. The second return has not executed successfully.

All phone physical rows remain NOT RUN; headless S06/R01 remain FAIL. The VM's
root session, epoch clock, battery Waiting and Foot locale fallback are fixture
conditions, not a daily-driver mobile security or telemetry qualification.
