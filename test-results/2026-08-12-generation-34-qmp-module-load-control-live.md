# Generation 34 QMP-UFS no-bind module-load live result

Status: **PASS; consumed; never retry or flash**.

Generation 34 temporarily booted the exact signed RAM-only candidate once.
The UFS PHY device-tree node was disabled, so loading
`phy-qcom-qmp-ufs.ko` exercised relocation and driver registration without a
matching platform bind or probe.

- stable target NCM: 58.894 seconds after target start;
- unchanged post-module NCM control window: 12.008 seconds;
- maximum observed temperature: 47.8 C;
- exact Alpine fallback, fallback profile restoration, and strict SSH identity:
  passed;
- phone-storage access: none;
- pstore/PMIC reset evidence: absent, therefore inconclusive.

The result clears QMP-UFS module relocation and driver registration. Combined
with Generation 33's loss after insertion with the active PHY node, it places
the next discriminating boundary inside active platform binding or
`qmp_ufs_probe`. The claim is irreversibly consumed and this candidate must not
be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation34-live-20260812.b7dBEvme`.
