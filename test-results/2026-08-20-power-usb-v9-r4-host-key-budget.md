# Power/USB v9 incident: missing private firmware in rebuilt initramfs

ID/date: power-usb-v9 / 2026-08-20
Primary question of the cycle: Can accepted key-only SSH launch and capture the deferred side-port charging probe?
Earliest failed stage: target host-key rendezvous after exact NCM/NFS readiness and before runtime acceptance or probe execution.
Observed evidence: recovery, transfer, PREPARE/COMMIT, target NCM, exact `/30`, and NFS remained stable. Host-key pinning timed out after exactly 450 seconds; exact stock slot-A fallback and `FALLBACK_RETURNED` intent resolution passed.
Root cause: proven R2 deployed-composition defect, corrected by retained V9 pstore exposed during the next recovery boot. At target uptime 355.536 seconds, `prepare_shutdown_root` failed because the generic rebuilt initramfs contained no `/opt/rog5-charge-firmware` source. The later 450-second host-key timeout was downstream, not causal.
Was the candidate consumed?: yes.
Was phone storage modified?: no.
Why existing host tests missed it: the archive verified the probe script but did not require the private firmware payload that `prepare_shutdown_root` copies for deferred execution.
New regression fixture/test: private firmware is an explicit hash-pinned build input; archive verification requires the exact 29-file, 30,900,841-byte inventory.
Systemic prevention change: V11 embeds the verified WW33 ADSP firmware while retaining the measured V10 timeout lattice.
Successor prerequisites: preserve kernel/DT/recovery bytes, rebuild only the firmware-complete candidate-bound initramfs, pass exact composition checks, and run one deferred SSH charging observation.
