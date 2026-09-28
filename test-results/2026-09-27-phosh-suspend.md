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
