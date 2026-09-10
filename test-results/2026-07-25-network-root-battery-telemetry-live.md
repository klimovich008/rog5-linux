# Network-root v8 read-only battery telemetry — live result

Date: 2026-07-25

Result: **passed for read-only SM8350 battery telemetry**. Linux 7.1 read a
real aggregate battery snapshot through the ADSP PMIC GLINK path while UFS,
charging controls, UCSI, alt-mode, and every other remote processor remained
absent. A normal systemd reboot returned to the exact persistent fallback and
removed all target and host runtime state.

This result does not accept charging control, Type-C policy, sustained
current-direction accuracy, or the phone's dual-cell topology.

## Scope and safety boundary

- Temporary `fastboot boot` followed by an attended RAM kexec; nothing was
  flashed.
- Linux `7.1.4-g7a5cef0db479` with OverlayFS over a read-only NFSv4.2 lower.
- SCSI/UFS absent from the kernel, zero physical block devices, and zero
  block-backed mounts.
- PMK8350 RTC disabled and never written.
- ADSP was the only enabled remote processor.
- The battery-only PMIC GLINK diagnostic mode exposed one power-supply
  auxiliary device and suppressed UCSI and alt-mode auxiliary devices.
- The three SM8350 power-supply descriptors had no setter or writable
  threshold property.
- Exact stock ADSP firmware was copied only to target tmpfs. Private firmware,
  SSH material, and live logs remained outside Git and every boot artifact.
- An independent process-group SysRq watchdog was armed before firmware
  selection or any ADSP/PMIC module load.

## Reproducible candidate

The accepted ADSP candidate received one additional root node:

```dts
pmic-glink {
    compatible = "qcom,sm8350-pmic-glink", "qcom,pmic-glink";
};
```

Its semantic diff contains no child node or other device enablement.
Independent builds produced:

- telemetry DTB SHA-256
  `0fb6d415597630508779263693803af40f35496adee17e82995b0189b2aa9c78`;
- nested staging initramfs SHA-256
  `eba1c3b862a47f75fbbcca8baed064baa5ebad37f4f138094a143eef7d062863`;
- ASUS wrapper Image SHA-256
  `db280a590c99bc487f50a3dadbc1f81468481277afde007346d47b0e17b138e3`;
- raw header-v3 image SHA-256
  `f136e723ab131015cb38fc2ac56f47a5ced257b4072dae90bc42ed77ba73911f`;
- AVB-sized temporary image SHA-256
  `bed4381c0a5fefc76ac88a103b354df496acb16b790687569f492079690c58ef`;
  and
- battery-only PMIC GLINK module SHA-256
  `fa38f4f8d4ab428bd828601dc0c9805fcabe3d265afe3cdb0ba6ed977ac9c666`.

Both clean kernel wrappers, both nested initramfs builds, and both Android
image repacks were byte-identical. The complete bundle verifier passed with
private firmware and the diagnostic module supplied externally.

## IPC/PDR diagnosis

The first v8 telemetry run registered the expected battery, USB, and wireless
supplies, but every property returned `EAGAIN`. The probe then exited through
an unstructured `set -e` path; its still-armed watchdog safely reset the
phone.

Source review isolated two missing, manually blocked dependencies:

1. Linux 7.1 already links `ns.o` into `qrtr.ko` and initializes QRTR name
   service in-kernel. The stale Kconfig statement about a userspace daemon was
   not the blocker.
2. `qrtr_smd` must bind the ADSP `IPCRTR` RPMsg endpoint, and
   `qcom_pd_mapper` must answer the local `tms/servreg` domain lookup for
   `msm/adsp/charger_pd`. Only then can PMIC GLINK observe both its RPMsg
   endpoint and PDR service as up.

The two modules were audited from the exact clean Linux source, pinned by
archive and runtime hash, and loaded before PDR/PMIC:

- `qrtr-smd.ko` SHA-256
  `87e4797a61b75efd02cb52d47e013af5c28cee57affcf484f872ea5a1fb69178`;
- `qcom_pd_mapper.ko` SHA-256
  `7eac8fd204c74f0cae8d28a082dec54c8e30d55d420dfd2418052e7f5c9777f7`.

The transport only moves QRTR packets over the named RPMsg endpoint. The
mapper only serves domain-list metadata and acknowledges failure reports; it
contains no battery, Type-C, regulator, RTC, storage, remoteproc boot, or
remoteproc shutdown control path.

The next guarded attempt rejected an incorrect test assertion before PMIC
GLINK loaded. Live sysfs showed exactly one bound mapper device and revealed
the auxiliary driver name
`qcom_pd_mapper.qcom-pdm-mapper`, rather than the unprefixed directory assumed
by the assertion. The watchdog again reset the phone. The corrected
device-to-driver-symlink check and the full suite passed before the final
attempt.

## Accepted live run

The final run passed the complete corrected probe:

- ADSP remoteproc remained `running`;
- `qrtr_smd` bound exactly one `IPCRTR` endpoint;
- the SM8350 PD mapper bound exactly once;
- PMIC GLINK remained in `battery_only=Y`;
- exact supplies were `qcom-battmgr-bat`, `qcom-battmgr-usb`, and
  `qcom-battmgr-wls`;
- battery capacity, voltage, current, temperature, and status files were
  mode `0444`;
- USB input-current limit was mode `0444`;
- no charge-control threshold, UCSI driver, alt-mode driver, Type-C device,
  physical block device, or block-backed mount appeared;
- systemd, USB carrier, and the read-only NFS lower remained healthy;
- no new warning, call trace, IOMMU fault, remoteproc crash, or fatal kernel
  signature appeared; and
- the exact module allowlist and independent-watchdog teardown passed.

The one-time snapshot was:

| Property | Value |
|---|---:|
| capacity | 84% |
| voltage | 8.255 V |
| current | 81 mA |
| temperature | 30.3 C |
| status | Discharging |
| USB online | 1 |
| wireless online | 0 |

The simultaneous `Discharging` and USB-online values are recorded as raw
evidence, not interpreted as charging correctness. A longer comparison
against the fallback driver and physical power states is still required.

## Rollback and verification

After the probe disarmed its own watchdog, a normal `systemctl reboot`
returned to `5.4.134-qgki-perf-00001-g6c308144c23e`. Strict key-only fallback
SSH passed. ModemManager and the fallback `/16` profile were restored, while
the attended NFS export, listener, kernel threads, `/30`, temporary firewall
state, and all target tmpfs inputs were absent.

The repository's 31 tests passed after the live-informed correction,
including the VPN/hotspot test in an isolated privileged network namespace.
The full v8 telemetry bundle verifier also passed.

## Accepted and pending

Accepted:

- ADSP-to-PMIC GLINK service discovery through the exact QRTR/PDR path;
- one aggregate read-only SM8350 battery telemetry snapshot;
- absence of charging and Type-C control surfaces in the diagnostic tier; and
- normal rollback with complete host cleanup.

Still pending:

1. repeat telemetry across unplugged and known charging states;
2. compare current sign, status, voltage, and capacity with the fallback
   driver without writing charger controls;
3. characterize the dual-cell/aggregate topology and thermal behavior;
4. run a longer idle/load stability interval; and
5. design charging control as a later, separately reviewed and explicitly
   authorized tier.
