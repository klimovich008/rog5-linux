#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
prepare=$repo/scripts/device/prepare-mainline-gpucc-rcg2-diagnostic.sh
build=$repo/scripts/device/build-mainline-gpucc-rcg2-diagnostic.sh
generic_build=$repo/scripts/device/build-mainline-gpucc-parent-diagnostic.sh
loader=$repo/scripts/device/load-mainline-network-root.sh
probe=$repo/scripts/device/probe-mainline-coldplug-module.sh
acm=$repo/scripts/host/network-root-acm.py

for file in "$prepare" "$build" "$generic_build" "$loader" "$probe" "$acm"; do
	[ -x "$file" ]
done
sh -n "$prepare" "$build" "$generic_build" "$loader" "$probe"

grep -Fq \
	'0010-clk-qcom-trace-attended-SM8350-DISPCC-RCG-parent-read.patch' \
	"$prepare"
grep -Fq \
	'0010-clk-qcom-trace-attended-SM8350-DISPCC-RCG-parent-read.patch' \
	"$build"

for contract in \
	'6e40861cc51c067f9989c4513003e8fbd046c22f' \
	'49ef6cb95768496b8f926b11e428ea224406464e'
do
	grep -Fq "$contract" "$prepare"
	grep -Fq "$contract" "$generic_build"
done

for contract in \
	'rcg2_parent_trace=${ROG5_RCG2_PARENT_TRACE:-0}' \
	'command_line="$command_line rog5_rcg2_parent_trace=1"' \
	'awk '\''$0 == "rog5_rcg2_parent_trace=1" { count++ }'
do
	grep -Fq "$contract" "$loader"
done

for contract in \
	'rog5_rcg2_parent_trace=1' \
	'/sys/module/kernel/parameters/rog5_rcg2_parent_trace' \
	'RCG2 parent trace core parameter became writable'
do
	grep -Fq "$contract" "$probe"
done

grep -Fq 'ROG5_RCG2_PARENT_TRACE=1' "$acm"

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|pm_runtime_(get|put|resume|suspend)' \
	"$prepare" "$build" "$generic_build" "$loader" "$probe" "$acm"
then
	echo 'FAIL RCG2 integration adds flashing, storage, or runtime-PM control' >&2
	exit 1
fi

echo 'PASS RCG2 source, build, loader, ACM, and live preflight remain exact and behavior-preserving'
