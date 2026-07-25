#!/bin/sh
set -eu

repro_source_dir=/root/src/linux-7.1.4
repro_output_dir=/root/build/rog5-linux-7.1.4-network-root
source_dir=${SOURCE_DIR:-$repro_source_dir}
output_dir=${OUTPUT_DIR:-$repro_output_dir}
base_fragment=${BASE_FRAGMENT:-/workspace/repo/configs/kernel/rog5-mainline.fragment}
network_fragment=${NETWORK_FRAGMENT:-/workspace/repo/configs/kernel/rog5-network-root.fragment}
gpucc_patch=${GPUCC_TRACE_PATCH:-/workspace/repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch}
common_patch=${COMMON_TRACE_PATCH:-/workspace/repo/patches/linux-7.1.4/0006-qcom-cc-add-attended-registration-trace.patch}
ccf_patch=${CCF_TRACE_PATCH:-/workspace/repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch}
orphan_patch=${ORPHAN_TRACE_PATCH:-/workspace/repo/patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch}
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_gpucc=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea
expected_common=d4bb00313e92514f89bc0a9e7a7dffcb4884834f
expected_ccf=6eef0ab56609f5a5ee6d2de9807178daf1065fa7
expected_orphan=b2059b161861d6d7d1aeb9b7d93ad86b13d85048
expected_tree=040d5f9b7be022489079b2ea9cab20a04934d85f
expected_release=7.1.4-g7a5cef0db479
jobs=${JOBS:-1}
btf_jobs=1

[ "$source_dir" = "$repro_source_dir" ] || {
	echo "FAIL SOURCE_DIR must be $repro_source_dir for reproducible vDSO build IDs" >&2
	exit 1
}
[ "$output_dir" = "$repro_output_dir" ] || {
	echo "FAIL OUTPUT_DIR must be $repro_output_dir for reproducible vDSO build IDs" >&2
	exit 1
}
[ -d "$source_dir/.git" ] || {
	echo "FAIL missing source tree: $source_dir" >&2
	exit 1
}
for input in "$base_fragment" "$network_fragment" "$gpucc_patch" \
	"$common_patch" "$ccf_patch" "$orphan_patch"
do
	[ -r "$input" ]
done
[ "$(git -C "$source_dir" rev-parse HEAD^^^^)" = "$expected_base" ]
[ "$(git -C "$source_dir" rev-parse HEAD^^^)" = "$expected_gpucc" ]
[ "$(git -C "$source_dir" rev-parse HEAD^^)" = "$expected_common" ]
[ "$(git -C "$source_dir" rev-parse HEAD^)" = "$expected_ccf" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_orphan" ]
[ "$(git -C "$source_dir" rev-parse HEAD^{tree})" = "$expected_tree" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ ! -d "$output_dir" ] ||
	[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
	echo 'FAIL output directory is not empty' >&2
	exit 1
}

export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
export KBUILD_BUILD_TIMESTAMP="$(git -C "$source_dir" show -s \
	--format=%cD "$expected_base")"
export PYTHONHASHSEED=0

mkdir -p "$output_dir"
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 \
	KERNELRELEASE="$expected_release" defconfig
"$source_dir/scripts/kconfig/merge_config.sh" -m -O "$output_dir" \
	"$output_dir/.config" "$base_fragment" "$network_fragment"
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 \
	KERNELRELEASE="$expected_release" olddefconfig
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
	KERNELRELEASE="$expected_release" JOBS="$btf_jobs" Image.gz modules

modules_stage=$output_dir/modules-staging
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 \
	KERNELRELEASE="$expected_release" INSTALL_MOD_PATH="$modules_stage" \
	modules_install
[ "$(cat "$output_dir/include/config/kernel.release")" = "$expected_release" ]
source_date_epoch=$(git -C "$source_dir" show -s --format=%ct "$expected_base")
tar --sort=name --mtime="@$source_date_epoch" --owner=0 --group=0 \
	--numeric-owner -C "$modules_stage" -cf - lib/modules |
	gzip -n >"$output_dir/modules.tar.gz.tmp"
mv "$output_dir/modules.tar.gz.tmp" "$output_dir/modules.tar.gz"

module=$output_dir/drivers/clk/qcom/gpucc-sm8350.ko
[ -s "$module" ]
{
	printf 'kernel_commit=%s\n' "$expected_base"
	printf 'gpucc_patched_commit=%s\n' "$expected_gpucc"
	printf 'common_patched_commit=%s\n' "$expected_common"
	printf 'ccf_patched_commit=%s\n' "$expected_ccf"
	printf 'orphan_patched_commit=%s\n' "$expected_orphan"
	printf 'patched_tree=%s\n' "$expected_tree"
	printf 'kernel_release=%s\n' "$expected_release"
	printf 'compiler=%s\n' "$(clang --version | head -1)"
	printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
	printf 'pahole_jobs=%s\n' "$btf_jobs"
	printf 'gpucc_trace_patch_sha256=%s\n' \
		"$(sha256sum "$gpucc_patch" | cut -d ' ' -f 1)"
	printf 'common_trace_patch_sha256=%s\n' \
		"$(sha256sum "$common_patch" | cut -d ' ' -f 1)"
	printf 'ccf_trace_patch_sha256=%s\n' \
		"$(sha256sum "$ccf_patch" | cut -d ' ' -f 1)"
	printf 'orphan_trace_patch_sha256=%s\n' \
		"$(sha256sum "$orphan_patch" | cut -d ' ' -f 1)"
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
	printf 'gpucc_module_sha256=%s\n' \
		"$(sha256sum "$module" | cut -d ' ' -f 1)"
} >"$output_dir/build-meta.txt"

cat "$output_dir/build-meta.txt"
echo 'PASS Linux 7.1.4 network-root build with bounded GPUCC orphan tracing'
