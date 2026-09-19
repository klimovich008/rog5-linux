# Monotonic failure journal and subshell EXIT correction — 2026-09-19

**Failure-journal collection is repaired and host-qualified. The corrected EXIT
placement has not run in a VM; portal timing remains unresolved.** No phone
operation, signing, candidate, admission, claim consumption, installation or
protected-storage mutation occurred.

## Source and executed checks

Starting source `f564b86affe5b512a30d5996daa7afafe1f29e78`, tree
`c45731f10e90016b4264e2561930f7c56464c273`.
Initial journal implementation and VM source
`1901bd6cbca98ac4b0f4fc60444963b8176032bb`, tree
`c630e5e18b51ca346bb857c4877471d8da8d2c72`.
Final EXIT correction `ff9966efb053cd66078d9bd9c37656e7e7dba9f3`, tree `475cccf4c700bc6f3362265e89577e2c8ad995c4`.
Only `tools/qemu-virtio-drm/logind-session.sh` and
`scripts/host/test-qemu-logind-runner.py` change executable/test behavior.
Publication metadata is a later revision, not the VM execution source.

The journal retains the current boot, existing systemd-logind/user@1000 filters
and 80-record limit. It now uses short-monotonic output, a 5s collection deadline
with 1s kill grace, line buffering, a 16 KiB encoded-output cap and excess draining.
It reuses the bounded capture/publish helpers; existing device diagnostic labels
remain unchanged. Journal timestamps are not exact unit transition timestamps.

Initial regression: three assertions fail and the unbounded journal stalls
past the fixture's 3s outer bound (3.177s total). The fixture was corrected to own
and kill its process group before repeating this failing-before check.
Initial corrected checks: 17 focused cases PASS 8.982s, four new cases under -O
PASS 0.615s, 111 runner cases PASS 23.312s; active tier 109 PASS in 179.210s.

The actual VM then exposed an untested exit path: a failing subshell function
with its own EXIT trap bypasses the parent's ERR trap. New production-function
regression fails against 1901bd6c (six cases, one failure, 0.439s). Journal/PAM-log
collection now runs once in the existing supervisor EXIT handler before mount
restoration. ERR retains its line marker. The triggering status survives journal
failure; success performs no failure capture. Existing mount cleanup is preserved.

Final checks: 25 focused cases PASS 8.583s; six journal cases under Python -O
PASS 0.616s; all 113 runner cases PASS 22.616s. Cases cover normal/subshell failures,
success, timeout retaining a prefix, incomplete stderr, journal failure,
oversize/forged markers, and unchanged mount cleanup. Exact retained ARM64 Bash,
under qemu-user, independently confirms ERR omission and EXIT logging, both
preserving status 42 (0.090/0.102s). This small check proves trap semantics, not
full journal transport or VM/phone operation.

Final frozen active tier: 109 PASS, 0 FAIL, 0 BLOCKED, 0 SKIPPED, 255 NOT_SELECTED,
180.203s. Three declared optional historical subchecks remain
SKIPPED: charging archive, trial-state ARM replay and rail-reader ARM binary.
Shell syntax and whitespace pass. These are personally executed local checks,
not imported CI. The unchanged 30s runner limit was sufficient; no runtime
startup/service/VM deadline was increased.

## Actual VM before the EXIT correction

The device wait began at boottime 207.38 and ended with status 1 at 216.80.
The 9.42s bracket includes command/capture scheduling around the unchanged 8s
udevadm budget. All 201 captured bytes survived, including an explicit device
initialization timeout. An ignored netns warning also appears in the preceding
successful wait; it is not established as causal.

The separately bounded 3s snapshot returned 124 while retaining 1028 bytes.
At 219.47s, card0 was a root:root character device mode 600; event0 had the same
ownership/mode at 220.14s. tty1 was root:tty mode 600; fuse was root:root mode 666.
Those four property queries completed; event1 metadata began before the timeout.
vport0p1 and the worker journal were not reached. These are later observations,
not exact timeout state or proof of a particular udev worker's failure.

PAM, Denial rendering, portal startup, app mapping/release and text entry were
NOT RUN in this VM. No session journal appeared because of the now-demonstrated
ERR/EXIT gap. The previous run's four frames/page flips remain historical evidence
and do not belong to this run. The hardware-database update logged 13.704s CPU
and 75.279s wall time; the root runtime contains no compiled hwdb.bin. This is a
real startup cost, not proof that it caused the wait or portal timeout.

VM result FAIL: application transport closed before approved teardown. QEMU
container command ended -9 after 241.622s; harness 283.592s, wrapper 283.667s.
Guest Power down and a /var unmount failure remain recorded. No RCU stall was
reported. All 38 input identities and runtime bytes/mapped metadata passed
post-run checks; 37 inputs match the previous device-diagnostics VM. Only the
supervisor script changed. Same kernel, Denial/Flutter, payload, resources,
network isolation, read-only runtime and single-TCG policy. Owned container absent.

No second VM was run after the EXIT fix. The retained 14 MB hardware-database
cache matches SHA-256
`f08f47c0b7054020ad7671e78d85b4d0633a4a88887f06e61e63085505484655`.
Its earlier target-tool generation/query passed; current integration is NOT
IMPLEMENTED. No cache or runtime bytes were changed during this audit.

[Qualification JSON](2026-09-19-monotonic-failure-journal-qualification.json) records the separate
source identities, exact commands, input/evidence hashes, counts and recipes.
Raw evidence remains in `rog5-portal-monotonic-20260919-r1` under local state.

## Next action and improvement

The bounded monotonic journal now runs from supervisor EXIT: 113 runner tests, the final active tier and exact ARM64 Bash semantics pass; this corrected placement has not run in a VM. The preceding VM explicitly timed out waiting for device initialization and captured partial root-only DRM/input permissions, before PAM/Denial/portals. Audit and integrate the retained matching hardware-database cache with bounded staging/consumer regressions before another controlled VM; the current runtime lacks hwdb.bin and rebuilt it for75.279s, but causation of udev/portal failures remains unproven. Preserve eight-second device,25-second service,145-second PAM and300-second VM deadlines. Portal timing, app release/text entry and real-phone qualification remain open; S06/R01 FAIL and phone physical NOT RUN unchanged.

Failure reporting (2026-09-19): a subshell function with its own EXIT trap can skip the parent ERR trap. An external-command fixture missed this; the actual readiness function reproduces it, and retained ARM64 Bash confirms the semantics. Collect failure evidence in the existing supervisor EXIT path, preserve the original status, and keep ERR only for an available line marker. A control failing before its intended observation can still expose a concrete defect; repair that defect offline before another VM. The partial device snapshot is a later observation and does not identify the exact state at timeout. Reuse the retained validated hardware-database cache only after matching its input/consumer and staging contract; a costly cold rebuild is not proof of the later timeout cause.

The preceding goal turn was progress (qualified device diagnostics and a mixed
VM result). This turn adds a demonstrated reporting fix and concrete startup
observations. The final active tier was repeated only after the VM exposed a new
source defect. No kernel/Denial/Flutter rebuild or unchanged VM retry was used.
