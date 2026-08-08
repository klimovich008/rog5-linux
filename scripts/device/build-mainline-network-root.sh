#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4-network-root}
base_fragment=${BASE_FRAGMENT:-/workspace/repo/configs/kernel/rog5-mainline.fragment}
network_fragment=${NETWORK_FRAGMENT:-/workspace/repo/configs/kernel/rog5-network-root.fragment}
expected_commit=${LINUX_COMMIT:-7a5cef0db4795d9d453a12e0f61b5b7634fc4d40}
expected_release=${EXPECTED_RELEASE:-7.1.4-g7a5cef0db479}
if [ -n "${JOBS+x}" ]; then
	jobs=$JOBS
else
	jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '%s\n' 1)
	[ "$jobs" -le 16 ] || jobs=16
fi
btf_jobs=1
case $0 in
	/*) builder_path=$0 ;;
	*/*) builder_path=$(pwd -P)/$0 ;;
	*)
		echo 'FAIL invoke the network-root builder by an explicit path' >&2
		exit 1
		;;
esac

case ${ROG5_NETWORK_ROOT_CLEAN_ENV:-0} in
	0)
		clean_home=${HOME:-/nonexistent}
		exec /usr/bin/env -i PATH="$PATH" HOME="$clean_home" LC_ALL=C \
			SOURCE_DIR="$source_dir" OUTPUT_DIR="$output_dir" \
			BASE_FRAGMENT="$base_fragment" NETWORK_FRAGMENT="$network_fragment" \
			LINUX_COMMIT="$expected_commit" EXPECTED_RELEASE="$expected_release" \
			JOBS="$jobs" INCREMENTAL_BUILD="${INCREMENTAL_BUILD:-0}" \
			KBUILD_CCACHE="${KBUILD_CCACHE:-0}" \
			ROG5_NETWORK_ROOT_CLEAN_ENV=1 "$builder_path"
		;;
	1)
		environment_names=$(
			/usr/bin/env -0 |
				/usr/bin/cut -z -d= -f1 |
				/usr/bin/sort -z |
				/usr/bin/tr '\0' '\n'
		)
		expected_environment_names='BASE_FRAGMENT
EXPECTED_RELEASE
HOME
INCREMENTAL_BUILD
JOBS
KBUILD_CCACHE
LC_ALL
LINUX_COMMIT
NETWORK_FRAGMENT
OUTPUT_DIR
PATH
PWD
ROG5_NETWORK_ROOT_CLEAN_ENV
SHLVL
SOURCE_DIR
_'
		[ "$environment_names" = "$expected_environment_names" ] &&
			[ "$LC_ALL" = C ] &&
			[ "$PWD" = "$(pwd -P)" ] || {
			echo 'FAIL network-root builder environment is not the exact allowlist' >&2
			exit 1
		}
		;;
	*)
		echo 'FAIL invalid network-root builder environment state' >&2
		exit 1
		;;
esac
unset BASE_FRAGMENT EXPECTED_RELEASE JOBS LINUX_COMMIT NETWORK_FRAGMENT \
	OUTPUT_DIR ROG5_NETWORK_ROOT_CLEAN_ENV SOURCE_DIR environment_names \
	expected_environment_names
script_dir=$(CDPATH='' cd -- "${builder_path%/*}" && pwd)
kernel_contract=$script_dir/kernel-build-contract.sh
builder_path=$(realpath -e -- "$builder_path")

[ -d "$source_dir/.git" ] || { echo 'FAIL missing pinned Linux source' >&2; exit 1; }
[ -r "$base_fragment" ] && [ -r "$network_fragment" ]
[ -f "$kernel_contract" ] && [ ! -L "$kernel_contract" ] &&
	[ "$(stat -c '%u' "$kernel_contract")" = "$(id -u)" ] &&
	[ "$(stat -c '%a' "$kernel_contract")" = 755 ] || {
	echo 'FAIL unsafe kernel build contract' >&2
	exit 1
}
kernel_contract_sha256=$(sha256sum "$kernel_contract" | cut -d ' ' -f 1)
# shellcheck disable=SC1090,SC1091
. "$kernel_contract"
case $jobs in
	''|*[!0-9]*) rog5_kernel_fail 'JOBS must be an integer from 1 through 64' ;;
esac
[ "$jobs" -ge 1 ] && [ "$jobs" -le 64 ] ||
	rog5_kernel_fail 'JOBS must be an integer from 1 through 64'
[ -d "$source_dir" ] && [ ! -L "$source_dir" ] ||
	rog5_kernel_fail 'kernel source must be a regular directory'
