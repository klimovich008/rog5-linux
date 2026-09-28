# Stock ASUS kernel vs ours: consolidated plan (2026-09-27)

Source: nine read-only comparisons of the stock ZS673KS msm-5.4 kernel
(+ techpacks, flashed DTBO, vendor image) against our 7.2.7 production
kernel, run with codegraph indices of both trees
(`~/.local/state/rog5-kernel-compare-20260927/{stock,ours}`, `codegraph -p <tree>`).
Reports: `test-results/2026-09-27-compare-{cpu-thermal,displayport-dex,connectivity,
gpu,audio,display,battery-charging,asus-specific,platform}.md`, plus
`2026-09-27-cxsd-aoss-blockers.md`, `2026-09-27-display-gpu-investigation.md` and
the brightness reports.

Status legend: DONE (in the default or a built trial), NEXT (queued), PLAN (needs
work), NO (not needed / not feasible).

## Reliability and correctness

| Item | Area | Status |
|---|---|---|
| Suspend VT switch paused the seat session | display/session | DONE 0069 |
| DPU cmd-mode core clock (top-edge line), encoder from state, dumb padding | display | DONE 0070-0072 |
| PCIe root port hotplug blocked D3 in suspend | connectivity | DONE 0073 |
| WoWLAN link keep (wakeup-enabled endpoints) | connectivity | DONE 0076 (WoWLAN itself off: firmware crashes) |
| PCIe L0s on the WCN6855 link (stock: no-l0s) | connectivity | DONE 0077 (r134) |
| USB host torn down on every s2idle (no wakeup-source) | connectivity | DONE usbwake DTB (r134) |
| USB modules never autoload (/lib/modules empty) | connectivity | DONE udev rule + service |
| Battery temperature ~30 C always, 2S charge doubled, health enum shifted | battery | DONE 0078 + DT flag (r135) |
| UFS still in discovery containment (no runtime PM, ahit=0, no WB/BKOPS) | platform | WAITING for the user: dropping the two DISCOVERY options was denied by the permission classifier on 2026-09-28 (storage-safety change) |
| No APSS hardware watchdog (softdog only) | platform | PLAN: qcom,apss-wdt node after the observer check |
| Panel ESD: ERR_FG (gpio27) and TE check missing | display | PLAN |
| Iris6 reset gpio93 never driven | display | PLAN (diagnostic first) |
| msm probe WARN: DSI PLL(0) lock failed then dsiclk double disable/unprepare (orphan reparent in of_clk_add_hw_provider enables the PHY PLL before the PHY is powered; __clk_set_parent_before ignores the failed enable, __clk_set_parent_after disables anyway; cosmetic) | display | PLAN (S, low value) |
| Haptics reset gpio116 not declared | asus | PLAN (S) |
| No skin/connector thermistors or skin thermal policy | cpu-thermal | DONE r140 (skin zone 42/46/65 C) |
| USB-connector temperature not exposed / no charge cut | battery | exposed r140 (usb-conn zone, hot 70 C); charge cut PLAN |
| CS35L45 speaker protection firmware not loaded (no hibernate, no excursion/thermal protection) | audio | PLAN |
| Stereo channels swapped vs stock | audio | DONE route (r136), listening check pending |
| Side-port combo PHY supplies swapped in the base DTS | DeX | DONE in the dp overlay |

## Performance

| Item | Area | Status |
|---|---|---|
| L3 cache never scales (no EPSS L3 node / CPU OPP tables) | cpu | DONE r139 (power, not speed: firmware default was the top level) |
| DDR/LLCC floor tied to big-core frequency | cpu | PLAN (after L3) |
| CPU capacity / energy model | cpu | PLAN (retest with uclamp) |
| GPU passive trip 85 C vs stock 95 C | cpu/gpu | DONE (r136) |
| 90/120/144 Hz panel modes (exact per-mode commands found) | display | PLAN (M) |
| WriteBooster / UFS clock scaling | platform | with the UFS item |
| 24-bit SENARY MI2S to the amps | audio | DONE 0079 (r136) |
| USB 3 on the side port (HS-only today) | connectivity | PLAN (after DP stage 1) |

## Power

| Item | Area | Status |
|---|---|---|
| SoC never reaches CXSD/AOSS/DDR sleep | power | open: 0068 did not help; next: rpmhpd sync_state/devlink check, rpmh vote readback (votes/vx), wrapper leftovers, disp_rsc |
| Wi-Fi power save when idle; reachable mode | power | DONE (policy) |
| GPU ACD (DT only) | gpu | DONE r141 |
| GPU IFPC (inter-frame power collapse) | gpu | PLAN (L) |
| Display DDR vote held in screen-on idle | display | PLAN (S-M) |
| Denial-only helpers polling battmgr under Phosh | power | DONE |

## Features

| Item | Area | Status |
|---|---|---|
| External monitor over USB-C (DeX) | DeX | stage 1b: 0080 in r136 (panel keeps its DPU blocks); next: DP retest with the hub, then 4-lane (typec switch modules in the ramdisk) |
| Charge limit / bypass charging (server) | battery | PLAN (OEM glink 0x2117/0x2105) |
| Adapter power limit, input current limit | battery | PLAN (S) |
| Torch / camera flash LED | platform | DONE white:flash (r136) |
| ALS lux scale 2x too small (ROG5 is ONE_PL: 846) | platform | DONE (r134) |
| Microphones (4 DMIC via TX/VA macro) | audio | PLAN (M-L) |
| 3.5 mm jack (ESS ES928x, no mainline driver) | audio | PLAN (L) |
| Bottom USB-C port (RT1711H, USB3803 hub, redriver) | connectivity | PLAN (M-L) |
| AeroActive cooler (needs the bottom port) | asus | PLAN (after bottom port) |
| Touch: charger-noise mode, tap-to-wake | platform | PLAN (S/M) |
| SLPI extra sensors (barometer, step, tilt) | platform | PLAN (userspace) |
| Brightness low byte (4 levels) | display | open investigation (lab module) |
| AirTriggers, fingerprint, cameras, NFC | platform/asus | NO for now (large vendor ports / TEE) |
