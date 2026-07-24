#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
fragment=$repo/configs/kernel/rog5-network-root.fragment

[ -r "$fragment" ] || {
	echo 'FAIL missing network-root kernel fragment' >&2
	exit 1
}

for symbol in \
	CONFIG_NFS_FS=y \
	CONFIG_NFS_V4=y \
	CONFIG_NFS_V4_2=y \
	CONFIG_ROOT_NFS=y \
	CONFIG_NFS_DISABLE_UDP_SUPPORT=y \
	CONFIG_OVERLAY_FS=y \
	CONFIG_TMPFS=y \
	CONFIG_TMPFS_XATTR=y \
	CONFIG_USB_CONFIGFS_ACM=y \
	CONFIG_USB_CONFIGFS_NCM=y \
	CONFIG_IKCONFIG=y \
	CONFIG_IKCONFIG_PROC=y; do
	grep -qx "$symbol" "$fragment" || {
		echo "FAIL network-root fragment: $symbol" >&2
		exit 1
	}
done

for symbol in \
	SCSI \
	SCSI_UFSHCD \
	SCSI_UFSHCD_PLATFORM \
	SCSI_UFS_QCOM \
	BLK_DEV_SD \
	CHR_DEV_SG \
	BLK_DEV_BSG \
	SCSI_UFS_BSG \
	RPMB \
	SCSI_UFS_CRYPTO \
	SCSI_UFS_HWMON \
	PHY_QCOM_QMP_UFS \
	PHY_QCOM_QMP_COMBO \
	PHY_QCOM_QMP_PCIE \
	PHY_QCOM_QMP_PCIE_8996 \
	PHY_QCOM_QMP_USB \
	PHY_QCOM_QMP_USB_LEGACY \
	NFS_V2 \
	NFS_V3 \
	NFS_SWAP \
	NFS_FSCACHE; do
	grep -qx "# CONFIG_$symbol is not set" "$fragment" || {
		echo "FAIL network-root fragment must disable CONFIG_$symbol" >&2
		exit 1
	}
done

echo 'PASS network-root kernel contract uses built-in NFS/overlay and compiles UFS out'
