# Power/USB v19 incident: optional Type-C attribute and variable collision

ID/date: power-usb-v19 / 2026-08-21
Primary question: does the no-BTF PDR override advance PMIC GLINK/UCSI?
Earliest failed stage: Type-C snapshot after UCSI created `port0`.
Observed evidence: ADSP, PDR, PMIC GLINK, UCSI, NCM/NFS, systemd, strict SSH, runtime acceptance, and fallback passed. `port0/port_type` was absent.
Root cause: proven R3 capability-assumption defect plus R7 normalization defect. Linux 7.1 intentionally hides `port_type` when the driver has no `port_type_set` operation. The snapshot also reused global `mode` for a file mode and emitted `mode=644` instead of `mode=charging`.
Was the candidate consumed?: yes. Phone storage modified: no.
Regression: data role, power role, and power-operation mode remain mandatory; source-valid missing `port_type` is emitted as `absent`; a linked or unsafe optional attribute still fails. File permission uses a separate `property_mode` variable. Fixtures prove present, absent, linked, and writable cases.
Successor: V20 changes only the target probe/initramfs. Kernel, DTB, firmware, recovery, and modules are unchanged.
