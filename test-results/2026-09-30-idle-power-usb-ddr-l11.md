# Idle power: usb-ddr votes follow the attached devices (0148), PM8350C LDO11 off (DTB r10)

2026-09-30. Prepared offline on bundle production-7.2.7-r207 (kernel r110, DTB r9). The phone
was only inspected read-only (it was in use). Nothing is installed yet.

## 1. USB controllers' DDR votes: patch 0148

**Where the votes come from.** Both controllers bind `dwc3-qcom-legacy`: side a6f8800 (otg,
usb-role-switch from UCSI) and bottom a8f8800 (host only). Each has `maximum-speed = high-speed`.
`dwc3_qcom_interconnect_init()` votes usb-ddr 240/700 MB/s (tag 0, so every bucket) and apps-usb
0/40 MB/s at probe. It drops them only in glue suspend (`icc_disable`), and none of our patches
changes that. The ROG5 keeps both controllers runtime active on purpose, so the votes last for the
whole uptime:
- the side port: xHCI runtime resume lost state;
- the bottom port: `power/control=on` from rog5-usb-bottom.

**What stock does.** In msm-5.4 dwc3-msm:
- LPM (`dwc3_msm_suspend`) votes `BUS_VOTE_NONE`: nothing attached, or everything suspended.
- HS host mode votes SVS = 240/700.
- Otherwise it uses the default (NOMINAL) vote.
- `BUS_VOTE_MIN` = 1/1 is only a sysfs override.

**The change.** `0148-usb-dwc3-qcom-legacy-ROG5-usb-ddr-vote-follows-the-attached-devices.patch`
never runtime-suspends, unbinds or resets anything. It works like this:
- A USB notifier (USB_DEVICE_ADD/REMOVE) is registered before the core populates the xHCI. It
  tracks the non-hub devices below this glue's root hubs, one reference each.
  - Each device is counted once, in the bucket of its speed at ADD: a failed reset can change
    `udev->speed`.
  - A device that goes away without REMOVE (a failed generic_subclass driver probe) is dropped at
    the next event.
  - usbip-host-style device drivers send neither notification and run at the lower vote.
- The usb-ddr vote is chosen as follows:
  - **full vote** (unchanged): in the device role, or when a high-speed or faster device is
    attached;
  - **2/12 MB/s**: only low- or full-speed devices are attached (keyboard, mouse, pad);
  - **1/1 kB/s floor** with nothing attached. This keeps the path's BCMs enabled, as stock
    BUS_VOTE_MIN does, because the running controller still writes its event ring.
- The role comes from the legacy `pre_set_role` hook (0143). DEVICE raises the vote before the
  gadget starts. Leaving DEVICE, the full vote stays for another 2 s (delayed work) while the
  gadget stops.
- Glue suspend/resume and vote changes share one lock. s2idle is unchanged.
- `dwc3_qcom_legacy.ddr_bw_follows_devices` (default Y, writable) set to N restores the fixed vote
  at once, for A/B tests. Probe joins the instance list under the setter's lock.
- The 1 kB/s floor keeps the BCMs enabled, but that is not proof of DMA latency for a running xHCI.
  The trial must attach and detach at the floor, and must run s2idle with the hub.

**Checks.**
- The patched file compiles with the r110 flags plus `-Werror`.
- The patch applies to the r110 tree (0001-0147).
- These suites pass: `test-production-kernel-build.py` (11), `test-rebase-kernel-series.py` (2),
  `test-production-build-diagnostics.py` (17), `check-repository-static`, `test-standby-bisect.py`,
  and the new `scripts/device/test-idle-power-votes.py` (9).
- GPT-6.1-Sol reviewed it read-only (`docs/reviews/2026-09-30-gpt-6.1-sol-usb-ddr-l11.md`). It
  found no P0/P1 and eight P2/P3. All eight are fixed:
  - speed-change bucket;
  - unpaired ADD;
  - early drop when leaving DEVICE;
  - probe vs parameter race;
  - an LDO11 voltage request;
  - invalid ddr_stats windows;
  - restore under a second signal;
  - the window duration.

**Is it the DDR floor?** Not proven. On this boot (read-only, about 22:40, panel on at brightness 40),
ddr_stats has no 200 MHz row at all: 451 MHz is the floor.
- The ebi aggregate then was avg 2.52 GB/s:
  - display: 2 x 1.02 GB/s;
  - USB: 2 x 240 MB/s.
- The peak was 0.8 GB/s from the LLCC-DDR bwmon opp-0 and the display.
- The bwmon OPP table maps 200 MHz to 800 MB/s peak. So a 700 MB/s USB peak alone fits 200 MHz,
  and the 451 MHz floor with the panel off may come from the average term: the USB 480 MB/s is
  then the only HLOS average.
- The A/B below decides it.

**Estimate.**
- If the USB votes set the floor, awake idle with the panel off moves from 451 to 200 MHz when
  nothing (or only FS devices) is attached. That is roughly 20-40 mW (DDR PHY/controller clocks
  and a lower MX/CX corner), about 3-5 mA of the ~100 mA (2S) awake panel-off draw.
