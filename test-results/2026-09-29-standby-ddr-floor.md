# ROG5 standby: who keeps DDR at 200 MHz in s2idle (r185, kernel r86)

2026-09-29, default bundle production-7.2.7-r185. The phone was on the side-port
USB-C hub (USB power online, battery Full), so the metric is the RPMh/DDR
counters, not battery current. Every run: rog5-sleep-policy stopped, AOP CXPC
violator log armed, `rtcwake -m no -s 60` + `systemctl suspend
--check-inhibitors=no`, qcom_stats/ddr_stats/interrupts/clocks read before and
after, tracefs (boot clock) on qcom_glink, rpmh_send_msg, clk enable/disable,
wakeup_source_activate and ipcc/glink/usb/rtc IRQs. Tools:
`tools/standby_probe/` (sx.sh, ddrdiff.sh, rog5-holdbw.c, rog5-aop-qmp.c).

## Result: the APPS side is clean; the 200 MHz floor comes from another RPMh master

cxsd/aosd/ddr stayed 0 in all six runs; the CXPC violator log showed
DDR_AUX=5 in every sample (AUDIO=1 or HLOS at entry/exit only).

| run | change before the 60 s suspend | DDR during suspend (ddr_stats delta) |
|---|---|---|
| base | none | 200 MHz 57.4 s, +14 entries; 451 MHz 9.3 s (awake part) |
| clk | clock trace added | 200 MHz 56.8 s, +14 |
| perfoff | AOP `{class: ddr, perfmode: off}` | 200 MHz 56.6 s, +14 (no change) |
| clients | APR audio + both fastrpc channels unbound, hexagonrpcd + iio-sensor-proxy stopped | 200 MHz 57.4 s, +10 (no change) |
| hold | rog5-holdbw: ACTIVE_ONLY 10 GB/s DDR vote held through suspend | awake at 2736 MHz, **suspended at 200 MHz 56.1 s** |
| noadsp | ADSP stopped before suspend | 451 MHz 64.7 s, no 200 MHz entries |

What this shows:

1. **The APPS RSC sleep set is applied in s2idle.** With a 10 GB/s
   active-only vote held by a module (DDR at 2736 MHz while awake), DDR still
   dropped to 200 MHz for the whole suspend. If the cluster never reached the
   RSC sleep handshake, DDR would have stayed at 2736 MHz. (A 200 MHz floor
   alone cannot tell this apart: the APPS wake/AMC MC0 vote at entry is
   y=1000 = 3.2 GB/s = exactly CP1, from icc_bwmon plus the MC0 keepalive.)
2. **The APPS sleep TCS carries zero DDR votes.** At s2idle entry the flush
   writes MC0/SH0/SH4/SN0/MM0/CN0/QUP0-2/ACV all 0 (valid bit clear); it is
   written once (cache clean afterwards). No GCC clock is enabled at that
   point (clock trace from `clk_enable_count` + events): only bi_tcxo/xo_board.
3. **Linux-side DSP clients do not matter.** Removing APR audio, fastrpc and
   the sensor daemons changed nothing.
4. **The floor holder is not HLOS.** Candidates left: the ADSP (AUDIO) or
   SLPI (SENSOR) sleep sets, TZ, HYP (Gunyah), SECPROC (SPSS never loaded by
   Linux), L3/DEBUG/ARC_CPRF; DISPLAY was zeroed earlier (0086) and the GPU
   DRV only ever votes zero (a660 HFI bw table, level 0 = SH0/ACV/MC0 off).
5. **A stopped DSP freezes its last active DDR vote.** After an ADSP stop, DDR
   sat at 451 MHz (the ADSP's awake vote) for the whole suspend. Stop-based
   eliminations of ADSP or SLPI can't settle this; the earlier ADSP/SLPI stop
   runs were inconclusive for this reason.

## Wake-ups while suspended (trace with the boot clock)

s2idle entry 948.1 s, RTC wake 1004.9 s: the APSS woke only twice (960.7 s,
991.3 s, 30 s apart). Each time the ADSP sent battmgr messages on
PMIC_RTR_ADSP_APPS (144-byte status + a 16-byte notification ->
qcom-battmgr-bat wakeup source), then ~30 request/response pairs of 24 bytes
(power_supply property reads from the uevent). No UCSI traffic. So the APSS
sleeps 12-30 s at a time. The ~14 DDR 200 MHz re-entries per minute come
mostly from the ADSP, which wakes ~7-30 times a minute (qcom_stats adsp)
without waking the APSS. ADSP stop removed them.

## Other checks

- `{class: lpm_mon, type: ddr}` clears the violator region and writes nothing
  across a suspend (the same as before); only cxpc logs.
- `{class: ddr, res: drvs_ddr_votes}` does not change the message RAM (raw
  dump of 0x200 bytes before/after): this AOP doesn't publish per-DRV DDR
  votes.
- ddr_stats LPM entries (0xd4/0xd3/0x11/0xd0) are 0 since boot, even awake.

## Side effects (phone left degraded, needs one reboot)

The client unbind/rebind and the ADSP stop/start left three things broken:
- q6afe-clock failed to re-register (`LPASS_CLK_ID_PRI_MI2S_IBIT` -EINVAL),
  so the VA macro (microphones) returns -EINVAL.
- The SLPI fastrpc channel vanished. An SLPI stop/start to get it back hits
  "watchdog received: SFR Init" 2 s after boot and stays offline, so there
  are no sensors, and rog5-sensors.service restart-loops.
- After the ADSP restart, UCSI reported the side port as a device role; the
  hub's xHCI was removed and `data_role host` timed out.
Charging (battmgr, USB online) and Wi-Fi are fine. A normal reboot restores
all three. Lesson: runtime SLPI restarts don't work on this firmware (it
needs the boot-time sequence); don't unbind the APR/fastrpc rpmsg devices.

## Next step

Split the remaining masters with boot-time bisects, since runtime stops leave
stale votes:
1. Default install with the SLPI remoteproc disabled in the DTB (init only
   needs the ADSP), one 60 s suspend: if cxsd/ddr > 0, the SLPI sleep set is
   the holder (then look at SSC registry/island config).
2. If not: the ADSP can't be left out of this init (battmgr/UCSI gate the
   boot). Either build a ramdisk variant that skips the ADSP for one test
   boot, or compare with the stock 5.4 wrapper (qcom_stats + ddr_stats in its
   RAM session, same ADSP firmware with stock clients; that path needs
   fastboot, so the user must approve it).
3. SPSS/CDSP/modem are never loaded under Linux but always under stock;
   loading the CDSP (firmware from vendor_a) is the other cheap stock
   difference to try.
