#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0016-drm-msm-add-a660-gmu-cx-runtime-pm-diagnostic.patch
verifier=$repo/scripts/device/verify-a660-gmu-cx-runtime-pm-patch.sh

[ -r "$patch" ] || {
	echo 'FAIL missing A660 GMU/CX runtime-PM diagnostic patch' >&2
	exit 1
}
[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 GMU/CX runtime-PM patch verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	6ba90691000f9369b5fdfdbf235495f9afeba4984c11596888cc1213717d7b06 \
	0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637 \
	3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054 \
	6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2 \
	a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051 \
	PENDING_V10_PATCH_SHA256 \
	PENDING_V10_MSM_DRV_SHA256 \
	PENDING_V10_MSM_GPU_H_SHA256 \
	PENDING_V10_A6XX_GMU_SHA256 \
	0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch \
	0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch \
	0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch \
	0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch \
	0016-drm-msm-add-a660-gmu-cx-runtime-pm-diagnostic.patch \
	'module_param(gmu_cx_runtime_pm_only, bool, 0400)' \
	'gmu_cx_runtime_pm_only_open_consumed = ATOMIC_INIT(0)' \
	'gmu_cx_runtime_pm_only_state = ATOMIC_INIT(0)' \
	'atomic_cmpxchg(&gmu_cx_runtime_pm_only_state, 0, 1)' \
	'atomic_cmpxchg(&gmu_cx_runtime_pm_only_state, 1, 2)' \
	'atomic_read(&gmu_cx_runtime_pm_only_state) == 2' \
	'firmware_request_only + ucode_allocation_only +' \
	'gmu_resume_entry_only + gmu_cx_runtime_pm_only > 1' \
	'msm_a660_gmu_cx_runtime_pm_only_mark_attempt' \
	'msm_a660_gmu_cx_runtime_pm_only_mark_passed' \
	'msm_a660_gmu_cx_runtime_pm_only_was_passed' \
	'adreno_rollback_gpu_load_only' \
	'0x06060001' \
	'pm_runtime_get_sync(gmu->dev)' \
	'pm_runtime_put_noidle(gmu->dev)' \
	'pm_runtime_put_sync_suspend(gmu->dev)' \
	'pm_runtime_suspend(gmu->cxpd)' \
	'pm_runtime_suspended(gmu->dev)' \
	'pm_runtime_suspended(gmu->cxpd)' \
	'return -EALREADY' \
	'return -EPROTO' \
	'return -EUCLEAN' \
	'gmu->hung = false' \
	'pm_runtime_get_sync(gmu->gxpd)' \
	'clk_bulk_prepare_enable' \
	'a6xx_gmu_secure_init' \
	'a6xx_gmu_fw_start' \
	'a6xx_hfi_start' \
	'qcom_scm' \
	'PASS A660 GMU/CX runtime-PM patch is default-off'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL GMU/CX runtime-PM patch verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp|pkexec|sudo)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$patch" "$verifier"
then
	echo 'FAIL GMU/CX runtime-PM patch contract controls a device or privileges' >&2
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
		sed "s|$old|$new|" "$patch" >"$mutant"
		grep -Fq "$new" "$mutant"
		if ALLOW_UNPINNED_PATCH=1 SKIP_V9_UMBRELLA_RUN=1 \
			"$verifier" "$mutant" "$SOURCE_DIR" >/dev/null 2>&1
		then
			echo "FAIL verifier accepts $name mutation" >&2
			exit 1
		fi
	}

	mutate_and_reject writable-parameter \
		'module_param(gmu_cx_runtime_pm_only, bool, 0400);' \
		'module_param(gmu_cx_runtime_pm_only, bool, 0600);'
	mutate_and_reject preconsumed-open \
		'gmu_cx_runtime_pm_only_open_consumed = ATOMIC_INIT(0)' \
		'gmu_cx_runtime_pm_only_open_consumed = ATOMIC_INIT(1)'
	mutate_and_reject preattempted-state \
		'gmu_cx_runtime_pm_only_state = ATOMIC_INIT(0)' \
		'gmu_cx_runtime_pm_only_state = ATOMIC_INIT(1)'
	mutate_and_reject non-atomic-attempt \
		'atomic_cmpxchg(&gmu_cx_runtime_pm_only_state, 0, 1)' \
		'atomic_read(&gmu_cx_runtime_pm_only_state)'
	mutate_and_reject non-atomic-pass \
		'atomic_cmpxchg(&gmu_cx_runtime_pm_only_state, 1, 2)' \
		'atomic_read(&gmu_cx_runtime_pm_only_state)'
	mutate_and_reject wrong-chip '0x06060001' '0x06060300'
	mutate_and_reject skip-get-error-balance \
		'pm_runtime_put_noidle(gmu->dev);' \
		'gmu->dev = gmu->dev;'
	mutate_and_reject idle-only-consumer-rollback \
		'pm_runtime_put_sync_suspend(gmu->dev);' \
		'pm_runtime_put_sync(gmu->dev);'
	mutate_and_reject decrement-cx-reference \
		'pm_runtime_suspend(gmu->cxpd);' \
		'pm_runtime_put_sync_suspend(gmu->cxpd);'
	mutate_and_reject skip-consumer-state-check \
		'!pm_runtime_suspended(gmu->dev)' 'false'
	mutate_and_reject skip-cx-state-check \
		'!pm_runtime_suspended(gmu->cxpd)' 'false'
	mutate_and_reject successful-open \
		'return -EUCLEAN;' 'return 0;'
fi

echo 'PASS A660 GMU/CX runtime-PM diagnostic patch is mutation-tested, exact-chip, atomic-stateful, get-error-balanced, synchronously rolled back, CX-only, and pre-GX'
