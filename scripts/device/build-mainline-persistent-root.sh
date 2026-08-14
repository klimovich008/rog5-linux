#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4-discovery}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4-persistent-root}
base_fragment=${BASE_FRAGMENT:-/root/rog5-build/rog5-mainline.fragment}
discovery_fragment=${DISCOVERY_FRAGMENT:-/root/rog5-build/rog5-ufs-discovery.fragment}
root_fragment=${ROOT_FRAGMENT:-/root/rog5-build/rog5-persistent-root.fragment}
write_fragment=${WRITE_FRAGMENT:-/root/rog5-build/rog5-ufs-local-write.fragment}
storage_mode=${UFS_STORAGE_MODE:-read-only}
expected_base=${LINUX_BASE_COMMIT:-7a5cef0db4795d9d453a12e0f61b5b7634fc4d40}
expected_commit=${LINUX_COMMIT:-359318de534f196c1281de7195fbf5868c6f7333}
expected_tree=${LINUX_TREE:-8528fcd29e4ad19cf944f79c2ebb3438feee5e0b}
expected_release=${EXPECTED_RELEASE:-7.1.4-g359318de534f}
jobs=${JOBS:-1}
btf_jobs=1

case $storage_mode in
	read-only | local-write) ;;
	*)
		echo 'FAIL UFS_STORAGE_MODE must be read-only or local-write' >&2
		exit 1
		;;
esac

[ -d "$source_dir/.git" ] || {
	echo "FAIL missing source tree $source_dir" >&2
	exit 1
}
for fragment in "$base_fragment" "$discovery_fragment" "$root_fragment"; do
	[ -r "$fragment" ] || {
		echo "FAIL missing kernel fragment: $fragment" >&2
		exit 1
	}
done
if [ "$storage_mode" = local-write ]; then
	[ -r "$write_fragment" ] || {
		echo "FAIL missing kernel fragment: $write_fragment" >&2
		exit 1
	}
fi
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ]
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ]
git -C "$source_dir" merge-base --is-ancestor "$expected_base" \
	"$expected_commit"
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ ! -d "$output_dir" ] ||
	[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
	echo 'FAIL output directory is not empty' >&2
	exit 1
}

export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
export KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s \
	--format=%cD "$expected_base")
export PYTHONHASHSEED=0
# Clang otherwise records the distinct O= directory in DWARF. That changes the
# vDSO build IDs embedded in Image and the debug sections of modules. The
# compat vDSO deliberately does not inherit KCFLAGS, so give its compiler the
# same exact debug-path contract through CC_COMPAT.
debug_flags="-fdebug-prefix-map=$source_dir=/usr/src/rog5-linux -fdebug-compilation-dir=/usr/src/rog5-linux-build"
export KCFLAGS=$debug_flags
export KAFLAGS=$KCFLAGS
export CC_COMPAT="clang $debug_flags"

kernel_make() {
	case ${KBUILD_CCACHE:-0} in
		0) make "$@" ;;
		1)
			command -v ccache >/dev/null || {
				echo 'FAIL KBUILD_CCACHE=1 but ccache is unavailable' >&2
				exit 1
			}
			CCACHE_COMPILERCHECK=content CCACHE_CONFIGPATH=/dev/null \
				make "$@" 'CC=ccache clang' 'HOSTCC=ccache clang' \
				'HOSTCXX=ccache clang++'
			;;
		*)
			echo 'FAIL KBUILD_CCACHE must be 0 or 1' >&2
			exit 1
			;;
	esac
}

mkdir -p "$output_dir"
kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 defconfig
if [ "$storage_mode" = local-write ]; then
	"$source_dir/scripts/kconfig/merge_config.sh" -m -O "$output_dir" \
		"$output_dir/.config" "$base_fragment" "$discovery_fragment" \
		"$root_fragment" "$write_fragment"
else
	"$source_dir/scripts/kconfig/merge_config.sh" -m -O "$output_dir" \
		"$output_dir/.config" "$base_fragment" "$discovery_fragment" \
		"$root_fragment"
fi
kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 olddefconfig
kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
	JOBS="$btf_jobs" Image.gz

