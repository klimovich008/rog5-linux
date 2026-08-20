# Power/USB v4 incident: host readiness order

ID/date: power-usb-v4 / 2026-08-20
Primary question: Can the existing mainline kernel sustain side-port NCM/SSH while exposing charging telemetry, then return to stock slot A?
Earliest failed stage: recovery NCM host readiness, before bundle transfer.
Observed evidence: the exact wrapper booted, recovery `1d6b:0104` and the physical USB continuity anchor passed, but `enp4s0f3u1u2` retained no `169.254.77.1/30` address for the complete 120-second readiness window.
Root cause: proven host lifecycle ordering defect. The lifecycle waited for the address before starting the existing bundle controller whose reviewed setup path configures that address.
Failure class: R7.
Candidate state: consumed; no bundle, PREPARE, COMMIT, NFS, or target execution occurred.
Phone storage: unchanged.
Fallback: the 300-second recovery watchdog returned exact stock slot A; host cleanup passed.
Regression: the real-output lifecycle fixture now withholds the host address until `bundle:start`; the controller must start before recovery readiness can pass.
Successor: generated v5 reuses the unchanged target/kernel/DT/initramfs bytes and changes only host ordering plus one-use identities.
