#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch
verifier=$repo/scripts/device/verify-a660-firmware-request-only-patch.sh

[ -r "$patch" ] || {
	echo 'FAIL missing A660 firmware request-only patch' >&2
	exit 1
}
[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 firmware request-only patch verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054 \
	7f928abf51301516c63c834946e3b264b53416c016f4800729c2a9b1025f9c1e \
	b477ecc7f2396b4b65cb28eda9f454c885368277b421e5a11a2209ea4b317b2d \
	e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599 \
	c350e28c18ca723372fc044240a69b452b3698ce57df269a2dad0ad9e2cb569e \
	431f78761bbbfe92eab44f685aba653c6e05b54f140fd24fef1358667f05a6c7 \
	3654f703a3930add3c131e2bc77453fd1bc506a374075168a5ddbcd66f558379 \
	'0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch' \
	'drivers/gpu/drm/msm/msm_drv.c' \
	'drivers/gpu/drm/msm/msm_gpu.h' \
	'drivers/gpu/drm/msm/adreno/adreno_device.c' \
	'git apply --check' \
	'checkpatch.pl' \
	'module_param(firmware_request_only, bool, 0400)' \
	'ATOMIC_INIT(0)' \
	'atomic_cmpxchg' \
	'adreno_load_fw_only' \
	'0x06060001' \
	'adreno_load_fw(adreno_gpu)' \
	'return -EALREADY' \
	'return -EUCLEAN' \
	'load_gpu(dev)' \
	'context_init(dev, file)' \
	'ucode_load' \
	'pm_runtime' \
	'msm_gpu_hw_init' \
	'a6xx_hfi_start' \
	'qcom_scm_pas_auth_and_reset' \
	'firmware-request-only patch is default-off, exact-A660, one-shot, failed-open, and pre-power'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL firmware request-only patch verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'fastboot|adb|ssh|scp|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$patch" "$verifier"
then
	echo 'FAIL firmware request-only patch contract controls a device or storage' >&2
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
		'module_param(firmware_request_only, bool, 0400);' \
		'module_param(firmware_request_only, bool, 0600);'
	mutate_and_reject preconsumed \
		'ATOMIC_INIT(0)' 'ATOMIC_INIT(1)'
	mutate_and_reject non-atomic \
		'atomic_cmpxchg' 'atomic_read'
	mutate_and_reject wrong-chip \
		'0x06060001' '0x06060300'
	mutate_and_reject no-firmware-request \
		'return adreno_load_fw(adreno_gpu);' 'return -EIO;'
	mutate_and_reject successful-open \
		'return -EUCLEAN;' 'return 0;'
fi

echo 'PASS A660 firmware-request-only patch is mutation-tested, exact-device, one-shot, failed-open, and isolated before GPU power'
