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

sed '/^&gpu_zap_shader {/,/^};/d' "$overlay" >"$stage/no-zap.dtso"
printf 'dummy\n' >"$stage/base.dtb"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/no-zap.dtso" "$stage/output.dtb" >/dev/null 2>&1
then
	echo 'FAIL builder accepted an overlay without the ZAP shader' >&2
	exit 1
fi

sed '/^&gmu {/,/^};/d' "$overlay" >"$stage/no-gmu.dtso"
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

sed 's#qcom/sm8350/a660_zap.mbn#qcom/a660_zap.mbn#' "$overlay" \
	>"$stage/firmware-mutant.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/firmware-mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1
then
	echo 'FAIL builder accepted an unpinned ZAP firmware path' >&2
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

awk '
	{ print }
	END {
		print ""
		print "&mdss {"
		print "\tstatus = \"okay\";"
		print "};"
	}
' "$overlay" >"$stage/display-mutant.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/display-mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1
then
	echo 'FAIL builder accepted an extra display consumer' >&2
	exit 1
fi

for contract in \
	da471966073cfb26581b4a5224218904162c5925155b0aa8c24a2b3e4ad0526f \
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
	base_hash=$(sha256sum "$BASE_DTB" | cut -d ' ' -f 1)
	"$builder" "$BASE_DTB" "$overlay" "$stage/one.dtb" >/dev/null
	"$builder" "$BASE_DTB" "$overlay" "$stage/two.dtb" >/dev/null
	cmp "$stage/one.dtb" "$stage/two.dtb"
	[ "$(sha256sum "$BASE_DTB" | cut -d ' ' -f 1)" = "$base_hash" ]

	cp "$BASE_DTB" "$stage/base-mutant.dtb"
	truncate -s +1 "$stage/base-mutant.dtb"
	if "$builder" "$stage/base-mutant.dtb" "$overlay" \
		"$stage/mutant-output.dtb" >/dev/null 2>&1
	then
		echo 'FAIL builder accepted a modified v18 base' >&2
		exit 1
	fi

	if "$builder" "$BASE_DTB" "$overlay" "$BASE_DTB" >/dev/null 2>&1
	then
		echo 'FAIL builder accepted an output aliasing its base' >&2
		exit 1
	fi
fi

echo 'PASS A660 registration DT is deterministic, mutation-tested, and storage-disabled'
