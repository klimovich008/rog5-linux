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

## Regulatory and Wi-Fi crypto follow-up

Full local CI for `e647ae7` passed in 444.63s; exact-head/merge/QEMU/publication
run `33307402616` passed. A subsequent exact-runtime replay found dependencies
that a module ELF dependency list does not capture:

- Without the SHA-256 Crypto API module, the valid signed regulatory database
  was rejected even though both upstream signing certificates were loaded.
- Without the AES module, allocating `cmac(aes)` failed with ENOENT. AES, CTR,
  CCM, GCM and the matching GF128 hash library complete the required crypto set.
- The default Alpine alias `aes → aes_generic` names an old module. The
  canonical runtime root list uses the kernel's `crypto-aes` alias instead.
- Assembly debug paths are normalized with KAFLAGS as well as KCFLAGS. All
  22 module files now match across two build paths; the V11 kernel is unchanged.
- The completed 22-module builder passed from fresh output in 91.60s. The
  focused tests and active tier passed (105.36s alongside that build).
- Dependency-list publication now propagates any modprobe failure instead of
  hiding it behind a successful sort. A regression fixture proves refusal.

With the resulting module set, QEMU accepts the exact signed database, loads
the test-only US regulatory domain, and allocates sha256, cmac(aes), ccm(aes),
gcm(aes), and ctr(aes). A one-byte-corrupted database is rejected and leaves
the world domain. No signature or regulatory guard was disabled. The test
country setting was confined to QEMU, which had no physical/network devices.

The bounded Opus review was attempted but failed before review because its
OAuth session expired. No independent approval is claimed. Focused tests pass;
the active tier passed in 78.18s before the final selector-window correction.

## Conditional WCN6851/hw1.1 backport

The exact source rejected hardware major1/minor0x10 with EOPNOTSUPP. The
[reviewed upstream addition](https://patchew.org/linux/20260601-sm8350-wifi-v1-2-242917d88031@oss.qualcomm.com/)
is now a module-only backport, retaining three vdevs. The author's follow-up
reports a firmware crash with four, so that later value was not copied.
Selection uses the hardware-reported revision, not a forced ASUS assumption.

`build-native-ath11k-modules.sh SOURCE KERNEL_KIT BASE_WIFI_SYMVERS NEW_OUTPUT`
copies and patches only the ath driver family. The source checkout and matching
config/vmlinux kit were mounted read-only. A measured build took22.202s, versus
the previous91.60s whole-Wi-Fi build. The kernel Image was not rebuilt.

Seven focused tests cover the added selector, firmware directory/vdev limit,
MSI layout, prerequisite refusal, dependency-export filtering and build flags.
An additional exact-source C harness executes the full WCN selector: pristine
source fails hw1.1, patched source passes518 revision/fuse cases including
existing hw2.x/QCA subtypes and unsupported inputs. A regression prevents
accidentally testing the earlier QCA6390 selector instead of the WCN selector.

The selected AHB module shares the changed hardware enum and is rebuilt along
with core/PCI. Its old exports must not be recycled as external dependencies.
That regression failed before the filter correction and now passes.

The first twins had identical compiled/linked objects but differing BTF type
ordering. The dedicated builder had omitted the existing builder's `JOBS=1`
override: Kbuild uses it for pahole separately from compile `-j`. Restoring it
and rerunning only final link/BTF made all four outputs byte-identical; original
parallel-BTF artifacts were preserved. No C objects or kernel were recompiled.
The build-command regression fails without serial BTF while retaining `-j4`.

The combined archive twins match:
`38e1dafb389e7ef1b63d8469cb33f68248de0bd7f570b7a73e86ffda60827628`.
Exactly three files differ from the rails-v4 package: ath11k, ath11k_pci and
ath11k_ahb. Every other module, metadata file and the existing common ath module
is byte-identical. Exact V11 Image QEMU loads all17 runtime roots plus AHB,
exports accepted BTF for all three changed modules, and passes the existing
crypto, regulatory and nft checks. This does not exercise real radio hardware.
The active tier passed in81.154s; full local CI was not repeated for unchanged
kernel/recovery/lifecycle inputs.

No candidate was created, signed or executed. No phone slot, storage or power
control was changed. V11 remains boot1b24ebf0-e4a1-466c-8197-13904886f5cf,
Good8.636V/30.1°C, with state/Tailscale services active. The S12 reset remains
unresolved. Hardware revision, ASUS supply mapping and correct hw1.1 firmware/
BDF inputs still require evidence before another phone candidate is issued.
