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

	stage=$(mktemp -d)
	trap 'rm -rf "$stage"' EXIT INT TERM

	mutate_and_reject() {
		name=$1
		old=$2
		new=$3
		mutant=$stage/$name.patch
		replacement=$(printf '%s\n' "$new" | sed 's/&/\\\&/g')
		sed "s|$old|$replacement|" "$patch" >"$mutant"
		grep -Fq "$new" "$mutant"
		if ALLOW_UNPINNED_PATCH=1 SKIP_V9_UMBRELLA_RUN=1 \
			"$verifier" "$mutant" "$SOURCE_DIR" >/dev/null 2>&1
		then
			echo "FAIL verifier accepts $name mutation" >&2
			exit 1
		fi
	}

	mutate_and_reject writable-parameter \
		'module_param(gmu_clock_preparation_only, bool, 0400);' \
		'module_param(gmu_clock_preparation_only, bool, 0600);'
	mutate_and_reject preconsumed-open \
		'gmu_clock_preparation_only_open_consumed = ATOMIC_INIT(0)' \
		'gmu_clock_preparation_only_open_consumed = ATOMIC_INIT(1)'
	mutate_and_reject preattempted-state \
		'gmu_clock_preparation_only_state = ATOMIC_INIT(0)' \
		'gmu_clock_preparation_only_state = ATOMIC_INIT(1)'
	mutate_and_reject wrong-chip '0x06060001' '0x06060300'
	mutate_and_reject wrong-clock-count \
		'gmu->nr_clocks != 7' 'gmu->nr_clocks != 8'
	mutate_and_reject missing-core-clock-check \
		'IS_ERR_OR_NULL(gmu->core_clk)' 'false'
	mutate_and_reject skip-gmu-get-balance \
		'pm_runtime_put_noidle(gmu->dev);' 'gmu->dev = gmu->dev;'
	mutate_and_reject skip-gx-get-balance \
		'pm_runtime_put_noidle(gmu->gxpd);' 'gmu->gxpd = gmu->gxpd;'
	mutate_and_reject wrong-core-rate '200000000' '201000000'
	mutate_and_reject wrong-hub-rate '150000000' '151000000'
	mutate_and_reject skip-clock-disable \
		'clk_bulk_disable_unprepare(gmu->nr_clocks, gmu->clocks);' \
		'gmu->nr_clocks = gmu->nr_clocks;'
	mutate_and_reject skip-hub-rate-restore \
		'clk_set_rate(gmu->hub_clk, hub_rate)' \
		'clk_get_rate(gmu->hub_clk)'
	mutate_and_reject skip-core-rate-restore \
		'clk_set_rate(gmu->core_clk, core_rate)' \
		'clk_get_rate(gmu->core_clk)'
	mutate_and_reject async-gx-rollback \
		'pm_runtime_put_sync_suspend(gmu->gxpd)' \
		'pm_runtime_put(gmu->gxpd)'
	mutate_and_reject async-gmu-rollback \
		'pm_runtime_put_sync_suspend(gmu->dev)' \
		'pm_runtime_put(gmu->dev)'
	mutate_and_reject skip-cx-suspend \
		'pm_runtime_suspend(gmu->cxpd)' \
		'pm_runtime_active(gmu->cxpd)'
	mutate_and_reject skip-gx-state-check \
		'!pm_runtime_suspended(gmu->gxpd)' 'false'
	mutate_and_reject successful-open 'return -EUCLEAN;' 'return 0;'
fi

echo 'PASS A660 GMU clock-preparation patch is default-off, exact-chip, one-shot, seven-clock, rollback-safe, and pre-secure'
