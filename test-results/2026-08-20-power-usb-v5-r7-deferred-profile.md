# Power/USB v5 incident: deferred host profile

ID/date: power-usb-v5 / 2026-08-20
Primary question: Does bundle-controller-first ordering cross recovery readiness and reach target transfer?
Earliest failed stage: bundle-controller host setup, before ready/transfer.
Observed evidence: exact recovery USB and continuity passed; the controller started immediately, then refused because `169.254.77.1/30` was absent and the exact `rog5-fallback-usb-ssh` profile was intentionally disconnected with `autoconnect=no`.
Root cause: proven R7 host profile-state contract mismatch. Host doctor requires deferred `autoconnect=no`; the controller requires an already-active profile with `autoconnect=yes`.
Candidate state: consumed; no bundle, PREPARE, COMMIT, NFS, or target execution occurred.
Fallback: recovery watchdog returned exact stock slot A and host cleanup passed.
Successor: v6 is authority-free pending an explicit, rollback-safe recovery-profile primer; no kernel or target bytes change.
