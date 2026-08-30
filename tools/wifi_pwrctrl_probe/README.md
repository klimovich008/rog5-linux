# QEMU-only PCI power-control probe

This tests the exact V11 kernel's PCI power-control creation, the matching WCN
provider/client modules, and a dummy power-on/off cycle. The synthetic DT has
no physical GPIOs or supply providers. The module refuses machines other than
`linux,dummy-virt`. Never put this fixture module or DT in a phone bundle.

The real phone trace ended after PHY success and entry to
`pci_pwrctrl_create_devices()`. That is the last delivered event, not proof that
the fault is inside that function: a reset can lose later buffered records.
Creation, binding and dummy power-on/off succeed in this fixture. It does not
emulate ASUS electrical behavior, firmware or all parent-device interactions.

Build the fixture as an external module against the unchanged, matching kernel
source/kit with the pinned LLVM builder used by `build-native-wifi-modules.sh`.
The included Makefile selects only the fixture object. Compose `fixture.dtso`
onto QEMU virt's generated DTB. Boot the exact Image with the included `init`,
matching BusyBox/runtime, and these files in `/modules`:

- `pwrseq-qcom-wcn.ko`
- `pci-pwrctrl-pwrseq.ko`
- `rog5-wifi-pwrctrl-probe.ko`

To test diagnostic pauses, apply
`patches/linux/diagnostic/pci-pwrctrl-pwrseq-observation.patch` only to a copied
external-module source. It is not part of the production kernel patch series.
Use `rog5.pwrctrl_pause=0`, `250`, or `1001` on the QEMU command line. The last
case must reject the invalid delay before the client can bind/power on.
Run without disks/networking and with an outer timeout and `-no-reboot`.

Validate each saved console log using:

```sh
python3 scripts/device/test-wifi-pwrctrl-probe.py --validate-log 250 LOG_FILE
```

The delay is diagnostic-only, bounded at 1000 ms, and disabled by default.
It changes timing and therefore cannot itself be presented as a production fix.
