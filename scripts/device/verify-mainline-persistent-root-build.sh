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
write_fragment=${WRITE_FRAGMENT:-$repo/configs/kernel/rog5-ufs-local-write.fragment}
verify_meta=$repo/scripts/device/verify-build-meta-hash.sh
storage_mode=${UFS_STORAGE_MODE:-read-only}
expected_base=${LINUX_BASE_COMMIT:-7a5cef0db4795d9d453a12e0f61b5b7634fc4d40}
expected_commit=${LINUX_COMMIT:-359318de534f196c1281de7195fbf5868c6f7333}
expected_tree=${LINUX_TREE:-8528fcd29e4ad19cf944f79c2ebb3438feee5e0b}
expected_release=${EXPECTED_RELEASE:-7.1.4-g359318de534f}

case $storage_mode in
	read-only | local-write) ;;
	*)
		echo 'FAIL UFS_STORAGE_MODE must be read-only or local-write' >&2
		exit 1
		;;
esac

if grep -qx 'CONFIG_SCSI_UFSHCD=m' "$config"; then
	for file in "$meta" "$config" "$image" "$image_gz"; do
		[ -s "$file" ] || {
			echo "FAIL missing deferred-UFS build input: $file" >&2
			exit 1
		}
	done
	for record in \
		"base_commit=$expected_base" \
		"patched_commit=$expected_commit" \
		"patched_tree=$expected_tree" \
		"ufs_storage_mode=$storage_mode" \
		'kbuild_version=1' \
		'debug_compilation_dir=/usr/src/rog5-linux-build' \
		'python_hash_seed=0' \
		'pahole_jobs=1'; do
		grep -qx "$record" "$meta"
	done
	"$verify_meta" "$meta" /configs/kernel/rog5-mainline.fragment \
		"$repo/configs/kernel/rog5-mainline.fragment"
	"$verify_meta" "$meta" /configs/kernel/rog5-ufs-deferred-probe.fragment \
		"$deferred_fragment"
	if [ "$storage_mode" = local-write ]; then
		"$verify_meta" "$meta" /configs/kernel/rog5-ufs-local-write.fragment \
			"$write_fragment"
	fi
	"$verify_meta" "$meta" /.config "$config"
	"$verify_meta" "$meta" /arch/arm64/boot/Image "$image"
	"$verify_meta" "$meta" /arch/arm64/boot/Image.gz "$image_gz"
	gzip -t "$image_gz"
	gzip -dc "$image_gz" | cmp - "$image"

	for symbol in \
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
	case $storage_mode in
		read-only)
			grep -qx 'CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y' "$config" || {
				echo 'FAIL read-only build lost the UFS discovery guard' >&2
				exit 1
			}
			if ! grep -qx '# CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE is not set' \
				"$config"; then
				! grep -q '^CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=' "$config" &&
					[ "$expected_commit" = \
						ae717d919f87b47ea9ed2173ea96660186b62a66 ] &&
					[ "$expected_tree" = \
						939729426dcfa3bd72c75d81c0a675c6f0a193da ] || {
					echo 'FAIL read-only build permits UFS data writes' >&2
					exit 1
				}
			fi
		;;
		local-write)
			grep -qx 'CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y' \
				"$config" || {
				echo 'FAIL local-write build lost UFS discovery containment' >&2
				exit 1
			}
			grep -qx 'CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=y' \
				"$config" || {
				echo 'FAIL local-write build lacks the bounded data-write profile' >&2
				exit 1
			}
		;;
	esac
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
				"$expected_release" ] || {
			echo "FAIL deferred-UFS module metadata changed: $module" >&2
			exit 1
		}
	done
	image_marker='ROG5 UFS discovery: forced read-only before registration'
	scsi_marker='ROG5 UFS discovery: blocked SCSI opcode'
	guard_markers='ROG5 UFS discovery: blocked device query
ROG5 UFS discovery: optional device writes and high-speed gear switch disabled
ROG5 UFS discovery: auto-hibern8 disabled; link remains active
ROG5 UFS discovery: host runtime PM forbidden; active reference retained
ROG5 UFS discovery: WL power transition rejected
ROG5 UFS discovery: host power transition rejected
ROG5 UFS discovery: shutdown power transition skipped
ROG5 UFS discovery: WLUN runtime PM forbidden'
	if [ "$storage_mode" = read-only ]; then
		strings "$image" | grep -Fq "$image_marker"
		strings "$module_dir/ufshcd-core.ko" | grep -Fq "$scsi_marker"
		printf '%s\n' "$guard_markers" | while IFS= read -r marker; do
			strings "$module_dir/ufshcd-core.ko" |
				grep -Fq "$marker" || {
				echo "FAIL deferred UFS guard marker missing: $marker" >&2
				exit 1
			}
		done
	else
		if strings "$image" | grep -Fq "$image_marker"; then
			echo 'FAIL local-write Image retained forced disk read-only state' >&2
			exit 1
		fi
		if strings "$module_dir/ufshcd-core.ko" | grep -Fq "$scsi_marker"; then
			echo 'FAIL local-write module retained the SCSI data-write guard' >&2
			exit 1
		fi
		printf '%s\n' "$guard_markers" | while IFS= read -r marker; do
			strings "$module_dir/ufshcd-core.ko" |
				grep -Fq "$marker" || {
				echo "FAIL local-write module lost discovery containment: $marker" >&2
				exit 1
			}
		done
	fi
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

echo "PASS dedicated $storage_mode persistent-root config, UFS policy/modules, hashes, and Image.gz"
