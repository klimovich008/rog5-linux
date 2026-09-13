# Authenticated Denial OSK editor interaction — 2026-09-13

**Host implementation PASS; authenticated OSK runtime qualification FAIL.**
The corrected run stopped before apps at the GTK service-start deadline.

This qualification connects the retained pointer-only OSK sequence to the actual
local PAM/logind mobile session in a generic ARM64 VirGL VM. Phone OLED, A660,
touch, charging, suspend and installed integration remain NOT RUN. Historical
headless S06/R01 stay FAIL. No phone operation, protected-storage mutation,
signing, admission, claim or new phone candidate occurred.

Start commit0ef288a7c39661f45c252c5cdeeb1b3103a99884,
tree3210b6adbdfbe38831b6e793f244229e59c26314. The initial implementation was
b83e4caad455afa9cee59f35a4caa8b049b85a23, tree5e03eac81a0a9c8cc49b405a53e59a04b1c122d4.
The correction preserves the established `/tmp/rog5-text-probe.txt` filename
instead of changing the parser's title contract. Final source and tree are
recorded by the VM and integrated-tier receipts; source was clean at launch.
Publication changes only status/provenance/documentation.

The optional `--observe-editor` mode requires the existing combined session
archive, receipt and explicit host render node. It closes Foot normally, then
launches native Mousepad. A single guest writer streams attributed editor
protocol through its dedicated virtual serial port. Both the retained client
log and transport are capped at1MiB while excess input continues draining.
Only that virtual port is assigned guest mobile ownership; no host device or
runtime package permissions change. The existing absolute tablet device,
540×1224 scale1 output, raw UNIX VNC capture and fixed pointer sequence are
reused. No direct keyboard events or credential typing are permitted.

The live observer reuses the production editor protocol parser and existing
EditorObserver. It requires a titled, committed surface with stable keyboard
focus for1.5 seconds before input. It checks every event, including leave/reenter
within a single read, and fails on focus loss during input. Stream replacement,
symlink, disappearance, truncation, partial final lines and size bounds fail.
Action/capture completion and exact12 focused key events must both pass;
neither alone is sufficient. Pointer release is attempted before owned-container
removal. Rootless memory/CPU/network/log limits and65-second application,
120-second user,140-second PAM and300-second VM deadlines remain unchanged.

The first VM failed in236.005s. Services passed in18/0/1 seconds and Foot
closed normally with0. The real Mousepad title was
`~/rog5-text-probe.txt - Mousepad`, outside the retained oracle's filename
contract. No pointer actions, screenshots or keys occurred. Replaying its exact
log with only the established `/tmp` title substitution admitted the same
committed and focused surface; this is a diagnostic replay, not runtime success.
The guest user deadline expired, PAM close/delete/end returned0, but complete
session cleanup did not qualify. Executable-view restoration failed with
`/usr/bin` EBUSY, the temporary alias remained and shutdown recorded an init
SIGBUS panic. All those failures remain retained. No new kernel/driver cause is
inferred. The corrected runner checks shutdown/panic before reporting a failed
UI observation so that failure cannot conceal shutdown evidence.

The first focused commit was around guest00:03:01 and session logout around
00:03:30. The last client protocol record at00:03:12 is not a process-exit
measurement. Independent replay confirmed valid configure/ack, pointer and
keyboard availability, geometry and stable focus after the title correction.

| Executed focused check | Result | Seconds |
| --- | --- | --- |
| Live-process polling hook, original runner |1 ERROR, missing poll argument |0.003 |
| Final process ownership/finalization tests |5 PASS |0.633 |
| Actual awk transport and failed-Foot ordering |2 PASS |0.249 |
| Runner suite before finalizer-order case |43 PASS |9.551 |
| Final parser/observer tests |19 PASS |0.243 |
| Filename correction, transport and archive checks |4 PASS |0.257 |

Two intermediate suite failures came from source-extraction fixtures retaining
an unmatched optional branch, not from executing the VM. Their9.119s/9.361s logs
remain. Extraction boundaries were repaired and the affected tests passed.
The bounded read-only integration review caught relative mouse versus absolute
tablet mismatch before VM execution. The kernel already had builtin virtual
console and input support; no kernel rebuild was necessary.

