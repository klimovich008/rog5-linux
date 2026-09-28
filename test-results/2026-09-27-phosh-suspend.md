# 2026-09-27: Phosh session, working suspend/wake, rotation

Phone: default production-7.2.7-r121 (kernel r36), slot B. Phosh 0.57 is now the
boot default (`rog5-shell --default phosh`); Denial is still installed
(`rog5-shell --default denial` switches back).

## Suspend: the VT switch paused the seat session
- `rog5-sleep-policy` read `pm_wakeup_irq` right after `systemctl suspend`,
  which returns before the kernel suspends, so it acted on the previous wake.
  It now waits until `suspend_stats` success+fail changes and reads the wake
  IRQ only after a successful suspend (offline loop test in
  `test-rog5-sleep-policy.sh`).
- Root cause of the broken wakes: with no fbdev client, nothing registers
  `pm_vt_switch_required(dev, false)`, so every suspend switched to the suspend
  VT. Under Denial, seatd disabled the client and deniald never re-added its
  libinput devices (event0-5), so touch and keys were dead after a wake. Under
  Phosh, logind paused phoc, phoc re-created DSI-1 on resume, and phosh died
  with a Wayland error, ending the session.
- Fix: `tools/kmod/rog5_no_vt_switch` (loaded at boot by
  `rog5-no-vt-switch.service` from `/usr/local/lib/rog5/modules/$(uname -r)/`)
  now; kernel patch 0069 (msm KMS registers the same thing) for the next build.
- Result (user, unplugged): screen blanks with the power key; after 60 s the
  policy suspends (s2idle); one power-key press wakes it with the display on
  (`display after power-key wake: On (0 replays)`, so the real key is
  delivered). The PIN unlocks, touch works, and the key blanks again. There's
  no seat pause in the journal.

## Phosh bring-up
- Arch's phoc links the stock wlroots0.20; phoc needs its embedded wlroots with
  the layer-shell 0-height revert, otherwise phosh dies after "Phosh ready"
  (`zwlr_layer_surface_v1#81 ... height 0 requested without setting top and
  bottom anchors`). Rebuilt as phoc 0.57.0-1.1 (`packaging/arch/phoc`);
  `IgnorePkg = phoc`.
- Session: `rog5-phosh.service`, user `phone` (uid 1000, groups video render
  audio input), PAM service `phosh`, tty7, `WLR_DRM_DEVICES=/dev/dri/card1`
  (msm_dpu KMS; Adreno renders through renderD128). Scale 2.5 (`/etc/phosh/phoc.ini`).
- Lock: phosh always locks on suspend, so the `phone` account got a numeric
  PIN (set by the user's request; SSH stays key-only:
  PasswordAuthentication no). dconf: lock-enabled, lock-delay 0; gsd-power
  sleep 'nothing' (rog5-sleep-policy owns suspend); black background.
- Audio: user PipeWire/WirePlumber with `/etc/wireplumber/.../50-rog5-speakers.conf`
  plays through both speakers (user confirmed). Root rog5-pipewire is disabled
  when Phosh is the default.
- A live `dconf update` made gnome-settings-daemon re-grab its shortcuts, and
  the running phosh lost its XF86PowerOff binding until the session restarted.
  Restart the session after changing dconf defaults.

## Rotation
- The SLPI accelerometer (libssc through iio-sensor-proxy) reported
  bottom-up when upright. Added `ACCEL_MOUNT_MATRIX=-1,0,0;0,-1,0;0,0,1`
  (`configs/udev/81-rog5-ssc-accel.rules`). The user confirmed portrait and
  both landscape directions. Restarting iio-sensor-proxy leaves phosh without
  an accelerometer until the session restarts.

## Open
- Build a kernel with 0069 (and test the untested 0068) and retire the module bridge.
- Idle-standby current under Phosh is not measured yet.
- `gbm_bo_create failed: Invalid argument` for phosh screencopy thumbnails,
  and a power-on `Atomic commit failed: Device or resource busy`: handed to
  the screen/GPU investigation.

