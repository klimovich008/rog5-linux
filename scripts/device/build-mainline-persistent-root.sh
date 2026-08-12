#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4-discovery}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4-persistent-root}
base_fragment=${BASE_FRAGMENT:-/root/rog5-build/rog5-mainline.fragment}
discovery_fragment=${DISCOVERY_FRAGMENT:-/root/rog5-build/rog5-ufs-discovery.fragment}
root_fragment=${ROOT_FRAGMENT:-/root/rog5-build/rog5-persistent-root.fragment}
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_tree=d2f03d2055227b8b72ab41be949847a066924c5a
expected_release=7.1.4-gcfd385a1c754
jobs=${JOBS:-1}
btf_jobs=1

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
[ "$(git -C "$source_dir" rev-parse HEAD^)" = "$expected_base" ]
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ ! -d "$output_dir" ] ||
	[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
	echo 'FAIL output directory is not empty' >&2
	exit 1
}

export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
export KBUILD_BUILD_TIMESTAMP
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s \
	--format=%cD "$expected_base")
export PYTHONHASHSEED=0

mkdir -p "$output_dir"
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 defconfig
"$source_dir/scripts/kconfig/merge_config.sh" -m -O "$output_dir" \
	"$output_dir/.config" "$base_fragment" "$discovery_fragment" \
	"$root_fragment"
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 olddefconfig
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
	JOBS="$btf_jobs" Image.gz

deferred_module_dir=
if grep -qx 'CONFIG_SCSI_UFSHCD=m' "$output_dir/.config"; then
	for symbol in \
		CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y \
		CONFIG_SCSI_UFSHCD_PLATFORM=m \
		CONFIG_SCSI_UFS_QCOM=m; do
		grep -qx "$symbol" "$output_dir/.config" || {
			echo "FAIL incomplete deferred UFS configuration: $symbol" >&2
			exit 1
		}
	done
	make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
		JOBS="$btf_jobs" \
		drivers/ufs/core/ufshcd-core.ko \
		drivers/ufs/host/ufshcd-pltfrm.ko \
		drivers/ufs/host/ufs-qcom.ko

	deferred_module_dir=$output_dir/deferred-ufs-modules
	mkdir -m 0755 "$deferred_module_dir"
	install -m 0644 "$output_dir/drivers/ufs/core/ufshcd-core.ko" \
		"$deferred_module_dir/ufshcd-core.ko"
	install -m 0644 "$output_dir/drivers/ufs/host/ufshcd-pltfrm.ko" \
		"$deferred_module_dir/ufshcd-pltfrm.ko"
	install -m 0644 "$output_dir/drivers/ufs/host/ufs-qcom.ko" \
		"$deferred_module_dir/ufs-qcom.ko"
	for module in ufshcd-core.ko ufshcd-pltfrm.ko ufs-qcom.ko; do
		case $module in
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

{
	printf 'base_commit=%s\n' "$expected_base"
	printf 'patched_commit=%s\n' "$(git -C "$source_dir" rev-parse HEAD)"
	printf 'patched_tree=%s\n' "$expected_tree"
	printf 'compiler=%s\n' "$(clang --version | head -1)"
	printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
	printf 'pahole_jobs=%s\n' "$btf_jobs"
	sha256sum "$base_fragment" "$discovery_fragment" "$root_fragment" \
		"$output_dir/.config" \
		"$output_dir/arch/arm64/boot/Image" \
		"$output_dir/arch/arm64/boot/Image.gz"
	if [ -n "$deferred_module_dir" ]; then
		sha256sum \
			"$deferred_module_dir/ufshcd-core.ko" \
			"$deferred_module_dir/ufshcd-pltfrm.ko" \
			"$deferred_module_dir/ufs-qcom.ko"
	fi
} >"$output_dir/build-meta.txt"

cat "$output_dir/build-meta.txt"
echo 'PASS dedicated Linux 7.1.4 read-only persistent-root kernel build'
