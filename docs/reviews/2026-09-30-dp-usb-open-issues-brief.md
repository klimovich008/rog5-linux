# Review request: three open DP/USB problems on the ROG Phone 5 (2026-09-30)

Read-only analysis. Do not modify files and do not run anything against the
phone. For each problem: rank the causes with file:line evidence, propose the
smallest kernel/DT change (diff against the named files) and a pass/fail test.

Source: mainline 7.2.7 + our patches (`patches/linux-7.2.7/series.production`),
patched tree `/home/deck/.local/state/rog5-kernel-7.2.7-build-r94/source`.
Stock ASUS msm-5.4 (read-only): `/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4`
(techpack/display/msm/dp, sde, drivers/usb/dwc3/dwc3-msm*.c, drivers/usb/pd,
drivers/soc/qcom altmode/pmic_glink, arch/arm64/boot/dts/vendor/qcom).
Notes: `test-results/2026-09-29-dp-hub-bringup.md`, `test-results/2026-09-29-hbr2-and-server-checks.md`,
`docs/reviews/2026-09-29-gpt-6-astra-dp-followup.md`, `docs/reviews/2026-09-30-gpt-6.1-sol-dp-pcon.md`,
`docs/reviews/2026-09-30-steamdeck-dp-capture.md`.

## 1. Blue screen (latched DPU underrun) on the first enable after a plug-in or a new mode

Side USB-C DP alt mode, direct to an MSI MPG 491C (native DP 1.4 input, DPCD
0x0000 = 12 14 c4 81 01 00 01 40 02 00 06 00 00 00 83, 0x2200 = 14 1e c4 81 ...:
up to HBR3, 4 lanes). GNOME (mutter) drives DP-1 with the DSI panel off. After
a replug, or when mutter switches to 5120x1440@60 (469 MHz, 2 lanes HBR2,
18 bpp), the monitor shows only the DPU underflow colour (blue). The INTF_0
underrun IRQ ([0,24] in debugfs core_irq) jumps by ~75-475 at the enable and
then stops counting, but the screen stays blue until the next modeset; a
mode change (1920x1080 -> 3840x1080@60, 266.5 MHz, 30 bpp) then gives a clean
picture. rog5-gnome.service pins core_perf before mutter starts
(`configs/systemd/rog5-gnome.service`: fix_core_clk_rate 460000000,
fix_core_ab_vote/ib 15500000, perf_mode 2). Patches 0099/0100/0101/0106 try to
address the first-enable underrun. Why does the pipeline stay latched after
the IRQ stops counting, and what recovers it without a modeset (INTF/CTL
reset, underrun recovery like stock's)? Is 5120x1440@60 (469 MHz pixel clock
> 460 MHz pinned core clock, widebus, 2 LMs?) within DPU limits at all, and
what should mode_valid reject? What makes the first enable fail when a later
modeset of the same mode works?

## 2. Four DP lanes (and HBR3) on the side port

Today: `dts/qcom/sm8350-asus-rog-phone5-displayport-side.dtso` makes the QMP
combo PHY orientation-switch only (always USB3+DP, 2 DP lanes), `data-lanes
= <0 1>`, link-frequencies up to 5.4 GHz. The side port's dwc3 uses only the
USB2 PHY (no USB3), so the USB3 lanes are idle. pmic_glink_altmode
(drivers/soc/qcom/pmic_glink_altmode.c) turns the ADSP's pin assignment into
TYPEC_DP_STATE_C/D/E; the combo PHY switches to DP-only (4 lanes) for C/E only
if it is a mode-switch (phy-qcom-qmp-combo.c typec_mux_set). The ADSP firmware
negotiates the pin assignment with the partner (USB PD Discover/Configure).
Questions: how do we see and influence which pin assignment the ADSP picks
(stock pmic_glink/altmode messages, a "USB3 not needed" hint, a configure
request from the host)? What DT changes (mode-switch on usb_1_qmpphy, data-lanes
<0 1 2 3>, link-frequencies incl. 8.1 GHz, the gpio-sbu-mux) are needed and are
they safe for pin assignment D partners (the USB-C HDMI hub reports 2 lanes)?
Does msm on SM8350 support 4 lanes + HBR3 on this PHY (QMP V5 tables at 8.1G)?
What does stock Android do on this phone (4 lanes to a USB-C monitor?)

## 3. USB 2.0 fails after a role switch (error -71 at full speed)

With DP attached (hub or the monitor's USB-C KVM), after a replug the side
port's xHCI comes up but every device fails `device descriptor read/64, error
-71` at full speed. Working workaround (`scripts/device/rog5-usb-reconnect`):
unbind/bind the dwc3 core a600000.usb, wait ~8 s in device mode, then set the
usb_role to host; then the hub enumerates at high speed. Switching to host 1 s
after the bind still fails. The controller boots in dr_mode peripheral with
VBUS forced valid and a UCSI role switch (patch 0055 gates the pullup by role).
What is the real cause (dwc3 host init without a core soft reset, HS PHY
(phy-qcom-snps-femto-v2.c) not re-initialised for host, GUSB2PHYCFG/susphy,
the qcom glue's VBUS/ID override in dwc3-qcom-legacy, UCSI role ordering), and
what is the proper kernel fix?

Output: one section per problem with ranked causes, evidence, a diff, and a
test; then anything else wrong you notice on the way.
