# Dedicated VM protocol channel — 2026-09-13

**PASS: native two-app launcher/switch observation in the retained ARM64 VirGL
VM.** Mousepad→Foot→Mousepad→Foot delivered all four client focus visits, with
100 frames/page flips, no terminal render errors and clean session/application/
container cleanup. Direct capture inspection confirms both applications at
launch and return. This does not prove phone OLED, Adreno, touch, input, power,
installation or mobile security. No phone operation occurred.

The previous goal turn was progress: patch0012 repaired outgoing Wayland flush,
and the retained VM isolated a subsequent evidence failure. An unrelated partial
Flutter console write preceded Foot's complete enter record, so the strict
parser ignored its missing initial prefix. That historical run remains FAIL;
its counterfactual replay was never promoted to runtime acceptance.

The correction uses one dedicated virtual serial port, explicitly numbered1 and
named `rog5.launcher`, with one guest FIFO collector as its only writer. A small
Rust helper emits each prefixed record with one write of at most4096 bytes to a
blocking Linux FIFO. This provides atomic records across concurrent clients.
Clients are capped at1MiB each; malformed/oversized input emits failure and is
drained without terminating the observed client with SIGPIPE. The native
forwarder preserves console output and sends the existing terminal boundary to
the evidence FIFO before forwarding its native line. The host independently
bounds `protocol/events.log` at3MiB and rejects truncation/missing terminal.
Original global frame counters and cleanup requirements remain separate.

The source and byte identities are distinct:

- Starting repository `c299602ddde85c56c4e596583964848c35e24da6`, tree
  `caf49cece24ad4c834e75d501783d7e353ef14b5`.
- Frozen channel source `d9666184de8df6da54df96a09fbfd3eaf71d9010`, tree
  `6a409c84d444c184b9ab30dbd33e3b0e5f3eed7a`.
- Rust writer source SHA256
  `0b78b2cc7e7a0a138f6fe2d5ce32cc0230c1a158592e5e7fa902c01b638eb717`.
- ARM64 writer SHA256
  `f055f339f7f37493b7fc092e9744feeaf14943cef3441375d726ab01d05003e4`,398104 bytes.
- Unchanged native compositor source
  `0f31e56bda1d692eaffa1bc6276bfb050379173e`; binary
  `40b1fc631643d602b57db2b988eb2caf8839e1e044890f7c9aa4ad0555bb8af0`.
- Unchanged diagnostic AOT source
  `0c126920a25763bd38eca78f5971b13f87325424`; binary
  `09a07cb992507e4ef3aab814fadb316aab7af51b4da520608856e52e91a93fcb`.