The exact prior kernel, runtime package closure, Denial/Smithay/Flutter binaries
and unsigned session archive were reused. Generic Image SHA256:
`2b1c8d95f54dda28e772df82be54af7508b2ce84183f1b0024a7f14e3d5ce0fc`;
config `23af1f7083bb5607f65904ab6d46a101c5d67fd73a6ae10dd868877db16870af`;
Linux7a5cef0db4795d9d453a12e0f61b5b7634fc4d40, release7.1.4+, no modules.
Session archive SHA256:
`1ff417307c96bac90977b64a143e1a81b535d94a03109ca967c40e9b1f269d0c`;
Denial executable40b1fc631643d602b57db2b988eb2caf8839e1e044890f7c9aa4ad0555bb8af0.
Only the small VM helper compilation and initramfs staging were rerun.
No GitHub CI, phone board build or package authentication rerun is claimed.

The qualification JSON records full commands, per-step durations, source/tree,
input/output hashes, all VM outcomes and host JSON/JUnit summaries. Raw logs and
captures remain private. Publication adds a separate authenticated-editor pointer;
it preserves the preceding successful authenticated-session pointer, prior521
artifact sets, all other pointers, both acceptance contracts and historical state.

The corrected VM source42f6cfbffc999d7ef0c11c8d6be23b5d01194640,
tree3457c13d2f090a5279ee2c1c3fecb3b3be90b71a, failed earlier in166.822s:
service-start returned124 after21s against its20-second bound. The GTK portal
had consumed13.678s CPU over20.446s wall time when cleanup stopped it. No editor
or Foot was launched, no input was sent and no screenshots exist for this run.
PAM closed and logind removed the session; normal VM poweroff occurred without
panic, while the historical /var-unmount failure message remains. This does not
erase the first run's failed shutdown or qualify the corrected editor flow.

A read-only prerequisite audit found no retained system Fontconfig cache files,
679 font files, and configured cache paths under `/var/cache/fontconfig`, XDG
cache and `~/.fontconfig`. The fixture overlays `/var` with an empty RAM filesystem
and does not run fc-cache. Its fixed guest clock is midnight, earlier than the
font directory's recorded06:01mtime; prior GTK logs warned about future mtimes.
This establishes missing preparation and a timestamp mismatch, not the cause
of the observed service timeout. Next measure bounded guest font-cache work and
verify consumed caches before another interaction run. Do not increase deadlines
or disable required services to conceal an unmeasured prerequisite.

Integrated preflight initially refused in0.114s because the new test existed in
the declarative manifest but was omitted from the still-active shell selector.
No test body ran. Commit548ee8a0 adds that one selector entry; it changes none
of the VM-consumed input bytes. The final integrated run uses that clean source,
with the VM's exact inputs compared independently. This source distinction avoids
rerunning an unchanged VM merely to qualify test registration.

Final integrated source548ee8a0d1906e4f7377c47ca20412d828f2d3a1,
tree9c7471a2ddcbdf709b41abad7b6bd5505b1f45b8:98 PASS,0 FAIL/BLOCKED/SKIPPED,
255 NOT_SELECTED,146.052s. Three declared optional subchecks remain SKIPPED.
The44-method runner and19-method live-editor suites are included. The final
active tier ran once after the selector preflight refusal; no intermediate full
tier was run during VM prerequisite discovery. All VM-consumed source hashes
still match after the selector-only commit.

[Qualification JSON](2026-09-13-authenticated-editor-qualification.json) contains
commands, exact identities, failure evidence and bounded host/VM results.
The native-phone goal remains active and incomplete. The next smallest offline
experiment is bounded guest font-cache preparation/consumption measurement,
followed by the corrected authenticated text flow when service prerequisites
are qualified. Hardware tests remain outside current authorization.

Publication checks: metadata regressions5 PASS (0.926s), mobile status regressions
8 PASS (0.022s), inventory PASS522 sets/827 registered/177 tracked files with68
small tracked hashes checked, generated status and git diff --check PASS.
Large/private byte validation, admission and physical qualification remain
outside that inventory check. Separate preservation comparisons passed for all
prior521 sets, every prior artifact pointer, both acceptance contracts and the
historical current-state body. Owned containers are absent; free disk was
3,361,787,904 bytes. Qualification SHA256:
`8ad3203f1d023a5b9bd1b0d9257758a2affb52929d1ca38fba09f10939aece5b`.
