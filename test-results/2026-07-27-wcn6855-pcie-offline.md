# WCN6855 PCIe board candidate — offline acceptance

Date: 2026-07-27

Result: **PASS offline; HOLD for packaging and live use**

## Outcome

The first isolated Linux 7.1.4 Wi-Fi board candidate now passes its static,
mutation, schema, module, and reproducibility gates. It adds an opt-in
WCN6855 PMU and PCIe0 description over the exact accepted UFS-disabled
network-root v8 DTB. The accepted base DTB is not modified.

Two clean kernel builds in separate rootless Podman volumes are byte-identical.
The final module archive contains the Qualcomm QMP PCIe PHY, PCI power
control, WCN power sequencing, MHI host, generic MHI PCI, ath11k core, and
ath11k PCI drivers. Their module names, Linux 7.1.4 vermagic, dependency
metadata, WCN6855 device-tree aliases, and PCI `17cb:1103` ath11k alias pass
the dedicated verifier.

This is not a boot image and is not runtime acceptance. The phone was not
booted, rebooted, kexeced, flashed, or contacted for this checkpoint. No
module, firmware, radio, NFS/RPC service, VPN, hotspot, or credential was
activated.

## Test-first sequence

The failing contracts precede their implementations:

| Boundary | Fail-first commit | Passing implementation |
|---|---|---|
| isolated board/DT contract | `5af268b` | `02f3364` |
| reproducible kernel/module contract | `dbc8506` | `cdbbc19` |

The board contract rejects missing host or endpoint rails, a changed base
DTB, output aliasing the base, unverified calibration/link-speed properties,
and any phone-control or storage-write command. The kernel contract requires
the exact source commit, all required config symbols and modules, matching
aliases and vermagic, deterministic archives, distinct clean build
directories, and byte-identical accepted outputs.

## Board description

The tracked overlay is
[`dts/qcom/sm8350-asus-rog-phone5-wifi.dtso`](../dts/qcom/sm8350-asus-rog-phone5-wifi.dtso).
It is intentionally separate from the accepted recovery/GPU board base.

It describes:

- `qcom,wcn6855-pmu` with all ten host inputs and ten PMU LDO outputs;
- the endpoint `pci17cb,1103` with all nine binding-defined output supplies;
- WLAN enable, Bluetooth enable, and switch-control GPIOs 64, 65, and 153;
- antenna control GPIOs 141, 142, and 144;
- PCIe0 PERST, CLKREQ, and WAKE on GPIOs 94, 95, and 96;
- SM8350 PCIe0 and its QMP PHY, with L5B and L6B PHY rails; and
- the source-backed S10B 1.8 V, S11B 0.952 V, S12B 1.35 V, PMR735A S2E
  0.976 V, and S1C 1.88 V host rails.

The candidate does not guess a maximum PCIe link speed, calibration variant,
board-data variant, or Bluetooth runtime behavior.

## Device-tree validation

The immutable base is the accepted network-root v8 telemetry DTB:

```text
0fb6d415597630508779263693803af40f35496adee17e82995b0189b2aa9c78
```

The overlay builder produces the same merged DTB twice and leaves that base
byte-identical. The merged candidate identity is:

```text
15acdcd6fad910f105047ef53de08b47cafadbbf94827e123931408d92310d89
```