## Kernels r122 and r123 (later on 2026-09-27)
- r122 = kernel r38 = r36 + 0069. The RAM trial with the module bridge
  unloaded and an rtcwake s2idle cycle showed no seat pause. Installed as the
  default; two ordinary boots committed healthy.
- Display/GPU investigation (read-only; report in
  `2026-09-27-display-gpu-investigation.md`) gave 0070-0072:
  - 0070: the DPU vblank/scanout queries take the encoder from the atomic
    state (no "no encoder found for crtc 0").
  - 0071: dumb buffers are padded to 32-row blocks. The kmsro import of
    heights like 385 or 1045 failed with EINVAL, so phoc
    "gbm_bo_create failed" left the phosh thumbnails empty.
  - 0072: command-mode CRTC core clock scale (default 200 % -> 345 MHz OPP).
    At 200 MHz the DPU needed 259 us for the first 48-line DSC slice row,
    later than the panel scan, which caused the top-edge glitch line.
- r39/r40 failed the warning gate: 0072 moves an upstream kernel-doc warning
  in dpu_core_perf.c from line 41 to 58. The policy entry was updated (line,
  file hash, reason).
- r123 = kernel r41 = r38 + 0070-0072. `core_clk_rate` 335165040 and
  `mdp_clk` 345 MHz. The gbm probe on card1 now passes 979x385, 979x386 and
  561x1045 (all failed on r121). The user confirmed that the top-edge line is
  gone and the phosh thumbnails render.
- r123 installed as the default (default-install-r123-session.py); two
  ordinary boots committed healthy. The rog5-no-vt-switch module bridge is
  retired (0069 is built in): the unit, the module and its source are removed.

## Standby: PCIe0 stayed powered in every suspend (0073)
- The first unplugged measurement on r123 (Phosh; it started right off a
  full charge): one ~90 min s2idle, 242 mA as reported (charge_counter,
  2S). cxsd/aosd/ddr stayed at 0. SLPI and ADSP slept almost the whole
  window. glink-smem (LPASS) interrupts ran at about 1 per 2.3 s:
  PMIC_RTR_ADSP_APPS traffic.
- Awake-side glink traffic came from rog5-battery-log (4 battmgr reads every
  2 s) and rog5-powerd, which still ran under Phosh. Both are now
  WantedBy/PartOf rog5-denial.service.
- Root cause for PCIe: the SM8350 root port resets with SLTCAP HotPlug+
  Surprise+. With pciehp not built, pci_bridge_d3_possible() refuses D3
  and pci_host_common_d3cold_possible() returns 0 (kretprobe), so
  dw_pcie_suspend_noirq() returned early: the link, clocks and votes stayed
  up. 0073 clears HPC/HPS in the 2.7.0 post_init.
