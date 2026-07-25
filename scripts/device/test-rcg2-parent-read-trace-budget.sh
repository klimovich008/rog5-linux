#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0010-clk-qcom-trace-attended-SM8350-DISPCC-RCG-parent-read.patch
ccf_patch=$repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch

[ -r "$patch" ] && [ -r "$ccf_patch" ]
limit=$(sed -n \
	's/^+#[[:space:]]*define ROG5_CCF_ORPHAN_TRACE_LIMIT \([0-9][0-9]*\)$/\1/p' \
	"$patch")
delay_ms=$(sed -n 's/^+.*msleep(\([0-9][0-9]*\));.*$/\1/p' \
	"$ccf_patch" "$patch" | sort -u)
[ "$limit" = 2 ]
[ "$delay_ms" = 100 ]

existing_markers_per_orphan=20
rcg2_markers_per_exact_read=2
exact_reads_in_probe=1
pre_scan_budget_ms=20000
probe_settle_ms=30000
reset_margin_ms=15000
watchdog_ms=75000
trace_budget_ms=$((limit * existing_markers_per_orphan * delay_ms +
	rcg2_markers_per_exact_read * exact_reads_in_probe * delay_ms))
total_budget_ms=$((pre_scan_budget_ms + trace_budget_ms +
	probe_settle_ms + reset_margin_ms))
spare_ms=$((watchdog_ms - total_budget_ms))

[ "$trace_budget_ms" -eq 4200 ]
[ "$total_budget_ms" -le "$watchdog_ms" ]
[ "$spare_ms" -ge 5000 ]

echo "PASS two-orphan RCG2 trace is capped at $trace_budget_ms ms, preserves the 15-second reset margin, and leaves $spare_ms ms spare"
