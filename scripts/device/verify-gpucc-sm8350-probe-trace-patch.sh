#!/bin/sh
set -eu

patch=${1:?usage: verify-gpucc-sm8350-probe-trace-patch.sh PATCH [PINNED_SOURCE]}
source_dir=${2:-}

[ -r "$patch" ]
[ "$(git apply --numstat "$patch" | wc -l)" -eq 1 ]
git apply --numstat "$patch" |
	grep -Eq '^[0-9]+[[:space:]]+[0-9]+[[:space:]]+drivers/clk/qcom/gpucc-sm8350[.]c$'

grep -Fq 'static bool probe_trace;' "$patch"
grep -Fq 'module_param(probe_trace, bool, 0400);' "$patch"
grep -Fq 'MODULE_PARM_DESC(probe_trace,' "$patch"
[ "$(grep -c '^+.*ROG5 GPUCC diagnostic:' "$patch")" -eq 8 ]

for marker in \
	'ROG5 GPUCC diagnostic: begin' \
	'ROG5 GPUCC diagnostic: map-complete' \
	'ROG5 GPUCC diagnostic: pll0-begin' \
	'ROG5 GPUCC diagnostic: pll0-complete' \
	'ROG5 GPUCC diagnostic: pll1-begin' \
	'ROG5 GPUCC diagnostic: pll1-complete' \
	'ROG5 GPUCC diagnostic: registration-begin' \
	'ROG5 GPUCC diagnostic: registration-complete ret=%d'
do
	grep -Fq "$marker" "$patch"
done

added=$(sed -n 's/^+//p' "$patch")
if printf '%s\n' "$added" |
	grep -Eq 'regmap_(write|update_bits)|writel|writeq|clk_(prepare_)?enable|regulator_(enable|set_voltage)|reset_control_|pm_runtime_|gdsc_(enable|disable)|status[[:space:]]*=[[:space:]]*"okay"|fastboot|/dev/'
then
	echo 'FAIL GPUCC trace patch adds a hardware-control or persistent-write path' >&2
	exit 1
fi

if [ -n "$source_dir" ]; then
	[ -d "$source_dir/.git" ]
	[ "$(git -C "$source_dir" rev-parse HEAD)" = \
		7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 ]
	[ -z "$(git -C "$source_dir" status --porcelain)" ]
	git -C "$source_dir" apply --check "$patch"
fi

echo 'PASS GPUCC trace patch is default-off, read-only, phase-complete, and touches one driver'