deferred_module_dir=
if grep -qx 'CONFIG_SCSI_UFSHCD=m' "$output_dir/.config"; then
	for symbol in \
		CONFIG_SCSI_UFSHCD_PLATFORM=m \
		CONFIG_SCSI_UFS_QCOM=m \
		CONFIG_PHY_QCOM_QMP_UFS=m; do
		grep -qx "$symbol" "$output_dir/.config" || {
			echo "FAIL incomplete deferred UFS configuration: $symbol" >&2
			exit 1
		}
	done
	case $storage_mode in
		read-only)
			grep -qx 'CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y' \
				"$output_dir/.config" || {
				echo 'FAIL read-only mode lost the UFS discovery guard' >&2
				exit 1
			}
			;;
		local-write)
			grep -qx 'CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y' \
				"$output_dir/.config" || {
				echo 'FAIL local-write mode lost UFS discovery containment' >&2
				exit 1
			}
			grep -qx 'CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=y' \
				"$output_dir/.config" || {
				echo 'FAIL local-write mode lacks the bounded data-write profile' >&2
				exit 1
			}
			;;
	esac
	kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
		JOBS="$btf_jobs" \
		drivers/phy/qualcomm/phy-qcom-qmp-ufs.ko \
		drivers/ufs/core/ufshcd-core.ko \
		drivers/ufs/host/ufshcd-pltfrm.ko \
		drivers/ufs/host/ufs-qcom.ko

	deferred_module_dir=$output_dir/deferred-ufs-modules
	mkdir -m 0755 "$deferred_module_dir"
	install -m 0644 \
		"$output_dir/drivers/phy/qualcomm/phy-qcom-qmp-ufs.ko" \
		"$deferred_module_dir/phy-qcom-qmp-ufs.ko"
	install -m 0644 "$output_dir/drivers/ufs/core/ufshcd-core.ko" \
		"$deferred_module_dir/ufshcd-core.ko"
	install -m 0644 "$output_dir/drivers/ufs/host/ufshcd-pltfrm.ko" \
		"$deferred_module_dir/ufshcd-pltfrm.ko"
	install -m 0644 "$output_dir/drivers/ufs/host/ufs-qcom.ko" \
		"$deferred_module_dir/ufs-qcom.ko"
	for module in phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko \
		ufs-qcom.ko; do
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
		path=$deferred_module_dir/$module
		[ "$(modinfo -F name "$path")" = "$expected_name" ] &&
			[ "$(modinfo -F vermagic "$path" | awk '{ print $1 }')" = \
				"$expected_release" ] &&
			[ "$(modinfo -F depends "$path")" = "$expected_depends" ] || {
			echo "FAIL invalid deferred UFS module: $module" >&2
			exit 1
		}
	done
fi

meta_hash() {
	printf '%s  %s\n' "$(sha256sum "$1" | cut -d ' ' -f 1)" "$2"
}

{
	printf 'base_commit=%s\n' "$expected_base"
	printf 'patched_commit=%s\n' "$expected_commit"
	printf 'patched_tree=%s\n' "$expected_tree"
	printf 'ufs_storage_mode=%s\n' "$storage_mode"
	printf 'compiler=%s\n' "$(clang --version | head -1)"
	printf 'kbuild_version=%s\n' "$KBUILD_BUILD_VERSION"
	printf 'debug_compilation_dir=%s\n' '/usr/src/rog5-linux-build'
	printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
	printf 'pahole_jobs=%s\n' "$btf_jobs"
	meta_hash "$base_fragment" /configs/kernel/rog5-mainline.fragment
	meta_hash "$discovery_fragment" \
		/configs/kernel/rog5-ufs-deferred-probe.fragment
	meta_hash "$root_fragment" /configs/kernel/rog5-persistent-root.fragment
	meta_hash "$output_dir/.config" /.config
	meta_hash "$output_dir/arch/arm64/boot/Image" /arch/arm64/boot/Image
	meta_hash "$output_dir/arch/arm64/boot/Image.gz" \
		/arch/arm64/boot/Image.gz
	if [ "$storage_mode" = local-write ]; then
		meta_hash "$write_fragment" /configs/kernel/rog5-ufs-local-write.fragment
	fi
	if [ -n "$deferred_module_dir" ]; then
		for module in phy-qcom-qmp-ufs.ko ufshcd-core.ko \
			ufshcd-pltfrm.ko ufs-qcom.ko; do
			meta_hash "$deferred_module_dir/$module" \
				"/deferred-ufs-modules/$module"
		done
	fi
} >"$output_dir/build-meta.txt"

cat "$output_dir/build-meta.txt"
echo "PASS dedicated Linux 7.1.4 $storage_mode persistent-root kernel build"
