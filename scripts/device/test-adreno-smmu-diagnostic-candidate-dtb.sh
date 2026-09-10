#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-adreno-smmu-diagnostic.dtso
builder=$repo/scripts/device/build-adreno-smmu-diagnostic-candidate-dtb.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$overlay" ] || {
	echo 'FAIL missing Adreno SMMU diagnostic overlay' >&2
	exit 1
}
[ -x "$builder" ] || {
	echo 'FAIL missing executable Adreno SMMU DT builder' >&2
	exit 1
}
sh -n "$builder"

[ "$(grep -c '^&' "$overlay")" -eq 2 ]
[ "$(grep -c '^&gpucc {' "$overlay")" -eq 1 ]
[ "$(grep -c '^&adreno_smmu {' "$overlay")" -eq 1 ]
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 2 ]

sed '/^&adreno_smmu {/,/^};/d' "$overlay" >"$stage/no-smmu.dtso"
printf 'dummy\n' >"$stage/base.dtb"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/no-smmu.dtso" "$stage/output.dtb" >/dev/null 2>&1; then
	echo 'FAIL builder accepted an overlay without the Adreno SMMU' >&2
	exit 1
fi

sed 's/^&adreno_smmu {/\&gpu {/' "$overlay" >"$stage/gpu-mutant.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/gpu-mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1; then
	echo 'FAIL builder accepted a GPU enablement' >&2
	exit 1
fi

awk '
	/^&adreno_smmu \{/ {
		print
		print "\tfirmware-name = \"qcom/a660_sqe.fw\";"
		next
	}
	{ print }
' "$overlay" >"$stage/firmware-mutant.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/firmware-mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1; then
	echo 'FAIL builder accepted a firmware property' >&2
	exit 1
fi

for contract in \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/ufshc@1d84000 \
	/soc@0/display-subsystem@ae00000 \
	/soc@0/remoteproc@3000000 \
	/soc@0/spmi@c440000/pmic@0/rtc@6100 \
	'qcom,sm8350-smmu-500 qcom,adreno-smmu qcom,smmu-500 arm,mmu-500' \
	'bus iface ahb hlos1_vote_gpu_smmu cx_gmu hub_cx_int hub_aon' \
	'wc -w)" -eq 14' \
	'wc -w)" -eq 2' \
	'wc -w)" -eq 36' \
	'dma-coherent'
do
	grep -Fq "$contract" "$builder" || {
		echo "FAIL Adreno SMMU builder omits: $contract" >&2
		exit 1
	}
done

if [ -n "${BASE_DTB:-}" ]; then
	[ -s "$BASE_DTB" ]
	"$builder" "$BASE_DTB" "$overlay" "$stage/one.dtb" >/dev/null
	"$builder" "$BASE_DTB" "$overlay" "$stage/two.dtb" >/dev/null
	cmp "$stage/one.dtb" "$stage/two.dtb"
fi

echo 'PASS Adreno SMMU diagnostic DT is deterministic, mutation-tested, and consumer-free'
