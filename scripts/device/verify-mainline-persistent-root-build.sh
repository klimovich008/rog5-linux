#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-persistent-root-build.sh BUILD_DIR}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
meta=$output_dir/build-meta.txt
config=$output_dir/.config
image=$output_dir/arch/arm64/boot/Image
image_gz=$output_dir/arch/arm64/boot/Image.gz
root_fragment=$repo/configs/kernel/rog5-persistent-root.fragment
deferred_fragment=$repo/configs/kernel/rog5-ufs-deferred-probe.fragment
verify_meta=$repo/scripts/device/verify-build-meta-hash.sh

if grep -qx 'CONFIG_SCSI_UFSHCD=m' "$config"; then
	for file in "$meta" "$config" "$image" "$image_gz"; do
		[ -s "$file" ] || {
			echo "FAIL missing deferred-UFS build input: $file" >&2
			exit 1
		}
	done
	for record in \
		'base_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' \
		'patched_commit=cfd385a1c754684dd28b63a4559e04baa5e902b1' \
		'patched_tree=d2f03d2055227b8b72ab41be949847a066924c5a' \
		'python_hash_seed=0' \
		'pahole_jobs=1'; do
		grep -qx "$record" "$meta"
	done
	"$verify_meta" "$meta" /configs/kernel/rog5-mainline.fragment \
		"$repo/configs/kernel/rog5-mainline.fragment"
	"$verify_meta" "$meta" /configs/kernel/rog5-ufs-deferred-probe.fragment \
		"$deferred_fragment"
	"$verify_meta" "$meta" /.config "$config"
	"$verify_meta" "$meta" /arch/arm64/boot/Image "$image"
	"$verify_meta" "$meta" /arch/arm64/boot/Image.gz "$image_gz"
	gzip -t "$image_gz"
	gzip -dc "$image_gz" | cmp - "$image"

	for symbol in \
		CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y \
		CONFIG_SCSI=y \
		CONFIG_SCSI_UFSHCD=m \
		CONFIG_SCSI_UFSHCD_PLATFORM=m \
		CONFIG_SCSI_UFS_QCOM=m \
		CONFIG_PHY_QCOM_QMP=y \
		CONFIG_PHY_QCOM_QMP_UFS=m \
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
		grep -qx "$symbol" "$config" || {
			echo "FAIL final deferred-UFS config: $symbol" >&2
			exit 1
		}
	done
	for symbol in \
		CHR_DEV_SG BLK_DEV_BSG SCSI_UFS_BSG RPMB SCSI_UFS_CRYPTO \
		SCSI_UFS_HWMON PHY_QCOM_QMP_COMBO PHY_QCOM_QMP_PCIE \
		PHY_QCOM_QMP_PCIE_8996 PHY_QCOM_QMP_USB \
		PHY_QCOM_QMP_USB_LEGACY; do
		grep -qx "# CONFIG_$symbol is not set" "$config" || {
			echo "FAIL final config must disable CONFIG_$symbol" >&2
			exit 1
		}
	done
	module_dir=$output_dir/deferred-ufs-modules
	[ "$(find "$module_dir" -mindepth 1 -maxdepth 1 -printf '%f\n' |
		LC_ALL=C sort | tr '\n' ' ')" = \
		'phy-qcom-qmp-ufs.ko ufs-qcom.ko ufshcd-core.ko ufshcd-pltfrm.ko ' ] || {
		echo 'FAIL deferred-UFS module inventory changed' >&2
		exit 1
	}
	for module in phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko \
		ufs-qcom.ko; do
		path=$module_dir/$module
		[ -s "$path" ] && [ ! -L "$path" ] || {
			echo "FAIL missing deferred-UFS module: $module" >&2
			exit 1
		}
		"$verify_meta" "$meta" "/deferred-ufs-modules/$module" "$path"
		case $module in
			phy-qcom-qmp-ufs.ko)
				expected_name=phy_qcom_qmp_ufs
				expected_depends=
				;;
			ufshcd-core.ko)
				expected_name=ufshcd_core
				expected_depends=
				;;
			ufshcd-pltfrm.ko)
				expected_name=ufshcd_pltfrm
				expected_depends=ufshcd-core
				;;
			ufs-qcom.ko)
				expected_name=ufs_qcom
				expected_depends=ufshcd-pltfrm,ufshcd-core
				;;
		esac
		[ "$(modinfo -F name "$path")" = "$expected_name" ] &&
			[ "$(modinfo -F depends "$path")" = "$expected_depends" ] &&
			[ "$(modinfo -F vermagic "$path" | awk '{ print $1 }')" = \
				7.1.4-gcfd385a1c754 ] || {
			echo "FAIL deferred-UFS module metadata changed: $module" >&2
			exit 1
		}
	done
	strings "$image" | grep -Fq \
		'ROG5 UFS discovery: forced read-only before registration'
	for marker in \
		'ROG5 UFS discovery: blocked SCSI opcode' \
		'ROG5 UFS discovery: blocked device query' \
		'ROG5 UFS discovery: optional device writes and high-speed gear switch disabled' \
		'ROG5 UFS discovery: auto-hibern8 disabled; link remains active' \
		'ROG5 UFS discovery: host runtime PM forbidden; active reference retained' \
		'ROG5 UFS discovery: WL power transition rejected' \
		'ROG5 UFS discovery: host power transition rejected' \
		'ROG5 UFS discovery: shutdown power transition skipped' \
		'ROG5 UFS discovery: WLUN runtime PM forbidden'; do
		strings "$module_dir/ufshcd-core.ko" |
			grep -Fq "$marker" || {
			echo "FAIL deferred UFS guard marker missing: $marker" >&2
			exit 1
		}
	done
else
	"$repo/scripts/device/verify-mainline-discovery-build.sh" "$output_dir" \
		>/dev/null
fi

"$verify_meta" "$meta" /configs/kernel/rog5-persistent-root.fragment \
	"$root_fragment"

for symbol in \
	CONFIG_EXT4_FS=y \
	CONFIG_EXT4_FS_POSIX_ACL=y \
	CONFIG_EXT4_FS_SECURITY=y \
	CONFIG_OVERLAY_FS=y \
	CONFIG_TMPFS=y \
	CONFIG_TMPFS_XATTR=y; do
	grep -qx "$symbol" "$config" || {
		echo "FAIL final P2 config: $symbol" >&2
		exit 1
	}
done
! grep -qx 'CONFIG_OVERLAY_FS=m' "$config"
strings "$image" |
	grep -Fq "overlayfs: overlay with incompat feature '%s' cannot be mounted"

echo 'PASS dedicated read-only persistent-root config, UFS guards/modules, hashes, and Image.gz'
