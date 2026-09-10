# Generation 36 QMP-UFS DT/MMIO-stage live result

Status: **PASS; consumed; never retry or flash**.

Generation 36 temporarily booted the exact signed RAM-only candidate once. Its
SM8350-only diagnostic QMP-UFS module bound to the active PHY, completed the
already-cleared clock/regulator setup, selected the reviewed DT binding, mapped
the PHY resources through `qmp_ufs_parse_dt`, and returned before clock-provider
registration, PHY creation, or provider registration.

- stable target NCM: 58.860 seconds after target start;
- unchanged post-module NCM control window: 12.294 seconds;
- maximum observed fallback temperature: 46.4 C;
- exact Alpine fallback, fallback profile restoration, and strict SSH identity:
  passed;
- phone-storage access: none;
- pstore/PMIC reset evidence: absent, therefore inconclusive.

The result clears DT binding selection and MMIO resource mapping. The next
discriminating boundary is QMP-UFS clock-provider registration. The claim is
irreversibly consumed and this candidate must not be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation36-live-20260812.zI0GtnYQ`.
