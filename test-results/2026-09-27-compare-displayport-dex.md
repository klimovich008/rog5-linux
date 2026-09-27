# ROG5 external display (USB-C DP alt mode): stock vs ours

Phone was unreachable (169.254.77.2 publickey denied, 10.77.0.2/192.168.1.219 no route); everything below is from source.

## 1. Ranked table

| # | Item | Stock behaviour | Ours | Impact | Proposed fix | Effort | Risk | Conf. |
|---|------|-----------------|------|--------|--------------|--------|------|-------|
| 1 | Combo USB3/DP PHY driver not built | `usb_qmp_dp_phy: ssphy@88e8000` "qcom,usb-ssphy-qmp-dp-combo" (lahaina-usb.dtsi:142) always on for usb0 | `# CONFIG_PHY_QCOM_QMP_COMBO is not set` (build r42 .config); `phy@88e8000` status "disabled" (ours-board.dts:2587) | missing feature (no SS, no DP) | `CONFIG_PHY_QCOM_QMP_COMBO=m` in configs/kernel/rog5-production.fragment; enable `&usb_1_qmpphy` | S | low | confirmed |
| 2 | DP controller disabled | `sde_dp: qcom,dp_display@ae90000` enabled, HBR3 (dp_panel.c:3059 `max_bw_code = DP_LINK_BW_8_1`), 4 lanes, `max-pclk 675000 kHz` (lahaina-sde.dtsi) | `displayport-controller@ae90000` compatible "qcom,sm8350-dp" present but `status = "disabled"` (ours-board.dts:2951); driver supports it (dp_display.c:174, desc sc7180, wide bus) | missing feature | new overlay enabling `&mdss_dp`, `&mdss_dp_out { data-lanes = <0 1 2 3>; }` | S | low | confirmed |
| 3 | Type-C SBU/AUX switch (discrete GPIO mux, not FSA4480) | `&sde_dp { qcom,dp-gpio-aux-switch; qcom,aux-en-gpio = <&tlmm 167 0>; qcom,aux-sel-gpio = <&pm8350c_gpios 1 0>; }` (ZS673KS-ER1-overlay.dts:41-44 overriding EVB gpio93; fsa4480@42 "disable" EVB:155; flashed dtbo0.dts:8637-8639/11017). dp_power.c:433-451: on connect aux-en driven **0**, aux-sel = orientation flip (1 = CC2); comment "aux-en default is high" (dp_power.c:479) | missing (no `gpio-sbu-mux` node; tlmm167 and pm8350c gpio1 unused in ours-board.dts) | missing feature (AUX/HPD never reach the sink) | add `gpio-sbu-mux` node (driver present: `CONFIG_TYPEC_MUX_GPIO_SBU=m`) wired to pmic-glink connector port@2; see §2.3 | S | low (polarity of enable must be verified) | confirmed (wiring) / likely (active-low enable) |
| 4 | pmic-glink connector graph incomplete | ADSP altmode-glink client + `qcom,ucsi` port linked to usb0 (lahaina.dtsi:5580-5592, lahaina-usb.dtsi:111); DP HPD/orientation/pin-assignment come from ADSP (dp_altmode.c) | connector@0 only has port@0 (HS) (usb-otg-side.dtso:36-47); no port@1 (SS → `usb_1_qmpphy_out`), no port@2 (SBU mux); pmic_glink_altmode.ko is built (QCOM_PMIC_GLINK=m, Makefile:14) and sm8350 client_mask includes ALTMODE (pmic_glink.c:392-395) | missing feature | extend connector@0 like sm8350-hdk.dts:41-81 | S | low | confirmed |
| 5 | usb_1 forced high-speed only | usb0 `maximum-speed = "super-speed-plus"`, phys = HS + combo (lahaina-usb.dtsi:66-77) | `qcom,select-utmi-as-pipe-clk`, `maximum-speed = "high-speed"`, `phy-names = "usb2-phy"` from recovery.dtso:35-43 (also ufs-discovery.dtso:17-25) end up in the production DTB (ours-board.dts:2761,2783-2791) | missing feature (SS + DP), also USB 3 hubs run at 480 Mb/s | production tier must not apply the HS-only properties (overlays cannot delete base properties: either a DP-tier variant of recovery.dtso or `fdtput -d` in compose-production-dtb.sh after overlay apply); restore `phys = <&usb_1_hsphy>, <&usb_1_qmpphy QMP_USB43DP_USB3_PHY>` | M | medium (SS link bring-up on this board untested; keep HS tier as fallback) | confirmed |
| 6 | QMP combo PHY supplies swapped in our base DTS | vdd (0.912 V) = pm8350_l1, core = pm8350_l6 (lahaina-usb.dtsi:147-150) | `&usb_1_qmpphy { vdda-phy-supply = <&vreg_l6b_1p2>; vdda-pll-supply = <&vreg_l1b_0p88>; }` (sm8350-asus-rog-phone5.dts:298-300) — HDK/binding: vdda-phy = l1b_0p88, vdda-pll = l6b_1p2 (sm8350-hdk.dts:860-865) | bug (latent; would apply wrong load/voltage requests once enabled) | swap the two supplies | S | low | confirmed |
| 7 | DP audio | ext_disp/msm-ext-disp audio via LPASS DP port (`qcom,ext-disp = <&ext_disp>`) | mdss_dp has `#sound-dai-cells`, dp_audio.c uses hdmi-codec (built, SND_SOC_HDMI_CODEC=m); sm8250.c handles DISPLAY_PORT_RX (sound/soc/qcom/sm8250.c:37); no dai-link in audio.dtso | missing feature (monitor speakers) | add a `DISPLAY_PORT_RX` dai-link (cpu `<&q6afedai DISPLAY_PORT_RX>`, codec `<&mdss_dp>`) to sm8350-asus-rog-phone5-audio.dtso after video works | S | low | likely |
| 8 | ASUS ADSP may notify DP on SVID 0xFF00 | dp_altmode.c:254-267 registers a second client for `USB_SID_PD` (0xFF00) "displayport_backup" on ZS673KS | pmic_glink_altmode_sc8280xp_notify (ours:470-505) treats svid != 0xFF01 as USB/safe: a 0xFF00 DP notification would never raise HPD | reliability (speculative) | only if dmesg shows notifications with no HPD: small patch treating svid 0xFF00 with `mux_ctrl` DP4LN/USB3_DP as DP | S | low | speculative |
| 9 | Stock waits for USB host before DP configure | dp_altmode.c:179-186 waits `usb_host_complete1` up to 3 s | mainline: UCSI sets the role (patch 0058 retry), altmode independent | none expected | none; note ordering when debugging | – | – | likely |
| 10 | DSC/FEC/MST over DP | `qcom,dsc-feature-enable; qcom,fec-feature-enable; qcom,mst-enable` on sde_dp | mainline msm DP has none | limitation (no 4K120/5K, no MST) | accept | – | – | confirmed |

