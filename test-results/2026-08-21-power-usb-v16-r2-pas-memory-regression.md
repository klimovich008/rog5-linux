# Power/USB v16 incident: deployed DTB lost the accepted PAS memory exclusions

ID/date: power-usb-v16 / 2026-08-21
Earliest failed stage: ADSP PAS metadata initialization after systemd, NCM, NFS, and key-only SSH passed.
Observed evidence: `qcom_scm_pas_init_image()` returned `-EINVAL` for the exact WW33 `adsp.mdt`; PMIC GLINK and UCSI were not reached. Exact stock slot-A fallback passed.
Root cause: proven R2 deployed-composition defect. The deployed DTB omitted `0xcbc00000+68 MiB`, `0xd8000000+8 MiB`, and `0xedc00000+288 MiB`, although retained live evidence had already proved those stock-owned exclusions are required to keep PAS metadata out of secure/vendor RAM.
Was the candidate consumed?: yes. Phone storage modified: no.
Regression: the active bundle build now invokes a focused DTB verifier; its hostile test rejects the exact V16 omission, wrong geometry, and wrong mapping policy before wrapper compilation. DTB and bundle-manifest hashes are generated from the canonical artifact record instead of copied into integration fields.
Successor: V17 adds only the three accepted reserved-memory nodes; kernel, initramfs, firmware, recovery, and charging probe are unchanged.
