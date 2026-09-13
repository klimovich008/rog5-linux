# Denial window-focus delivery repair — 2026-09-13

Offline source, ARM64 build and VirGL VM evidence only. No phone operation,
production candidate, signing, admission, claim, installation or protected-storage
mutation occurred. Cellular remains excluded. Headless S06/R01 remain FAIL;
all mobile physical rows remain NOT RUN.

The bounded diagnostic control showed Dart animation completion and focus send,
accepted native enqueue/drain, and core activation from Foot9 to Mousepad7 with
no keyboard grab. Clients received no matching focus events before shutdown.
The source's Flutter window-command path did not flush outgoing Wayland events;
its ordinary display callback flushed on readable client input. Idle clients
could therefore retain their old view of focus. Historical reports inferred
“native focus” from delivered client protocol; this investigation distinguishes
that evidence from the newly traced compositor core state.

Patch0012 flushes after early and final command drains and retries on empty or
locked passes. Authentication, command routing, bounded queues, engine-replacement
drains and error propagation remain intact. The pinned backend suppresses
per-client flush errors, including WouldBlock: API Ok proves an attempt, not
successful delivery. The extracted-production regression uses a bounded real
Unix socket adapter; it does not implement the Wayland wire protocol.

Source identities:

- Starting repository commit `63d4d39b4a187fd1a7609204837ae781aa443365`, tree
  `7f62a29c5249da9f184a165b3be311e99107fd68`.
- Diagnostic native/Dart source `0c126920a25763bd38eca78f5971b13f87325424`, tree
  `0a3bb06080b443cc1a203ed05ac81ebba5d82d81`.
- Native flush source `0f31e56bda1d692eaffa1bc6276bfb050379173e`, tree
  `117d6e193b303ad6a602b58bc48bd92d5e983119`.
- Denial `85b2303e2f09ae7b7b993641f90061a200f03d53`; Smithay
  `812bd33259ff58810dadef6086d8385eeac1ca55`. All12 Denial patches are recorded
  in order with SHA256s and separate frozen control/treatment source inventories.

Executed checks and builds:

| Check | Result | Duration |
| --- | --- | --- |
| Dart logger/animation/wire extraction | 3 PASS | 0.655 / 0.605 / 0.573 s |
| Native bounded trace helper | 6 PASS | compile0.598 s; test0.00265 s |
| VM prerequisite/opt-in regressions | 27 PASS | 0.192 s wall |
| Flush production extraction before | 9 PASS / 8 expected FAIL | compile0.745 s; test0.00359 s |
| Flush production extraction after | 18 PASS | compile0.697 s; test0.00356 s |
| Diagnostic Dart frontend / ARM64 AOT | PASS / PASS | 23.008 / 20.007 s |
| Diagnostic ARM64 compositor | PASS | 209.575 s |
| Flush ARM64 compositor | PASS | 211.575 s |
| Diagnostic VM | FAIL: absent client focus delivery | 102.739 s |
| Flush VM with original observer | FAIL: observer cross-client log-order rejection | 73.909 s |

The first flush treatment delivered Mousepad keyboard enter(serial23) at72.985526s
and Foot leave(serial23) at72.990908s. Those are independent client logs: their
printing order is not a global event-delivery order. The observer rejected the
valid reversed log order and aborted before the return capture, second switch
and normal terminal counters. Preserve that FAIL; container removal passed,
but graceful guest cleanup and terminal rendering counts are NOT RUN for this
aborted observation. The retained Foot capture directly shows a normally sized
terminal and prompt. No returned Mousepad screenshot was taken in that run.

Exact binary SHA256s:

- Diagnostic native: `fbb8850b60679c521db9791b06200eb39ae7c9782b6b6ee3f151a1ca51665c1d`.
- Flush native: `40b1fc631643d602b57db2b988eb2caf8839e1e044890f7c9aa4ad0555bb8af0`.
- Shared diagnostic AOT: `09a07cb992507e4ef3aab814fadb316aab7af51b4da520608856e52e91a93fcb`.
- Engine unchanged: `a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`.

Builds use locked offline dependencies, one Cargo worker, 3GiB/no swap and2CPU
limits. VM inputs retain the generic kernel, read-only runtime/payload, disabled
network, one host render-node exposure, 120-second harness bound and8MiB serial
bound. These results do not establish Adreno, panel, touchscreen, synchronization,
power or installed-phone behavior. Exact commands, input/output hashes and
per-check durations are in the companion qualification JSON; no GitHub CI run
is claimed as personally executed evidence.

The observer correction holds overlapping client focus pending until the old
client's matching-serial leave arrives; it does not advance the generation or
permit a focused capture while pending. Missing leaves, wrong serial/keyboard/
surface and unresolved transitions remain failures. Replay of the retained
aborted run establishes only Mousepad→Foot→Mousepad protocol delivery: the full
four-step sequence remains FAIL because the second switch was not executed.

