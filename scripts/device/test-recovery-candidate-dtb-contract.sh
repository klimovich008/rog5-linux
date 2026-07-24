#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-recovery.dtso
builder=$repo/scripts/device/build-recovery-candidate-dtb.sh
bundle_verifier=$repo/scripts/device/verify-network-root-bundle.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$overlay" ] && [ -x "$builder" ] && [ -x "$bundle_verifier" ]
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 2 ]
[ "$(grep -c 'status = "disabled";' "$overlay")" -eq 5 ]
[ "$(grep -c '^&' "$overlay")" -eq 8 ]

for label in rmtfs_mem gpu gmu gpucc adreno_smmu; do
	grep -q "^&$label {" "$overlay"
	grep -Eq "^[[:space:]]*$label([[:space:]]|$)" "$builder"
done

for node in \
	/reserved-memory/memory@9b800000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000
do
	grep -Fq "$node" "$builder"
	grep -Fq "$node" "$bundle_verifier"
done

# Every missing isolation status must fail before the DT tools are invoked.
printf 'dummy\n' >"$stage/base.dtb"
for label in rmtfs_mem gpu gmu gpucc adreno_smmu; do
	awk -v label="$label" '
		$0 == "&" label " {" { target = 1 }
		target && /status = "disabled";/ { target = 0; next }
		{ print }
	' "$overlay" >"$stage/mutant.dtso"
	if PATH=/nonexistent "$builder" "$stage/base.dtb" \
		"$stage/mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1; then
		echo "FAIL builder accepted recovery overlay without $label isolation" >&2
		exit 1
	fi
done

echo 'PASS recovery DT contract requires GPU, GPUCC, GMU, SMMU, and RMTFS isolation'
