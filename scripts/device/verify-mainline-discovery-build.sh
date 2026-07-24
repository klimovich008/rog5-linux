#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-discovery-build.sh BUILD_DIR}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_patched=cfd385a1c754684dd28b63a4559e04baa5e902b1
expected_tree=d2f03d2055227b8b72ab41be949847a066924c5a
meta=$output_dir/build-meta.txt
config=$output_dir/.config
image=$output_dir/arch/arm64/boot/Image
image_gz=$output_dir/arch/arm64/boot/Image.gz

for file in "$meta" "$config" "$image" "$image_gz"; do
	[ -s "$file" ] || { echo "FAIL missing $file" >&2; exit 1; }
done
grep -qx "base_commit=$expected_base" "$meta"
grep -qx "patched_commit=$expected_patched" "$meta"
grep -qx "patched_tree=$expected_tree" "$meta"
grep -qx 'python_hash_seed=0' "$meta"
grep -qx 'pahole_jobs=1' "$meta"

check_recorded_hash() {
	recorded_path=$1
	actual_path=$2
	expected=$(awk -v path="$recorded_path" '$2 == path { print $1 }' "$meta")
	[ "$(printf '%s\n' "$expected" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ]
	[ "$(sha256sum "$actual_path" | cut -d ' ' -f 1)" = "$expected" ]
}
check_recorded_hash /repo/configs/kernel/rog5-mainline.fragment \
	"$repo/configs/kernel/rog5-mainline.fragment"
check_recorded_hash /repo/configs/kernel/rog5-ufs-discovery.fragment \
	"$repo/configs/kernel/rog5-ufs-discovery.fragment"
check_recorded_hash /root/build/output/.config "$config"
check_recorded_hash /root/build/output/arch/arm64/boot/Image "$image"
check_recorded_hash /root/build/output/arch/arm64/boot/Image.gz "$image_gz"

gzip -t "$image_gz"
gzip -dc "$image_gz" | cmp - "$image"

for symbol in \
	CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y \
	CONFIG_SCSI=y \
	CONFIG_SCSI_UFSHCD=y \
	CONFIG_SCSI_UFSHCD_PLATFORM=y \
	CONFIG_SCSI_UFS_QCOM=y \
	CONFIG_PHY_QCOM_QMP=y \
	CONFIG_PHY_QCOM_QMP_UFS=y \
	CONFIG_BLK_DEV_SD=y \
	CONFIG_EFI_PARTITION=y \
	CONFIG_PINCTRL_SM8350=y \
	CONFIG_REGULATOR_QCOM_RPMH=y \
	CONFIG_INTERCONNECT_QCOM_SM8350=y \
	CONFIG_QCOM_COMMAND_DB=y \
	CONFIG_QCOM_RPMH=y \
	CONFIG_RESET_QCOM_AOSS=y \
	CONFIG_USB=y \
	CONFIG_USB_DWC3=y \
	CONFIG_USB_DWC3_QCOM=y \
	CONFIG_USB_GADGET=y \
	CONFIG_USB_CONFIGFS=y \
	CONFIG_USB_CONFIGFS_ACM=y \
	CONFIG_USB_CONFIGFS_NCM=y \
	CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=y \
	CONFIG_IKCONFIG=y \
	CONFIG_IKCONFIG_PROC=y; do
	grep -qx "$symbol" "$config" || { echo "FAIL final config: $symbol" >&2; exit 1; }
done
for symbol in \
	CHR_DEV_SG BLK_DEV_BSG SCSI_UFS_BSG RPMB SCSI_UFS_CRYPTO \
	SCSI_UFS_HWMON PHY_QCOM_QMP_COMBO PHY_QCOM_QMP_PCIE \
	PHY_QCOM_QMP_PCIE_8996 PHY_QCOM_QMP_USB PHY_QCOM_QMP_USB_LEGACY; do
	grep -qx "# CONFIG_$symbol is not set" "$config" || {
		echo "FAIL final config must disable CONFIG_$symbol" >&2
		exit 1
	}
done

for marker in \
	'ROG5 UFS discovery: forced read-only before registration' \
	'ROG5 UFS discovery: blocked SCSI opcode' \
	'ROG5 UFS discovery: blocked device query' \
	'ROG5 UFS discovery: optional device writes and high-speed gear switch disabled' \
	'ROG5 UFS discovery: auto-hibern8 disabled; link remains active' \
	'ROG5 UFS discovery: host runtime PM forbidden; active reference retained' \
	'ROG5 UFS discovery: WL power transition rejected' \
	'ROG5 UFS discovery: host power transition rejected' \
	'ROG5 UFS discovery: shutdown power transition skipped' \
	'ROG5 UFS discovery: WLUN runtime PM forbidden'; do
	strings "$image" | grep -Fq "$marker" || {
		echo "FAIL compiled guard marker missing: $marker" >&2
		exit 1
	}
done

echo 'PASS dedicated discovery config, compiled guards, hashes, and Image.gz'
