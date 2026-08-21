# Power/USB v15 incident: service masks blocked normal systemd readiness

ID/date: power-usb-v15 / 2026-08-21
Earliest failed stage: minimal runtime acceptance after key-only SSH appeared.
Observed evidence: pre-switch masks prevented candidate module coldplug, but systemd never reached `running`; the probe was not invoked. Exact fallback passed.
Root cause: proven R3 precondition composition defect. Masking whole boot services was broader than the required module isolation.
Was the candidate consumed?: yes. Phone storage modified: no.
Regression: V16 keeps normal services and installs a volatile pre-switch `modprobe.d` blacklist only for top-level ADSP/QRTR/PMIC/UCSI autoload entrypoints; explicit direct reviewed modprobe remains available.
Successor: V16; kernel, DTB, firmware, recovery, and probe protocol are unchanged.
