#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-a660-registration.dtso
builder=$repo/scripts/device/build-a660-registration-candidate-dtb.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$overlay" ] || {
	echo 'FAIL missing A660 registration overlay' >&2
	exit 1
}
[ -x "$builder" ] || {
	echo 'FAIL missing executable A660 registration DT builder' >&2
	exit 1
}
sh -n "$builder"

[ "$(grep -c '^&' "$overlay")" -eq 5 ]
for node in gpucc adreno_smmu gpu gmu gpu_zap_shader; do
	[ "$(grep -c "^&$node {" "$overlay")" -eq 1 ]
done
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 4 ]
grep -Fqx \
	'	firmware-name = "qcom/sm8350/a660_zap.mbn";' "$overlay"

sed '/^&gmu {/,/^};/d' "$overlay" >"$stage/no-gmu.dtso"
printf 'dummy\n' >"$stage/base.dtb"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/no-gmu.dtso" "$stage/output.dtb" >/dev/null 2>&1
then
	echo 'FAIL builder accepted an overlay without the GMU' >&2
	exit 1
fi

sed 's/status = "okay";/status = "disabled";/' "$overlay" \
	>"$stage/disabled-mutant.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/disabled-mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1
then
	echo 'FAIL builder accepted a disabled registration dependency' >&2
	exit 1
fi

awk '
	/^&gpu \{/ {
		print
		print "\treg = <0 0 0 0>;"
		next
	}
	{ print }
' "$overlay" >"$stage/register-mutant.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/register-mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1
then
	echo 'FAIL builder accepted a GPU register override' >&2
	exit 1
fi

for contract in \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/gpu@3d00000/zap-shader \
	'qcom,adreno-660.1 qcom,adreno' \
	'qcom,adreno-gmu-660.1 qcom,adreno-gmu' \
	'qcom/sm8350/a660_zap.mbn' \
	'/reserved-memory/memory@8b51a000' \
	'/soc@0/ufshc@1d84000' \
	'/soc@0/display-subsystem@ae00000' \
	'/soc@0/remoteproc@3000000'
do
	grep -Fq "$contract" "$builder" || {
		echo "FAIL A660 registration DT builder omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'build-gpu-candidate-dtb|build-gpu-recovery-initramfs|fastboot|adb|[[:space:]]mount[[:space:]]|[[:space:]]dd[[:space:]]' \
	"$overlay" "$builder"
then
	echo 'FAIL A660 registration DT path uses an unsafe historical or device-control path' >&2
	exit 1
fi

if [ -n "${BASE_DTB:-}" ]; then
	[ -s "$BASE_DTB" ]
	"$builder" "$BASE_DTB" "$overlay" "$stage/one.dtb" >/dev/null
	"$builder" "$BASE_DTB" "$overlay" "$stage/two.dtb" >/dev/null
	cmp "$stage/one.dtb" "$stage/two.dtb"
fi

echo 'PASS A660 registration DT is deterministic, mutation-tested, and storage-disabled'
