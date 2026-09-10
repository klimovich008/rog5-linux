#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
helper=$repo/initramfs/rog5-charging-firmware.sh

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ -f $helper ]] || fail 'charging firmware resolver is missing'
sh -n "$helper"
# shellcheck source=/dev/null
. "$helper"

work=$(mktemp -d)
cleanup() {
	find "$work" -depth -mindepth 1 -delete 2>/dev/null || true
	rmdir "$work" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM
sys_block=$work/sys/class/block
dev_root=$work/dev
mkdir -p "$sys_block" "$dev_root"

add_partition() {
	local node=$1
	local partname=$2
	local start=$3
	local size=$4
	local devname=${5:-$node}
	mkdir -p "$sys_block/$node"
	printf 'DEVNAME=%s\nDEVTYPE=partition\nPARTNAME=%s\n' \
		"$devname" "$partname" >"$sys_block/$node/uevent"
	printf '%s\n' "$start" >"$sys_block/$node/start"
	printf '%s\n' "$size" >"$sys_block/$node/size"
	: >"$dev_root/$node"
}

expect_refusal() {
	if rog5_resolve_exact_partition \
		"$sys_block" "$dev_root" modem_b 1704888 450560 >/dev/null 2>&1; then
		fail "$1 was accepted"
	fi
}

expect_refusal 'zero candidate'
add_partition sdg28 modem_b 1704888 450560
resolved=$(rog5_resolve_exact_partition \
	"$sys_block" "$dev_root" modem_b 1704888 450560)
[[ $resolved == "$dev_root/sdg28" ]] || fail 'exact modem_b did not resolve'

add_partition sdg29 modem_b 1704888 450560
expect_refusal 'duplicate candidate'
find "$sys_block/sdg29" -depth -delete
rm -f "$dev_root/sdg29"

printf '%s\n' 1704889 >"$sys_block/sdg28/start"
expect_refusal 'wrong start sector'
printf '%s\n' 1704888 >"$sys_block/sdg28/start"
printf '%s\n' 450559 >"$sys_block/sdg28/size"
expect_refusal 'wrong size'
printf '%s\n' 450560 >"$sys_block/sdg28/size"
printf 'DEVNAME=../sdg28\nDEVTYPE=partition\nPARTNAME=modem_b\n' \
	>"$sys_block/sdg28/uevent"
expect_refusal 'path-like DEVNAME'
printf 'DEVNAME=sdg28\nDEVTYPE=partition\nPARTNAME=modem_a\n' \
	>"$sys_block/sdg28/uevent"
expect_refusal 'wrong slot partition'

echo 'PASS charging firmware resolver accepts only exact unique modem_b geometry'
