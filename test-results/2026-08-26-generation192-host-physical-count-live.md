# Generation 192 mainline runtime pass with stale host count

ID/date: Generation 192 / 2026-08-26

Primary question of the cycle: Does the current mainline charging/UFS runtime
reach local Arch and expose the post-Stage-1 read-only storage topology?

Earliest failed stage: Host runtime acceptance after authenticated SSH.

Observed evidence: Target runtime passed at 254.08 seconds with kernel
`7.1.4-gae717d919f87`, `physical_blocks=117`, two read-only backing mounts,
`/dev/sda23`, strict key-only SSH, zero blocked device/SCSI commands, zero UFS
errors, and no journal recovery. Exact stock slot-A fallback and intent
resolution passed. Private evidence:
`/home/deck/.local/state/rog5-generation192-live-20260826-r1`.

Root cause (proven): The host parser retained the pre-Stage-1 literal
`physical_blocks=116`. Target attestation and current geometry correctly use
117.

Failure class: R7 — host-only parser/current-state drift.

Was the candidate consumed?: Yes; permanently revoked.

Was phone storage modified?: No p24 write path exists in this target. p23 and
the local image were mounted read-only with `noload`.

Why existing host tests missed it: Their accepted runtime fixture duplicated
the same stale 116 value.

New regression fixture/test: Runtime parser fixtures now require 117 and reject
missing or changed current-layout counts.

Systemic prevention change: Current storage geometry is propagated into target
attestation and host acceptance together.

Successor prerequisites: Fresh signed target identity and AVB generation with
the exact same recovery/mainline payload bytes; focused host tests; exact
fastboot before one read-only diagnostics cycle.
