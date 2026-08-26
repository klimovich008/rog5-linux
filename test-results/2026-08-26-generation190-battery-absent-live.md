# Generation 190 stable-wrapper battery capability result

ID/date: Generation 190 / 2026-08-26

Primary question of the cycle: Can the stable ASUS wrapper satisfy the strict
battery and thermal gate through exact type-based power-supply discovery?

Earliest failed stage: `S10_TOPOLOGY / temperature_battery_absent`.

Observed evidence: Exact guards, topology, p24 identity, and empty-signature
classification passed. No `type=Battery` supply existed. The target remained
untouched and returned to exact slot-A fastboot at 8714 mV with
`battery-soc-ok=yes`. Private evidence:
`/home/deck/.local/state/rog5-generation190-live-20260826-r1`.

Root cause (proven): The stable ASUS 5.4 wrapper does not expose battery
telemetry required by the destructive Stage-2 safety gate. This is a kernel
capability absence, not a path-name mismatch.

Failure class: R3 — exact recovery capability absent.

Was the candidate consumed?: Yes; permanently revoked.

Was phone storage modified?: No. No write window, mount, or watchdog disarm
was reached.

Why existing host tests missed it: Synthetic fixtures proved discovery logic,
but only hardware could prove whether this exact wrapper publishes a Battery
supply.

New regression fixture/test: Type-based battery discovery and finite failure
classification remain covered. No additional wrapper fixture can create the
missing hardware capability.

Systemic prevention change: Stop issuing ASUS-wrapper successors for Stage 2.
Reuse the already-proven mainline charging/UFS runtime where qcom-battmgr,
net-positive charging, temperature, and high-speed UFS all passed.

Successor prerequisites: One read-only mainline boot must prove exact p23/p24
identity, no block mounts, Battery/USB/thermal telemetry, and slot-A separation
before the existing clone executor is adapted or any p24 write is admitted.
