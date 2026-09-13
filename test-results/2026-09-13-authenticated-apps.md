# Authenticated launcher app switching and text

Offline ARM64 VirGL VM fixture. Phone physical rows NOT RUN; no phone, USB,
protected storage, signing, admission, claim or candidate operation.

Starting source 2b8bbe576e39dc8a4ff8342a340dc39e3ec83fd5,
tree 999dd1686842df478635813a5fe2b452c348a420. Source was frozen before the VM.
The preceding completed run qualified direct client launches and OSK text;
this run tests desktop-tile launches and app switching under real PAM/logind.

The host reuses the actual AppTextObserver, LauncherProtocol and EditorProtocol.
A dedicated duplex virtual serial channel carries attributed events through a
single writer. The host sends its exact per-run completion token only after
all fixed UI actions/captures and both protocol oracles pass. Guest teardown
requires that token. Final observation success also requires one zero exit from
each owned app. Compositor terminal counters, rendering errors, scope cleanup
and normal VM poweroff are separately required by the existing runner.

The guest desktop overrides invoke guarded supervisors; preparation starts no
apps. Existing Foot normal-close and process-reaping functions are serialized
verbatim into private guest RAM, avoiding a second lifecycle implementation.
Each supervisor retains PID/start identity and reaps its child. Prefix readers
finish before the sole event writer closes. Existing inner and outer deadlines
remain unchanged. Actual app timeout headroom is still a runtime question.

Two demonstrated implementation defects were caught before the VM: after an
observation exception, a later tick could resume and send an ACK; and a client
exit42 was collapsed to1. Both regressions now preserve the original failure.
An older service fixture's extraction assumed the editor branch came first;
its boundary was updated to exercise the unchanged service gate before either
observation branch.

Focused final Python -O checks:55 runner tests in11.926s,23 live apps tests in
1.484s,16 guest supervision tests in4.083s, all PASS. Host fixtures exercise
real sockets/FIFOs/processes and production parsers/actions, with synthetic
QMP/images and inert app/writer seams. These tests are not GUI or phone proof.
An independent read-only review found no demonstrated integration blocker.

The retained kernel, Denial executable, Flutter shell and authenticated package
closure were reused. Only the small VM probes/initramfs staging were built.
The readonly runtime and unsigned session archive do not identify installed
phone bytes. Historical failures and accepted rescue/server contracts remain.

First VM source c4d826bc4eaadbff4781befe7030d4d69f671a97 failed in196.033s
(wrapper; runner195.971s). Services returned0 in a17.474s monotonic bracket;
launcher tile signatures matched, and the first synthetic click was delivered.
The controller then encountered `/dev/vport0p1: Device or resource busy` because
virtio-console permits only one open and the event cat already owned the port.
No app owner, OSK event or completion ACK was admitted. PAM close/credential
removal, all-filesystem unmount and normal VM poweroff were observed, but the
user session and overall qualification remain FAIL. A transient early `/var`
unmount failure remains in the raw log; final shutdown unmounted all filesystems.

Final source f7441b7ecf09811fd09d282944362f862fa93648,
tree324d3613836d4f541fe9b160643b0b28477b529d, opens the port O_RDWR once during
preparation. A narrowly optional inherited-FD argument lets the existing event
cat duplicate that description while the parent alone reads acknowledgements.
Cleanup drains writers and then closes the last descriptor. Existing default
callers retain their path-based interface. Two production-function regressions
failed against the prior source and now pass even after the original sink path
is removed. Final guest suite20PASS4.903s; existing launcher10PASS2.241s; existing
evidence-channel5PASS0.115s with the retained real host Rust writer. No deadline,
Mesa/kernel/Flutter/Denial binary or GBM/fence policy was changed for the second VM.

Second VM: UI action/protocol oracles and inspected text captures PASS, but the
full qualification FAIL in305.480s (runner305.396s; bounded VM container292.378s
under300s). It launched Mousepad and Foot through desktop tiles, restored
Mousepad, delivered the exact12 focused OSK press/release events, visibly edited
`test → tes → test`, and restored Foot. The single-open transport carried118401
bytes, accepted one exact ACK and recorded the approved teardown. Foot exited0;
Mousepad's supervisor exited143, so the zero-exit gate correctly refused PASS.
Denial reported206frames/page flips with no recorded renderer error. PAM closed,
all filesystems unmounted and the VM powered down normally. Service readiness
returned0 across an18.951s monotonic bracket. These partial successes do not
replace the failed whole-session result or qualify startup reliability.

Source inspection then found a concrete completion race in close/cleanup:
finished could appear between the outer check and the owner check, which itself
refuses finished owners. A successful child completion could therefore become
parent failure and trigger cleanup of another closing app. Deterministic
production-function fixtures reproduce this interleaving. That establishes the
source defect; the second VM's sparse close diagnostics do not prove it caused
this particular143. Correct the recheck and add bounded atomic lifecycle records
before a successor, preserving the exact-zero requirement and original statuses.

