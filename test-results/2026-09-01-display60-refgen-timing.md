# Display60 V4 REFGEN timing result

Result: **partial display fix; fallback PASS**.

- V4 reached switch-root and target SSH with safe battery/storage/NCM.
- DSI `vdda` and PHY `vdds` dummy-regulator warnings disappeared.
- REFGEN remained unavailable, DSI stayed deferred, PLL lock still failed,
  and fb0/backlight remained absent.
- V4 is consumed and must never be retried.

A no-reboot V11 probe built the same REFGEN driver for the running fallback ABI,
loaded it from tmpfs, and proved:

- platform device `88e7000.regulator` bound to `qcom-refgen-regulator`;
- regulator class exposed `name=refgen`;
- module removal succeeded with display disabled;
- no storage or persistent state changed.

The driver and DT are valid. The remaining defect is making a critical provider
available early enough for the built-in DSI host. V5 changes only
`CONFIG_REGULATOR_QCOM_REFGEN=m` to `y`; the display supply DT remains as V4.
