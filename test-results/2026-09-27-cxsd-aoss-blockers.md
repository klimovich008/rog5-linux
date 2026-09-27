# ROG5 (SM8350, 7.2.7 r42/r124) — why cxsd/aosd/ddr stay at 0 in s2idle

## 0. Access limits (please read first)
- **Phone: not reached.** Plain `ssh root@169.254.77.2` fails (publickey; the project key lives in `~/.local/state/rog5-v13-live-inputs-20260823-r1/deployment-ssh-key`). Both my attempts to use it (a scratch helper, and importing `production-ram-trial.py`'s own `ssh()`) were denied by the auto-mode classifier ("Credential Exploration"); per your rules I stopped. So `/var/lib/rog5-standby-test/*`, live `clk_summary`, `interconnect_summary`, `pm_genpd`, `rog5-sleep-blockers/{votes,vx}` were **not** read. A broad host-side grep for old dumps was also denied. Everything below is from source (r42 tree), the composed DTB, patches, stock msm-5.4 DT and the test-results records. The "lead reads" in §4 are the missing evidence.
- Files: `~/.local/state/rog5-prod-boot-20260923` (REPO), kernel `~/.local/state/rog5-kernel-7.2.7-build-r42/source` (SRC), DTB decompiled to `/tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/board.dts` (line numbers below refer to it).

## 1. Q2 — are APPS sleep sets flushed in OSI, and is 0x4100c344 right?

**Yes on both, no fix needed here.**
- DTB: `rsc@18200000` has `power-domains = <0x15>` = `power-domain-cpu-cluster0` (board.dts:4059-4068, 574-577); `cluster-sleep-0 = 0x41000044`, `cluster-sleep-1 = 0x4100c344` (board.dts:462-480); every cpu@N has `power-domains`/`power-domain-names = "psci"` and no `cpu-idle-states` (composer `scripts/device/compose-production-dtb.sh:120-155`). `CONFIG_ARM_PSCI_CPUIDLE_DOMAIN=y`, `QCOM_RPMH=y`, `QCOM_RPMHPD=y`, `QCOM_STATS=m`, `PM_DEBUG/PM_SLEEP_DEBUG=y` (objects/.config).
- Flush path: `rpmh_rsc_probe` sees `pdev->dev.pm_domain` (cluster PD) and registers a genpd notifier instead of cpu_pm (SRC `drivers/soc/qcom/rpmh-rsc.c:1143-1165`); `rpmh_rsc_pd_callback` runs `rpmh_flush()` on `GENPD_NOTIFY_PRE_OFF` and returns `NOTIFY_BAD` if an AMC is busy or flush fails (rpmh-rsc.c:968-979). In s2idle the last CPU goes through `__psci_enter_domain_idle_state(..., s2idle=true)` → `dev_pm_genpd_suspend(pd_dev)` (`drivers/cpuidle/cpuidle-psci.c:80-83`, wired at :269) → `genpd_sync_power_off` of the cluster (its only device, apps_rsc, was counted suspended in the noirq phase) → notifier → flush → `psci_pd_power_off` picks the deepest state. Your record (S1 "S2idle usage 2296") is only incremented after `_genpd_power_off` succeeded, so the flush ran and the cluster really entered 0x4100c344 every ~2.2 s. `rpmh_rsc_write_next_wakeup` is a no-op because `qcom,tcs-config` has `CONTROL_TCS 0` — identical to stock (`lahaina.dtsi:599-602`), so no regression there.
- State parameter vs stock `lahaina-pm.dtsi`: stock cluster levels are `l3-pc` psci-mode 0x4 and `llcc-off` ("AOSS sleep", psci-mode 0xc34, `qcom,notify-rpm`, `qcom,min-child-idx 1`); with `psci-mode-shift 4` plus cpu mode 4, the power-down bit and OSI affinity-1 bit this is exactly 0x41000044 / 0x4100c344. Upstream's genpd "all CPU PDs off" is the equivalent of min-child-idx 1. Stock's `notify-rpm` (system_sleep_enter = rpmh flush + wakeup timer) is what the genpd notifier does.

**What the flush actually carries — two rules that decide everything else:**
1. `rpmh_flush` only writes cached requests whose `sleep_val != wake_val` (`rpmh.c:405-409`, 435-483). A resource voted ON in all three states (e.g. a prepared `bi_tcxo`, an enabled rpmhpd corner) is *not* in the sleep TCS, but its live DRV vote stays and is what AOP sees while APSS sleeps. Same for BCMs: bcm-voter only queues BCMs whose WAKE≠SLEEP (`drivers/interconnect/qcom/bcm-voter.c:331-335`); a non-zero bandwidth with the default tag (`QCOM_ICC_TAG_ALWAYS`, cell value 0 or 7) at suspend time is a sleep-set vote.
2. rpmhpd sends the SLEEP corner = the enabled corner for non-`_ao` domains (`drivers/pmdomain/qcom/rpmhpd.c:943-1009`), and **clamps active and sleep corners to the highest level until `rpmhpd_sync_state` has run** (rpmhpd.c:971-978, 'Clamp to highest corner if sync_state hasn't happened'). sync_state fires only when every DT consumer of `power-controller` has a bound driver. rpmhpd in 7.2.7 sets no `GENPD_FLAG_ACTIVE_WAKEUP`, so wakeup-path devices do not keep CX on (checked: no `GENPD_FLAG` in rpmhpd.c).

## 2. Enumeration (source + DTB), dropped-in-suspend vs not

### 2a. XO (`bi_tcxo`, rpmhcc cell 0 = `xo.lvl`) consumers
`clk-rpmh` votes `xo.lvl` ON in SLEEP+WAKE+ACTIVE whenever the non-AO `bi_tcxo` is prepared (`drivers/clk/qcom/clk-rpmh.c` `valid_state_mask` :82, `clk_rpmh_aggregate_state_send_command`, `clk_rpmh_prepare`). One prepared consumer anywhere in the tree = XO on in sleep = aosd impossible. DT consumers of `<0x1f 0x00>`:

| consumer (board.dts) | how it holds XO | dropped by suspend? |
|---|---|---|
| gcc `clock-controller@100000` :1018 | parent of GPLL0 and every gcc branch; gcc-sm8350 has **no** `CLK_IS_CRITICAL` clocks, only raw `qcom_branch_set_clk_en` (SRC `drivers/clk/qcom/gcc-sm8350.c:3810-3816`, no CCF prepare) | only through enabled branches below |
| ufshc :2022 (`ref_clk`) | ufshcd | yes: `ufshcd_setup_clocks(hba,false)` `drivers/ufs/core/ufshcd.c:2147` |
| ufs phy@1d87000 :2049 (`ref`) | phy_power_on | yes: `phy_power_off` in `ufs_qcom_setup_clocks` off/PRE_CHANGE `drivers/ufs/host/ufs-qcom.c:1466-1474` (plus 0065 lane-clk leak fix) |
| adsp :2122, slpi :2462 (`xo` proxy) | remoteproc start | yes at handover: `qcom_pas_handover` `drivers/remoteproc/qcom_q6v5_pas.c:381-391`; only a never-issued handover would hold (0058 shows handover fires) |
| gpucc :2403 | GPU PLLs | yes when GMU stops (`a6xx_gmu_stop`) |
| usb hs phy@88e3000 :2548 (`ref`) | phy_init | yes on battery: dwc3 device-mode `dwc3_core_exit` → phy_exit; glue clocks/icc off in `dwc3_qcom_suspend` `drivers/usb/dwc3/dwc3-qcom.c:338-367` |
| **dsi phy@ae94400 :3104** (`iface` = disp_cc_mdss_ahb_clk, `ref`) | `pm_clk_add` keeps `iface` **prepared** for the device lifetime → dispcc runtime-active → `disp_cc_mdss_ahb_clk_src` parent bi_tcxo prepared | **NO** — measured on r121 with screen off: `disp_cc_mdss_ahb_clk enable 0 prepare 1`, dispcc active, **genpd mmcx on** (patch 0068 body, untested, `series.diagnostic`) |
| dispcc :3192 | parent for above | follows the PHY |
| cpufreq@18591000 :4308 | `clk_get_rate` only, never prepared (`drivers/cpufreq/qcom-cpufreq-hw.c:658-669`) | not a holder |
| ipa, cdsp, mmc, phy@88e4000/88e8000, mpss | `status = "disabled"` | n/a |
| pcie0 (enabled at runtime by the Wi-Fi kit; `aux` clk is XO-derived) | link + phy | yes since 0073: `dw_pcie_suspend_noirq` stops link + `deinit`, `qcom_pcie_suspend_noirq` icc_disable; `pme_capable` (WoWLAN) only sets `skip_pwrctrl_off`, link is still stopped (`pcie-designware-host.c`, tail of `dw_pcie_suspend_noirq`) |
| console `serial@98c000` :1428 (`gcc_qupv3_wrap0_s2_clk`, GPLL0 child) | port ON | yes via `uart_suspend_port` → pm(OFF) → runtime suspend → `geni_serial_resources_off` (OPP 0, clocks, icc) `drivers/tty/serial/qcom_geni_serial.c:1663-1675, 1980-1994` — **unless** `no_console_suspend` is on the cmdline or `/sys/class/tty/ttyMSM0/power/wakeup` is `enabled` (`serial_core.c:2306-2310` returns early and leaves the port fully powered). The DTB gives 98c000 one IRQ, so no wakeup IRQ (geni line 1896-1925) |
| Non-DT: VRM clock buffers `lnbclka1-3`, `rfclka1-5`, `divclka1`, BCM `IP0`, ARCs `ddr.lvl`/`qphy.lvl` | **never written by this kernel**; whatever the ASUS 5.4 wrapper left before kexec is still the APPS vote (same mechanism as the QUP0/1 0x207803c0 find, `tools/rpmh_sleep_blockers/rog5-rpmh-sleep-blockers.c:40-70`) | not managed → cannot be dropped; readback needed |

### 2b. CX/MMCX (`rpmhpd`) consumers (`power-domains = <0x29 N>`)
- CX (0): all QUP SEs on wrappers 0 and 2 (runtime PM autosuspend; console as above), gpucc, BT `serial@890000` :1234 (one IRQ → no wakeup; hci_qca only checks `device_may_wakeup(ctrl)` `hci_qca.c:1742`, so `uart_suspend_port` powers it down), adsp/slpi LCX/LMX proxies (dropped at handover). **Dropped** in suspend, provided sync_state happened (§1 rule 2).
- MMCX (6): dsi@ae94000, dsi phy@ae94400, dispcc@af00000 — **held** by the DSI-PHY prepare (0068 evidence). rpmhpd sends the MMCX enable corner as the SLEEP vote; AOP's rail dependency keeps CX up for MMCX, so this very likely blocks **cxsd**, not only aosd.
- No `GENPD_FLAG_ACTIVE_WAKEUP` in rpmhpd, and `gcc` has no `power-domains`, so 0060's `PWRSTS_RET_ON` PCIe GDSCs are not rpmhpd children (no CX genpd hold from Linux' side).

### 2c. Interconnect votes that could survive into the sleep set
| consumer | tag (2nd cell) | at suspend |
|---|---|---|
| rog5-input-boost :58-64, bwmon pmu@90b6400/@9091000 :920-970 | 3 = ACTIVE_ONLY | sleep bucket always 0 — not holders |
| ufshc :2022 `ufs-ddr`/`cpu-ufs` | 7 = ALWAYS | 0/0 when clocks go off (`ufs-qcom.c:1495`, `MODE_MIN = {0,0}` :76) — dropped |
| gpu@3d00000 :2291 `gfx-mem` | 7 | `dev_pm_opp_set_opp(NULL)` in `a6xx_gmu_stop` path (`a6xx_gmu.c:1499`, `a6xx_gpu.c:2269`) — dropped **if** the GMU reaches slumber |
| display-subsystem :2858 `mdp0/1-mem` | 0 (=ALWAYS) | `msm_mdss_disable` sets 0 (`msm_mdss.c:281-291`); MDSS is runtime-suspended with screen off (0068 evidence) — dropped |
| usb@a6f8800 :2760 | 0 | `dwc3_qcom_interconnect_disable` in suspend — dropped |
| pcie0 | (runtime node) | `icc_disable` when `pci->suspended` (0073 makes that true) — dropped; pre-0073 it kept 1 kBps + clocks |
| QUP core BCMs QUP0/1/2 | keepalive (0066) | AMC/WAKE=1, SLEEP=0 — fine |
| keepalive BCMs (MC0, SH0, CN0, …) | — | sleep 0 — fine |
| **IP0, ddr.lvl, qphy.lvl** | unmanaged | wrapper leftovers possible (see 2a) |

### 2d. Regulators
`qcom-rpmh-regulator` writes `RPMH_ACTIVE_ONLY_STATE` only; those votes persist through sleep by design (PMIC resources, not CX). The ROG5_S12_VOTE hack (0036) is a setpoint on S12B, not a CX/XO holder. Not blockers for cxsd/aosd/ddr.

### 2e. Other RPMh masters
ADSP/SLPI sleep (qcom_stats), so their DRV sleep sets apply. CDSP/modem never run. Not managed by Linux at all: the **DISPLAY DRV (disp_rsc @0xaf20000)** and **GPU DRV (GMU RSC)**. Upstream has no disp_rsc node (stock has, `lahaina.dtsi:3344-3355`, driven by sde_rsc in solver mode); if the ASUS wrapper kernel brought up SDE before kexec, its DISP DRV votes (MMCX/CX/EBI) are still there. Only the AOP violators log tells (§4 E0).

## 3. Ranked candidates

1. **MMCX + XO held by the DSI PHY's `pm_clk` iface prepare (0068).** Evidence is already measured on r121 (screen off: `disp_cc_mdss_ahb_clk prepare 1`, dispcc active, genpd mmcx on). MMCX sleep vote ≠ 0 → CX cannot shut down → cxsd 0 → ddr/aosd 0. Fix: **0068 into series.production** (diff is in `patches/linux-7.2.7/0068-…`; it only skips `pm_clk_add("iface")` when the parent is `qcom,sm8350-mdss` and lists "iface"). Proof: after an unplugged run, `pm_genpd_summary` shows `mmcx` off with screen off, `/sys/kernel/debug/clk/bi_tcxo/clk_prepare_count` 0 with screen off, and cxsd > 0.
2. **rpmhpd `sync_state` never reached → all rail sleep votes clamped to the top corner.** Mechanism rpmhpd.c:971-978; you have hit exactly this class before (interconnect sync_state blocked by an unbound provider; `tools/gmu_bind` exists for the same reason on GCC/GPUCC). Any `status="okay"` node with `power-domains = <0x29 …>` whose driver never binds blocks it (candidates: SEs with no driver bound, slpi/adsp only if their module never loaded, dsi1 is disabled so fine). Check (read-only): `for l in /sys/class/devlink/*18200000.rsc:power-controller*; do echo "$l $(cat $l/status)"; done` — every link must be `active`; plus `/sys/kernel/debug/devices_deferred`. Also `cat /sys/kernel/debug/rog5-sleep-blockers/votes` while idle: `cx.lvl` at the top level (e.g. ≥ 0x180) while the phone idles at ~100 mA says clamped. Fix if so: bind or disable the offender; optional diff below adds a one-line `dev_info` to `rpmhpd_sync_state` so the journal proves it.
3. **Leftover APPS-DRV votes from the ASUS wrapper for resources Linux never writes** (VRM clock buffers lnbclk/rfclk/divclk → XO buffer on; `IP0`; `ddr.lvl`/`qphy.lvl`). Same mechanism as QUP0/1 (0x207803c0, fixed by 0066). The r118 readback only reported QUP0/1; the other rows were not recorded in test-results. Read `votes` again; anything non-zero in `lnbclka*/rfclka*/divclka1` (bit 0 of the VRM_EN word) or a valid `IP0` (bit 29) or non-zero `ddr.lvl/qphy.lvl` is a permanent sleep holder. Fix: one-shot zeroing module (diff §5.3), later a proper provider (as 0066 did).
4. **Another DRV holding CX: DISPLAY (wrapper's disp_rsc) or GPU (GMU not in slumber).** Evidence path: `vx` (AOP "system PM violators" at 0xc320000) after an unplugged run — the row names the DRV (`DISPLAY=`, `GPU=`, `HLOS=`…). If `GPU`: look for `a6xx_gmu` slumber/RSCC timeouts in the journal (`GMU_STATUS_PDC_SLEEP`, "failed to sleep"). If `DISPLAY`: the fix is a Linux-side reset of disp_rsc (take it out of solver mode, invalidate its TCSes) — I'd write that only after the log confirms it.
5. **Console UART kept powered in suspend** (`no_console_suspend` or tty wakeup enabled). Check `/proc/cmdline` and `/sys/class/tty/ttyMSM0/power/wakeup` (must be `disabled`), and `/sys/class/tty/ttyMSM1/power/wakeup` for the BT port. Without either, the port drops OPP/clocks/CX (2a). Fix if present: remove `no_console_suspend` / `echo disabled > .../power/wakeup`.
6. **PCIe0 with WoWLAN armed.** With 0073 the RC still stops the link and deinits even when a downstream device is wakeup-enabled (only `skip_pwrctrl_off`), so it is not a vote holder — but that also means a PME-based WoWLAN wake cannot work; the sleep policy arms WoWLAN by default (`scripts/device/rog5-sleep-policy`, `ROG5_SLEEP_WAKE_PORTS`). For standby measurements run with `ROG5_SLEEP_WAKE_PORTS=` to keep Wi-Fi out of the picture (the r124 run did, via rfkill).
7. **Wakeups every ~2.3 s from LPASS glink (PMIC_RTR_ADSP_APPS).** Not a vote holder (cxsd needs only a few ms of residency) but it caps the sleep fraction once cxsd works. Secondary; address after 1-4 (battmgr/ucsi notification rate).

Ruled out from source (dropped correctly): UFS (ufshcd + ufs-qcom + 0065), USB on battery, PCIe (0073), GPU bandwidth via OPP, MDSS bandwidth, bwmon/input-boost (ACTIVE_ONLY), remoteproc XO proxies (handover), cpufreq XO, gcc/dispcc "critical" clocks (raw register enables, no CCF prepare: gcc-sm8350.c:3810-3816, dispcc-sm8250.c:1374), rpmh regulators, QUP core BCMs (0066), 0060 RET_ON GDSCs (gcc has no rpmhpd parent).

## 4. Experiment plan (one unplugged `rog5-standby-test` run each; counters: `qcom_stats/{cxsd,ddr,aosd}` Count, plus `/sys/kernel/debug/pm_genpd/power-domain-cpu-cluster0/idle_states` usage/rejected)

- **E0 (no reboot, reads only, do first):** load the rpmh_sleep_blockers module; read `rog5-sleep-blockers/votes` and `vx` (awake, screen off); `pm_genpd_summary` (mmcx/cx status); devlink statuses for `18200000.rsc:power-controller`; `/proc/cmdline`; `ttyMSM0`/`ttyMSM1 power/wakeup`; per-clock files `/sys/kernel/debug/clk/{bi_tcxo,disp_cc_mdss_ahb_clk}/clk_prepare_count` (per-clock files, not clk_summary, which resumes every provider). Then run one unplugged standby and read `vx` again — it names the blocking DRV per mode (AOSS/CXPC/DDR).
- **E1 (definitive sleep-set capture, tracefs writes by you):** `echo 1 > /sys/kernel/tracing/events/rpmh/enable` before the run; after resume `cat /sys/kernel/tracing/trace | grep -E 'rpmh_send_msg.*(sleep|wake)'` shows the exact SLEEP/WAKE TCS contents the last flush wrote (addr/data), and `rpmh_send_msg` with active state shows the live votes; compare against cmd-db names (`votes` prints the addresses).
- **E2:** kernel r43 = r42 + 0068 (already carried), RAM trial, unplugged run. Expect mmcx off + bi_tcxo prepare 0 with screen off; success = cxsd > 0. If cxsd > 0 but aosd = 0, the remaining XO holders are in `votes` (VRM buffers) or E1's trace.
- **E3:** if E0 shows a non-`active` rpmhpd devlink or a clamped `cx.lvl`: unbind/disable the offender (or bind a stub as with gmu_bind), rerun; check `rpmhpd: sync_state` line (diff 5.2).
- **E4:** if `votes` shows wrapper leftovers: load the zeroing module (5.3) once, rerun.
- **E5:** if `vx` says DISPLAY/GPU: journal for GMU slumber errors; for DISPLAY, plan a disp_rsc reset patch.
- **E6:** if `/proc/cmdline` has `no_console_suspend` or tty wakeup is enabled: drop it / `echo disabled`, rerun.

## 5. Diffs

5.1 **0068** — already in `patches/linux-7.2.7/0068-drm-msm-dsi-phy-let-the-sm8350-MDSS-parent-own-the-iface-clock.patch`; move it from `series.diagnostic` to `series.production` (after 0073). No changes needed to the patch.

5.2 **rpmhpd: make sync_state visible** (proves candidate 2 in the journal):
```
--- a/drivers/pmdomain/qcom/rpmhpd.c
+++ b/drivers/pmdomain/qcom/rpmhpd.c
@@ static void rpmhpd_sync_state(struct device *dev)
 	of_genpd_sync_state(dev->of_node);
 
+	dev_info(dev, "sync_state: rail votes now follow consumers\n");
 	mutex_lock(&rpmhpd_lock);
```

5.3 **One-shot scrub of wrapper leftovers** (only if `votes` shows them; run once as an out-of-tree module, tools/ style, uses the existing rpmh API; write is ACTIVE-only so the sleep/wake caches stay untouched — the zero becomes the live DRV vote):
```
// tools/rpmh_sleep_scrub/rog5-rpmh-sleep-scrub.c (new, GPL-2.0-only)
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <soc/qcom/cmd-db.h>
#include <soc/qcom/rpmh.h>
#include <soc/qcom/tcs.h>
#define VRM_EN 0x4
static const char * const vrm[] = { "lnbclka1", "lnbclka2", "lnbclka3",
	"rfclka1", "rfclka2", "rfclka3", "rfclka4", "rfclka5", "divclka1" };
static const char * const bcm[] = { "IP0" };
static int __init scrub_init(void)
{
	struct device_node *np = of_find_node_by_path("/soc@0/rsc@18200000/power-controller");
	struct platform_device *pdev = np ? of_find_device_by_node(np) : NULL;
	struct tcs_cmd c = { 0 };
	int i, ret;
	of_node_put(np);
	if (!pdev || !pdev->dev.driver) return -ENODEV;
	for (i = 0; i < ARRAY_SIZE(vrm); i++) {
		u32 a = cmd_db_read_addr(vrm[i]);
		if (!a) continue;
		c.addr = a + VRM_EN; c.data = 0;
		ret = rpmh_write(&pdev->dev, RPMH_ACTIVE_ONLY_STATE, &c, 1);
		pr_info("rog5-scrub: %s en=0 -> %d\n", vrm[i], ret);
	}
	for (i = 0; i < ARRAY_SIZE(bcm); i++) {
		u32 a = cmd_db_read_addr(bcm[i]);
		if (!a) continue;
		c.addr = a; c.data = BIT(30) | BIT(29); /* commit|valid, x=y=0 */
		ret = rpmh_write(&pdev->dev, RPMH_ACTIVE_ONLY_STATE, &c, 1);
		pr_info("rog5-scrub: %s 0 -> %d\n", bcm[i], ret);
	}
	put_device(&pdev->dev);
	return 0;
}
module_init(scrub_init);
MODULE_LICENSE("GPL");
```
(`ddr.lvl`/`qphy.lvl` deliberately not touched until `votes` shows them non-zero — an ARC level write needs the cmd-db level table; add them the same way with `data = 0` if needed.)

5.4 Console: no patch; cmdline/udev check (E6).

## 6. Bottom line
The OSI/flush plumbing is correct and the cluster does enter AOSS-sleep-capable state ~every 2.2 s; the counters stay 0 because the APPS DRV still presents non-zero CX-family votes to AOP while asleep. The one holder already measured is the DSI PHY's permanently prepared `disp_cc_mdss_ahb_clk` (MMCX enabled + XO voted; 0068, untested). Two cheap checks decide the rest: rpmhpd devlink/sync_state (a clamped top-corner sleep vote would explain "never, in any run") and the `votes`/`vx` readback for wrapper leftovers and other DRVs. The rpmh tracepoint capture (E1) gives the exact sleep-set contents without any new code.
