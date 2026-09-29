#!/bin/sh
# One 60 s suspend (systemctl suspend, RTC wake) with before/after counters,
# glink/irq/rpmh/wakeup tracing and the AOP CXPC violator log.
# Usage: sx.sh TAG [pre-command]   results in /var/tmp/sx-TAG/
TAG=$1; PRE=$2; SECS=${SECS:-60}
D=/var/tmp/sx-$TAG; rm -rf $D; mkdir -p $D
S=/sys/kernel/debug/qcom_stats; T=/sys/kernel/tracing
exec > $D/log 2>&1
set -x
systemctl stop rog5-sleep-policy
trap 'systemctl start rog5-sleep-policy' EXIT
[ -n "$PRE" ] && sh -c "$PRE"
snap() {
  for s in cxsd aosd ddr adsp adsp_island slpi slpi_island apss; do printf '%s ' $s; tr '\n' ' ' < $S/$s; echo; done > $D/stats.$1
  cat $S/ddr_stats > $D/ddr.$1
  cat /proc/interrupts > $D/irq.$1
  (cd /sys/kernel/debug/clk; for c in *; do [ -f $c/clk_enable_count ] && e=$(cat $c/clk_enable_count) && [ "$e" != 0 ] && echo "$c $e"; done) > $D/clk.$1
  cat /sys/kernel/debug/wakeup_sources > $D/ws.$1
  cat /sys/kernel/debug/pm_genpd/power-domain-cpu-cluster0/idle_states > $D/cl.$1 2>/dev/null
}
echo 0 > $T/tracing_on; echo > $T/trace; echo 16384 > $T/buffer_size_kb
echo > $T/set_event
echo ${TCLK:-boot} > $T/trace_clock
for e in clk:clk_enable clk:clk_disable qcom_glink rpmh:rpmh_send_msg power:wakeup_source_activate irq:irq_handler_entry qcom_smp2p ucsi; do echo "$e" >> $T/set_event; done
echo 'name ~ "*glink*" || name ~ "*ipcc*" || name ~ "*smp2p*" || name ~ "*rtc*" || name ~ "*pwrkey*" || name ~ "*usb*" || name ~ "*dwc*" || name ~ "*xhci*"' > $T/events/irq/irq_handler_entry/filter
if [ -e /sys/kernel/debug/rog5-aop-qmp/send ]; then
  echo "{class: lpm_mon, type: ${VXT:-cxpc}, dur: 1000, flush: 5, ts_adj: 1}" > /sys/kernel/debug/rog5-aop-qmp/send
fi
snap before
before=$(cat /sys/power/suspend_stats/success)
echo 1 > $T/tracing_on
echo "sx-$TAG: suspend start" > /dev/kmsg
# Never suspend without a wake alarm (review 2026-09-29).
rtcwake -m no -s $SECS || { echo "sx-$TAG: rtcwake failed, not suspending" > /dev/kmsg; echo 0 > $T/tracing_on; exit 1; }
systemctl suspend --check-inhibitors=no
i=0; while [ "$(cat /sys/power/suspend_stats/success)" = "$before" ] && [ $i -lt $((SECS+60)) ]; do sleep 1; i=$((i+1)); done
sleep 2
echo 0 > $T/tracing_on
snap after
cat $T/trace > $D/trace
echo > $T/set_event; echo 0 > $T/events/irq/irq_handler_entry/filter; echo > $T/trace; echo 1408 > $T/buffer_size_kb; echo local > $T/trace_clock
[ -e /sys/kernel/debug/rog5-sleep-blockers/vx ] && cat /sys/kernel/debug/rog5-sleep-blockers/vx > $D/vx && cat /sys/kernel/debug/rog5-sleep-blockers/vx_raw > $D/vx_raw
journalctl -k -b --since "-$((SECS+80)) s" --no-pager > $D/kmsg
echo "success $before -> $(cat /sys/power/suspend_stats/success) waited $i"
echo DONE > $D/done
