# Combined launcher and OSK text observation — 2026-09-13

**PASS for the combined automated VM flow and visible text changes.** The retained
ARM64 VirGL VM launched Mousepad, launched Foot, returned to Mousepad, entered
`test`, deleted the final character to `tes`, restored `test`, and returned to
Foot. Native client evidence records all four focus visits and exactly12 key
press/release events, with no unfocused keys. Terminal counters report208 frames
and208 page flips with no render errors. Session, application and container
cleanup passed. This is not phone GPU, OLED, touch or power evidence.

The keyboard-dismissal image is intermediate: the editor header overlaps the
status area and a sliver of keys remains at the bottom. It does not establish
fully settled dismissal, regardless of its filename. The final Foot capture
shows the keyboard absent. Explicit viewport panning was required; automatic
caret visibility remains NOT RUN. Client-attributed presentation intervals also
remain NOT RUN; global terminal counters are separate evidence. Root VM apps do
not qualify the non-root mobile session or its security.

Starting commit: `07b7f692ab47b810b5c2023a748df6db19e72362`, tree
`1a55abb341d05ee86f1340999ae84b8044f7f75e`.
Frozen executed source: `6d01f0c3bb0a881103213140145c6258e99fe93e`, tree
`5ee9d665372a6d0e16e805f51ecd48537f704f3d`.
The later evidence commit adds only this report and qualification/status metadata;
it is not the revision that produced the run.

The observer composes the existing launcher and42-step editor sequence through
the production action functions. Text steps refuse to proceed without current
Mousepad focus. The combined mode alone receives a96-command QMP budget; the
normal64-command limit and command allowlist remain. Actual use was84 requests.
The polling delay follows the next action deadline within10–200ms while retaining
200ms idle polling. This resolves the measured scheduling mismatch: nominal9.5s
editor actions otherwise take at least12.9s with fixed200ms polling. Original
90s shell and120s harness deadlines remain unchanged. Held-pointer cleanup is
preserved. Independent read-only source/gesture review found no blocker.

Validation personally executed:

| Check | Result | Duration |
| --- | --- | --- |
| `python3 -O scripts/host/test-qemu-mobile-observer.py` |51 cases PASS|2.799s|
| `python3 -O scripts/host/test-qemu-virtio-drm-prerequisites.py` |29 cases PASS|0.282s|
| Combined retained VirGL VM, `--observe-mobile-apps-text` |PASS|103.516s|
| `scripts/host/test-repository-linux.sh active` |92 suites PASS|133.820s|

The active tier reports0FAIL,0BLOCKED,0selected-suite SKIPPED and255NOT_SELECTED;
three optional subchecks were SKIPPED. Focused case counts and repository suite
counts are different units. No GitHub CI result is claimed as executed. Exact
commands, resource bounds, inputs, output hashes and JSON/JUnit identities are
in the [qualification JSON](2026-09-13-launcher-text-qualification.json).

No compiler, kernel, native compositor, engine, Dart AOT or writer rebuild ran.
Reused source and binary identities:

- Native source `0f31e56bda1d692eaffa1bc6276bfb050379173e`; binary SHA256
  `40b1fc631643d602b57db2b988eb2caf8839e1e044890f7c9aa4ad0555bb8af0`.
- AOT source `0c126920a25763bd38eca78f5971b13f87325424`; binary SHA256
  `09a07cb992507e4ef3aab814fadb316aab7af51b4da520608856e52e91a93fcb`.
- Writer source `d9666184de8df6da54df96a09fbfd3eaf71d9010`; binary SHA256
  `f055f339f7f37493b7fc092e9744feeaf14943cef3441375d726ab01d05003e4`.
- Engine SHA256 `a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`.
- Generic kernel SHA256 `34279d12dee925c4c58de9f49411c5e5f9fe85d016214e3939f80cd2f8b797f9`.
  Linux `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`; Denial
  `85b2303e2f09ae7b7b993641f90061a200f03d53`; Smithay
  `812bd33259ff58810dadef6086d8385eeac1ca55`.

New protocol log SHA256
`b8fe2a272610ae39aa60b732d5634c3f7aea264ead34c8dfc635774c23e61e1d`;
serial log `a3f466e62be76749abdde433d74dce792757ce4d495c31eeb63cbd7ec582578c`;
initramfs `daa517d073b3ada650b7c635cf50acaab3dd20afa840c69d2bfe494be1171460`.
Raw logs/runtime remain private; this initramfs is a VM fixture, not a phone
candidate. Network was disabled and runtime/payload mounts were read-only.

A verified60,090,129-byte duplicate payload from the previous terminal VM was
retired after streaming comparison against retained durable copies and checking
its exact named container was absent. Restoration mappings remain private.
Unique logs, captures, binaries, previous507 artifact sets, acceptance contracts
and historical current-state paragraphs are preserved. No phone operation,
protected-storage mutation, signing, admission, claim consumption, production
candidate, installation or history rewrite occurred. S06/R01 remain FAIL; mobile
physical rows remain NOT RUN. The real-phone goal remains incomplete.

Next smallest useful work is offline inspection of automatic caret visibility
and keyboard-close state, using this intermediate capture to identify the missing
settling condition. Do not repeat this unchanged successful VM or rebuild native
code just to reconfirm it. Exact phone source/package binding and physical
qualification require their existing safeguards and separate current operation
authorization.

Source-group changed files:

- `scripts/host/qemu-mobile-observer.py`
- `scripts/host/test-qemu-mobile-observer.py`
- `scripts/host/test-qemu-virtio-drm.py`
- `scripts/host/test-qemu-virtio-drm-prerequisites.py`
- `docs/development.md`
- `docs/development-lessons.md`

Evidence-group changed files:

- `test-results/2026-09-13-launcher-text.md`
- `test-results/2026-09-13-launcher-text-qualification.json`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `configs/project-status.json`
- `docs/current-state.md` (generated header only)

Final metadata checks all passed after evidence publication:

| Command | Result | Duration |
| --- | --- | --- |
| `python3 -O scripts/host/test-review-metadata-checkers.py Checkers` | PASS | 0.920s |
| `python3 scripts/host/test-mobile-status.py` | PASS | 0.079s |
| `python3 scripts/host/check-artifact-inventory.py` | PASS | 0.069s |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.043s |
| `git diff --check` | PASS | 0.031s |

The checker suites exercised5 metadata and8 mobile-status cases. The inventory
check covers508 sets and68 small tracked hashes; it explicitly does not claim
large/private byte verification or physical admission. Separate preservation
checks confirmed all507 prior sets, both acceptance contracts and the historical
current-state body unchanged. No full active-tier rerun was needed for these
evidence-only additions. Qualification SHA256:
`da656adbef6d74f5162117a2663fdf8f4f1d7bfb3e33b48a383d57082e76f1a8`.
