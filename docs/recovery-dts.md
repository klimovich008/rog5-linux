# Recovery DTS translation

The ASUS DTS remains a compile-only serial skeleton. It records the reviewed UFS and left-side USB hardware contracts but keeps both subsystems and all required PHYs explicitly disabled. It must not be booted.

## Reviewed UFS mapping

| Vendor fact | Mainline representation | State |
|---|---|---|
| controller at `0x01d84000` | `&ufs_mem_hc` | disabled |
| PHY at `0x01d87000` | `&ufs_mem_phy` | disabled |
| reset GPIO 203, active-low | `reset-gpios = <&tlmm 203 GPIO_ACTIVE_LOW>` | compiled and checked |
| PM8350 L7, 2.4–3.008 V | UFS VCC | compiled and checked |
| PM8350 L9, fixed 1.2 V | UFS VCCQ | compiled and checked |
| PM8350 L5, 0.88–0.888 V | PHY analog rail | compiled and checked |
| PM8350 L6, 1.2–1.208 V | PHY PLL rail | compiled and checked |

The rail identities, voltage ranges, and reset wiring match both the running ASUS vendor tree and upstream SM8350 board examples. Only the required PM8350/PM8350C regulator graph is present.

The vendor `vdd-hba` reference points at the UFS GDSC. Mainline `sm8350.dtsi` already represents that relationship as the `UFS_PHY_GDSC` power domain, so the vendor property is not copied. The vendor-only VCCQ parent property is likewise not copied because it is absent from the mainline UFS binding; the upstream RPMh regulator topology supplies the L9 rail.

## Memory safety map

The board DTS now records the four live memory-bank tuples, including the vendor zero-sized placeholder tuple. The upstream SM8350 fixed reserved-memory map already matches the board for the secure heaps, remote-processor regions, SMEM, command DB, and firmware spans used by the recovery tier.

Three ASUS deltas are explicit and compile-checked:

- the removed-memory span at `0xd8800000` is enlarged to the vendor size;
- the region at `0x9b800000` is enlarged so the whole vendor safety/debug allocation stays out of the page allocator;
- boot splash and display-refresh data spans are added as `no-map` reservations.

The `rmtfs_mem` label is retained only because disabled upstream remote-processor nodes reference its phandle. Its ASUS recovery size is deliberately conservative; modem/rmtfs enablement requires a separate dynamic-memory review and must not reuse this placeholder contract unchanged.

## Early-boot hardware guards

TLMM GPIOs 52-59 are reserved with `gpio-reserved-ranges = <52 8>`, matching
other upstream SM8350 boards. Without that reservation, mainline reads an
inaccessible register page while registering the gpiochip and takes a
synchronous external abort at GPIO 52.

## Reviewed USB mapping

The vendor inventory confirms DWC3 regions at `0x0a600000` and `0x0a800000`, corresponding to upstream `usb_1` and `usb_2`. A read-only live query shows that the currently connected USB networking link is configured on `usb_1`; `usb_2` is unattached.

`usb_1` is the reviewed left-side connector. This mapping follows three independent facts: its vendor node links to the PMIC UCSI endpoint, its primary QMP PHY is the combined USB3/DisplayPort PHY, and ASUS documents that only the left-side connector provides DisplayPort. `usb_2` uses the secondary USB-only PHY and separate board controls, so it remains outside the first recovery tier.

| USB recovery fact | Mainline representation | State |
|---|---|---|
| left-side controller | `&usb_1`, DWC3 at `0x0a600000` | disabled |
| forced gadget role | `&usb_1_dwc3` with `dr_mode = "peripheral"` | compiled and checked |
| HS PHY rails | PM8350 L5, PM8350C L1, PM8350 L2 | compiled and checked; PHY disabled |
| ASUS HS-PHY register overrides | eight upstream `qcom,*` tuning properties | compiled, checked, and used by recovery |
| USB3/DP PHY rails | PM8350 L6 and PM8350 L1 | compiled and checked; PHY disabled |
| bottom connector | `&usb_2`, DWC3 at `0x0a800000` | untouched and disabled |

The vendor rail identities and voltage ranges match the upstream SM8350 MTP/HDK representation. The vendor HS-PHY override sequence is translated to the upstream disconnect, squelch, amplitude, pre-emphasis, rise/fall, crossover-voltage, and output-impedance properties. The offline inspector reports only allowlisted USB properties and their phandle targets; it never prints boot arguments or unrelated private-tree values.

Sources: the pinned Linux `v7.1.4` SM8350 DTS files and the [ASUS ZS673KS English user guide](https://dlcdnets.asus.com/pub/ASUS/ZenFone/ZS673KS/E20050_ZS673KS_EM_v3_WEB.pdf).

## Recovery overlay and promotion gate

The base skeleton deliberately keeps UFS and USB disabled. A separate
`sm8350-asus-rog-phone5-recovery.dtso` enables exactly the reviewed `usb_1`
wrapper and its HS PHY. It forces the DWC3 child to high-speed operation with
only `usb2-phy` and selects the UTMI clock in place of the absent SuperSpeed
pipe clock. The FEMTO USB2 PHY driver is built into the recovery kernel.
Static checks require exactly two `status = "okay"` changes and keep UFS, the
QMP/SuperSpeed PHY, and the secondary `usb_2` controller disabled.

The USB2-only overlay passes its static gates. The v6 target/staging initramfs,
header-v3 image, and AVB footer passed their then-current offline suite, but v6
failed live ACM data and rollback. Recovery v12 incorporated the ACM/wake-lock
fixes but remained unbooted after a final audit found no pre-USB block-device
lock. V13 added that fail-closed gate to both stages, and v14 limited
`BLKROSET` to physical disks and partitions. Both returned to fallback after
21 seconds without exact recovery USB. V15 reproduced the physical-storage
design with bounded timing diagnostics; its 31-second live interval proved
the wake-lock gate failed before storage isolation. V16 removes that
unnecessary gate and reached exact USB, NCM, and rollback, but its ACM device
node was absent. The authorized local v17 diagnostic proved the RAM/storage
contract and restored ACM with `mdev -s`. V18 requires that rescan, the
`ttyGS0` node, and a second storage gate before UDC binding; it reproduces
byte-for-byte and passes the expanded offline verifier. Credential-free live
USB, storage isolation, and rollback now pass twice, promoting the nested
Linux 7.1 recovery to one separately attended kexec attempt.

The historical v2 run produced staging and target logs, including Linux 7.1.4
at `/init`, configfs, its NCM/ACM gadget, the `a600000` UDC, and `usb0`.
Subsequent audit proved that v2 did not implement this recovery contract: its
staging `/` was writable physical UFS, and its target DTB enabled the UFS
controller, UFS PHY, and QMP/SuperSpeed PHY. The former zero-storage and
USB2-only pass claims are withdrawn. Nothing was flashed, but v2 must not be
booted again.

The diagnostic sources used to preserve and retrieve this evidence live under
`tools/diagnostics/`: `ramoops-raw` exposes the reserved 4 MiB region
read-only, while `bootloader-reason` arms the next reset for bootloader
recovery. Both refuse to load unless `expected_compatible` exactly matches the
running phone; the ramoops physical address remains a private build input and
all Kbuild byproducts are ignored. Filesystem repair, formatting, persistent
slot operations, and UFS enablement remain prohibited.