- If bwmon or the ADSP holds 451 MHz anyway, the gain is only the NoC BCM levels on the USB path,
  a few mW.
- s2idle does not change: the glue already disables both paths in suspend.

## 2. PM8350C LDO7 / LDO11 left on by the wrapper

**Stock** (runtime FDT `trial-stockcap-c1-session/stock-fdt.dts`, msm-5.4 lahaina-regulators +
ZS673KS overlays):
- **L7C** (3.3 V, HPM) supplies:
  - the VCNL36866 `vcc_psensor`: the stock driver enables it and disables it when ALS and
    proximity are both off;
  - the MS51 `vdd`: only below hw_stage 5, and MP boards power it from PM8350C GPIO 2.
- **L11C** (2.85 V, HPM) supplies only `vdd-3.0-antenna` of `qcom,ipa_fws`:
  - subsys-pil-tz, ASUS AntennaSwap, the cellular front end's antenna switch;
  - pil-tz enables it at probe;
  - its `antennaSwitch` sysfs node disables and re-enables it, so off is a state stock uses.
- stockcap-c1 shows both enabled (users=1) under the wrapper.

**Decision.**
- **L7 stays on and undeclared.** The light/proximity sensor runs on Linux on that rail
  (components.json "Light / proximity: ready").
  - Declaring LDO7 reset the phone in r34. r34 used min = max = 3.3 V. That value is not on the
    PLDO grid (1.504 V + n x 8 mV: 3.296 or 3.304 V). The mainline core rejects it ("unsupportable
    voltage constraints"), and the whole PM8350C regulator device then fails probe.
  - That is a plausible, untested explanation of r34.
- **L11 off:** there is no Linux consumer, and cellular is out of scope. New compose feature
  `l11off` (`dts/qcom/sm8350-asus-rog-phone5-antenna-rail-off.dtso`) declares `ldo11` as:
  - `regulator-boot-on`;
  - no voltage constraints and no mode, so registration sends nothing (any min/max sets
    `apply_uV`);
  - no consumer and no parent supply.
- How it turns off:
  - qcom-rpmh-regulator starts with an unknown enable state, which `regulator_late_cleanup()`
    skips.
  - Boot-on makes the core send enable=1 at registration (the wrapper's existing vote).
  - Late cleanup (30 s) then logs `rog5_l11c_antenna: disabling` and sends enable=0 (active-only).
  - The wrapper's sleep/wake TCS entries are gone after the first `rpmh_flush` invalidate.

**Composer checks** (compose-production-dtb.sh `l11off`):
- the node is PM8350C (`c`);
- the name is `rog5_l11c_antenna`, with no min/max voltage and no initial mode;
- boot-on is set and always-on is not;
- there is no phandle and no `vdd-l6-l9-l11-supply`;
- LDO7 is still absent.

**DTB r10** = the r9 feature list + `l11off`, on the V9 base with kernel r110 source:
`dda8b280da1ee6a4d4c85c663008551757f9766b278dc93dfeba0b875114788e`. r9 still reproduces
byte for byte (4a919c15...). The only difference from r9 (`dtc -s`) is one node:

    /soc@0/rsc@18200000/regulators-1/ldo11 {
        regulator-boot-on;
        regulator-name = "rog5_l11c_antenna";
    };

**Estimate.** LDO HPM ground current plus antenna-switch leakage is roughly 0.5-1.5 mW (under
0.2 mA on the 2S pack), below what input-power sampling resolves. After boot, check
`/sys/class/regulator/*` for rog5_l11c_antenna "disabled", the late-cleanup log line, and that Wi-Fi
(RSSI, throughput) and BT are unchanged.

## 3. Measurement (prepared, not run)

`scripts/device/rog5-idle-power-sample` (root, on the phone). Each window records:
- mean input power (V x I of the online battmgr inputs);
- battery current;
- DDR frequency residency deltas from `qcom_stats/ddr_stats`;
- the USB glues' ebi votes;
- the L7/L11 regulator state;
- the attached USB devices.

The default is one read-only window. A window whose ddr_stats is unreadable or went backwards
is marked INVALID and left out of the means. `--ab=N` alternates `ddr_bw_follows_devices` N/Y and
restores it on exit or on a signal.

Conditions:
- panel off, awake (sleep policy must not suspend);
- battery Full or bypass on a plain charger on the side port (no hub);
- bottom port empty;
- same adapter for every window.

On the next bundle (kernel with 0148, DTB r10):

    sudo rog5-idle-power-sample --label=baseline --seconds=300
    sudo rog5-idle-power-sample --ab=3 --settle=30 --seconds=300 --json=/var/tmp/usbbw-ab.json

Pass criteria:
- In the Y windows the USB ebi votes read 0/1/1 (floor) and the DDR residency shifts from 451 MHz
  to 200 MHz. If it does not shift, the floor comes from elsewhere (bwmon, ADSP), and the result
  still stands as a negative finding.
- The mean input difference Y vs N is taken over the rounds, as in the DP link test.

For L11 there is no in-boot A/B. Compare to an r9 boot under the same conditions only if the USB
A/B has resolved the noise.
