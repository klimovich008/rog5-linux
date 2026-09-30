# ROG5 standby: what still blocks CX/DDR collapse, and the bisect kit on DTB r9

2026-09-30, bundle production-7.2.7-r207 (kernel r110, DTB r9), phone in use
(panel off at the time, no suspend this boot). Read-only phone inspection only:
no suspend, no reboot, no QMP message, no RPMh read, no display-RSC or DP
debugfs access.

## sync_state is not a blocker

- Every boot log has `qcom-rpmhpd 18200000.rsc:power-controller: sync_state()
  pending due to ae00000.display-subsystem` (and the same for gcc, dispcc and
  five NoCs) at 17.4 s. That is fw_devlink's one-shot strict-mode report at
  the deferred-probe timeout: msm and the panel load from the root file system
  later (24+ s).
- Afterwards every provider syncs: all 51 `state_synced` files under
  /sys/devices read 1 (rpmhpd, gcc, gpucc, dispcc, all 11 interconnect
  providers, every genpd provider).
- Why it would matter: before sync_state, rpmhpd clamps every powered domain to
  its top corner in the active AND sleep sets (`rpmhpd_aggregate_corner`,
  `pd->state_synced` false: `level_count - 1`). r152 (no display driver)
  showed exactly that: HLOS=5 in the CXPC violator log. A bisect variant that
  leaves a consumer of rpmhpd/gcc/icc unprobed would confound the trial; the
  r9 variants leave none (see below) and the measure script lists unsynced
  providers.
- Runtime genpd now (awake, panel off): cx 128 (both QUP UARTs, serial@890000
  = Bluetooth 128, serial@98c000 = 48), mx 128, mmcx 192 (DP controller runtime
  active), lcx/lmx/ebi/gfx/mss/mxc off.

## Counters this boot (uptime 4267 s, never suspended)

- cxsd, aosd, ddr: 0. ddr_stats LPM (0xd4/0xd3/0x11/0xd0): 0.
- DDR residency: 451 MHz for 3944 s (92 %), 200 MHz 3 entries/0.8 ms. Awake
  floor = HLOS votes: interconnect_summary shows both dwc3 controllers
  (a6f8800 side, a8f8800 bottom) at 240 MB/s avg / 700 MB/s peak on ebi with
  tag 0 (all buckets) plus bwmon peaks. That is awake idle power, not s2idle
  (the 2026-09-29 trace showed all APPS sleep-set BCM votes at 0).
- ADSP: 1447 sleeps in 71 min (~20/min), asleep 94 %; adsp_island 0.
- SLPI: 6 sleeps in total, asleep continuously since ~130 s uptime; island
  entered 6 times in the first minute after hexagonrpcd served the registry,
  never since. The SLPI is fully power-collapsed (its sleep set applies), so
  "no island" is not by itself a DDR vote.
- qcom_stats apss, cdsp, cdsp1, modem, wpss, gpu, display, gpdsp*: empty.

## qcom_stats "apss" can never validate a trial under mainline

qcom_stats "apss" is SMEM item 631. Only downstream's rpmh_master_stat.c
(called from system_pm.c after a successful RPMh sleep) fills APSS stats, and
downstream keeps them in kernel memory; mainline never allocates the item. The
old `rog5-standby-bisect-measure` required APSS residency from that entry, so
every trial would have ended "VERDICT invalid". Fixed: APSS sleep is now the
time timekeeping stayed frozen (boot clock minus /proc/timer_list monotonic,
before/after) plus the cluster genpd cluster-sleep-1 s2idle requests and PSCI
refusals (both software evidence; hardware collapse shows only in the RPMh
counters). A POSITIVE verdict now needs qcom_stats ddr, ddr_stats LPM and cxsd
all rising; one or two of them is PARTIAL. Read-only check on the phone:
frozen -0.01 s, cluster S1 usage 160764, rejected 1044, s2idle 0.

## Wrapper-left regulator votes (small, not the CX/DDR blocker)

