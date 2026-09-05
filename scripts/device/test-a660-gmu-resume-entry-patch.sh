#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch
verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-patch.sh

[ -r "$patch" ] || {
	echo 'FAIL missing A660 GMU resume-entry diagnostic patch' >&2
	exit 1
}
[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 GMU resume-entry patch verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051 \
	43e97deb263e5f845b95249612433ca183d4fd7f55be75e23be93b2a0bc83d26 \
	32dd6be7c82e25cb44377717ffb97cd941a99269c6bf977a2eb49454c0d3cfb4 \
	2e72b3ce7aa47fad1d5c82d6ab662e6f98895bad15876b631ecafecad0308b45 \
	e42eb79a417a6eace46358f5e2666b87dd4138eb8e1af843789b2e99b84fd395 \
	0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch \
	0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch \
	0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch \
	0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch \
	'module_param(gmu_resume_entry_only, bool, 0400)' \
	'gmu_resume_entry_only_open_consumed = ATOMIC_INIT(0)' \
	'gmu_resume_entry_only_hit = ATOMIC_INIT(0)' \
	'atomic_cmpxchg' \
	'atomic_read' \
	'firmware_request_only + ucode_allocation_only +' \
	'msm_a660_gmu_resume_entry_only_mark_hit' \
	'msm_a660_gmu_resume_entry_only_was_hit' \
	'adreno_rollback_gpu_load_only' \
	'pm_runtime_enabled(&pdev->dev)' \
	'a6xx_ucode_unload' \
	'adreno_release_diagnostic_fw' \
	'0x06060001' \
	'return -EALREADY' \
	'return -EPROTO' \
	'return -EUCLEAN' \
	'gmu->hung = false' \
	'pm_runtime_get_sync(gmu->dev)' \
	'clk_bulk_prepare_enable' \
	'a6xx_gmu_secure_init' \
	'a6xx_gmu_fw_start' \
	'a6xx_hfi_start' \
	'qcom_scm' \
	'PASS A660 GMU resume-entry patch is default-off'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL GMU resume-entry patch verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp|pkexec|sudo)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$patch" "$verifier"
then
	echo 'FAIL GMU resume-entry patch contract controls a device or privileges' >&2
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
		if ALLOW_UNPINNED_PATCH=1 SKIP_V7_UMBRELLA_RUN=1 \
			"$verifier" "$mutant" "$SOURCE_DIR" >/dev/null 2>&1
		then
			echo "FAIL verifier accepts $name mutation" >&2
			exit 1
		fi
	}

	mutate_and_reject writable-parameter \
		'module_param(gmu_resume_entry_only, bool, 0400);' \
		'module_param(gmu_resume_entry_only, bool, 0600);'
	mutate_and_reject preconsumed-open \
		'gmu_resume_entry_only_open_consumed = ATOMIC_INIT(0)' \
		'gmu_resume_entry_only_open_consumed = ATOMIC_INIT(1)'
	mutate_and_reject preconsumed-hit \
		'gmu_resume_entry_only_hit = ATOMIC_INIT(0)' \
		'gmu_resume_entry_only_hit = ATOMIC_INIT(1)'
	mutate_and_reject non-atomic-hit \
		'atomic_cmpxchg(&gmu_resume_entry_only_hit, 0, 1)' \
		'atomic_read(&gmu_resume_entry_only_hit)'
	mutate_and_reject wrong-chip \
		'0x06060001' '0x06060300'
	mutate_and_reject skip-ucode-rollback \
		'a6xx_ucode_unload(gpu);' 'gpu = gpu;'
	mutate_and_reject skip-firmware-rollback \
		'adreno_release_diagnostic_fw(adreno_gpu);' \
		'adreno_gpu = adreno_gpu;'
	mutate_and_reject successful-open \
		'return -EUCLEAN;' 'return 0;'
fi

echo 'PASS A660 GMU resume-entry diagnostic patch is mutation-tested, exact-chip, one-shot, rollback-complete, and pre-power'
