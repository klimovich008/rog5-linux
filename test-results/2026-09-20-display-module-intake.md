# Exact module archive intake — 2026-09-20

**Host-only inert staging. No phone, VM, signing, claim or boot candidate.**
Previous turn was progress (production module packaging). This turn advances its
consumer: strict archive verification and host materialization, plus reuse of
existing firmware inputs. It does not yet implement an admitted live controller.

Start `c4d516203ec52d6ff9232265ba9a119f7816acbd`, tree `3af0ade9e5a2e45ff6a3d2f031bd165a3a7aee4e`.
Frozen source `345de08ac583fcfb3fb1f1a7fae8016d5a325410`, tree `e7038e623c4a97976e8c5b05c2e2c4ca758a08e8`.
Input packaging source remains 2fdd26fc; board/kernel artifacts remain unchanged.

## Implemented and exercised

The new `stage-production-display-modules.py` requires a pinned offline packaging
qualification. It verifies both archive identity and the canonical USTAR member
headers, order, names, ownership/modes, sizes, hashes, embedded manifest, padding
and terminal record. It uses no archive extraction API. Unexpected files, links,
special members, path traversal, duplicates and concatenated archives fail.

Every member must verify before a private staging directory is created. Copies
are rehashed and the held input's identity is checked before exclusive atomic
publication. Existing destinations are preserved. Interrupted/failed copying
removes owned temporary files; it does not delete another writer's directory.
A directory-fsync error after publication remains an error while preserving the
complete output. Member modes are 0644 even under restrictive umask; the host
container directory is private. This is not a root-owned phone payload.

Review caught an unbounded read: `hashlib.file_digest` read to EOF after fstat,
so growth could exceed the stated size bound. The regression read 151,552 bytes
against a 20,481-byte ceiling and failed. The fix uses exactly the qualified size
plus one EOF byte before parsing. The full suite now passes. This was a new
intake robustness defect, not evidence that a retained archive was corrupted.

## Personally executed results

- Initial 28 semantic tests PASS, 2.542s; ownership/publication additions: 30 PASS, 2.723s.
- Growing-input regression before fix: expected FAIL, 0.278s; preserved log.
- Final 31 semantic tests PASS, 2.801s. Real inert ARM64 ELF archives exercise the
  production packager and intake. Identity/ownership attacks are host fixtures;
  no module is inserted and no physical inference is permitted.
- Selector/workflow tests:37 PASS, 0.704s.
- Actual qualified archive intake PASS, 0.119335s: 14 modules, exact
  hashes/sizes/modes/file set verified after staging. No kernel rebuild.
- Frozen active tier: 115 PASS / 0 FAIL / 0 BLOCKED / 0 SKIPPED suites,
  255 NOT_SELECTED, 206.024s. Three declared optional historical
  subchecks remain separately skipped. These are local checks, not GitHub CI.

Input archive SHA256 `37835ca7455c3f654b5f1de432cf91992550ef1767ed89b641bd3b15f26c87a1`;
packaging qualification `6bf0e36e208fc37c13b3ba0c3495a00ea34be540dc6bd7e4bc1d2a0a95b63d3f`;
staged embedded manifest `ec9e258cce646d6f0981adf6e7d08a3b7817260f2563acbc1f326a14c5e1b2f8`.
[Qualification record](2026-09-20-display-module-intake-qualification.json)
SHA256 `b161a838a5a8a6cf414e375eb7cb82071852d29a82ee97b9a06a5904552dae4f` includes exact command, all selected-suite durations,
member identities and JSON/JUnit/log hashes. Private evidence is under
`rog5-display-module-intake-20260920-r1` in the host state directory.

Focused command: `python3 -O scripts/device/test-stage-production-display-modules.py`
(with `Intake.test_growing_archive_hash_read_is_bounded` for the failing control).
Integration: `scripts/host/test-repository-linux.sh active` on frozen source.
Real staging used the new CLI with the retained archive, exact qualification hash
and a fresh host output; its full command is in qualification. Staging owner:
256MiB/no swap,1CPU,64tasks,120s;21.4MiB measured peak. Active owner:1GiB/no swap,
2CPUs,256tasks,600s; two workers. Scratch/output is disk-backed; 219 GiB was free.

## Firmware reuse and remaining integration

The retained linux-firmware `b2722d241309a1872446c1d00c2e812bad055f89` component is available.
Fresh streaming checks matched all three firmware files, LICENSE/NOTICE/WHENCE,
and both existing component archives in 0.007850s. Firmware
archives still hash to 83fab937d3b02b295ec42ea389fe13f189d8ac619f1c9241b4e674f7e69d1c53.
Their existing upstream ZAP source is `qcom/qcm6490/a660_zap.mbn`, materialized at
the SM8350 path; no new source/license conclusion is implied.

Current exact A660 source requests SQE/GMU names matching these retained files;
read-only fdtget on the hash-verified current composed DTB returned
`qcom/sm8350/a660_zap.mbn`. This is byte/name compatibility, not SCM authentication,
firmware execution or GPU qualification. Existing component layout is
`usr/lib/firmware`; the historical RAM controller used
`/run/rog5-native-wifi/firmware`. The successor must qualify its exact search path
and survival across switch-root; downloading or rebuilding identical firmware
would not answer that boundary.

Next: integrate the verified module inputs with that retained firmware closure
and exact board/endpoint binding in a successor controller, exercising
provider-before-consumer activation, one-use entry and independently owned cleanup
through offline fixtures. Do not derive runnable insertion order from symbol
closure. No live controller or test is armed. The eventual physical question is
whether the exact current production provider/panel path prepares and accepts
zero brightness under retained recovery guards; this task grants no operation.

Historical controller, current-artifact pointer, accepted baseline, signed
fallback and consumed claims remain unchanged. S06/R01 and earlier Denial VM
failures remain FAIL. Firmware-path/activation/target staging/physical: NOT RUN.

Implementation files:

- `configs/repository-tests.json`
- `patches/display-controller/README.md`
- `scripts/device/stage-production-display-modules.py`
- `scripts/device/test-stage-production-display-modules.py`
- `scripts/host/test-repository-linux.sh`

Metadata adds this report/qualification and updates existing artifact inventory,
structured status, generated current-state header and development lessons.

## Final metadata verification

- `python3 scripts/host/check-mobile-status.py`: PASS, 0.040s.
- `python3 -O scripts/host/test-mobile-status.py`: PASS, 0.081s.
- `python3 scripts/host/check-artifact-inventory.py`: PASS, 0.081s.
- `git diff --check`: PASS, 0.044s.

The status regression suite passed all eight cases. Inventory validation covered
595 sets; its large/private-byte verification remains NOT RUN, independent of
the specific module/firmware byte checks above. All 594 prior artifact rows, the
current artifact pointer, headless contract, historical current-state body and
sealed historical loader were checked unchanged. The integrated owner exited
with status 0 and is inactive. Its final peak-memory counter was unavailable
after collection; no peak is inferred from interim measurements.

Metadata files changed:

- `configs/project-status.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `manifests/artifact-sets.json`
- `test-results/2026-09-20-display-module-intake-qualification.json`
- `test-results/2026-09-20-display-module-intake.md`
