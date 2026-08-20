# Power/USB v9 incident: host-key and charging budgets did not fit rollback

ID/date: power-usb-v9 / 2026-08-20
Primary question of the cycle: Can accepted key-only SSH launch and capture the deferred side-port charging probe?
Earliest failed stage: target host-key rendezvous after exact NCM/NFS readiness and before runtime acceptance or probe execution.
Observed evidence: recovery, transfer, PREPARE/COMMIT, target NCM, exact `/30`, and NFS remained stable. Host-key pinning timed out after exactly 450 seconds; exact stock slot-A fallback and `FALLBACK_RETURNED` intent resolution passed.
Root cause: proven R4 timeout-lattice defect. V7 needed about 429 seconds from recovery boot to host-key evidence and had 223 of 600 watchdog seconds remaining. V9 retained approximately 30 MB of firmware for the deferred probe, exceeded the 450-second host-key deadline, and could not safely fit the 150-second probe in the remaining watchdog window.
Was the candidate consumed?: yes.
Was phone storage modified?: no.
Why existing host tests missed it: the central lattice covered target and rollback totals but the power profile still used a fixed 450-second host-key timeout and a 600-second rollback derived from the faster non-retained path.
New regression fixture/test: the power profile derives host-key timeout from its canonical target budget; rollback, server, and sampler bounds are validated as one generated lattice.
Systemic prevention change: V10 uses target 600, rollback 900, network server 1020, and sampler 960 seconds.
Successor prerequisites: preserve kernel/DT/recovery bytes, rebuild only the candidate-bound initramfs, pass exact composition checks, and run one deferred SSH charging observation.
