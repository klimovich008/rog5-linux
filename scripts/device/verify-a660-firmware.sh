#!/bin/sh
set -eu

root=${1:?usage: verify-a660-firmware.sh FIRMWARE_ROOT}

check_hash() {
	file=$root/$1
	[ -s "$file" ]
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$2" ]
}

check_hash qcom/a660_sqe.fw d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76
check_hash qcom/a660_gmu.bin 8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7
check_hash qcom/sm8350/a660_zap.mbn 5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d
readelf -h "$root/qcom/sm8350/a660_zap.mbn" | grep -q 'Class:.*ELF32'
readelf -h "$root/qcom/sm8350/a660_zap.mbn" | grep -q 'Machine:.*QUALCOMM DSP6'

echo 'PASS pinned A660 SQE, GMU, and SM8350 zap-shader firmware'