- r124 = kernel r42 = r41 + 0073. SltCap is now HotPlug- Surprise-, and
  d3cold_possible returns 1. Suspend now stops the link (non-fatal "Timeout
  waiting for L2 entry", since the WCN6855 firmware is already down), and
  resume retrains Gen3 x1. Wi-Fi reconnects with 0 % loss.
- Unplugged measurement on r124 (Wi-Fi rfkill-off during the window): 5076 s,
  61 s awake, one suspend, 106 mAh as reported = 75 mA as reported
  (~37 mA once halved). cxsd/aosd/ddr are still 0: another holder remains.
- scripts/device/rog5-standby-test: an unattended unplugged measurement
  (systemd-run); awake time from CLOCK_MONOTONIC; qcom_stats sleep seconds.

## 2026-09-28: fallback after the DP trial; r134 default; PD boot fix
- The r133 DP RAM trial hung after ~1 h 53 min (log ends while phoc
  rescans DP connectors). The next primary boot (r124) never committed, so
  the loader took safe-r2. Likely cause: the MSI monitor / hub stayed on the
  side port and supplied USB-PD above 6.5 V, and the production power-USB
  check requires 4.0-6.5 V (usb-voltage-invalid).
- load-persistent-root-power-usb.sh (production branch) now accepts
  4-21 V (USB-PD fast chargers, docks, monitors); the PC/NCM branch is
  unchanged.
- r134 = kernel r48 (0077 L0s off, 0078 battmgr (not active: needs the
  dual-cell DT flag), qmp combo, DP and USB server modules) + DTB usbwake +
  ALS scale 846: RAM trial, then installed as the default; two ordinary
  boots committed healthy.

## 2026-09-28: r135 default (0078 active, PD-safe ramdisk)
- r135 = kernel r48 + DTB platform-usbwake-battfix-dtb-r1 (usbotg now sets
  asus,cell-voltage-readonly) + ramdisk with the 4-21 V power-USB window.
- Battery sysfs before (r134) -> after (r135), same charger, full:
  temp 298 -> 253 (0.1 C; the r134 value is the stuck ~30 C), charge_full
  4970000 -> 2485000, charge_full_design 5500000 -> 2750000, charge_counter
  halved, cell_voltages 4309/4316 mV (new), health Good, capacity 100.
- RAM trial t135, then default install: two ordinary boots committed.
  calltraces=2 on every boot = pre-existing msm probe WARN pair ("DSI PLL(0)
  lock failed", dsi0_phy_pll_out_dsiclk already disabled/unprepared), also
  in r134; queued as a display cleanup item.

## 2026-09-28: r136 default (24-bit speakers, stereo order, torch, GPU trips, DP fix)
- r136 = kernel r50 (+0079 SENARY MI2S S24_LE/32-bit slots/3.072 MHz, +0080
  DPU top-down allocation for non-DSC CRTCs) + DTB platform-torch-gputrip-dtb-r1
  + ramdisk with the stock stereo order (RCV=left, SPK=right) and
  leds_qcom_flash in boot-modules.
- RAM trial t136: white:flash present (max_brightness 255), lit at 20 and off
  again; gpu-top/bottom trips 95000/100000; DSI CRTC on mixer 0/1 ctl 0;
  PipeWire playback RUNNING through the 24-bit back end with no ASoC/q6
  errors; s2idle + RTC wake after 15 s works. One-off at leds_qcom_flash
  probe: "spmi cleanup_irq apid=143 sid=0x2 per=0xee" (a latched flash
  peripheral interrupt without a handler, disabled by pmic_arb) plus the
  genirq descriptor dump of the arbiter IRQ; PMIC interrupts keep working.
- Default install: two ordinary boots committed; calltraces=2 (the known DSI
  probe pair).
- Pending listening checks: stereo order (left = top edge in landscape with
  the side port down) and the 24-bit link at low volume.

## 2026-09-28: CXSD read-only experiment E0 (r135)
- All devices state_synced=1, incl. 18200000.rsc:power-controller: the
  rpmhpd "clamp to max until sync_state" is not the blocker.
- pm_genpd awake, screen off: cx and mx on at level 128; cx consumers are
  only 98c000.serial (console, 48) and 890000.serial (BT UART, 128);
  mmcx/ebi/lcx/lmx/mxc off. ttyMSM0 wakeup disabled, no no_console_suspend.
  disp_cc_mdss_ahb_clk prepare 0 (0068 works), bi_tcxo prepare/enable 8.
- rog5-rpmh-sleep-blockers (APPS DRV active votes): xo.lvl 3, cx 3, mx 2,
  others 0; clock buffers 0; QUP0/1/2 BCM 0x20004001; MC0/SH0/ACV/CN0 set.
- One 30 s s2idle on USB power: suspend ok, cxsd/aosd/ddr still 0, and the
  AOP violators region at 0xc320000 stays all zeros, so it is either not
  enabled on this AOP build or lives elsewhere.
- Each s2idle on USB power logs "qcom-pcie 1c00000.pcie: Timeout waiting for
  L2 entry! LTSSM: 0x11" (not seen on battery with Wi-Fi power save on).

## 2026-09-28: XO held through s2idle by the geni UARTs; 0081 (r138 default)
- Method: tracefs events clk_enable/clk_disable (fire only on 0<->1
  transitions), rpmh_send_msg and suspend_resume across one rtcwake s2idle,
  replayed from a clk_summary snapshot (scratchpad clk-trace.sh, installed on
  the phone as /usr/local/sbin/rog5-clk-trace).
- r136: rpmh never wrote xo.lvl before sleep (APPS XO vote stayed 3 in the
  sleep set: rpmh only puts single resources into the sleep TCS when sleep
  != wake). At timekeeping_freeze the only XO users left were
  gcc_qupv3_wrap0_s3_clk (console 98c000) and gcc_qupv3_wrap2_s4_clk (BT UART
  890000). UFS, PCIe, USB and display clocks were all off.
- Cause: qcom_geni_serial_pm() turns ports off with pm_runtime_put_sync(),
  which cannot suspend during system suspend (device_prepare holds a runtime
  PM reference). 0081 forces runtime suspend after uart_suspend_port and
  forces resume before uart_resume_port (not for wakeup ports).
- r138 = r136 + 0081 (kernel r51): in suspend bi_tcxo and xo_board reach 0
  and the APPS DRV sends xo.lvl 0, cx 0, mx 0, mmcx 0 before
  machine_suspend. Bluetooth scans after resume. cxsd still 0 in this run
  on USB power (charger/ADSP and the USB link keep their own votes); needs
  an unplugged run. Default install: two ordinary boots committed.

## 2026-09-28: L3 scaling (r139 default)
- sm8350.dtsi has no EPSS L3 node; the generic qcom,epss-l3 driver fits
  (shared vote at base+0x90). Overlay sm8350-asus-rog-phone5-cpu-l3.dtso (DTB
  feature l3): interconnect@18590000 + per-cluster CPU OPP tables (opp-hz =
  EPSS LUT rows 16/16/19) with opp-peak-kBps = L3 MHz x 32000 from the stock
  lahaina core->L3 tables (prime uses the big table; >= 2.4 GHz -> 1516.8
  MHz). CONFIG_INTERCONNECT_QCOM_OSM_L3=y (cpufreq-hw is built in).
- r139 = kernel r52 + DTB platform-l3-dtb-r1: all LUT frequencies kept, no
  cpufreq/OPP errors; L3 vote 1516.8 MHz with the prime core loaded, about
  998 MHz idle with the screen off (fast switching is off with an OPP table,
  as on sm8250/sc7280).
- xz -6 -T1 of 64 MiB: prime 34.6 s (r138) vs 34.5 s (r139), big 39.4 s vs
  40.2 s (warmer): the firmware left L3 at its top level before, so this
  change saves awake power and does not add speed.
- Default install: two ordinary boots committed.

## 2026-09-28: skin thermal (r140 default)
- Overlay sm8350-asus-rog-phone5-skin-thermal.dtso (DTB feature skin):
  PMK8350 ADC7 with the stock thermistor channels (xo 0x44, msm 0x144,
  bottom connector 0x145, hot pocket 0x146, side connector 0x347/0x349, PA
  0x44a/0x44b; 100k pull-up, ratiometric, 200 us), ADC-TM on the six stock
  channels, zones skin (msm_therm), usb-conn, hot-pocket, xo.
- Skin policy (step_wise, 2 s passive polling): 42 C -> big <= state 6
  (1766 MHz), prime <= 9 (1901 MHz), GPU <= 3 steps; 46 C -> big <= 12
  (1075 MHz), prime <= 18 (845 MHz), GPU unlimited; 65 C critical. Stock
  starts at 36 C (thermal-engine NORMAL); ours keeps full speed longer.
  Connector 70 C, hot pocket 60 C and XO 80 C are "hot" (report only).
- Modules qcom_spmi_adc5 + qcom_spmi_adc_tm5 (+ qcom_vadc_common) in
  boot-modules.
- r140 = kernel r52 + DTB platform-l3-skin-dtb-r1: on USB power, screen off:
  msm 32.4 C, side conn 32.4, bottom conn 27.8, hot pocket 33.4, xo 33.3, PA
  33.2/33.0; skin zone with 6 cooling bindings; no ADC errors. Default
  install: two ordinary boots committed.

## 2026-09-28: GPU ACD (r141 default)
- Overlay sm8350-asus-rog-phone5-gpu-acd.dtso (DTB feature acd): &gmu
  qcom,qmp = <&aoss_qmp>, qcom,opp-acd-level per GPU OPP with the stock
  bin-0 values (lahaina-v2-gpu.dtsi).
- r141 = kernel r52 + DTB platform-l3-skin-acd-dtb-r1: GMU firmware v3.1.10
  accepts the ACD table (no HFI/ACD/QMP error), GPU and phoc run.
- glmark2-es2-wayland --off-screen 1280x720 on wayland-0 (FD660): r140 297;
  r141 446 and 369. Run-to-run spread is large, so no speed claim; ACD's
  purpose is a lower GX voltage margin (power/thermal).
- The same benchmark on the headless virtual desktop (pixman sway) ran on
  llvmpipe: apps there have no GPU acceleration (wayvnc needed pixman). To
  revisit for DeX/remote use.
- Default install: two ordinary boots committed.

## 2026-09-28: simulated unplugged standby on r144 (force-discharge)
- USB input suspended with charge_behaviour=force-discharge (0082), so the
  sleep policy saw battery power while the USB data cable stayed attached.
  A WakeSystem systemd timer meant to restore "auto" after 22 min did not
  wake the phone; the power key did (the RTC alarm counted 2 wakeups).
- rog5-standby-test: 3659 s window, 3573 s suspended, 86 s awake, 2
  suspends; adsp 3547 s asleep, slpi 3659 s asleep; cxsd/aosd/ddr 0. The
  battery was at 100 %, so charge_counter (+7 mAh) gives no current figure.
- So with XO released by the APPS DRV (0081), CX collapse is still blocked
  by another voter: candidates are the display RSC (bootloader splash votes),
  TZ/HYP or the AOP; the AOP violators region stays empty.
- The USB gadget re-enumerated with the host side on 10.77.0.1 only
  (169.254.77.2 unreachable); use 10.77.0.2 then.

## 2026-09-28: built-in microphones (r146 default)
- Design (Opus agent, from the stock Bolero/lahaina sources): VA macro
  (qcom,sm8250-lpass-va-macro, same register map as Bolero 2.0) capturing
  DMIC0-3 on LPI gpio6-9 into VA_CODEC_DMA_TX_0 -> MultiMedia3 (PCM 3); mic
  bias from L2C 1.8 V; 0083 makes the VA macro take the LPASS macro/dcodec
  votes only while runtime-active (upstream holds them from probe, which
  would undo 0063's ADSP power collapse). DTB feature mic; modules
  snd_soc_lpass_va_macro + snd_soc_lpass_macro_common.
- r145 trial (kernel r57): card binds with PCM 3 capture, speakers still PCM
  0. arecord hw:0,3 5 s: 0.5 s start-up pop, then noise floor RMS 0.8 at 0 dB
  and 5 at +18 dB (stock gain, VA_DEC Volume 102); a sound at 2 s showed on
  ch0 only (independent mics). The VA macro runtime-suspends and the ADSP
  keeps entering sleep afterwards.
- rog5-audio-route sets the capture route (DMIC0 left, DMIC2 right, +18 dB);
  the controls are optional without the mic DTB. r146 = r145 + that route:
  default install, two ordinary boots committed.
- PipeWire: the source ("Built-in microphones") first stalled after <1 s:
  pro-audio groups all PCMs of the card under one driver, so the speakers
  (1024-frame periods) followed the mic (960) and xrun'd every cycle. A
  separate node.group for the mic fixes it: 7.8 s of 8 s recorded, and 5.8 of
  6 s while playing at the same time, 0 xruns. alsa-utils installed on the
  phone.
- Pending: a listening check of a recording.
