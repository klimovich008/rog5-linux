# Power/USB v11 incident: deferred probe preconditions were not composed

ID/date: power-usb-v11 / 2026-08-21
Primary question: Can the firmware-complete target run the deferred side-port charging probe after key-only SSH?
Earliest failed stage: deferred probe preflight, before ADSP, PMIC GLINK, battmgr, or UCSI activity.
Observed evidence: exact NCM/NFS, systemd, 29-zone runtime acceptance, and key-only SSH passed with 512 of 900 watchdog seconds remaining. The probe emitted no hardware evidence and refused because `systemd-udev-trigger.service` was not runtime-masked; source also required the outer watchdog to be disarmed. Exact fallback and `FALLBACK_RETURNED` passed.
Root cause: proven R3 capability/precondition composition defect. The deferred lifecycle invoked a probe whose older attended-gate preconditions it had not established.
Was the candidate consumed?: yes.
Was phone storage modified?: no.
New regression: the pinned SSH command runtime-masks both udev/module-load units, the charging-only probe attests the outer rollback watchdog remains armed, and a third pinned SSH command requests orderly reboot after exact evidence capture.
Successor: V12 with unchanged kernel/DT/recovery and firmware-complete target composition.
