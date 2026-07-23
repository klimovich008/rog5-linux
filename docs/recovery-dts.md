# Recovery DTS translation

The ASUS DTS remains a compile-only serial skeleton. It now records the reviewed UFS hardware contract but keeps both the controller and PHY explicitly disabled. It must not be booted.

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

## USB boundary

The vendor inventory confirms DWC3 regions at `0x0a600000` and `0x0a800000`, corresponding to upstream `usb_1` and `usb_2`. Neither is described or enabled in the ASUS DTS yet. The next translation must identify which controller reaches each physical connector and verify HS/QMP PHY rails and role behavior before choosing the single recovery gadget port.

## Promotion gate

UFS may change from `disabled` to `okay` only after the recovery initramfs exists, Android boot-image packaging is proven offline, and temporary boot rollback is available. USB requires the same gate plus a verified physical-port map. Storage must first be discovered read-only; no filesystem repair, formatting, or persistent slot operation belongs in initial bring-up.
