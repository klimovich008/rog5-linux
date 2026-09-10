# Power/USB v10 pre-COMMIT postmortem abort

ID/date: power-usb-v10 / 2026-08-21
Primary question: Does retained V9 evidence disprove the timeout-only successor before target execution?
Earliest boundary: recovery PREPARED; V10 COMMIT was never sent.
Observed evidence: the recovery pstore snapshot contains `shutdown initramfs preparation failed; rebooting` at V9 target uptime 355.536 seconds, followed by restart. Archive inspection proved V9/V10 omitted `/opt/rog5-charge-firmware`; the exact private WW33 archive remained only on the host.
Root cause: proven R2 missing deployed input. The host interrupted V10 before COMMIT, cleaned NFS/firewall state, and the recovery watchdog returned stock slot A.
Was the candidate consumed?: wrapper/claim yes; target execution no.
Was phone storage modified?: no.
New regression: hash-pinned private firmware archive ingestion plus exact embedded inventory/byte-count verification.
Successor: V11; no kernel, DTB, recovery raw, or phone-storage change.
