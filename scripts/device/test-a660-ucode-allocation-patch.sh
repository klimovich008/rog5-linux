#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch
verifier=$repo/scripts/device/verify-a660-ucode-allocation-patch.sh

[ -r "$patch" ] || {
	echo 'FAIL missing A660 ucode-allocation diagnostic patch' >&2
	exit 1
}
[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 ucode-allocation patch verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054 \
	6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2 \
	7f928abf51301516c63c834946e3b264b53416c016f4800729c2a9b1025f9c1e \
	b477ecc7f2396b4b65cb28eda9f454c885368277b421e5a11a2209ea4b317b2d \
	e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599 \
	29733589c6375930852cb26cfee674f83008084e6bdb792fd86164ea487bf85d \
	fefca6579b234fda7c0afdcf07d5c2dbb80aade92674c45380c661e259d9f9bb \
	bf109068950c2e04d6121a5aea8bee7c20d7c3535a05107728e197351fc6e3c6 \
	d3312f908da1702a4f0e63b3e9aed9f77ed7fe352381c2e31647b8225e2993ec \
	0954e9cc45a948c02dbecca34d41f1343f004880a983403baa668b3c96a095c2 \
	34ba40a1de4705b471a09266c51a1b5d20f06534faea6bff70d2b0025d185ae7 \
	5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5 \
	'0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch' \
	'0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch' \
	'module_param(ucode_allocation_only, bool, 0400)' \
	'ATOMIC_INIT(0)' \
	'atomic_cmpxchg' \
	'firmware_request_only && ucode_allocation_only' \
	'adreno_load_ucode_only' \
	'a6xx_ucode_unload' \
	'0x06060001' \
	'adreno_load_fw(adreno_gpu)' \
	'gpu->funcs->ucode_load(gpu)' \
	'msm_gem_unpin_iova' \
	'msm_gem_kernel_put' \
	'release_firmware' \
	'pwrup_reglist_bo' \
	'pwrup_reglist_emitted = false' \
	'return -EALREADY' \
	'return -EUCLEAN' \
	'load_gpu(dev)' \
	'context_init(dev, file)' \
	'pm_runtime' \
	'msm_gpu_hw_init' \
	'a6xx_hfi_start' \
	'qcom_scm_pas_auth_and_reset' \
	'PASS ucode-allocation patch is default-off, exact-A660, one-shot, rollback-complete, failed-open, and pre-power'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL ucode-allocation patch verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[[:space:]])(fastboot|adb|ssh|scp|pkexec|sudo)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$patch" "$verifier"
then
	echo 'FAIL ucode-allocation patch contract controls a device, storage, or privileges' >&2
	exit 1
fi

if [ -n "${SOURCE_DIR:-}" ]; then
	[ -d "$SOURCE_DIR" ]
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
		if ALLOW_UNPINNED_PATCH=1 \
			"$verifier" "$mutant" "$SOURCE_DIR" >/dev/null 2>&1
		then
			echo "FAIL verifier accepts $name mutation" >&2
			exit 1
		fi
	}

	mutate_and_reject writable-parameter \
		'module_param(ucode_allocation_only, bool, 0400);' \
		'module_param(ucode_allocation_only, bool, 0600);'
	mutate_and_reject preconsumed \
		'ucode_allocation_only_consumed = ATOMIC_INIT(0)' \
		'ucode_allocation_only_consumed = ATOMIC_INIT(1)'
	mutate_and_reject non-atomic \
		'atomic_cmpxchg' 'atomic_read'
	mutate_and_reject wrong-chip \
		'0x06060001' '0x06060300'
	mutate_and_reject skip-ucode \
		'ret = gpu->funcs->ucode_load(gpu);' 'ret = 0;'
	mutate_and_reject skip-shadow-rollback \
		'msm_gem_kernel_put(a6xx_gpu->shadow_bo, gpu->vm);' \
		'drm_gem_object_put(a6xx_gpu->shadow_bo);'
	mutate_and_reject skip-reglist-rollback \
		'msm_gem_kernel_put(a6xx_gpu->pwrup_reglist_bo, gpu->vm);' \
		'drm_gem_object_put(a6xx_gpu->pwrup_reglist_bo);'
	mutate_and_reject successful-open \
		'return -EUCLEAN;' 'return 0;'
fi

echo 'PASS A660 ucode-allocation diagnostic patch is mutation-tested, one-shot, rollback-complete, and isolated before GPU power'
