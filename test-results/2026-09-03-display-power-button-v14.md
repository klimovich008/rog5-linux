# Display power-button V14 checkpoint

Result: **runtime and input path PASS; physical press pending**.

## Primary question

Can one physical PMK8350 power-button press toggle the proven minimal status
screen without affecting server health, recovery, storage, power or SSH?

## Root cause and correction

V11 packaged the exact display-ABI `qcom-pon.ko`, but its confined button
service lacked `CAP_SYS_MODULE`. Moving the load to trusted pre-switch runtime
then made V12 fail at `runtime` without a discriminator. V13 added finite
classification and reported `pwrkey-module-name`.

Exact V13 BusyBox tests on the phone proved that `modinfo -F name` requires
`/lib/modules/$(uname -r)/modules.dep` even with an explicit module pathname.
Host QEMU had masked this dependency by exposing its host module index. An
empty mode-0444 index in initramfs tmpfs made the same real-ARM command return
`qcom_pon`. Commit `30adb55c` creates that bounded index before loading and
leaves the long-running service without module-loading capability.

Failure class: **R3 — exact recovery capability assumed**.

## V14 evidence

Boot `94a2e268-29de-4665-8e1b-6e5829ab48c5` passed:

- `runtime` and `switch-root`;
- kernel `7.1.4-rog5-display60-v1` and P2 attestation;
- systemd running with zero failed units;
- exact `qcom_pon` module and one `pmic_pwrkey` input bound to
  `pm8941-pwrkey` with `qcom,pmk8350-pwrkey`;
- active `rog5-power-button.service` with zero restarts;
- screen state `off`, brightness `0/1023`;
- Wi-Fi `192.168.1.7/24`, Tailscale, healthd and strict SSH;
- Full/Good battery at about 8.52 V and 30.1 C;
- exactly `sda` and `sda23` writable across 117 UFS nodes.

No physical press arrived during the attended monitor windows. The independent
rollback timer returned to accepted V10 boot
`d1668631-bd7d-4cd7-90ca-f48f19590d4b`; healthd and normal NCM were restored.
V11 through V14 are consumed and must never be retried.

No partition, GPT, slot, boot image or protected device data changed. A fresh
candidate is justified only when an operator is present to press the button.
