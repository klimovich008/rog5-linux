# Mobile pointer origin and bottom-caret probe — 2026-09-13

Input origin correction passes actual-method regressions and ARM64 shell compilation. The new VM run timed out at 300 s with no app-stream bytes or UI actions; bottom-caret runtime qualification remains NOT RUN.

## Source correction and regression

Frozen source `b9d6a5ab84a2cb4af2fbc4ee66b3f5a971464ddf`, tree `b417571906ac9e0cdad2d24de71c8d280bdc96b4`.
The prior source at 08a2811b retained an input origin error: Mousepad's committed
content geometry is `(26,23,540,1176)`. Painting subtracts this origin, but the
mobile input publisher omitted it. The retained earlier VM click at approximately
`(270.49,200.14)` arrived at `(270.49,152.14)` instead of the painted surface point
`(296.49,175.14)`. Prior successful typing was insufficient proof of tap alignment.

Patch0019 adds the content origin to the root input region. The executable
regression extracts the actual `_buildTexture`, `mapSurfaceRect`, input publisher
and matching Flutter `applyBoxFit` with value/widget adapters. The old source
fails precisely the two nonzero-origin round trips. All 14 cases pass after the
correction: origin 26/23 or 0/0, translation 0 or 367.2, visibility and root identity.
The 13 existing caret-policy cases pass; their translation assertion now subtracts
the surface origin explicitly. These tests are not Flutter rasterization or
native Smithay event delivery. Non-1:1 native pointer scaling remains unresolved.

The opt-in `--bottom-caret` mode keeps the normal empty-document test unchanged.
It creates 64 labeled lines in guest RAM, selects a low caret by pointer, reveals
the keyboard and retaps near its upper boundary. The bounded protocol tracker
requires a newly supplied cursor rectangle committed after the tap, matching
surface identity and committed geometry. A repeated commit of an old rectangle
cannot qualify. Parsing errors remain fatal through ACK and teardown. The
ordinary client 65-second lifetime and kill grace are unchanged.

## Build and tests

The 385-file workspace differs in only one source file; all 281 copied package
entries match retained inputs. All 666 hashes passed again after build.
Real frontend compilation took 23.509s;
ARM64 AOT took 21.508s. Existing native Denial,
VM kernel, engine and package diagnostics were reused. No full kernel rebuild
or phone candidate was generated.

AOT SHA256: `e1f8d492919cbdb38904398855d52815097443db89daf3ea5a9f442b15e67bf0`.
Unsigned VM archive SHA256: `bbf5bbb4e94d6334bb9c7f22cc45dccb51781a1c100a6dc215b354675089abad`.
The archive is a VM fixture with authority=none; source/build identities do not
qualify installation or hardware operation.

| Check | Result |
|---|---|
| Actual old/new paint/input methods | old2FAIL/12PASS; corrected14PASS |
| Existing caret cases | 13PASS |
| Focused mobile observer cases | 66PASS |
| New protocol tracker cases | 32PASS |
| Opt-in/default real UNIX-socket app observer cases (delegated) | 59PASS |
| CLI and guest preparation cases (delegated) | 15PASS |
| Exact patch application to retained source and resulting-byte comparison | PASS |
| Frozen active tier | {'PASS': 104, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255} |
| Bounded VM | FAIL, 314.442s |

Active tier duration: 173.645s. Declared optional subcheck
results:{'SKIPPED': 3}. These are locally executed results; no new
GitHub CI result is claimed. The active tier includes the new protocol test.
The explicit-source Dart method test is separately executed, not silently
included in a generic CI pass.

## Runtime findings and limits

The host command ended after314.442s including preparation and cleanup. Its300-second VM deadline expired, and the named container was removed and confirmed absent. No app events, captures, pointer actions or ACK occurred; there are no rendering counters or normal guest shutdown proof for this run. Early boot/session/user/observer inputs match the previously successful run. First independent snapshot was148.17s versus110.77s; PAM session journal was226s versus137s. Last snapshot245.49s showed PAM-open/user-manager/scope startup and a Bash child. User-session output is buffered in /run/pam-session.log until the child returns, so the current evidence does not locate the remaining delay. Cold-cache, host load and scheduler explanations are unproven. Source correctness is separate from this startup failure.

Reuse the exact compiled shell/native/kernel inputs. Add a bounded encoded PAM-log and child-state snapshot to the independent startup observer, then perform one diagnostic VM run under the unchanged300s deadline before retrying the bottom-caret interaction.

The prior icon/Mousepad137 failures and all older FAIL/BLOCKED/NOT RUN results
remain historical evidence. Diagnostics may affect timing. VM success does not
prove phone touch, OLED, Adreno, battery behavior or physical controls. No phone,
USB, production signing, admission, claim consumption, installation or protected-storage
operation occurred. Physical remains NOT RUN; S06/R01 remain FAIL. The full
native-phone goal is active and incomplete.

[Exact commands, source/artifact identities and results](2026-09-13-bottom-caret-qualification.json).

The next startup diagnostic is prepared privately at
`/home/deck/.local/state/rog5-bottom-caret-20260913-r1/startup-diagnostic-prep/`.
Eight host semantic cases passed, including timeout, payload bounds, forged
serial success markers and the original four-snapshot schedule. It encodes PAM
log and selected child metadata as hex so diagnostic payload cannot satisfy
serial success checks. This prototype was not staged in the failed VM or included
in the frozen104-suite integration result; integrate it before the next run.
