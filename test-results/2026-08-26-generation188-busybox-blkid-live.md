# Generation 188 BusyBox `blkid` control-flow failure

ID/date: Generation 188 / 2026-08-26

Primary question of the cycle: Does a fixed 4-KiB prefix classify the p24
residual without writing storage?

Earliest failed stage: `S10_TOPOLOGY / arch_root_signature_size`.

Observed evidence: Exact p24 identity and all recovery guards passed. No
`SIGNATURE` record was emitted. The target reported `target_state=untouched`,
then returned to exact slot-A fastboot at 8715 mV with
`battery-soc-ok=yes`. Private transcript:
`/home/deck/.local/state/rog5-generation188-live-20260826-r1`.

Root cause (proven): The executor treated BusyBox `blkid` exit status as proof
that output existed. The exact sealed BusyBox 1.37 returns status 0 and emits
zero bytes for both `/dev/null` and a nonexistent path. Therefore the prior
claims that Generations 186/187 exceeded their output caps were unsupported;
the same terminal reason also covers a zero-byte capture.

Failure class: R3 — exact recovery/BusyBox semantics were assumed.

Was the candidate consumed?: Yes; permanently revoked.

Was phone storage modified?: No. No write window, mount, or watchdog disarm
was reached.

Why existing host tests missed it: They asserted the bounded command syntax
but did not replay the exact zero-output-success behavior through the executor
branch.

New regression fixture/test: `test-storage-layout-stage2-runtime.sh` supplies a
`blkid` that returns 0 with no output and requires the bounded capture to be
classified absent. The exact sealed BusyBox behavior was also reproduced under
QEMU before the source correction.

Systemic prevention change: Signature presence is now based on one bounded,
non-empty capture; command success is not an oracle.

Successor prerequisites: Focused runtime/contract tests and the active tier
must pass, the corrected executor must be sealed into clean twins, and only one
fresh read-only cycle may test whether p24 emits recognizable signature bytes.