Final source7b9cf4cbe4dc6a23039dcf5c2bcbf54abe6be900,
tree2703fe0fc08667efb5713748ef61411fb0a19afe. Two deterministic close-race
regressions failed before;22 guest tests passed after in4.741s (wall4.808s).
Live protocol23tests also passed in1.474s. Atomic lifecycle records now distinguish
actual normal-close status from cleanup signals. Zero-exit requirements are
unchanged. The successful successor does not retrospectively prove the cause
of the previous143.

Third VM: complete PASS in280.326s (runner280.252s; bounded VM step266.742s).
Service readiness returned0 across19.865s under the unchanged25s allowance.
Both desktop-tile launches, Mousepad→Foot→Mousepad→Foot focus sequence, exact12
OSK events and original full-resolution `test → tes → test` captures passed.
Foot's controlled terminal was visible on launch and restoration; its first
character is near the left screen edge, so broader terminal layout is not
qualified. Both atomic lifecycle records report normal-close status0 and
child_status0; both final supervisor exit records are0. The observer's completion
ACK was sent once and accepted before teardown. Denial reported204raster frames
and204page flips with no recorded rendering errors. Authenticated PAM/logind
session/scope cleanup, final filesystem unmount and normal VM poweroff passed.

No fourth VM was run. The exact kernel, compositor, Flutter payload and package
closure were reused throughout. This run qualifies the launcher-driven flow in
this generic authenticated VM, not phone touch, OLED, Adreno performance,
charging, suspend or startup reliability. Manual viewport panning is still part
of the test; automatic caret visibility and settled editor keyboard dismissal
remain open. Earlier FAIL results and current headless S06/R01 FAIL remain.

Full source/tree identities, exact commands, input/output/provenance hashes,
per-step deadlines/durations, before/after regressions, all three VM outcomes,
visual assessments and JSON/JUnit identities are in the
[qualification record](2026-09-13-authenticated-apps-qualification.json).
Raw logs and captures remain private. The added artifact set is a fixture with
no admission or execution authority; existing active/signed pointers and all
prior artifact records are preserved. No phone operation, protected-storage
mutation, production signing or claim/candidate creation occurred.

Next smallest authorized experiment: isolate whether the native editor caret
stays visible when the OSK opens without the fixed manual viewport pan, reusing
this authenticated VM input and capture flow. Phone display/touch/GPU trials
remain NOT RUN and require their existing exact-artifact authorized process.

The first final active-tier attempt failed after21PASS/1FAIL/79BLOCKED, with
255NOT_SELECTED and no suite skips, in26.321s. Its Rust container reported125:
image not known. A focused reproduction showed that systemd's inherited
XDG_DATA_HOME pointed at a launcher test's temporary directory, while ordinary
host execution still used `/home/deck/.local/share/containers/storage`.
The newly added fixture's shell-function mocks were bypassed by `timeout`, which
execed the real D-Bus activation updater and changed that one host variable.
Earlier fixture PASS results therefore have this isolation limitation.

The host manager's leaked variable was removed; D-Bus activation was restored to
the effective ordinary default `/home/deck/.local/share`. A fresh user service
confirmed the normal container store. No full prior manager snapshot existed,
so this is effective-default restoration, not a claim about the exact previous
string. No phone, credential, protected storage or other environment-setting
mutation was performed. The test fix uses private executable mocks, strict
argument/execution records and absent private session/system buses. Its final
24tests PASS in4.999s, wall5.070s. The unsafe fixture was not replayed.

Only this host test changed after the successful VM. The corrected integrated
source is recorded separately; runtime input hashes remain those of7b9cf4cb.
The first failed tier is retained and a second fresh tier is justified by the
demonstrated isolation correction. No fourth VM or compositor rebuild was needed.

Final active tier at c6fa7e079ebd86ed674133bf0068fc99ad74e0d0,
treeb20dc50ea410188cbd8a21f9603f70de9537b8f7:101PASS,0FAIL/BLOCKED/SKIPPED,
255NOT_SELECTED,150.355s. Three declared optional subchecks are SKIPPED.
This was the first integrated execution after the fixture isolation repair;
no GitHub CI or phone board build is claimed. The host manager's XDG_DATA_HOME
remained absent after the corrected focused suite and integrated tier.

Final metadata checks:5 checker regressions PASS1.003s;8 mobile-status tests
PASS0.023s. Inventory covers525sets,827registered/177tracked files and68small
tracked hashes. All524prior sets, all other current pointers, both acceptance
contracts and the historical current-state body remain unchanged. Ninety input
bindings across all three VMs were verified against their recorded Git revisions
or streaming durable-file hashes. All9owned VM/build containers are absent.
Final active peak memory519.4M, swap0B; free/home3302895616bytes, above3GiB.
The qualification lists every changed file; final publication commit/tree are
recorded in the private completion receipt after committing.
