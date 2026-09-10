# Power/USB v6 incident: stale thermal-count envelope

ID/date: power-usb-v6 / 2026-08-20
Primary question of the cycle: Can Linux sustain side-port NCM/SSH and expose charging telemetry?
Earliest failed stage: host runtime acceptance after target systemd and key-only SSH passed, before the power/USB probe.
Observed evidence: the target reported 29 thermal zones spanning 32700–35200 millidegrees C; all other runtime fields passed, including exact NFSv4.2 read-only lower, OverlayFS, eight CPUs, 10.37 GiB available memory, NCM, key-only SSH, zero failed units, zero fatal signatures, and the armed rollback watchdog.
Root cause: proven R7 host-only acceptance defect. The verifier required at least 30 zones without a hardware contract requiring 30; the current accepted DT has two TSENS controllers totaling 29 sensors.
Was the candidate consumed?: yes; COMMIT was claimed and target execution was proven.
Was phone storage modified?: no.
Why existing host tests missed it: the golden replay used the historical 33-zone result and explicitly treated 29 as hostile.
New regression fixture/test: the exact observed 29-zone, 32700–35200 millidegree record now passes; 28 and 129 remain rejected.
Systemic prevention change: runtime cardinality follows the accepted 29-sensor DT contract instead of historical enumeration count.
Successor prerequisites: keep target/kernel/DT/initramfs bytes unchanged, issue a byte-distinct wrapper generation and one-use v7 identity, pass focused/full/exact-head checks, and run only the deferred side-port telemetry question.
