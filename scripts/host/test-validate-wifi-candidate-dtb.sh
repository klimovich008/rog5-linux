#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
validator=$repo/scripts/host/validate-wifi-candidate-dtb.sh
dockerfile=$repo/containers/dtschema/Dockerfile

[ -x "$validator" ] || {
	echo 'FAIL missing executable Wi-Fi DT schema validator' >&2
	exit 1
}
[ -r "$dockerfile" ]
sh -n "$validator"

for contract in \
	'ubuntu:24.04@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90' \
	'dtschema==2026.6' \
	'yamllint==1.38.0'
do
	grep -Fq "$contract" "$dockerfile" || {
		echo "FAIL dtschema container omits: $contract" >&2
		exit 1
	}
done

# The last contract intentionally contains literal shell variable syntax.
# shellcheck disable=SC2016
for contract in \
	'7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' \
	'0fb6d415597630508779263693803af40f35496adee17e82995b0189b2aa9c78' \
	'--network=none' \
	'qcom,qca6390-pmu' \
	'qcom,ath11k-pci' \
	'qcom,pcie-sm8350' \
	'qcom,sc8280xp-qmp-pcie-phy' \
	'qcom,rpmh-regulator' \
	'qcom,sm8350-tlmm' \
	'candidate-a.dtb' \
	'candidate-b.dtb' \
	'cmp "$output_real/candidate-a.dtb" "$output_real/candidate-b.dtb"'
do
	grep -Fq -- "$contract" "$validator" || {
		echo "FAIL Wi-Fi schema validator omits: $contract" >&2
		exit 1
	}
done

if grep -Eq '^[[:space:]]*(fastboot|adb|ssh|mount|dd)([[:space:]]|$)' \
	"$validator" "$dockerfile"
then
	echo 'FAIL Wi-Fi schema validation controls the phone or external storage' >&2
	exit 1
fi

echo 'PASS Wi-Fi DT schema validation is pinned, offline, reproducible, and phone-independent'
