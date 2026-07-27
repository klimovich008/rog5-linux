#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-network-root-build.sh BUILD_DIR}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
expected_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
meta=$output_dir/build-meta.txt
config=$output_dir/.config
image=$output_dir/arch/arm64/boot/Image
image_gz=$output_dir/arch/arm64/boot/Image.gz
modules=$output_dir/modules.tar.gz

for file in "$meta" "$config" "$image" "$image_gz" "$modules"; do
	[ -s "$file" ] || { echo "FAIL missing $file" >&2; exit 1; }
done
grep -qx "kernel_commit=$expected_commit" "$meta"
grep -qx 'python_hash_seed=0' "$meta"
grep -qx 'pahole_jobs=1' "$meta"

check_hash() {
	label=$1
	file=$2
	expected=$(sed -n "s/^${label}=//p" "$meta")
	[ "$(printf '%s\n' "$expected" |
		awk 'NF { count++ } END { print count + 0 }')" -eq 1 ]
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ]
}
check_hash base_fragment_sha256 "$repo/configs/kernel/rog5-mainline.fragment"
check_hash network_fragment_sha256 "$repo/configs/kernel/rog5-network-root.fragment"
check_hash config_sha256 "$config"
check_hash image_sha256 "$image"
check_hash image_gz_sha256 "$image_gz"
check_hash modules_sha256 "$modules"

gzip -t "$image_gz"
gzip -dc "$image_gz" | cmp - "$image"
tar -tzf "$modules" | grep -q '/modules.dep$'

for symbol in \
	CONFIG_NFS_FS=y \
	CONFIG_NFS_V4=y \
	CONFIG_NFS_V4_2=y \
	CONFIG_ROOT_NFS=y \
	CONFIG_NFS_DISABLE_UDP_SUPPORT=y \
	CONFIG_OVERLAY_FS=y \
	CONFIG_TMPFS=y \
	CONFIG_TMPFS_XATTR=y \
	CONFIG_IP_PNP=y \
	CONFIG_SUNRPC=y \
	CONFIG_LOCKD=y \
	CONFIG_KEYS=y \
	CONFIG_USB_CONFIGFS_ACM=y \
	CONFIG_USB_CONFIGFS_NCM=y \
	CONFIG_IKCONFIG=y \
	CONFIG_IKCONFIG_PROC=y; do
	grep -qx "$symbol" "$config" || {
		echo "FAIL final network-root config: $symbol" >&2
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
	PHY_QCOM_QMP_PCIE_8996 \
	PHY_QCOM_QMP_USB \
	PHY_QCOM_QMP_USB_LEGACY \
	NFS_V2 \
	NFS_V3 \
	NFS_SWAP \
	NFS_FSCACHE; do
	if grep -Eq "^CONFIG_$symbol=(y|m)$" "$config"; then
		echo "FAIL final network-root config enables CONFIG_$symbol" >&2
		exit 1
	fi
done

case ${ALLOW_QMP_PCIE:-n} in
	n)
		if grep -Eq '^CONFIG_PHY_QCOM_QMP_PCIE=(y|m)$' "$config"; then
			echo 'FAIL final network-root config enables CONFIG_PHY_QCOM_QMP_PCIE' >&2
			exit 1
		fi
		;;
	m)
		grep -qx 'CONFIG_PHY_QCOM_QMP_PCIE=m' "$config"
		;;
	*)
		echo 'FAIL ALLOW_QMP_PCIE must be n or m' >&2
		exit 1
		;;
esac

echo 'PASS final network-root config, Image, modules, and recorded hashes'
