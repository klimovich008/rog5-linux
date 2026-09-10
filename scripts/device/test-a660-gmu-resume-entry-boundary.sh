#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-boundary.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 GMU resume-entry boundary verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a \
	b212534041828bd81fc7e6684d87fea3f9b53151017a734e2ea77301d1905adc \
	'test-a660-ucode-allocation-v7-contract.sh' \
	'ret = adreno_load_fw(adreno_gpu)' \
	'gpu->funcs->ucode_load' \
	'pm_runtime_enable(&pdev->dev)' \
	'pm_runtime_get_sync(&pdev->dev)' \
	'pm_runtime_put_noidle(&pdev->dev)' \
	'pm_runtime_disable(&pdev->dev)' \
	'return gpu->funcs->pm_resume(gpu)' \
	'ret = a6xx_gmu_resume(a6xx_gpu)' \
	'gmu->hung = false' \
	'pm_runtime_get_sync(gmu->dev)' \
	'pm_runtime_get_sync(gmu->gxpd)' \
	'clk_set_rate(gmu->core_clk, 200000000)' \
	'clk_bulk_prepare_enable' \
	'a6xx_gmu_secure_init' \
	'a6xx_gmu_set_initial_bw' \
	'enable_irq(gmu->gmu_irq)' \
	'a6xx_gmu_fw_start' \
	'a6xx_hfi_start' \
	'adreno_zap_shader_load' \
	'qcom_scm_pas_auth_and_reset' \
	'PASS A660 GMU resume has an entry-only seam'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL GMU resume-entry boundary verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp|pkexec|sudo)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL GMU resume-entry boundary verifier controls a device or privileges' >&2
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

echo 'PASS A660 GMU resume-entry boundary is source-pinned, v7-dependent, error-propagating, and pre-power'
