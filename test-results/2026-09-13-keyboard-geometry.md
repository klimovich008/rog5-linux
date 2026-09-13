# Keyboard animation and native input geometry — 2026-09-13

**Confirmed and corrected:** the keyboard sheet animated at the controller's
current position while application translation and native input regions used
its open/closed target. Closing could remove keyboard input regions while keys
were still visible; opening had the inverse mismatch. The right-edge strip also
reserved native input before its visible0.98 threshold. An interrupted spring
seeded a new drag from target state, causing a position jump.

Patch0013 retains the target for animation control and publishes one coalesced
visual sample in the next scheduler transient phase. The sheet, viewport and
native keyboard/strip regions use that sample. Publication avoids synchronous
notifier reentry and post-frame writes ahead of painted geometry. Disposal
cancels the pending callback and removes the listener. Interrupted drags start
at the displayed sample. Lock exclusivity and existing native/local viewport
boundaries remain intact; manual panning is retained.

Independent review caught a terminal detail before source freeze. The exact
Flutter `SpringSimulation` defaults `snapToEnd=false`; an unbounded animation can
finish above zero. The previous sheet hid at0.001. The correction normalizes
that cutoff centrally, so an invisible residual sheet cannot retain native input
regions. Open endpoints are normalized consistently as well. Tests cover finite
validation, clamping and deduplicated updates.

Starting repository commit `6ee0f132f301dcadf545dd7a1739a1828067d0a7`, tree
`20f3ed16a520d0e3b3869793664adebae7985739`.
Frozen executed source `d2a2ae7c3e54d1c8b28353357adfa70761f0ddef`, tree `1394e5606b4dbb6bea7a8ac74bf10c041a91a712`.
The following evidence commit is not the revision that produced these runs.
The previous turn was progress; this turn is also progress toward native mobile
usability, while real-phone acceptance remains incomplete.

Validation personally executed:

| Check | Result | Duration |
| --- | --- | --- |
| Actual-method regression, prior source |1PASS,9 expected FAIL|5.833s|
| Same regression, corrected source |10PASS,0FAIL|5.911s|
| Patch application check against retained matching shell source |PASS|0.003s|
| Real matching Flutter frontend compilation |PASS|23.508s|
| ARM64 AOT generation |PASS|20.007s|
| Changed-AOT generic ARM64 VirGL VM |PASS|103.927s|

The regression executes extracted production viewport, controller, scheduling
and native-layout methods with widget/geometry/scheduler adapters. It covers
opening/closing, panning, strip threshold, locked/closed state, interrupted drag,
coalesced tick publication/disposal and invalid/terminal values. It does **not**
execute actual Flutter rasterization or Riverpod lifecycle. The original test
adapter initially returned the haptics object for a state read; that fixture-only
failure remains retained. The final before/after pair uses the corrected identical
fixture, and its old-source failures are genuine semantic counterexamples.

The complete frontend build checks real framework types. All381
retained workspace files and pinned tool inputs were verified before build;
changed files were mounted as read-only overlays. Three changed-file hashes were
also read inside the live frontend container. A later query for all overlays
returned125 because the successful container had already exited; that observation
failure is retained and did not trigger a rebuild. ARM64 ELF identity was checked
with `readelf -h`. Native compositor, engine, kernel and runtime package bytes
were reused; only the shell AOT changed.

