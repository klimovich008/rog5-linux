#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
default_source=/home/deck/.local/state/rog5-qmp-ufs-first-clock-runtime-pm-stage-20260813-r2/linux-source
[ "$#" -eq 0 ] || {
	echo 'usage: check-persistent-root-power-usb-composition.sh' >&2
	exit 1
}
explicit_source=${ROG5_COMPOSED_SOURCE+x}
explicit_config=${ROG5_COMPOSED_CONFIG+x}
source_repository=${ROG5_COMPOSED_SOURCE:-$default_source}
config=${ROG5_COMPOSED_CONFIG:-$repo/artifacts/persistent-root-p2/config-7.1.4-persistent-root}
module_root=${ROG5_COMPOSED_MODULE_ROOT:-}

expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_commit=ae717d919f87b47ea9ed2173ea96660186b62a66
expected_tree=939729426dcfa3bd72c75d81c0a675c6f0a193da
expected_release=7.1.4-gae717d919f87
v26_release=7.1.4-g7a5cef0db479
patch=$repo/patches/linux-7.1.4/0032-phy-qcom-qmp-ufs-publish-of-phy-provider.patch
fragment=$repo/configs/kernel/rog5-persistent-root-power-usb.fragment

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ -f "$patch" ] && [ ! -L "$patch" ] &&
	grep -Fqx "From $expected_commit Mon Sep 17 00:00:00 2001" "$patch" ||
	fail 'exact ae717 UFS source patch is absent'
[ -f "$fragment" ] && [ ! -L "$fragment" ] ||
	fail 'persistent-root power/USB fragment is absent'
[ -f "$config" ] && [ ! -L "$config" ] ||
	fail 'persistent-root kernel config is absent'
for symbol in CONFIG_NVMEM_SPMI_SDAM=y CONFIG_NVMEM_REBOOT_MODE=y; do
	grep -Fqx "$symbol" "$fragment" ||
		fail "power/USB fragment lacks early reboot support: $symbol"
	if [ -n "$explicit_config" ]; then
		grep -Fqx "$symbol" "$config" ||
			fail "kernel config lacks early reboot support: $symbol"
	fi
done

if [ -d "$source_repository/.git" ]; then
	[ ! -L "$source_repository" ] && [ ! -L "$source_repository/.git" ] ||
		fail 'retained Linux source repository is linked'
	[ "$(git -C "$source_repository" rev-parse "$expected_commit^{commit}")" = \
		"$expected_commit" ] || fail 'retained source lacks the exact ae717 commit'
	[ "$(git -C "$source_repository" rev-parse "$expected_commit^{tree}")" = \
		"$expected_tree" ] || fail 'exact ae717 source tree changed'
	git -C "$source_repository" merge-base --is-ancestor \
		"$expected_base" "$expected_commit" || fail 'ae717 source lost Linux 7.1.4 ancestry'
elif [ -n "$explicit_source" ]; then
	fail 'explicit retained Linux source repository is absent'
fi

for symbol in \
	CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y \
	CONFIG_QRTR=m \
	CONFIG_QRTR_SMD=m \
	CONFIG_BATTERY_QCOM_BATTMGR=m \
	CONFIG_TYPEC=m \
	CONFIG_TYPEC_UCSI=m \
	CONFIG_UCSI_PMIC_GLINK=m \
	CONFIG_REMOTEPROC=y \
	CONFIG_QCOM_PIL_INFO=m \
	CONFIG_QCOM_RPROC_COMMON=m \
	CONFIG_QCOM_Q6V5_COMMON=m \
	CONFIG_QCOM_Q6V5_PAS=m \
	CONFIG_RPMSG=y \
	CONFIG_RPMSG_QCOM_GLINK=y \
	CONFIG_RPMSG_QCOM_GLINK_SMEM=m \
	CONFIG_QCOM_PD_MAPPER=m \
	CONFIG_QCOM_PDR_HELPERS=m \
	CONFIG_QCOM_PDR_MSG=m \
	CONFIG_QCOM_PMIC_GLINK=m; do
	grep -Fqx "$symbol" "$config" || fail "kernel config lacks $symbol"
done
if grep -Fqx 'CONFIG_SCSI_UFSHCD=y' "$config"; then
	ufs_linkage=y
else
	ufs_linkage=m
fi
for symbol in CONFIG_SCSI_UFSHCD=$ufs_linkage \
	CONFIG_SCSI_UFSHCD_PLATFORM=$ufs_linkage \
	CONFIG_SCSI_UFS_QCOM=$ufs_linkage \
	CONFIG_PHY_QCOM_QMP_UFS=$ufs_linkage; do
	grep -Fqx "$symbol" "$config" || fail "incoherent UFS linkage: $symbol"
done
for symbol in \
	'# CONFIG_SCSI_UFS_BSG is not set' \
	'# CONFIG_RPMB is not set' \
	'# CONFIG_SCSI_UFS_CRYPTO is not set'; do
	grep -Fqx "$symbol" "$config" || fail "kernel config lost containment: $symbol"
done

if [ -n "$module_root" ]; then
	[ -d "$module_root/lib/modules" ] && [ ! -L "$module_root" ] ||
		fail 'composed module root is absent or linked'
	releases=$(find "$module_root/lib/modules" -mindepth 1 -maxdepth 1 \
		-type d -printf '%f\n' | sort)
	[ "$releases" != "$v26_release" ] ||
		fail 'V26 ABI modules cannot be reused by the composed kernel'
	[ "$releases" = "$expected_release" ] ||
		fail 'composed module root must contain exactly the ae717 release'
	module_dir=$module_root/lib/modules/$expected_release
	for relative in \
		kernel/drivers/power/supply/qcom_battmgr.ko \
		kernel/drivers/remoteproc/qcom_common.ko \
		kernel/drivers/remoteproc/qcom_pil_info.ko \
		kernel/drivers/remoteproc/qcom_q6v5.ko \
		kernel/drivers/remoteproc/qcom_q6v5_pas.ko \
		kernel/drivers/rpmsg/qcom_glink_smem.ko \
		kernel/drivers/soc/qcom/pdr_interface.ko \
		kernel/drivers/soc/qcom/pmic_glink.ko \
		kernel/drivers/soc/qcom/qcom_pd_mapper.ko \
		kernel/drivers/soc/qcom/qcom_pdr_msg.ko \
		kernel/drivers/usb/typec/typec.ko \
		kernel/drivers/usb/typec/ucsi/typec_ucsi.ko \
		kernel/drivers/usb/typec/ucsi/ucsi_glink.ko \
		kernel/net/qrtr/qrtr-smd.ko \
		kernel/net/qrtr/qrtr.ko; do
		path=$module_dir/$relative
		[ -f "$path" ] && [ ! -L "$path" ] ||
			fail "composed module closure lacks $relative"
		[ "$(modinfo -F vermagic "$path" | awk '{print $1}')" = \
			"$expected_release" ] || fail "module ABI mismatch: $relative"
	done
	! readelf -S "$module_dir/kernel/drivers/soc/qcom/pdr_interface.ko" |
		grep -q '[.]BTF' || fail 'composed PDR module retains rejected BTF'
fi

echo 'PASS exact ae717 read-only UFS kernel composition includes the V26 charging stack without ABI reuse'
