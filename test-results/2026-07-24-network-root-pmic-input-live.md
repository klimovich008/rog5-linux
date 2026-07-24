# Network-root PMIC RTC and power-key live report

Status: **v4 RTC rejected safely; v5 power-key dependency passed; exact fallback
restored**. The physical button-press observation remains pending. Nothing was
flashed and no phone storage or RTC value was written.

## Scope

This tier started from the accepted network-root v3 DTB. UFS, its PHY, RMTFS,
GPUCC, GPU, GMU, the Adreno SMMU, display, QMP/SuperSpeed, and secondary USB
remained disabled. USB2 recovery, read-only NFSv4.2, tmpfs/OverlayFS, strict
SSH, and the retained exitrd were unchanged.

V4 enabled exactly two existing DT nodes:

- `qcom,pmk8350-rtc`;
- `qcom,pmk8350-pwrkey`.

After the RTC result was rejected, v5 enabled only the power-key node and
required the RTC node to remain disabled.

## Offline gates

Both tiers were built from two clean source/output pairs. Their DTBs, staging
initramfs archives, ASUS 5.4.210 wrapper Images, header-v3 images, and unsigned
AVB images reproduced byte-for-byte. Each complete fourteen-file bundle
passed the inherited network-root semantic verifier.

Additional v4 checks required:

- the RTC and power-key nodes to be the only enabled nodes;
- no `allow-set-time`, NVMEM offset, or UEFI RTC property;
- the PMK8350 RTC module and built-in PM8941 power-key driver in the exact
  Linux 7.1.4 config/module archive.

Additional v5 checks required:

- exactly one overlay target and one `status = "okay"` mutation;
- PMK8350 RTC status `disabled`;
- PMK8350 power-key status `okay`, exact compatible, and `KEY_POWER` DT code;
- every prior storage, GPU, display, and USB recovery boundary unchanged.

Exact sizes and hashes are recorded in `manifests/artifacts.tsv`. Generated
artifacts remain outside Git.

## V4 live result

The first serial attempt was intended to use diagnostic systemd masks, but a
terminal cursor-response byte corrupted the separate environment export. The
payload itself verified and loaded, but the resulting target was correctly
classified as an unplanned normal-coldplug boot rather than a diagnostic
result.

The normal target passed:

- exact Linux `7.1.4-g7a5cef0db479`, running systemd, and zero failed units;
- OverlayFS `/` with exact read-only NFS lower;
- zero physical block devices and zero block-backed mounts;
- exact USB point-to-point address and carrier;
- 33 thermal zones with a 37 C maximum;
- zero fatal kernel signatures;
- one PMK8350 RTC and one PMK8350 power-key input device.

The exact source and live sysfs established the input naming:

- input name `pmic_pwrkey`;
- platform driver `pm8941-pwrkey`;
- DT compatible `qcom,pmk8350-pwrkey`.

The RTC read path was stable and advanced five seconds during a five-second
sample. It also set system time exactly from the RTC. However, the raw PMIC
clock was near the Unix epoch, leaving Linux about 56 years behind the host.
That is unusable for TLS, package management, logs, and automation. No RTC or
system-clock write was attempted.

V4 is therefore **rejected as a server-time source**. Enabling persistent RTC
writes or Qualcomm offset storage is a separate future tier requiring its own
recovery analysis and explicit authorization.

The race-safe network-root watchdog disarm completed after the safety gate.
A normal systemd reboot returned to the exact persistent fallback. The
non-autoconnecting fallback host profile then required its expected manual
activation; strict fallback SSH passed and all NFS, firewall, mount, kernel
thread, and temporary address state was absent.

## V5 live result

V5 used a non-terminal raw serial pipe. All nested payload hashes passed, and
the loader received diagnostic mode and a 900-second rollback timeout in one
inline command. Before hardware probing, the target proved:

- both systemd coldplug units `masked-runtime` through generator symlinks to
  `/dev/null`;
- RTC DT status `disabled`, no RTC module, and zero RTC devices;
- exact kernel/systemd/OverlayFS/NFS/USB state;
- zero physical storage and an armed rollback watchdog.

No power-key input device existed before module probing. Read-only modalias
resolution identified `qcom_pon` as the missing parent. This is expected
because `CONFIG_POWER_RESET_QCOM_PON=m` while the PM8941 input driver is built
in.

After the full base safety gate and verified watchdog disarm,
`qcom_pon` was loaded through the existing independent SysRq-guarded coldplug
probe. The 30-second settle gate passed with:

- running systemd and zero failed units;
- stable read-only NFS/USB;
- zero physical storage and zero block-backed mounts;
- no new warning, fault, or fatal signature.

The post-probe gate found exactly one input event with:

- input name `pmic_pwrkey`;
- driver `pm8941-pwrkey`;
- compatible `qcom,pmk8350-pwrkey`;
- `KEY_POWER` capability;
- wakeup enabled.

RTC remained disabled and unloaded. A temporary low-level logind inhibitor
protected two bounded physical-button observation windows, but no press event
was observed. Because no attended press was confirmed, physical switch/IRQ
operation is recorded as **pending**, not passed.

Normal systemd reboot with `qcom_pon` loaded returned to the exact persistent
fallback. Strict fallback SSH passed after activating the intentionally
non-autoconnecting host profile. Final cleanup proved zero NFS listeners,
exports, mounts, and threads; no temporary drop-zone rules or interfaces; no
network-root `/30`; no Fastboot or ADB device; and active ModemManager.

## Decision and next gate

- Keep v4 only as rejected RTC evidence; never flash it.
- Use v5 as the power-key-only hardware candidate; never flash it.
- Repeat one normal-coldplug v5 boot and observe a real short press while
  holding the low-level logind inhibitor.
- Do not map the button to display wake until the display/backlight tier
  passes. Registration alone cannot provide a visible indicator while DRM,
  panel, backlight, and LEDs remain disabled.
- Bootstrap system time from a trusted host/NTP source each boot. Do not
  enable PMIC RTC writes merely to hide the invalid raw-clock result.
