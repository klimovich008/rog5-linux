# Power/USB v12 incident: probe used obsolete reserved-memory paths

ID/date: power-usb-v12 / 2026-08-21
Primary question: Can the armed-rollback deferred probe reach ADSP/PMIC/UCSI after SSH?
Earliest failed stage: accepted-DT reservation validation, before ADSP startup or any PMIC/UCSI operation.
Observed evidence: NCM, NFS, systemd, runtime acceptance, key-only SSH, runtime masking, and armed rollback passed with 517 watchdog seconds remaining. The probe refused because `/reserved-memory/memory@cbc00000/reg` was absent. Exact fallback and intent resolution passed.
Root cause: proven R2 deployed-contract mismatch. The historical probe expected reservations from a different DT lineage; accepted V12 binds ADSP to `memory@86100000` and QRTR channels to `d7ef7000/d7f00000/d7f80000`.
Was the candidate consumed?: yes.
Was phone storage modified?: no.
New regression: exact accepted-DTB addresses, sizes, and `no-map` properties are asserted for ADSP and all three QRTR/channel buffers.
Successor: V13 with unchanged kernel, DTB, recovery raw, firmware, and rollback design.
