# Arch Wi-Fi vendor contract checkpoint — HOLD

Date: 2026-07-27

## Outcome

The ASUS fallback exposes the Qualcomm WLAN endpoint at PCI
`0000:01:00.0`, and the protected Arch successor-v3 root contains the matching
ath11k modules, firmware, regulatory database, and network packages. This
corrects the earlier assumption that no WLAN PCI endpoint was present.

The Linux 7.1 board port is still **HOLD** for Wi-Fi. The live vendor device
tree has one unresolved WLAN I/O-supply phandle, the current mainline board
DTS does not describe the PCIe/WCN6855 PMU path, and no mainline radio probe
or association has run.

All phone inspection in this checkpoint was read-only. No module was loaded,
radio or NFS service was started, kernel was booted, or storage was changed.

## Guarded scope

The phone was reachable on the installed Alpine fallback:

```text
kernel=5.4.134-qgki-perf-00001-g6c308144c23e
uptime_seconds=39823.14
wlan0=absent
panel_brightness=0
```

The uptime proves this was not a fresh reboot. The fail-closed vendor-log
collector rejected the retained ring because it no longer included the boot
origin, so it published no new raw log. The separate
[vendor boot-log checkpoint](2026-07-27-alpine-vendor-kernel-boot-log-hold.md)
remains open.

## Test-first collector

The read-only
[`collect-vendor-wifi-contract.py`](../scripts/device/collect-vendor-wifi-contract.py)
collector was added only after its fail-first fixture. The fixture requires:

- one unambiguous `qcom,cnss-qca6490` node and matching PCIe root complex;
- exact supply, GPIO, pinctrl, and PCI endpoint output;
- exit status `2` and `contract_status=HOLD` for any unresolved supply;
- rejection of duplicate CNSS nodes, malformed input, and relative roots;
- no subprocess, radio, boot, network, or storage mutation surface.

The dedicated
[`test-collect-vendor-wifi-contract.py`](../scripts/device/test-collect-vendor-wifi-contract.py)
test passes and is delegated by the aggregate Linux-rootfs tool suite:

```text
PASS vendor Wi-Fi contract collector is deterministic, read-only, and holds on unresolved supplies
```

The implementation sequence is preserved in commits `7474213`, `1cb19b5`,
`cc9bc7a`, and `2b4baa0`.

## Live vendor contract

Streaming the collector over the pinned SSH connection, without installing
it, produced:

```text
cnss_node=/soc/qcom,cnss-qca6490@b0000000
cnss_status=okay
wlan_root_complex=0
pcie_node=/soc/qcom,pcie@1c00000
pcie_status=okay
pcie_domain=0
pci_endpoint=0000:01:00.0|vendor=17cb|device=1103|subsystem_vendor=17cb|subsystem_device=0108|revision=01|class=028000|driver=cnss_pci|power_control=on|runtime_status=active|enable=0
unresolved_supply=vdd-wlan-io|phandle=214
unresolved_supply_count=1
unresolved_reference_count=0
contract_status=HOLD
```

The endpoint identity is therefore exact: Qualcomm `17cb:1103`, subsystem
`17cb:0108`, revision `01`, bound to the vendor `cnss_pci` driver. PCIe
enumeration is proven even though no `wlan0` netdev exists.

The remaining live CNSS and PCIe contract is:

| Function | Provider or pin | Requested value |
|---|---|---|
| WLAN AON | `pmr735a_s2` | 976000 µV |
| WLAN DIG | `pm8350_s11` | 950000–952000 µV |
| WLAN IO | stale phandle `214` | 1800000 µV |
| WLAN RFA1 | `pm8350c_s1` | 1880000 µV |
| WLAN RFA2 | `pm8350_s12` | 1350000 µV |
| antenna switch | `pmr735a_l7` | 2800000 µV |
| WLAN enable / BT enable / switch | TLMM 64 / 65 / 153 | active/sleep pinctrl resolved |
| PCIe 0.9 V / 1.8 V / CX | `pm8350_l5` / `pm8350_l6` / `pm8350c_s6_level` | vendor request cells preserved |
| PCIe PERST / WAKE | TLMM 94 / 96 | default/sleep pinctrl resolved |

The original flattened tree and expanded `/proc/device-tree` both lack a
provider for phandle `214`. The expanded tree does contain the intended
`pm8350_s10` regulator, but under phandle `1435`; the collector correctly
refuses to infer that substitution.