## 2. Details

### 2.1 Which port, which chips (confirmed)
- **Side (left) port = stock `usb0` (ssusb@a600000) = our `usb_1`**: SNPS HS PHY 88e3000 + QMP USB3/DP combo PHY 88e8000, PM8350B Type-C/PD run by the ADSP (`qcom,ucsi-glink` linked only to usb0, `qcom,altmode-glink`). This is the only DP-capable port. Our usb-otg-side.dtso already runs it as DRP via UCSI (`/sys/class/typec/port0`), HS only.
- **Bottom port = stock `usb1` (ssusb@a800000) = our `usb_2` (disabled)**: Richtek RT1711H TCPC on qup13 I2C @0x4e (EVB:793-936) with ID VDO "No DP" (EVB:868-871), USB3803 USB2 hub @0x29 (HUB_BYPASS tlmm97, HUB_RESET tlmm98, HUB_CONNECT tlmm173; ER1:266-284) and a "usb2 redriver" (vcc pm8008j_l6, RSTN tlmm3, EQ_EN tlmm62; PR1:71-77; dwc3-msm.c:3790-3815 acts only on "a800000.ssusb", hub mode is for the ROG fan accessory, dwc3-msm.c:4960-4975). None of this touches DP.
- No dedicated DP/USB mux or SS redriver on the side port: the combo PHY does lane/orientation switching itself (`orientation-switch` already in our `phy@88e8000`, ours-board.dts:2596; mainline registers typec switch + mux + `drm_aux_bridge`, phy-qcom-qmp-combo.c:4423-4523, 4902). Only the SBU (AUX) pair goes through a discrete 2:1 switch driven by tlmm167 (enable) and pm8350c GPIO1 (select).
- HPD: no GPIO; the ADSP forwards HPD state/IRQ and pin assignment in the USBC_NOTIFY_IND payload. Stock (`usbc_notify_ind_msg`, hdr+16+4 bytes, altmode-glink.c:43-47) and mainline (`struct usbc_notify`, ours pmic_glink_altmode.c:59-76) have the same size and layout (port, orientation, mux_ctrl, vid, svid, dp pin/hpd), so the mainline "sc8280xp" decoder matches the lahaina ADSP.
- PHY generation: stock `qcom,phy-version = <0x420>`, PLL "5nm-v1"; mainline `sm8350_usb3dpphy_cfg` (combo.c:2794) uses v4 DP serdes + v5 DP tx tables with RBR/HBR/HBR2/HBR3 — same silicon, no PHY table port needed. Stock AUX cfg bytes (00 13 A4 00 0A 26 0A 03 B7 03, lahaina-sde.dtsi) are the values mainline dp_catalog hardcodes.

