# Initial display/status-screen development

Result: **software path PASS; physical power-button press pending**.

The accepted 60 Hz display kernel now runs through persistent OverlayFS,
systemd, native Wi-Fi, Tailscale, healthd and strict SSH. Exact V9 boot
`c301ed1b-f760-4bb5-96f0-1b9b18f7069a` passed with:

- P2 attestation and zero failed units;
- DRM, `card0`, `renderD128`, `fb0` and backlight `ae94000.dsi.0`;
- native Wi-Fi `192.168.1.240/24` and Tailscale `Running`;
- status text containing time, Wi-Fi/IP and battery data;
- software screen on/off/on transitions while server services stayed active;
- Full/Good battery near 8.53 V and 30.2 C;
- exactly `sda` and `sda23` writable across 117 UFS nodes.

## Proven defects and corrections

1. The status installer rejected exact helpers persisted by an earlier RAM
   target. It now accepts only byte-identical, root-owned mode-0755 files and
   still rejects metadata or content changes.
2. P2 attestation ran before the status service blanked the OLED and failed
   with `a physical backlight is on`. The optional status payload now adds one
   transient `ExecStartPre=rog5-screen-toggle.sh off` drop-in to the P2 unit.
3. The display module archive omitted the QMP PCIe module from `modules.dep`.
   The probe now validates and loads that dependency-free module by its exact
   signed path.
4. The retained display ath11k module rejected the phone's WCN6855 revision
   `1.16`. Four ath/ath11k modules were rebuilt twice against the exact display
   ABI and BTF toolchain; twins matched, the full module root was reindexed,
   and native Wi-Fi then passed.
5. Diagnostic BusyBox initially failed after `switch_root` because its musl
   interpreter was outside `/lib`. The bounded diagnostic sender now invokes
   BusyBox through the retained initramfs loader.

## Power-button boundary

V10 enabled only the PMK8350 power-key DT property. The input did not appear
because `CONFIG_POWER_RESET_QCOM_PON=m` and `qcom-pon.ko` was not packaged.
Loading the exact dependency-free display-ABI module in RAM created one
`pmic_pwrkey` input and left the monitor active with the screen off. Repository
source now packages a validated PON-loader precondition for the power-button
service.

No physical press occurred during two bounded monitor windows. A connection
closed at the scheduled 900-second rollback boundary, so it is not evidence of
a button action. The next cycle must package the exact PON module and observe
one real press and release; no GPU, desktop or panel redesign is required.

No partition, GPT, slot, boot image or protected device data changed. Every
target candidate was RAM-only and one-use; slot A, installed recovery, V11 and
the persistent V10 fallback remain intact.