- Engine remains `a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`.
  Denial `85b2303e2f09ae7b7b993641f90061a200f03d53`, Smithay
  `812bd33259ff58810dadef6086d8385eeac1ca55`, generic Linux
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` and materialized runtime are retained.

Focused validation:

- 16 host Rust-helper cases and3 Rust unit cases PASS. Real concurrent FIFO test
 checks600 exact4096-byte records from4 producers; strace verifies one write per
 record. Tests cover short writes, EINTR, broken reader, caps/draining, invalid
 descriptors, missing/duplicate terminal, forwarding order and pipeline exit42.
 Compile0.534/0.541 seconds; host0.367 seconds; units0.00197 seconds.
- 5 guest channel/supervisor fixtures PASS: concurrent complete records isolated
 from a partial console write, terminal-before-exit ordering, missing writer,
 failed sink/reaping, and preserved client exit42. These exercise the actual
 shell functions and built Rust helper, with inert host apps and a FIFO sink.
- 28 harness prerequisites and26 existing protocol parser cases PASS.
- 10 existing launcher tests PASS in2.242 seconds. Shell syntax and diff checks PASS.
- ARM64 writer build PASS in1.540 seconds, with warnings denied, no dependencies,
 network disabled, immutable builder image,512MiB/no swap and1CPU bounds.
 No compositor, engine, shell or kernel rebuild was required.

One initial prerequisite test fixture omitted the already-required Flutter/
render-node flags and reached an earlier guard. Adding those inert arguments
made the intended writer guard test run; the initial fixture failure is retained.
The helper review also caught an fd-order issue before freezing: fd3 must be
opened before stdout can reuse a missing descriptor. Its regression passes.
Independent integration review found no blocking issue; explicit virtual-port
numbering was verified against the exact retained QEMU's device help.

One bounded VM run took103.559 seconds and passed the existing complete app-switch
sequence, including launcher tile checks, native mapping, each focus generation,
settled captures and normal terminal cleanup. Network remained disabled; runtime
and payload mounts remained read-only. The new writable host directory is only
the dedicated virtual-serial log sink. The preserved3GiB free-disk floor was
respected; the private wrapper reserves96MiB for the known60.1MB payload and
small helper/initramfs. Optional global presentation intervals are not
claimed: no global audits are forwarded to the protocol channel. Client-specific
presentation remains NOT RUN; terminal rendering counts and inspected pixels
provide their own separate evidence.

Evidence hashes:

- Dedicated protocol log:
  `f3e60d54881cde5ae74e1917d8ed0c30154a4e45d37dfc811f0ea7b268b04516`.
- Serial log: `a1606b9de1b49e65807fdb29a6b7b7c01bf5bbe662bd4295d6987cc8c7a80898`.
- Initramfs: `d9db0c2dfb9c8dd86f911330a87a4a50dc2d82998fbae9ef6696af6b5a1970e9`.

The inspected Mousepad captures show its full header/document and return caret;
Foot captures show the full terminal and prompt at launch and return. Text entry
was **NOT RUN in this observation**. These root VM applications do not qualify
normal non-root mobile sessions, lock security, or daily-driver usability.

Next smallest useful work: combine this launcher/switch path with the previously
separate OSK text/backspace/restoration observation, retaining automatic focus
and independent visible-text checks. No unchanged VM rerun or native rebuild is
needed just to repeat this result. Phone graphics/touch qualification remains a
separate exact-artifact, fallback-protected process requiring current operation
authorization. S06 andR01 remain FAIL; all mobile physical rows remain NOT RUN.
The real-phone goal is not complete.

A verified60,090,129-byte duplicate payload from the prior terminal VM was retired
only after streaming comparison against retained durable copies and exact named
container absence. Unique logs, captures, images, binaries, signed/recovery inputs,
all506 previous artifact sets and historical current-state paragraphs remain
preserved. No production candidate, claim, signing, admission, phone operation,
protected-storage mutation or history rewrite occurred.

[Qualification JSON](2026-09-13-protocol-channel-qualification.json) records exact
commands, input/output hashes, detailed tests, build and VM results. Full runtime
and raw logs remain private local evidence; no GitHub CI is claimed as executed.

The frozen active repository tier passed92 suites in133.968 seconds:0FAIL,
0BLOCKED,0selected-suite SKIPPED,255NOT_SELECTED. Three optional subchecks
were SKIPPED. New source/helper fixtures above ran explicitly; they are not
misreported as included in the active tier.

Source-group changed files:

- `docs/development-lessons.md`
- `docs/development.md`
- `scripts/host/test-qemu-evidence-writer.py`
- `scripts/host/test-qemu-launcher-evidence.py`
- `scripts/host/test-qemu-virtio-drm-prerequisites.py`
- `scripts/host/test-qemu-virtio-drm.py`
- `tools/qemu-virtio-drm/evidence-writer.rs`
- `tools/qemu-virtio-drm/guest.sh`
- `tools/qemu-virtio-drm/launcher-apps.sh`
- `tools/qemu-virtio-drm/launcher-evidence.sh`

Publication also changes `configs/project-status.json`, `docs/current-state.md`,
`manifests/artifact-sets.json`, `manifests/current-artifact.json`, this report
and its qualification JSON.

Post-publication checks (all PASS):

| Command | Seconds | Exit |
| --- | --- | --- |
| `python3 -O scripts/host/test-review-metadata-checkers.py Checkers` | 0.922 | 0 |
| `python3 scripts/host/test-mobile-status.py` | 0.082 | 0 |
| `python3 scripts/host/check-artifact-inventory.py` | 0.067 | 0 |
| `python3 scripts/host/check-mobile-status.py` | 0.040 | 0 |
| `git diff --check` | 0.028 | 0 |