### 2.2 Kernel config (fragment)
```
CONFIG_PHY_QCOM_QMP_COMBO=m        # missing today
CONFIG_TYPEC_MUX_GPIO_SBU=m        # already m
CONFIG_DRM_AUX_BRIDGE=m / CONFIG_DRM_AUX_HPD_BRIDGE=m  # already m
CONFIG_DRM_MSM_DP=y, CONFIG_DRM_DISPLAY_DP_HELPER=y     # already
CONFIG_TYPEC_DP_ALTMODE=m, CONFIG_UCSI_PMIC_GLINK=m     # already
CONFIG_SND_SOC_HDMI_CODEC=m                              # already (DP audio)
```
Initramfs/module list: qmp combo phy (`phy_qcom_qmp_combo`), `gpio_sbu_mux`, `pmic_glink_altmode`, `aux_hpd_bridge`, `aux_bridge` must load before/with msm.ko (mkinitfs modprobe model).

### 2.3 DT: new `sm8350-asus-rog-phone5-displayport-side.dtso` (values from stock)
```
&{/} {
    dp_sbu_mux: typec-mux {
        compatible = "gpio-sbu-mux";
        /* stock drives tlmm167 to 0 when DP is configured, idle high (dp_power.c) */
        enable-gpios = <&tlmm 167 GPIO_ACTIVE_LOW>;
        /* stock aux-sel = 1 for CC2 (flip) */
        select-gpios = <&pm8350c_gpios 1 GPIO_ACTIVE_HIGH>;
        mode-switch; orientation-switch;
        port { dp_sbu_mux_ep: endpoint { remote-endpoint = <&pmic_glink_sbu>; }; };
    };
};
&{/pmic-glink/connector@0/ports} {
    port@1 { reg = <1>; pmic_glink_ss_in: endpoint { remote-endpoint = <&usb_1_qmpphy_out>; }; };
    port@2 { reg = <2>; pmic_glink_sbu: endpoint { remote-endpoint = <&dp_sbu_mux_ep>; }; };
};
&usb_1_qmpphy { status = "okay"; vdda-phy-supply = <&vreg_l1b_0p88>; vdda-pll-supply = <&vreg_l6b_1p2>; };
&usb_1_qmpphy_out { remote-endpoint = <&pmic_glink_ss_in>; };
&usb_1_dwc3 { phys = <&usb_1_hsphy>, <&usb_1_qmpphy QMP_USB43DP_USB3_PHY>; phy-names = "usb2-phy", "usb3-phy"; };
&mdss_dp { status = "okay"; };
&mdss_dp_out { data-lanes = <0 1 2 3>; };
```
Plus: the HS-only properties from recovery.dtso/ufs-discovery.dtso (`qcom,select-utmi-as-pipe-clk`, `maximum-speed`, `phy-names = "usb2-phy"`) must not be present in the DP tier (item 5). tlmm167 pinctrl: stock `sde_dp_aux_active` = gpio function, bias-disable, drive-strength 8 (EVB:98-121, retargeted to gpio167 in ER1:46-64); the gpio-sbu-mux driver requests the line as plain GPIO, a pinctrl state is optional. pm8350c GPIO1 has no stock pinctrl entry. Nothing else in our DTB uses either line. mdss_dp already carries `assigned-clock-parents` pointing at the combo PHY's DP link/VCO clocks and `power-domains = MMCX`, so enabling the PHY makes dispcc's DP clocks non-orphan. `orientation-gpios` (HDK) is not needed.

Patches needed: none for the happy path; possible item 8 patch; fix item 6 in the base dts.