New AOT SHA256:
`e6434b805636598a937cfa69736012c213bd3e5b6c99f3607d495f7e4e292ba5`.
Reused compositor SHA256:
`40b1fc631643d602b57db2b988eb2caf8839e1e044890f7c9aa4ad0555bb8af0`.
Reused engine SHA256:
`a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`.
Denial `85b2303e2f09ae7b7b993641f90061a200f03d53`, Smithay
`812bd33259ff58810dadef6086d8385eeac1ca55`, generic Linux
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` remain the retained baselines.

One bounded changed-runtime VM passed Mousepad→Foot→Mousepad→Foot, the exact12
focused key press/release events for `test → tes → test`,212 terminal frames and
212 page flips with no reported render errors. App/session/container cleanup
passed. Direct captures confirm the visible text changes and final Foot prompt
with keyboard absent. The intermediate editor-dismissal capture still overlaps
the status area and contains a sliver of keys; its filename is not proof of a
settled close. This VM run is a real lifecycle/text regression, not a measurement
of every intermediate native routing region or a phone touch/Adreno test.

Protocol log SHA256 `63de5ffffbd288a1b9de59712e134b7ff57d685ccbb752fef825ee01dc8bd409`.
Serial log SHA256 `636cc10dc51ef0ffded622eaf1976637da68ce306dc25fe7e47b3f6dac3c55c7`.
VM initramfs SHA256 `b2808ca74bdcf9a63b3669a3f8b7b3a1bbd8e1094459e4bb93b07e2f12703688`.
The VM retained network isolation, read-only runtime/payload and existing
90s command/120s harness bounds. No further observer changes were required.

Space was reclaimed without losing unique bytes. The previous VM's60,090,129-byte
payload duplicates were removed only after streaming comparison with durable
copies, no open handles, and exact named-container absence. Current and prior
terminal frontend intermediates were losslessly compressed, decompressed through
a streaming hash, then removed from their raw paths; archive and restore mappings
are recorded in qualification. Restoring the old intermediate recreates its
original SHA256. Historical reports and artifact identities were not rewritten.
The3GiB host floor and96MiB VM staging reserve were retained. New runtime staging
uses read-only hardlinks to immutable retained inputs and the new AOT.

The [qualification JSON](2026-09-13-keyboard-geometry-qualification.json) records exact commands, source/tool and output
identities, build/resource limits, failures, VM evidence, retention/restoration,
and final repository validation. Raw runtime/logs remain private. No external
GitHub CI execution is claimed.

Unresolved, in priority order:

1. Native phone OLED/Adreno/touch qualification and installed package identity
remain absent for this Denial composition. Next bind the exact current native,
engine, AOT and package closure to existing graphics/touch trial inputs **offline**.
No candidate, admission, boot or phone contact is authorized by this task.
2. Automatic caret visibility remains NOT RUN. Native cursor rectangles exist,
but the shell's TextInputState wire payload lacks rectangle and window identity.
A separate coordinated transport or client-resize change is needed; guessing a
caret location or treating manual panning as automatic behavior is incorrect.
3. Settled editor keyboard dismissal and client-attributed presentation intervals
remain unqualified. Root VM apps do not qualify non-root mobile security.
4. Headless S06/R01 remain FAIL; all mobile physical rows remain NOT RUN.

No phone operation, signing, admission, claim creation/consumption, production
candidate, protected-storage mutation or history rewrite occurred. Accepted
server/rescue, ASUS slotA, V11 fallback and consumed claims were not altered.
The long-term goal remains active; the VM does not complete the phone.

Source-group changed files:

- `patches/denial-85b2303e/0013-align-keyboard-animation-input-geometry.patch`
- `patches/denial-85b2303e/README.md`
- `scripts/host/test-keyboard-animation-geometry.py`
- `docs/development.md`
- `docs/development-lessons.md`

The patch changes upstream `shell_state.dart`, `shell_controller.dart`,
`shell_input_layout_coordinator.dart`, `input_layout_publisher.dart` and
`edge_panel_layer.dart`. Evidence-group files are this report, its qualification
JSON, `manifests/artifact-sets.json`, `manifests/current-artifact.json`,
`configs/project-status.json` and the generated `docs/current-state.md` header.

The frozen active repository tier passed92 suites in135.824s:0FAIL,0BLOCKED,
0selected-suite SKIPPED and255NOT_SELECTED; three optional subchecks were SKIPPED.
The new ten-case source-dependent runner was executed explicitly and is not
misreported as part of that tier. Active memory peaked at331MiB with no swap.

Final metadata validation:

| Command | Result | Duration |
| --- | --- | --- |
| `python3 -O scripts/host/test-review-metadata-checkers.py Checkers` | PASS | 0.926s |
| `python3 scripts/host/test-mobile-status.py` | PASS | 0.080s |
| `python3 scripts/host/check-artifact-inventory.py` | PASS | 0.066s |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.040s |
| `git diff --check` | PASS | 0.032s |

The metadata suites exercised5 and8 cases. Inventory/current-status validation
passed again after adding the post-build gen_snapshot identity check. That tool
matched retained SHA256
`c0d9294287db1e33fea482e6f4f9907b763901f8a6c9bdf025b5791a991ebb01`.
The final qualification SHA256 is
`4b3e80352d856f64dcffb45ff08f343e5ed6b2baf01416a267bcdbe774ac5459`.
All508 prior artifact-set records, acceptance contracts and historical
current-state paragraphs are unchanged. Inventory validation explicitly does
not imply large/private artifact checks or physical admission.
