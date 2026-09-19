# Mousepad settings-sync diagnostic — 2026-09-19

**106 integrated checks PASS; diagnostic VM FAIL at its300-second deadline. Settings synchronization remains unobserved. Phone physical tests NOT RUN.**

## Source and purpose

Frozen source `5c1a6fb65b68d8da0b07351d9c2b71881387213f`, tree `043e256e501d794088c58776cdb7a341dbd35ba1`. The diagnostic distinguishes time inside the actual `g_settings_sync()` call from earlier/later Mousepad shutdown work. The exact0.7.0 upstream source invokes it during settings finalization; window destruction alone does not prove it was reached. The packaged version matches, but the complete package build recipe/source correspondence has not independently been reconstructed.

Changed files: `configs/repository-tests.json`, `scripts/host/test-logind-apps.py`, `scripts/host/test-qemu-logind-runner.py`, `scripts/host/test-qemu-logind.py`, `scripts/host/test-repository-linux.sh`, `scripts/host/test-settings-sync-diagnostic.py`, `tools/qemu-virtio-drm/logind-apps.sh`, `tools/qemu-virtio-drm/settings-sync-diagnostic.c`.

The opt-in C preloader records loaded/BEGIN/END using CLOCK_MONOTONIC and calls the real symbol exactly once, preserving errno. It writes only to an existing private0600, single-link regular file with bounded records; no stderr/FIFO dependency. It consumes its injection environment so exec children do not inherit the probe. The supervisor injects only into Mousepad, preserving owner, ACK, exit-zero, timeout and cleanup requirements. Diagnostic replay retains the2048-byte total cap. The runner checks/stages the exact AArch64 ELF and records both input and output identity; the ELF header check is not a loadability claim.

## Executed regressions and builds

- Old supervisor failed both new injection fixtures; corrected injection passed.
- A first close-diagnostic read failure42 was masked by the following successful read. The new regression failed before explicit propagation and passed after.
- The initial preloader leaked into an exec child without GIO, which exited125. The failing regression is retained; consuming injection variables fixed it. Final14 probe tests passed.
- Final supervisor42 tests passed25.181s; runner85 passed13.157s; diagnostic22 passed12.689s; selector37 passed0.660s. Python suites use `-O` where recorded. An intermediate fixture failed because it extracted the real launch expression without initializing its two new variables; its log remains preserved.
- Final ARM64 shared object compiled in0.465s with C11/O2/Wall/Wextra/Werror, oneCPU and128MiB/no swap: SHA256 `cd9ebf78923abf87de27651c762b82cd7c36e44434ccded4acd94d10bc3f9d4b`,70880bytes. Required GLIBC versions2.17/2.33/2.34. The earlier binary is superseded and was never used in a VM.
- Frozen active tier:106 PASS,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED;3 declared optional subchecks skipped.176.748s, peak532.3MiB, no swap. The terminal result is reused, not rerun for this evidence update. These are locally executed results, not GitHub CI.

Exact commands, timings, source/binary identities, failed-before logs and the integrated JSON/JUnit identities are in the [qualification record](2026-09-19-vm-settings-sync-qualification.json). Private evidence: `/home/deck/.local/state/rog5-mousepad-close-20260913-r1`.

## One VM execution

Same retained kernel, runtime, Denial, Flutter engine/shell and container images as the earlier control. Only small observer/helper artifacts changed; no phone kernel, Denial or Flutter rebuild. Overall command319.612s, QEMU deadline300.012s. Mousepad owner894/start29311 is observed and its initial Wayland registry exchange begins; neither app mapping/focus nor controlled close is qualified in this run. No probe-loaded/BEGIN/END record reached the observer. Such absence does not distinguish a failed preloader from a log that was never replayed.

The 300-second VM deadline fired after owned Mousepad launch at guest BOOTTIME293.11 and initial Wayland registry exchange, before mapping, controlled close or settings-sync log replay. No diagnostic BEGIN/END record was collected. This does not establish whether the preloader loaded or whether g_settings_sync was called; no GSettings/DConf causal inference is justified. Prior control mapping/focus PASS and Mousepad137 FAIL remain separate. Host container cleanup and absence passed; normal guest shutdown did not occur.

The prior control did reach both apps, exact ACK and approved teardown but Mousepad exited137. This new earlier timeout neither fixes nor reproduces that shutdown failure. Startup console messages show linker-cache generation and user-manager waits; elapsed service-console counters are not an exact critical-path measurement. Investigate preparation costs before another full UI attempt; do not increase grace or replace required clean exit with signal exit.

## Limits and next action

Prepare and verify reuse of exact runtime startup caches only if identity, target format and invalidation can be demonstrated. Retain startup-only mode to distinguish preparation from interaction. No accepted image, signed fallback, production key, admission, claim, phone, USB or protected storage was touched. S06/R01 remain FAIL. Native phone OLED/touch/Adreno Denial acceptance remains NOT RUN.

## Follow-up host experiment: exact ARM64 linker cache

The original materialized package tree, mounted read-only in an isolated networkless
bubblewrap namespace, permits the packaged static ARM64 `ldconfig -X` to generate
a63587-byte cache in0.166s (SHA256
`d94e98279622383bbbf642584d1721a4adfee436e7d23f1eb3b32b4e83ffc654`).
The target ldconfig lists1215 entries; the ARM64 dynamic loader resolves Mousepad
and Foot using71 and21 cache searches, respectively, exit0 and no missing libraries.
This proves host preparation/target consumption feasibility, not application
execution or faster VM startup. Commands, timings and identities are in the
[feasibility receipt](2026-09-19-linker-cache-feasibility.json).

Two preliminary attempts are preserved. The first refused a new mountpoint under
the read-only root. The second used the QEMU mapped-file view directly and generated
an unsuitable smaller cache: its host-visible symlinks are encoded regular files.
Only the original materialized tree supplies the real symlink semantics. No generated
cache has been admitted, staged into a VM or installed. Next implement narrowly scoped
cache identity/admission and RAM staging, preserving other first-boot services and
all deadlines; verify exact emulator identity rather than relying on binfmt setup.
