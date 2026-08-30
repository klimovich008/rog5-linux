# Native V11 Wi-Fi support — offline checkpoint

Wi-Fi is now an explicit standalone-server requirement. No Wi-Fi phone boot,
module load, radio activation, association or partition write occurred here.
V11 remains the live fallback. Package-keyring work is preserved separately at
`b9ceb26`; that helper is not yet deployed or integrated into boot.

## Implemented

- A module-only builder reuses V11's exact config, generated headers, symbols
  and vmlinux/BTF. The kernel Image is unchanged. The PCIe PHY's CONFIG symbol
  appears only in Kbuild, so its upstream object can be selected externally;
  required PCI/GENERIC_PHY APIs are already built in.
- The set includes PCIe PHY/power sequencing, MHI, QRTR-MHI, cfg80211/mac80211,
  ath11k, rfkill and crypto. QRTR-MHI is a firmware-control dependency and must
  not be omitted just because it is not a direct ath11k ELF dependency.
- All 16 new module files match between independent object builds. A final
  end-to-end builder run passed in **71.47s** and reproduced those files. All
  16 load in full-system QEMU with the exact V11 Image, without BTF/link errors.
  This proves module compatibility, not physical PCIe or radio operation.
- The native DT overlay reuses the historical wiring description, preserves
  UFS/USB/PAS memory and unrelated DT properties, and avoids forcing WLAN_EN
  low before the upstream sequencer takes ownership.
- Tests reject changed UFS/USB/IOMMU properties, unrelated nodes, old rail
  values, invalid selector windows and a missing BTF finalizer before building.

## Stock-derived electrical settings

Retained official WW33 vendor_boot SHA-256:
`86fcedbe5ebde8e5586c0d1404539f310b9b6bc5e9755bc117e001cb1eafb4e9`.
DTBO SHA-256: `531af0246723b15181649063fa5e2f5407eec7804e01485920694a8722e09ea0`.
All three SoC trees and all 20 composed overlays agree on the CNSS requests.

The requested digital 1.012 V and RFA2 1.350 V fall between the exact kernel's
PM8350 HFSMPS510 8 mV selectors. Copying them as fixed min=max constraints would
fail regulator initialization. The trial intervals retain those minima and
allow only the first available selector: **1.016 V** and **1.352 V**. RFA1 uses
the WW33 1.900–1.952 V interval. Upstream SM8450 HDK uses the same WCN6855 inputs
with digital 0.966–1.104 V and RFA2 1.350–1.400 V ranges, supporting this narrow
translation; that is not ROG5 hardware tolerance or runtime acceptance.

Candidate DTB SHA-256:
`d8ff02460c981c37bce105cce3f43a45c731d3645665b99517051f1f05b0613a`.
The first physical probe must retain USB rescue and stop p23 state cleanly so
all UFS nodes are read-only before activating Wi-Fi. Observe the shared rail
and UFS behavior; do not silently change the existing LDO parent graph.

## Firmware and remaining gate

The cached amss/m3/regdb blobs match the prior verified set. Board data was
recovered from [linux-firmware tag 20260622](https://gitlab.com/kernel-firmware/linux-firmware/-/tree/20260622/ath11k/WCN6855/hw2.0),
matching `9287fa8d14d915892666b03e9403135875d08371fd1438d2c6d9fe96ae71cf68`.
The signed wireless-regdb files also match the prior verified 2026.05.30 set.
Keep all binaries and raw vendor evidence private. Never guess a calibration
variant or bypass signed regulatory data.

Next is a fresh RAM-only test with the current native kernel/root, not the old
UFS-disabled Wi-Fi image. PCIe enumeration, firmware/BDF selection, association,
Wi-Fi-only SSH, reboot persistence and loaded charging remain unproven.
The native kernel exposes KEXEC, but the installed root has no kexec binary;
use verified recovery tools if that path is selected and preserve one-use
execution. No experimental boot-partition flash or V11 selector change.

The bounded Opus review was attempted but failed before review because its
OAuth session expired. No independent approval is claimed. Focused tests pass;
the active tier passed in 78.18s before the final selector-window correction.
