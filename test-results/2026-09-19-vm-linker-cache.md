# Exact-runtime linker cache and startup qualification — 2026-09-19

**Source and108 integrated checks PASS. Startup-only VM FAIL because the existing unit-timing query times out. Authentication, mediated devices, session cleanup and normal VM poweroff PASS. Phone tests NOT RUN.**

## Implementation

Source `bc3147d233e1597f31d83af0c875f14ec9a88ca6`, tree `26e6d4bb9459ae46008107b4a14f1188c84d20d1`. Changes:

- `scripts/host/prepare-qemu-linker-cache.py`: generate with the packaged ARM64 ldconfig under an explicitly bound host QEMU emulator in a networkless, read-only-root bubblewrap namespace. Verify every retained runtime byte, real symlink and mapped guest description before/after; bind exact guest metadata, tool/receipt/cache hashes and target-loader consumption. No mapped-file tree is executed directly. Admission rejects stale trees, metadata, receipts, preparer and cache bytes; staging uses new files only.
- `tools/qemu-virtio-drm/logind-linker-cache.sh`: optional private guest-RAM transaction. Cache, drop-in and verification marker are verified and published without overwriting existing paths. Only ldconfig gets an additional condition, effective after the final marker. Other first-boot services and /etc/.updated remain unchanged. EXIT/TERM/INT cleanup handles owned partial state; SIGKILL before the marker cannot suppress the service.
- `tools/qemu-virtio-drm/logind-boot.sh` and `scripts/host/test-qemu-logind.py`: opt-in `--linker-cache` admission before compilation, revalidation while staging, full input/output evidence, guest preparation only after the RAM /etc bind.
- `scripts/host/test-qemu-linker-cache.py` and `scripts/host/test-logind-linker-cache.py`: actual admission/staging and shell transaction regressions.
- `configs/repository-tests.json` and `scripts/host/test-repository-linux.sh`: mandatory selected regression suites. No guest, app, ACK, cleanup or VM deadline changed.

## Regressions and qualification

Initial mapped-metadata type mutation incorrectly passed; the retained before log records the failing assertion. Type validation fixes it. Independent review then demonstrated ordinary guest-mode mutation acceptance; the final record fingerprints actual mapped modes because owner-only extracted modes differ from guest package modes. A new executable-bit mutation test rejects the stale view. Encoded symlink lengths are checked before reading. The first marker layout crossed /etc and /run filesystems; an EXDEV fixture demonstrated failure and destination-filesystem staging fixes it.

Final focused tests:18 cache admission cases0.113s,21 guest transaction cases0.853s,85 existing runner cases12.849s,37 selector cases0.706s. Commands are Python `-O` invocations of the corresponding test scripts. Guest cases include partial input, malformed hash, symlink/hardlink/truncation, no-clobber, copy/hash/permission/publication failures, interruption and cross-filesystem marker staging. The runner suite ran once; changes afterward were confined to the new preparer/tests and then included in the frozen integrated tier.

Integrated `scripts/host/test-repository-linux.sh active`:108 PASS,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED;3 declared optional subchecks skipped.190.020s, peak617.2MiB, no swap. Source-only review found no remaining demonstrated blocker before the VM. These are local executions, not imported GitHub CI.

The final prepared63587-byte cache is SHA256 `d94e98279622383bbbf642584d1721a4adfee436e7d23f1eb3b32b4e83ffc654`, matching the earlier feasibility cache. Full preparation took31.308s, including two complete runtime verifications; target generation/inspection and Mousepad/Foot loader checks are separately timed in the receipt. The superseded first preparation took42.943s and lacks the final mapped-metadata binding; do not stage it. Target dependency resolution is not application or graphics execution proof.

## One startup-only VM

Exact command and identities are in the [qualification record](2026-09-19-vm-linker-cache-qualification.json). Host command283.476s, QEMU235.991s, exit0 and verified container cleanup/absence. Same retained kernel/runtime/Denial payload; Denial execution explicitly NOT RUN. The staged cache hash equals the admitted cache hash. GTK/font preparation, authenticated local session, user manager, mediated virtual devices, child execution, scope removal and normal poweroff are observed.

The nine-unit `systemctl show` timing command again returned124 with zero bytes under its existing8-second timeout. The host correctly retains overall FAIL. The complete packet is required to verify ldconfig's condition and exact critical-path timing; neither is inferred from missing console messages or successful authentication. This run proves the new preparation did not prevent startup/cleanup, not a quantified startup speedup. No UI retry was launched after the failed timing gate.

## Next action and limitations

Isolate the unit-timing query's execution/transport so a bounded observation can distinguish slow property retrieval from stdout buffering. Do not repeat an unchanged full UI run, extend app kill grace, or claim the unresolved Mousepad137 shutdown is fixed. Cache reuse remains VM-only, outside accepted phone artifacts. Runtime package authentication is inherited from the retained receipt, while byte/symlink/metadata checks were executed; package signatures were not rerun. Caller-owned immutable inputs/private guest filesystems remain the concurrency model.

Physical OLED/touch/Adreno Denial acceptance remains NOT RUN. S06/R01 remain FAIL. No phone/USB/SSH/fastboot, signed candidate, claim, production key or protected-storage operation occurred. Private raw evidence: `/home/deck/.local/state/rog5-linker-cache-integration-20260919-r1`.