The ASUS 5.4 wrapper runs first on every boot and shares the APPS RSC. Its
regulator table (stockcap-c1 capture) has pm8350c_l7 (3.3 V: vcnl36866
proximity and the ms51 MCU in stock) and pm8350c_l11 (2.85 V: modem antenna)
enabled; the production DT defines neither. qcom-rpmh-regulator starts with
`enabled = -EINVAL`, so regulator_late_cleanup skips unknown-state rails and
such APPS votes stay for the whole uptime, sleep included. Cost unknown (LDO
quiescent plus whatever the load draws); it cannot hold DDR active.

## Ranked blockers

1. **A non-APPS RPMh master's DDR vote; the ADSP first.** Every HLOS vote is 0
   in the sleep set (2026-09-29), all providers synced (above), CXPC violator =
   DDR_AUX=5 only (the DDR subsystem's own CX vote, an effect of DDR staying at
   CP1). The ADSP wakes ~20/min without the APSS and caused the 200 MHz
   re-entries; stopping it froze its awake 451 MHz vote. Test: noadsp.
2. **SLPI sleep set.** SENSOR=5 in some boots' violator logs; runtime stops
   don't work on this firmware. Weaker than 1 now that SLPI is shown fully
   power-collapsed. Test: noslpi (cheapest, first).
3. **Subsystems stock boots and Linux never does: CDSP, SPSS, modem.** The
   wrapper leaves spss/cdsp/modem OFFLINING; stock boots all three (SPSS is
   `qcom,boot-enabled`, pas-id 14). load_state off for modem/cdsp changed
   nothing; SPSS was never tried and has no mainline loader. Test: cdsp
   variant; SPSS only after 1-2.
4. **AOP/TZ/HYP-side policy** (DDR logging, secure-world votes): no direct
   evidence; `--ddr-log-off` is the only prepared probe.
5. Not blockers: rpmhpd sync_state, display RSC (0086), GPU/display stack
   (r152), UFS PM, QDSS, XO, LLCC table, Linux-side DSP clients, USB cable.

## Bisect kit requalified for DTB r9

`scripts/device/compose-standby-bisect-dtb.sh` now pins r9 (4a919c15...,
reproduced byte for byte by compose-production-dtb.sh from the V9 base and
kernel r110 with the r9 feature list), checks the r9 structure it relies on
(memx no-map hole, SLPI/ADSP/CDSP/pmic-glink/DP/sound, the usbbtmtc 5 V chain
TCPC -> btm_vbus -> btm_otg_boost on pmic-glink, the VA macro and LPI pinctrl
clocked only by q6afecc) and adds a `baseline` variant (markers only). noadsp
additionally disables codec@3370000, pinctrl@33c0000,
regulator-rog5-btm-vbus and typec@4e: btm_otg_boost only exists through
qcom_battmgr, so without the ADSP the bottom port has no 5 V (keep it empty).
Marker `/rog5,standby-bisect-base = production-dtb-r9`.

Composed on the real r9 (host, scratch; not staged):

| variant | sha256 |
|---|---|
| baseline | 2d84fadec90667a736b59537739d103be9029b71d126440281d483c7eb2b1817 |
| noslpi | 90a328f4b51d45279dc824522d7bbb11a141c926ce12428b26245f262272b808 |
| noadsp | ec834448fcd6bdac7a4adcb1b5be21241ae254cd2ac564ea2372cb802277a475 |
| cdsp | ea19ef7675267c108d4e3b956a23b28d4f8853abeff2f4b35d7e44312741a45a |

No variant adds an enabled consumer of a disabled or missing supplier (libfdt
walk with `#*-cells`, against r9's own pre-existing ones).
`scripts/device/test-standby-bisect.py` (13 tests, registered in
configs/repository-tests.json) covers composition, refusals, the ramdisk gate
on the composed noadsp tree and the measure verdict with a mocked suspend.
GPT-6.1-Sol reviewed the kit (read-only): its four findings (negative awake
offset, missing monotonic reading, usage_s2idle is only a request count,
first-supplier-only walk) are fixed.
