#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-a660-ucode-allocation-boundary.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 ucode-allocation boundary verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	f5e1226923f82528e8cc2ad2727d38834c64761d7691559e295da43fafcfbd8c \
	912846d98ef6ee9fb3c0fa9f0b455c49d47a2f43ff72e2ba1d14c1c284cbfe32 \
	'verify-a660-firmware-request-only-v4-live-acceptance.sh' \
	e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599 \
	3bd1c6a4d15f1f31ecfbda2ea1d1a07d6b122eb2864adfaf6178e8942bc9fbe0 \
	f1089d825f7b52029520509a39de23c6c05c4ef432e6dff0b084dbdb4bf547b8 \
	29733589c6375930852cb26cfee674f83008084e6bdb792fd86164ea487bf85d \
	fefca6579b234fda7c0afdcf07d5c2dbb80aade92674c45380c661e259d9f9bb \
	5a20c0a5151a8da2646380cddf14f6cdfa34a8f953b5330fe613774ae695daa6 \
	b477ecc7f2396b4b65cb28eda9f454c885368277b421e5a11a2209ea4b317b2d \
	49b304a0602361647d9cd86acc5b798b93bfcb2c275fa88e4b0eb05eb0290b53 \
	76840d1c84d6cc3b3b34b094c799f4d682998d10ac3d7888bf189b7540b869f1 \
	7bca4eda8aa3711b3fc0b3e3b74ff4f775ca94e6e13296cee761ee588ed4c1a2 \
	d196c1c9efb4af66729bf8eaeb26510f707b7acc1bc4edb43530315602785e29 \
	'ADRENO_CHIP_IDS(0x06060001)' \
	'ADRENO_QUIRK_HAS_HW_APRIV' \
	'[ADRENO_FW_SQE] = "a660_sqe.fw"' \
	'[ADRENO_FW_GMU] = "a660_gmu.bin"' \
	'adreno_fw_create_bo' \
	'fw->size - 4' \
	'MSM_BO_WC | MSM_BO_GPU_READONLY' \
	'MSM_BO_WC | MSM_BO_MAP_PRIV' \
	'msm_gem_kernel_new' \
	'msm_gem_get_and_pin_iova' \
	'msm_gem_pin_vma_locked' \
	'msm_gem_vma_map' \
	'iommu_map_sgtable' \
	'three new GPU-VM mappings' \
	'one SQE object, one shadow object, and one power-up reglist object' \
	'no AQE object' \
	'before GPU/GMU runtime power, register access, HFI, and ZAP/SCM' \
	'explicitly release all three objects and mappings' \
	'one-shot' \
	'normal a6xx_destroy does not release pwrup_reglist_bo' \
	'PASS A660 ucode allocation is source-isolatable with three SMMU mappings and mandatory explicit rollback'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL ucode-allocation boundary verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'fastboot|adb|ssh|scp|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|pkexec|sudo' \
	"$verifier"
then
	echo 'FAIL ucode-allocation source verifier controls a device or privileges' >&2
	exit 1
fi

set +e
"$verifier" /nonexistent >/dev/null 2>&1
missing_source=$?
set -e
[ "$missing_source" -ne 0 ]

if [ -n "${SOURCE_DIR:-}" ]; then
	[ -d "$SOURCE_DIR" ]
	"$verifier" "$SOURCE_DIR"
fi

echo 'PASS A660 ucode allocation has an offline-tested pre-power boundary with explicit three-object rollback required'
