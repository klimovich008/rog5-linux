# Generation 35 QMP-UFS clock/regulator-stage live result

Status: **PASS; consumed; never retry or flash**.

Generation 35 temporarily booted the exact signed RAM-only candidate once. Its
SM8350-only diagnostic QMP-UFS module bound to the active PHY, acquired the
driver's clocks and regulators, applied the existing reviewed regulator loads,
and returned before DT/MMIO parsing or provider creation.

- stable target NCM: 60.106 seconds after target start;
- unchanged post-module NCM control window: 12.002 seconds;
- maximum observed fallback temperature: 41.8 C;
- exact Alpine fallback, fallback profile restoration, and strict SSH identity:
  passed;
- phone-storage access: none;
- pstore/PMIC reset evidence: absent, therefore inconclusive.

The result clears the SM8350 QMP-UFS probe path through clock/regulator handle
acquisition and the reviewed regulator loads. The next discriminating boundary
is DT binding selection and MMIO resource mapping. The claim is irreversibly
consumed and this candidate must not be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation35-live-20260812.HzhDAoxA`.
