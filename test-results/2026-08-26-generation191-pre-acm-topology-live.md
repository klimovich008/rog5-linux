# Generation 191 historical recovery topology rejection

ID/date: Generation 191 / 2026-08-26

Primary question of the cycle: Does the proven mainline charging/UFS runtime
enumerate current p23/p24 read-only with valid battery and thermal telemetry?

Earliest failed stage: Stable recovery before ACM enumeration; target COMMIT
was never reached.

Observed evidence: Fastboot accepted the exact RAM-only wrapper. Recovery ACM
did not enumerate within the bounded gate, and stock slot-A recovery returned
as unauthorized ADB. The exact one-use claim is consumed. Private evidence:
`/home/deck/.local/state/rog5-generation191-live-20260826-r1`.

Root cause (proven / probable): Proven offline. The reused V54 recovery init
contains pre-Stage-1 userdata geometry and wrapper-topology assumptions, while
the phone now has p24 and 117 physical nodes. Current recovery source had a
mode-specific Stage-2 count but still retained 116 for normal full recovery.

Failure class: R2/R3 — deployed historical composition and exact recovery
capability did not match current storage state.

Was the candidate consumed?: Yes; permanently revoked.

Was phone storage modified?: No. The mainline target bundle never executed.

Why existing host tests missed it: The historical verifier correctly proved
the old deployed composition but did not claim compatibility with post-Stage-1
geometry.

New regression fixture/test: Recovery policy now requires 117 nodes for full
and Stage-2 modes and current p23 size `408997568` sectors. The full responder
ramdisk must be rebuilt and verified before a successor.

Systemic prevention change: Reuse the stable wrapper kernel cache, but rebuild
the recovery ramdisk whenever its storage-topology inputs change.

Successor prerequisites: Current full recovery clean twins, exact deployed
verification, fresh AVB generation/claim, and exact fastboot before one
read-only mainline attempt.
