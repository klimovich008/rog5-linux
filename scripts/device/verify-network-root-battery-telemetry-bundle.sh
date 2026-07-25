#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-battery-telemetry-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256 adsp|telemetry [PMIC_MODULE]}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing SHA-256 manifest}
mode=${5:?missing candidate mode}
pmic_module=${6:-}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)

case $mode in
	adsp) [ -z "$pmic_module" ] ;;
	telemetry) [ -n "$pmic_module" ] ;;
	*) echo 'FAIL mode must be adsp or telemetry' >&2; exit 1 ;;
esac

"$repo/scripts/device/verify-network-root-bundle.sh" \
	"$artifact_dir" "$mkbootimg_dir" "$avbtool" "$expected_sums"

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
config=$artifact_dir/config-7.1.4-network-root
modules=$artifact_dir/modules-7.1.4-network-root.tar.gz
adsp=/soc@0/remoteproc@3000000
pmic_glink=/pmic-glink
rtc=/soc@0/spmi@c440000/pmic@0/rtc@6100
pwrkey=/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey
stock_low=/reserved-memory/memory@cbc00000
stock_memshare=/reserved-memory/memory@d8000000
stock_high=/reserved-memory/memory@edc00000

[ "$(fdtget -t s "$dtb" "$adsp" status)" = okay ]
[ "$(fdtget -t s "$dtb" "$rtc" status)" = disabled ]
[ "$(fdtget -t s "$dtb" "$pwrkey" status)" = okay ]
[ "$(fdtget -t x "$dtb" "$stock_low" reg)" = '0 cbc00000 0 4400000' ]
[ "$(fdtget -t x "$dtb" "$stock_memshare" reg)" = \
	'0 d8000000 0 800000' ]
[ "$(fdtget -t x "$dtb" "$stock_high" reg)" = \
	'0 edc00000 0 12000000' ]
! fdtget "$dtb" "$stock_low" no-map >/dev/null 2>&1
fdtget "$dtb" "$stock_memshare" no-map >/dev/null
! fdtget "$dtb" "$stock_high" no-map >/dev/null 2>&1
for node in \
	/soc@0/remoteproc@4080000 \
	/soc@0/remoteproc@5c00000 \
	/soc@0/remoteproc@a300000
do
	[ "$(fdtget -t s "$dtb" "$node" status)" = disabled ]
done

case $mode in
	adsp)
		! fdtget -p "$dtb" "$pmic_glink" >/dev/null 2>&1
		;;
	telemetry)
		[ "$(fdtget -t s "$dtb" "$pmic_glink" compatible)" = \
			'qcom,sm8350-pmic-glink qcom,pmic-glink' ]
		[ "$(fdtget -p "$dtb" "$pmic_glink")" = compatible ]
		[ -z "$(fdtget -l "$dtb" "$pmic_glink")" ]
		;;
esac

for symbol in \
	CONFIG_FW_LOADER=y \
	CONFIG_REMOTEPROC=y \
	CONFIG_QCOM_RPROC_COMMON=m \
	CONFIG_QCOM_Q6V5_COMMON=m \
	CONFIG_QCOM_Q6V5_PAS=m \
	CONFIG_RPMSG=y \
	CONFIG_RPMSG_QCOM_GLINK=y \
	CONFIG_RPMSG_QCOM_GLINK_SMEM=m \
	CONFIG_QRTR=m \
	CONFIG_QRTR_SMD=m \
	CONFIG_QCOM_PD_MAPPER=m \
	CONFIG_QCOM_PDR_HELPERS=m \
	CONFIG_QCOM_PDR_MSG=m \
	CONFIG_QCOM_PMIC_GLINK=m \
	CONFIG_POWER_SUPPLY=y \
	CONFIG_BATTERY_QCOM_BATTMGR=m
do
	grep -qx "$symbol" "$config"
done

module_listing=$(tar -tzf "$modules")
for module in \
	qcom_q6v5_pas \
	qcom_q6v5 \
	qcom_common \
	qcom_pil_info \
	qcom_glink_smem \
	qrtr \
	qrtr-smd \
	qcom_pd_mapper \
	pdr_interface \
	qcom_pdr_msg \
	pmic_glink \
	qcom_battmgr
do
	[ "$(printf '%s\n' "$module_listing" |
		grep -Ec "/$module\\.ko$")" -eq 1 ]
done

verify_archived_module_hash() {
	module=$1
	expected_sha=$2
	module_path=$(printf '%s\n' "$module_listing" |
		grep -E "/$module[.]ko$")
	[ "$(printf '%s\n' "$module_path" | wc -l)" -eq 1 ]
	[ "$(tar -xOzf "$modules" "$module_path" | sha256sum |
		cut -d ' ' -f 1)" = "$expected_sha" ]
}
verify_archived_module_hash qrtr-smd \
	87e4797a61b75efd02cb52d47e013af5c28cee57affcf484f872ea5a1fb69178
verify_archived_module_hash qcom_pd_mapper \
	7eac8fd204c74f0cae8d28a082dec54c8e30d55d420dfd2418052e7f5c9777f7

for archive in \
	"$artifact_dir/rog5-network-root-initramfs.cpio.gz" \
	"$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz"
do
	listing=$(gzip -dc "$archive" | cpio -t 2>/dev/null)
	! printf '%s\n' "$listing" |
		grep -Eq '(^|/)(adsp\.(mdt|mbn|b[0-9][0-9])|pmic_glink-battery-only\.ko)$'
done

if [ "$mode" = telemetry ]; then
	[ -f "$pmic_module" ] && [ ! -L "$pmic_module" ]
	[ "$(sha256sum "$pmic_module" | cut -d ' ' -f 1)" = \
		fa38f4f8d4ab428bd828601dc0c9805fcabe3d265afe3cdb0ba6ed977ac9c666 ]
	[ "$(modinfo -F name "$pmic_module")" = pmic_glink ]
	[ "$(modinfo -F depends "$pmic_module")" = pdr_interface ]
	[ "$(modinfo -F vermagic "$pmic_module")" = \
		'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' ]
	modinfo -p "$pmic_module" |
		grep -Fxq 'battery_only:Expose only the battery client for attended diagnostics (bool)'
fi

echo "PASS $mode battery-telemetry bundle; audited QRTR/PDR inputs are pinned, stock-owned RAM and ADSP are isolated, storage/RTC remain disabled, and private firmware stays external"
