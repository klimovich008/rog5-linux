#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-a660-firmware-only-boundary.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 firmware-only boundary verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f \
	2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79 \
	'verify-a660-registration-v3-live-acceptance.sh' \
	7f928abf51301516c63c834946e3b264b53416c016f4800729c2a9b1025f9c1e \
	e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599 \
	3bd1c6a4d15f1f31ecfbda2ea1d1a07d6b122eb2864adfaf6178e8942bc9fbe0 \
	f1089d825f7b52029520509a39de23c6c05c4ef432e6dff0b084dbdb4bf547b8 \
	29733589c6375930852cb26cfee674f83008084e6bdb792fd86164ea487bf85d \
	97b2fc130862f00445b509855b16121b2eba6e5a5228f92457c2923297fd4999 \
	23a033cf675cb898cfaf2f660ce3fc60a5728d85d5a6fe35e35ce169657dfd9f \
	'a660_sqe.fw' \
	'a660_gmu.bin' \
	'qcom/sm8350/a660_zap.mbn' \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d \
	'msm_open' \
	'load_gpu(dev)' \
	'adreno_load_gpu(dev)' \
	'adreno_load_fw(adreno_gpu)' \
	'gpu->funcs->ucode_load' \
	'pm_runtime_enable' \
	'pm_runtime_get_sync' \
	'msm_gpu_hw_init' \
	'request_firmware_direct' \
	'a6xx_hfi_start' \
	'qcom_scm_pas_auth_and_reset' \
	'firmware request can be isolated before ucode, runtime power, hardware init, HFI, and ZAP/SCM'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL firmware-only boundary verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'fastboot|adb|ssh|scp|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL firmware-only source verifier controls a device or storage' >&2
	exit 1
fi

set +e
"$verifier" /nonexistent /nonexistent >/dev/null 2>&1
missing_inputs=$?
set -e
[ "$missing_inputs" -ne 0 ]

if [ -n "${SOURCE_DIR:-}" ] || [ -n "${FIRMWARE_ROOT:-}" ]; then
	[ -d "${SOURCE_DIR:-}" ]
	[ -d "${FIRMWARE_ROOT:-}" ]
	"$verifier" "$SOURCE_DIR" "$FIRMWARE_ROOT"
fi

echo 'PASS A660 first-open firmware request is source-isolatable before every GPU power, hardware, HFI, and ZAP/SCM step'
