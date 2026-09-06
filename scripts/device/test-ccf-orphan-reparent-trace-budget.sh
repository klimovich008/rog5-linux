#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch
ccf_patch=$repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch

[ -r "$patch" ] && [ -r "$ccf_patch" ]
limit=$(sed -n \
	's/^+#[[:space:]]*define ROG5_CCF_ORPHAN_TRACE_LIMIT \([0-9][0-9]*\)$/\1/p' \
	"$patch")
delay_ms=$(sed -n 's/^+.*msleep(\([0-9][0-9]*\));.*$/\1/p' \
	"$ccf_patch" | sort -u)
[ "$limit" = 4 ]
[ "$delay_ms" = 100 ]

common_phases=4
parent_phases=10
max_markers_per_orphan=$((common_phases + parent_phases))
[ "$max_markers_per_orphan" -eq 14 ]

for phase in \
	orphan-scan-entry \
	orphan-parent-lookup-begin \
	orphan-parent-lookup-complete \
	orphan-scan-complete
do
	[ "$(grep -Fc "\"$phase\"" "$patch")" -eq 1 ]
done
for phase in \
	orphan-parent-resolved \
	orphan-set-parent-before-begin \
	orphan-set-parent-before-complete \
	orphan-set-parent-after-begin \
	orphan-set-parent-after-complete \
	orphan-accuracy-begin \
	orphan-accuracy-complete \
	orphan-rates-begin \
	orphan-rates-complete \
	orphan-req-rate-complete
do
	[ "$(grep -Fc "\"$phase\"" "$patch")" -eq 1 ]
done

pre_scan_budget_ms=20000
probe_settle_ms=30000
reset_margin_ms=15000
watchdog_ms=75000
trace_budget_ms=$((limit * max_markers_per_orphan * delay_ms))
total_budget_ms=$((pre_scan_budget_ms + trace_budget_ms +
	probe_settle_ms + reset_margin_ms))
[ "$trace_budget_ms" -eq 5600 ]
[ "$total_budget_ms" -le "$watchdog_ms" ]

echo "PASS four-orphan trace is capped at $trace_budget_ms ms and leaves the required reset margin inside the 75-second watchdog"
