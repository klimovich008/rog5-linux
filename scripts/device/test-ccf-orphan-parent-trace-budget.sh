#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0009-clk-trace-attended-SM8350-GPUCC-orphan-parent-lookup.patch
orphan_patch=$repo/patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch
ccf_patch=$repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch

[ -r "$patch" ] && [ -r "$orphan_patch" ] && [ -r "$ccf_patch" ]
limit=$(sed -n \
	's/^+#[[:space:]]*define ROG5_CCF_ORPHAN_TRACE_LIMIT \([0-9][0-9]*\)$/\1/p' \
	"$orphan_patch")
delay_ms=$(sed -n 's/^+.*msleep(\([0-9][0-9]*\));.*$/\1/p' \
	"$ccf_patch" | sort -u)
[ "$limit" = 4 ]
[ "$delay_ms" = 100 ]

existing_markers_per_orphan=14
inner_markers_per_orphan=6
max_markers_per_orphan=$((existing_markers_per_orphan +
	inner_markers_per_orphan))
[ "$max_markers_per_orphan" -eq 20 ]

for phase in \
	orphan-parent-shape \
	orphan-runtime-state \
	orphan-get-parent-begin \
	orphan-get-parent-complete \
	orphan-parent-cache-begin \
	orphan-parent-cache-complete
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
spare_ms=$((watchdog_ms - total_budget_ms))
[ "$trace_budget_ms" -eq 8000 ]
[ "$total_budget_ms" -le "$watchdog_ms" ]
[ "$spare_ms" -ge 2000 ]

echo "PASS four-orphan inner trace is capped at $trace_budget_ms ms, preserves the 15-second reset margin, and leaves $spare_ms ms spare"
