#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0017-drm-msm-add-a660-gmu-clock-preparation-diagnostic.patch
verifier=$repo/scripts/device/verify-a660-gmu-clock-preparation-patch.sh

[ -f "$patch" ] || {
	echo 'FAIL missing A660 GMU clock-preparation patch' >&2
	exit 1
}
[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 GMU clock-preparation patch verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	'module_param(gmu_clock_preparation_only, bool, 0400)' \
	'atomic_cmpxchg(&gmu_clock_preparation_only_state, 0, 1)' \
	'adreno_gpu->chip_id != 0x06060001' \
	'gmu->nr_clocks != 7' \
	'IS_ERR_OR_NULL(gmu->core_clk)' \
	'IS_ERR_OR_NULL(gmu->hub_clk)' \
	'pm_runtime_get_sync(gmu->dev)' \
	'pm_runtime_get_sync(gmu->gxpd)' \
	'pm_runtime_put_noidle(gmu->gxpd)' \
	'clk_get_rate(gmu->core_clk)' \
	'clk_get_rate(gmu->hub_clk)' \
	'clk_set_rate(gmu->core_clk, 200000000)' \
	'clk_set_rate(gmu->hub_clk, 150000000)' \
	'clk_bulk_prepare_enable(gmu->nr_clocks, gmu->clocks)' \
	'clk_bulk_disable_unprepare(gmu->nr_clocks, gmu->clocks)' \
	'pm_runtime_put_sync_suspend(gmu->gxpd)' \
	'pm_runtime_put_sync_suspend(gmu->dev)' \
	'pm_runtime_suspend(gmu->cxpd)' \
	'pm_runtime_suspended(gmu->gxpd)' \
	'pm_runtime_suspended(gmu->dev)' \
	'pm_runtime_suspended(gmu->cxpd)' \
	'return -EUCLEAN' \
	'PASS A660 GMU clock-preparation patch is'
do
	grep -Fq "$contract" "$patch" "$verifier" || {
		echo "FAIL GMU clock-preparation patch contract omits: $contract" >&2
		exit 1
	}
done

for forbidden in \
	'a6xx_gmu_secure_init(a6xx_gpu)' \
	'gmu_write(' \
	'enable_irq(' \
	'a6xx_gmu_fw_start(' \
	'a6xx_hfi_start(' \
	'adreno_zap_shader_load(' \
	'qcom_scm_pas_auth_and_reset('
do
	if grep -F "$forbidden" "$patch" | grep -v '^-' >/dev/null; then
		echo "FAIL GMU clock-preparation patch adds forbidden later work: $forbidden" >&2
		exit 1
	fi
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp|pkexec|sudo)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL GMU clock-preparation patch verifier controls a device or privileges' >&2
	exit 1
fi

if [ -n "${SOURCE_DIR:-}" ]; then
	"$verifier" "$patch" "$SOURCE_DIR"
fi

echo 'PASS A660 GMU clock-preparation patch is default-off, exact-chip, one-shot, seven-clock, rollback-safe, and pre-secure'