Validation uses clean Linux source commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`, dtschema `2026.6`, and local
rootless image ID
`fc57d729064443c13c8c01eb1211867f438471f371875bb9b9e1c954772ffe39`.
The validator runs with container networking disabled and limits validation
to the relevant upstream bindings:

- `qcom,qca6390-pmu`
- `qcom,ath11k-pci`
- `qcom,pcie-sm8350`
- `qcom,sc8280xp-qmp-pcie-phy`
- `qcom,rpmh-regulator`
- `qcom,sm8350-tlmm`

The processed schema hash is
`070dd0ee64be8c6e9747b30e1a6ea8b4c32c8e00e66a285e65e01b88badef18d`.

## Kernel and modules

The Wi-Fi fragment layers after the accepted mainline and network-root
fragments. It deliberately re-enables the QMP PCIe PHY only for this opt-in
tier and requires:

```text
CONFIG_PHY_QCOM_QMP_PCIE=m
CONFIG_PCIE_QCOM=y
CONFIG_PCI_PWRCTRL=y
CONFIG_PCI_PWRCTRL_PWRSEQ=m
CONFIG_POWER_SEQUENCING=y
CONFIG_POWER_SEQUENCING_QCOM_WCN=m
CONFIG_MHI_BUS=m
CONFIG_MHI_BUS_PCI_GENERIC=m
CONFIG_ATH11K=m
CONFIG_ATH11K_PCI=m
```

Both clean builds used Ubuntu clang 18.1.3, four compile jobs, one serialized
`pahole` job, deterministic Kbuild identity/timestamp, `PYTHONHASHSEED=0`,
read-only source/repository mounts, separate output volumes, rootless Podman,
and disabled container networking. Each completed from an empty output
directory.

The required installed modules are:

```text
drivers/phy/qualcomm/phy-qcom-qmp-pcie.ko
drivers/pci/pwrctrl/pci-pwrctrl-pwrseq.ko
drivers/power/sequencing/pwrseq-qcom-wcn.ko
drivers/bus/mhi/host/mhi.ko
drivers/bus/mhi/host/mhi_pci_generic.ko
drivers/net/wireless/ath/ath11k/ath11k.ko
drivers/net/wireless/ath/ath11k/ath11k_pci.ko
```

The power-control module advertises device-tree endpoint
`pci17cb,1103`, the sequencer advertises `qcom,wcn6855-pmu`, and ath11k PCI
advertises PCI ID `17cb:1103`.

## Reproducible artifact identities

The complete nonsecret record is
[`manifests/wifi-pcie-v1.tsv`](../manifests/wifi-pcie-v1.tsv).

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| merged candidate DTB | 107,038 | `15acdcd6fad910f105047ef53de08b47cafadbbf94827e123931408d92310d89` |
| final `.config` | 239,666 | `79ea41dd4c4e2080923ad0cf855b6d847b09736d82a857546640f0cf26fa5380` |
| `Image` | 40,049,152 | `a4edaee34dca66534cf886fd0daa6068273d4fd722b63960d517ef17699af43e` |
| `Image.gz` | 14,751,791 | `53fc7f458ba203089355ad913f599dcf1505bb211e17206d17ab8e279cfce858` |
| module archive | 300,648,393 | `e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d` |
| build metadata | 728 | `7cd6e03913b9ded82870e4b7f65825db38368374a06adb7b2f3fa090769ef9f9` |

Build A and Build B match for `.config`, `Image`, `Image.gz`,
`modules.tar.gz`, and `build-meta.txt`.

## Reproduction

From the repository root, with the accepted base DTB and clean pinned Linux
source available:

```sh
scripts/device/test-wifi-candidate-dtb.sh
scripts/host/validate-wifi-candidate-dtb.sh \
  /path/to/linux-7.1.4 \
  artifacts/network-root-v8-telemetry/sm8350-asus-rog-phone5-recovery.dtb \
  /empty/output/wifi-schema
```

Run each kernel build from the pinned
`localhost/rog5-kernel-builder:ubuntu-24.04` image (digest
`sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`),
using a distinct empty output volume and network-disabled container:

```sh
SOURCE_DIR=/root/src/linux-7.1.4 \
OUTPUT_DIR=/root/build/rog5-linux-7.1.4-wifi \
JOBS=4 \
/workspace/repo/scripts/device/build-mainline-wifi.sh

scripts/device/verify-mainline-wifi-build.sh /path/to/build-a
scripts/device/verify-mainline-wifi-build.sh /path/to/build-b
scripts/device/compare-mainline-wifi-builds.sh \
  /path/to/build-a /path/to/build-b
```

The aggregate offline suite also delegates the board, schema, and static
kernel-build contracts:

```sh
scripts/host/test-linux-rootfs-tools.sh
```

## Decision and next gate

The board description and matching kernel/modules are accepted as compile-only
evidence. They do not prove PCIe link training, regulator sequencing,
firmware boot, board-data selection, regulatory acceptance, a `wlan0`
interface, association, suspend/resume, or stability.

Before any live use:

1. package this exact DTB, kernel, modules, and verified firmware into a
   storage-disabled RAM-only/client-only diagnostic derived from the accepted
   network-root recovery path;
2. add a fail-first runtime oracle for exact PCI `17cb:1103` enumeration,
   WCN6855 power sequencing, ath11k startup, bounded logs, zero RDDM/fatal
   faults, storage exclusion, and automatic fallback;
3. build and recursively verify a separate protected root, target gate,
   watchdog, one-shot/no-retry runner, and verifier-first bounded server;
4. perform another current-state HOLD review and request fresh, exact user
   authorization for at most one attended RAM-only cycle; and
5. keep credentials, AP mode, provider WireGuard, DHCP/DNS, throughput,
   thermals, and battery tests behind later independent gates.

No current result authorizes a radio activation, boot, reboot, module load,
NFS export, credential use, hotspot start, or flash.
