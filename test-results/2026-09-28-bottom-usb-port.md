# Bottom USB-C port, stage A (USB 2.0 host), 2026-09-28

Default since 2026-09-28: production-7.2.7-r160 = kernel r69 (0088 Haven
watchdog, 0089 bottom-port 5 V source, 0090 usb30_sec_gdsc retention) + DTB
platform-usbbtm-dtb-r2 (features ...,l3,skin,acd,mic,usbbtm).

Use: `rog5-usb-bottom on|off|status`. 5 V is off at boot, so a USB disk left
in the bottom port can't change the boot's UFS discovery count. Only USB
devices go in the bottom port (no Type-C policy yet: never a charger or PC).

## Trials

| Build | Result |
|---|---|
| r157 (boost node as a /pmic-glink child) | ramdisk rolled back: ucsi_glink "missing reg property", no typec port0, side-USB power check failed |
| r158 (same, bottom controller disabled) | same rollback (confirms the pmic-glink child, not the controller) |
| r159 (0089 via phandle; node a child of the GPIO4 fixed regulator) | boots; xHCI up; 5 V on acked by the ADSP; stick enumerated at 480M after a replug; 256 MB read 17.8 MB/s |
| r159 runtime PM | runtime-suspended controller: "xHC error in resume, Reinit", SMMU fault SID 0x20, Host Controller Error; rebind: "usb30_sec_gdsc status stuck at 'off'" |
| r160 (+0090 GDSC retention) | runtime resume from a gated glue enumerated; after s2idle enumerated; runtime PM still unreliable (resume reinit, xHCI not re-suspending), so the controller stays runtime-active (~5 mA awake, measured 59 vs 64 mA with noise); root hubs are held awake while 5 V is on (a suspended root hub saw CCS+CSC but never enumerated) |
| r160 final tool | 8/8 on-cycles enumerated in 2 s (Kingston DataTraveler 70) |
| r160 default install | two ordinary boots committed healthy (calltraces=2, the usual DSI PHY clk warnings) |

## Deep-sleep experiments the same day (DDR_AUX=5 unchanged in all)

icc_bwmon + rog5_input_boost unloaded; real cable unplug; IPA power collapse
QMP {class: bcm, res: ipa_pc, val: 1}; SLPI stopped (adds SENSOR=5); stock
smp2p "sleepstate" (APPS-awake bit 12 cleared in suspend; DT entries on
/smp2p-slpi + test module, r163). The cluster genpd reaches its deepest
state in s2idle (S1 S2idle count 68), so APSS sleeps. lpm_mon types "ddr"
and "aoss" produce no log on this AOP; only "cxpc" does. The Wi-Fi PCIe link
logs "Timeout waiting for L2 entry" each suspend but is powered off and its
interconnect votes dropped.

## Performance check on r160 (same evening)

| Load | Result |
|---|---|
| 1 thread on the prime + 1 on a big core (from < 50 °C) | prime 2841.6 MHz (max), big 2419.2 MHz (max) |
| all 8 cores, 5 s | little 1804.8 (max), big 1996.8 of 2419.2, prime 2496.0 of 2841.6 MHz; 69-73 °C: SoC limiter (LMh), as on stock SD888 |
| GPU | simple_ondemand, 315-840 MHz table complete |

ADSP stopped for one CXPC run: AUDIO=5 stays (a stopped subsystem keeps its
last vote), DDR_AUX=5 unchanged; like the SLPI stop, inconclusive.

## DisplayPort test with the user (r164 RAM trial = r160 + dp feature)

- USB-C hub with HDMI (Terminus 214b:7260 USB 2.0 hub): after a replug the
  DP link trained (2 lanes, 5.4 Gbit/s), EDID of an MSI MPG 491C OLED read
  (3840x1080, 2560x1440, ...; "DisplayID checksum invalid" warnings only),
  DP-1 enabled and Phosh extended the desktop onto it. The user reported the
  hub + HDMI as not working, so whether a picture appeared is unconfirmed.
- A second PD source (about 9 V) charged the phone but brought no DP and no
  USB: side-port enumeration failed (-108, then -71 at full speed).
- The phone then reset: my read of /sys/kernel/debug/dri/*/DP-1/* with DP
  disconnected hit a NULL dereference (+0xa8), 0.1 s after that SSH login
  (oops=panic). Not caused by the hub. After the RAM-trial crash the loader
  took safe-r2; r165 (= r160 content) was installed as the default, two
  boots committed.

## DisplayPort retest (r166 RAM trial = r164 content), same evening

- The same USB-C hub + HDMI + MSI MPG 491C works with the Steam Deck.
- On the phone: DP-1 connects ~4 s after the attach, EDID read, phoc drives
  3840x1080@60 (wlr-randr current), but the monitor shows no picture.
- rog5-usb-reconnect fired 6 s after each attach (device-mode branch, before
  the role switch settled, or host-mode branch) and unbound/rebound dwc3;
  that re-initialises the side port's QMP combo PHY that DP also uses.
  The phoc output was turned off right after (18:12:06, 18:15:25).
- The helper now refuses to re-initialise while a DP connector is connected
  (checked at the moment of the re-init). Not yet verified with the monitor:
  the one clean attempt ended with an unplug.
- phosh 0.57 segfaults when the DP output goes away (g_object_get_data in a
  notify handler); gnome-session then exits cleanly, so the session stayed
  down. rog5-phosh.service now has Restart=always.
- Still to check on the next try: the DP pixel clock (≈266 MHz for
  3840x1080@60) and a 1920x1080 mode (wlr-randr --mode was ignored once).