source_dir=$(realpath -e -- "$source_dir")
output_dir=$(realpath -m -- "$output_dir")
case $output_dir in
	"$source_dir"|"$source_dir"/*)
		rog5_kernel_fail 'kernel output must be outside the source tree'
		;;
esac
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
actual_release=$(
	cd "$source_dir"
	KERNELVERSION=7.1.4 ./scripts/setlocalversion --no-local .
)
[ "$actual_release" = "$expected_release" ] || {
	echo "FAIL source Git state yields kernel release $actual_release" >&2
	exit 1
}
export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
export KBUILD_BUILD_VERSION=1
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s --format=%cD HEAD)
export KBUILD_BUILD_TIMESTAMP
export PYTHONHASHSEED=0

source_tree=$(git -C "$source_dir" rev-parse 'HEAD^{tree}')
base_fragment_sha256=$(sha256sum "$base_fragment" | cut -d ' ' -f 1)
network_fragment_sha256=$(sha256sum "$network_fragment" | cut -d ' ' -f 1)
cache_identity=$(rog5_kernel_cache_identity)
toolchain_identity=$(rog5_kernel_toolchain_identity \
	make clang clang++ ld.lld llvm-ar llvm-nm llvm-objcopy llvm-strip \
	llvm-objdump llvm-readelf pahole python3 bc bison flex openssl perl depmod \
	tar gzip)
build_state=$(
	printf 'format=rog5-kbuild-inputs-v1\n'
	printf 'source_path=%s\n' "$source_dir"
	printf 'output_path=%s\n' "$output_dir"
	printf 'source_commit=%s\n' "$expected_commit"
	printf 'source_tree=%s\n' "$source_tree"
	printf 'expected_release=%s\n' "$expected_release"
	printf 'base_fragment_sha256=%s\n' "$base_fragment_sha256"
	printf 'network_fragment_sha256=%s\n' "$network_fragment_sha256"
	printf 'builder_sha256=%s\n' "$(sha256sum "$0" | cut -d ' ' -f 1)"
	printf 'contract_sha256=%s\n' "$kernel_contract_sha256"
	printf 'arch=arm64\nllvm=1\n'
	printf 'kbuild_user=%s\n' "$KBUILD_BUILD_USER"
	printf 'kbuild_host=%s\n' "$KBUILD_BUILD_HOST"
	printf 'kbuild_timestamp=%s\n' "$KBUILD_BUILD_TIMESTAMP"
	printf 'kbuild_version=%s\n' "$KBUILD_BUILD_VERSION"
	printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
	printf 'pahole_jobs=%s\n' "$btf_jobs"
	printf '%s\n' "$cache_identity" "$toolchain_identity"
)
rog5_kernel_prepare_output "$output_dir" "$build_state"
rog5_kernel_cache_stats

rog5_kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 defconfig
"$source_dir/scripts/kconfig/merge_config.sh" -m -O "$output_dir" \
	"$output_dir/.config" "$base_fragment" "$network_fragment"
rog5_kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 olddefconfig
rog5_kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
	JOBS="$btf_jobs" Image.gz modules

modules_stage=$output_dir/modules-staging
rm -rf -- "$modules_stage"
rog5_kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 \
	INSTALL_MOD_PATH="$modules_stage" modules_install
[ "$(cat "$output_dir/include/config/kernel.release")" = \
	"$expected_release" ] || {
	echo 'FAIL built kernel release changed' >&2
	exit 1
}
source_date_epoch=$(git -C "$source_dir" show -s --format=%ct HEAD)
tar --sort=name --mtime="@$source_date_epoch" --owner=0 --group=0 \
	--numeric-owner -C "$modules_stage" -cf - lib/modules |
	gzip -n >"$output_dir/modules.tar.gz.tmp"
mv "$output_dir/modules.tar.gz.tmp" "$output_dir/modules.tar.gz"
rog5_kernel_cache_stats

{
	printf 'kernel_commit=%s\n' "$expected_commit"
	printf 'compiler=%s\n' "$(clang --version | head -1)"
	printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
	printf 'pahole_jobs=%s\n' "$btf_jobs"
	printf 'base_fragment_sha256=%s\n' \
		"$(sha256sum "$base_fragment" | cut -d ' ' -f 1)"
	printf 'network_fragment_sha256=%s\n' \
		"$(sha256sum "$network_fragment" | cut -d ' ' -f 1)"
	printf 'config_sha256=%s\n' \
		"$(sha256sum "$output_dir/.config" | cut -d ' ' -f 1)"
	printf 'image_sha256=%s\n' \
		"$(sha256sum "$output_dir/arch/arm64/boot/Image" | cut -d ' ' -f 1)"
	printf 'image_gz_sha256=%s\n' \
		"$(sha256sum "$output_dir/arch/arm64/boot/Image.gz" | cut -d ' ' -f 1)"
	printf 'modules_sha256=%s\n' \
		"$(sha256sum "$output_dir/modules.tar.gz" | cut -d ' ' -f 1)"
} >"$output_dir/build-meta.txt"

cat "$output_dir/build-meta.txt"
echo 'PASS dedicated Linux 7.1.4 UFS-disabled network-root build'
