#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-a660-gmu-clock-preparation-boundary.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 GMU clock-preparation boundary verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	9ae66678340437c4a38b2d6ee390cc375e661548be97cb108bb8f891a418dee4 \
	6ba90691000f9369b5fdfdbf235495f9afeba4984c11596888cc1213717d7b06 \
	97b2fc130862f00445b509855b16121b2eba6e5a5228f92457c2923297fd4999 \
	39efbb61d7cc9a59e13f7e1ee9ebab6357d6fc4cbc981e8a89a28aa976b33755 \
	6c78ba4c8b58b99614fa0d7c3a6023e3d98754fc0fbf059c2bffc4ab431f11fc \
	58d28a520a21e21f55703ae968d6e45c6b7750e6a2d3138dcb6cafe2bc6d0a3c \
	f3170e9895ff60a89aab987db428cc5f50c0cfbe53335c8f0739b5be257ce16d \
	470df6235438d6b05e4f22f36627b7bb74c919ef3ca9a82654f6a982caecaee1 \
	'power_on = gdsc_gx_do_nothing_enable' \
	'gdsc_gx_do_nothing_enable' \
	'pm_runtime_get_sync(gmu->dev)' \
	'pm_runtime_get_sync(gmu->gxpd)' \
	'clk_get_rate(gmu->core_clk)' \
	'clk_get_rate(gmu->hub_clk)' \
	'clk_set_rate(gmu->core_clk, 200000000)' \
	'clk_set_rate(gmu->hub_clk' \
	'clk_bulk_prepare_enable(gmu->nr_clocks, gmu->clocks)' \
	'clk_bulk_disable_unprepare(gmu->nr_clocks, gmu->clocks)' \
	'pm_runtime_put_sync_suspend(gmu->gxpd)' \
	'pm_runtime_put_sync_suspend(gmu->dev)' \
	'a6xx_gmu_secure_init' \
	'enable_irq(gmu->gmu_irq)' \
	'a6xx_gmu_fw_start' \
	'a6xx_hfi_start' \
	'PASS A660 GMU clock-preparation boundary is'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL GMU clock-preparation boundary verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp|pkexec|sudo)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL GMU clock-preparation boundary verifier controls a device or privileges' >&2
	exit 1
fi

set +e
"$verifier" /nonexistent >/dev/null 2>&1
missing_source=$?
set -e
[ "$missing_source" -ne 0 ]

if [ -n "${SOURCE_DIR:-}" ]; then
	"$verifier" "$SOURCE_DIR"
fi

echo 'PASS A660 GMU clock-preparation source contract is v10-dependent, exact-SM8350, GX-aware, seven-clock, rollback-defined, and pre-secure'