### 2.4 Bandwidth and interactions
- Link: HBR3 x4 = 25.9 Gb/s payload (pin assignment C/E): 4K60 8-bit (~12.5 Gb/s) fits; 4K 10-bit/4K120 need DSC (stock only). Stock capped pclk at 675 MHz; DPU sm8350 2-LM 4K path is supported in mainline. Docks/adapters that also expose USB 3 use pin assignment D (2 lanes): 13 Gb/s → 4K30, 1440p60, 1080p120; USB 3 devices on the dock then run at 5 Gb/s on the other 2 lanes. With C/E (most plain USB-C→HDMI/DP adapters) USB stays HS only (D+/D-), hubs on the dock still work at 480 Mb/s.
- Side-port hubs today are HS-only anyway; once item 5 is done, SS hubs get 5/10 Gb/s and DP coexists per the pin assignment chosen by the ADSP.
- Charging: PD sink/source and VBUS remain owned by the ADSP (as stated in usb-otg-side.dtso); a PD dock will power the phone while in DP mode without Linux involvement; pmic_glink battery client keeps reporting. Docked = wake source and no s2idle deep sleep expected (separate agent).
- Interaction with patch 0072: it scales only command-mode CRTCs; the DP CRTC is video mode and is unaffected. DP uses INTF_0 (dpu_7_0_sm8350.h:300-306), the panel uses INTF_1.

### 2.5 Test plan (USB-C→HDMI or DP adapter/dock, with the phone's screen on)
1. Boot the DP tier; check probes: `dmesg | grep -E 'qmp|altmode|ucsi|gpio-sbu|msm-dp|dp_display'`; `ls /sys/class/typec/port0`, `/sys/class/drm/` should show `card*-DP-1` (status disconnected); `cat /sys/kernel/debug/dri/*/state` for the DP encoder.
2. Plug a USB-C→DP/HDMI adapter to the **side** port: expect `port0-partner` with a `displayport` altmode entry (`/sys/class/typec/port0/port0-partner/port0-partner.*/svid` = ff01), `dmesg`: "altmode ... DP" and "msm-dp ... connected", `cat /sys/class/drm/card1-DP-1/status` = connected, `edid` non-empty. Check the SBU mux: `cat /sys/kernel/debug/gpio` (tlmm167 low, pm8350c gpio1 per orientation). Flip the plug 180° and re-test (orientation via `cat /sys/class/typec/port0/orientation`).
3. If AUX times out (dmesg "aux ... timeout") but HPD arrived: invert the enable polarity of the SBU mux (item 3), or force it via `echo`ing the state in `/sys/kernel/debug/gpio` is not possible — rebuild the DTB with GPIO_ACTIVE_HIGH.
4. Render: `modetest -M msm -s <conn>@<crtc>:1920x1080` from a TTY, then Phosh (phoc picks the output automatically; docked mode with `phosh` ≥ 0.40).
5. USB test at the same time: keyboard/mouse on the dock (HS), an SSD on a pin-assignment-D dock (`lsusb -t` shows 5000M).
6. Unplug/replug 10×; suspend with the monitor attached and resume.
7. Later: DP audio dai-link (item 7): `aplay -l` shows the DP PCM; `speaker-test -D hw:0,<dp>`.

## 3. Checked, same or not needed
- ADSP firmware/glink transport already used by UCSI on ours; PAN_EN/ACK handshake in mainline mirrors stock (dp_altmode.c:236, pmic_glink_altmode.c:144-175).
- No SS redriver/retimer on the side port (redriver + USB3803 are bottom-port USB2 only); `qcom,pcie-mux-en-gpio` (tlmm173) existed on SR1 boards only and is the hub CONNECT line on production units.
- fsa4480@42 disabled on ROG5 (EVB:155-158) — do not add the FSA4480 node from the HDK.
- Stock `usbplug-cc-gpio` removed by ASUS; not needed.
- Combo PHY init/DP tables, AUX cfg, HBR3 support, 4-lane mapping: mainline sm8350 support matches lahaina; no vendor DP driver port needed.
- ASUS stock DP quirks (dp_panel.c:3163-3216: reject portrait modes, cap 60-144 Hz, HDMI-bridge 120 Hz, TPS4 workaround for two ASUS monitors) are policy, not needed.
- Bottom port (usb_2, RT1711H, hub): unrelated to DP; leave disabled.
