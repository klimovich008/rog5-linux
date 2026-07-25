#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-battery-telemetry-bundle.sh

[ -x "$verifier" ]
sh -n "$verifier"

for contract in \
	'verify-network-root-bundle.sh' \
	'/soc@0/remoteproc@3000000' \
	'/soc@0/remoteproc@4080000' \
	'/soc@0/remoteproc@5c00000' \
	'/soc@0/remoteproc@a300000' \
	'/reserved-memory/memory@cbc00000' \
	'/reserved-memory/memory@d8000000' \
	'/reserved-memory/memory@edc00000' \
	'/soc@0/spmi@c440000/pmic@0/rtc@6100' \
	'/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey' \
	'qcom,sm8350-pmic-glink qcom,pmic-glink' \
	'CONFIG_QRTR=m' \
	'CONFIG_QRTR_SMD=m' \
	'CONFIG_QCOM_Q6V5_PAS=m' \
	'CONFIG_QCOM_PD_MAPPER=m' \
	'CONFIG_QCOM_PMIC_GLINK=m' \
	'CONFIG_BATTERY_QCOM_BATTMGR=m' \
	'qcom_q6v5_pas' \
	'qcom_glink_smem' \
	'qrtr-smd' \
	'qcom_pd_mapper' \
	'pdr_interface' \
	'qcom_battmgr' \
	'adsp\.(mdt|mbn|b[0-9][0-9])' \
	'pmic_glink-battery-only\.ko' \
	'fa38f4f8d4ab428bd828601dc0c9805fcabe3d265afe3cdb0ba6ed977ac9c666' \
	'87e4797a61b75efd02cb52d47e013af5c28cee57affcf484f872ea5a1fb69178' \
	'7eac8fd204c74f0cae8d28a082dec54c8e30d55d420dfd2418052e7f5c9777f7' \
	'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL bundle verifier contract missing: $contract" >&2
		exit 1
	}
done

set +e
"$verifier" /missing /missing /missing /missing invalid >/dev/null 2>&1
invalid_mode=$?
"$verifier" /missing /missing /missing /missing telemetry >/dev/null 2>&1
missing_module=$?
set -e
[ "$invalid_mode" -ne 0 ]
[ "$missing_module" -ne 0 ]

echo 'PASS battery-telemetry bundle verifier distinguishes both tiers and excludes private firmware from artifacts'