Final observer source: `3acf8eaed9e46303551566b888a5ccb7989a668e`, tree
`21b93cd1198f7d56f955e42932422275fd24b207`. The parser regression passes26 cases
in0.09705 seconds. The old parser fails the new serial23 case.

The follow-up VM took102.940 seconds and remains **FAIL** for automated
observation. Both switch animations completed, both commands were accepted,
and core focus changed9→7→9 without a grab. Mousepad's return capture shows its
full title/menu/document; the later waiting capture visibly shows Foot's full
terminal prompt. Raw protocol contains both returns. However, an unrelated
partial Flutter write precedes the final Foot enter line:

```text
flutter[flutterFOOT_WAYLAND [00:01:15.849549] {Default Queue} wl_keyboard#21.enter(29, wl_surface#3, array[0])
```

The strict parser correctly ignores a line without its owned prefix at the
start. A private counterfactual replay removing exactly that stray fragment
recognizes all four visits; it is **not a new runtime PASS**, and original bytes
are unchanged. Normal terminal rendering reports95 frames/page flips and no
render errors. Shell exit, owned application cleanup and container removal PASS.
The earlier diagnostic control remains FAIL with80 frames/page flips; the
intermediate observer-aborted treatment remains FAIL without terminal counters.

The frozen applicable active tier passed92 suites in133.970 seconds:0FAIL,
0BLOCKED,0selected-suite SKIPPED,255NOT_SELECTED. Three optional subchecks were
SKIPPED. Source-dependent focused tests are recorded separately above. Metadata
checks ran after evidence publication and are recorded in the completion record.
No GitHub CI result is imported into these execution counts.

Remaining items, in order:

1. Isolate bounded client protocol evidence from unrelated shared-console writers.
   Test concurrent/partial writers, saturation, truncation, ownership, teardown
   and byte limits offline before one unchanged-binary VM. Do not relax the
   parser into accepting arbitrary embedded prefixes or rerun unchanged input.
2. Full automated two-app observation is still FAIL despite visible returns and
   traced focus delivery. It must complete its own strict transport and terminal
   checks before acceptance changes.
3. Automatic caret visibility, sustained application interaction and the wider
   mobile UX remain separate work. These two apps run as root in a VM fixture;
   this does not qualify the non-root mobile security profile.
4. Phone panel/GPU/touch/input/power qualification remains NOT RUN in this task.
   The next physical question still requires the existing exact-artifact,
   fallback and newly authorized coordinator process; no device action is
   implied by this offline evidence repair.

No superseded source finding was reinstated. All earlier artifact sets and
headless/mobile acceptance contracts are preserved byte-for-byte. Only the
generated current-state header changes; historical paragraphs remain intact.
Verified duplicate VM payload retirement reclaimed300,526,733 bytes this turn;
all unique source, binaries, runtime inputs, images, logs and captures are
retained. Restoration mappings identify identical durable copies. No project
history rewrite or recovery-artifact removal occurred.

[Machine-readable qualification](2026-09-13-focus-delivery-qualification.json)
contains exact commands, durations, source/build/runtime distinctions and hashes.
Raw VM logs and complete built runtime remain private local evidence.

Files changed in the source groups:

- `docs/development-lessons.md`
- `docs/development.md`
- `patches/denial-85b2303e/0010-trace-shell-focus-delivery.patch`
- `patches/denial-85b2303e/0011-trace-native-focus-delivery.patch`
- `patches/denial-85b2303e/0012-flush-flutter-window-command-output.patch`
- `scripts/host/qemu-launcher-protocol.py`
- `scripts/host/test-native-focus-trace.py`
- `scripts/host/test-qemu-launcher-protocol.py`
- `scripts/host/test-qemu-virtio-drm-prerequisites.py`
- `scripts/host/test-qemu-virtio-drm.py`
- `scripts/host/test-shell-focus-trace.py`
- `scripts/host/test-window-command-flush.py`
- `tools/denial-modifier-tests/native-focus-trace-tests.rs`
- `tools/denial-modifier-tests/window-flush-fixture.rs`
- `tools/qemu-virtio-drm/guest.sh`

Evidence publication also changes `configs/project-status.json`,
`manifests/artifact-sets.json`, `manifests/current-artifact.json`,
`docs/current-state.md`, this report and its qualification JSON.

Post-publication checks (all PASS):

| Command | Seconds | Exit |
| --- | --- | --- |
| `python3 -O scripts/host/test-review-metadata-checkers.py Checkers` | 0.912 | 0 |
| `python3 scripts/host/test-mobile-status.py` | 0.089 | 0 |
| `python3 scripts/host/check-artifact-inventory.py` | 0.073 | 0 |
| `python3 scripts/host/check-mobile-status.py` | 0.040 | 0 |
| `git diff --check` | 0.030 | 0 |