## ASUS source resolves intent, not live structure

The hash-pinned extracted ASUS source identifies the missing semantic link:

- `lahaina.dtsi` maps `vdd-wlan-io-supply` to `S10B` and requests fixed
  1.8 V.
- `lahaina-regulators.dtsi` defines `S10B` as `pm8350_s10`, fixed at 1.8 V.
- `ZS673KS-EVB-overlay.dts` keeps the same regulator fixed at 1.8 V.

Source hashes:

```text
eebd12d6b2a793682b4cfbaa7539246aa66750e31c9c3df9a670982c54135169  lahaina.dtsi
a8a5574d2d98ac4fe16873ebfb78f64bce80407a2d2bec270e3a2a95886b6178  lahaina-regulators.dtsi
6570ebc9c6a5b603ab040f78e1adf5bfb86fb75fab40420f5fbbda645a957b8f  ZS673KS-EVB-overlay.dts
```

This is sufficient for a testable mainline candidate, but not for silently
repairing or activating the vendor tree.

## Protected Arch input readiness

The read-only successor-v3 root has exact kernel release
`7.1.4-g7a5cef0db479`. Its modules include `ath11k`, `ath11k_pci`,
`ath11k_ahb`, `mhi`, `cfg80211`, `mac80211`, QRTR, and RFKILL support.
`ath11k_pci.ko` advertises PCI ID `17cb:1103`.

Its current packages include:

```text
linux-firmware-20260622-1
linux-firmware-atheros-20260622-1
wireless-regdb-2026.05.30-1
iw-6.17-1
networkmanager-1.58.0-1
wpa_supplicant-2:2.11-5
wireguard-tools-1.0.20260223-1
dnsmasq-2.93-1
```

The WCN6855 firmware set is present under
`/usr/lib/firmware/ath11k/WCN6855/hw2.0/`. Its `board-2.bin` has eight board
records matching endpoint `17cb:1103` and subsystem `17cb:0108`.

```text
e12b23ddc4b8d2d2a10a651a5d6fdcd00f60fcae884d2cf5dad17627211fcdfd  amss.bin
9287fa8d14d915892666b03e9403135875d08371fd1438d2c6d9fe96ae71cf68  board-2.bin
0c590881870d0e6e98fc7d393ce05690e09287933b1b535e935bf5d98b77713f  m3.bin
e1b774b1feda4cab01f5a26089124059539fc31544ac34129dce45c8ff26d645  regdb.bin
2fb33ca0074db573e05ef7dd50bb45b63c0ff98b7e852e1105ebad536fae8e6b  regulatory.db
c941c08f51c93e46722293b85631604c3740d86c3de0c75f79aef50d2e919179  regulatory.db.p7s
```

These facts prove input availability only. They do not prove firmware boot,
calibration, regulatory acceptance, association, AP mode, or stability.

## Mainline delta

Upstream ath11k lists WCN6855 hw2.0/hw2.1 support from Linux 5.17. The
[ath11k PCI binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/net/wireless/qcom%2Cath11k-pci.yaml)
uses `pci17cb,1103`; the
[WCN6855 PMU binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/regulator/qcom%2Cqca6390-pmu.yaml)
requires an explicit `qcom,wcn6855-pmu` input/output regulator graph.

The repository's current `sm8350-asus-rog-phone5.dts` intentionally remains a
small serial-first base. It has no PCIe 0 enablement, WCN6855 PMU, or ath11k
endpoint. Editing that accepted base before a separately testable radio tier
would invalidate unrelated recovery and GPU contracts.

## Required next gate

1. Add an isolated, compile-only Wi-Fi candidate or overlay with tests first.
2. Encode and schema-check the PCIe 0 PHY, PERST/CLKREQ/WAKE pins, WCN6855 PMU
   ten-input/nine-output graph, endpoint identity, and all host rails.
3. Build twice in clean directories and require byte-identical kernel/module/
   DTB products plus unchanged accepted recovery and GPU inputs.
4. Only after offline acceptance, request fresh explicit authority for one
   RAM-only, client-only probe with bounded logs and automatic fallback.
5. Keep AP mode, credentials, provider WireGuard, NFS, throughput, thermal,
   and battery testing as later separately authorized gates.

No current result authorizes a radio activation, module load, boot, reboot,
NFS export, credential provisioning, or hotspot start.
