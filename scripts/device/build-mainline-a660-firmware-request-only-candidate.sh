#!/bin/sh
set -eu

repo=${REPO_ROOT:-/workspace/repo}
source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4-a660-registration}
base_fragment=${BASE_FRAGMENT:-$repo/configs/kernel/rog5-mainline.fragment}
network_fragment=${NETWORK_FRAGMENT:-$repo/configs/kernel/rog5-network-root.fragment}
registration_fragment=${REGISTRATION_FRAGMENT:-$repo/configs/kernel/rog5-a660-registration.fragment}
gmu_patch=${GMU_PATCH:-$repo/patches/linux-7.1.4/0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch}
firmware_patch=${FIRMWARE_PATCH:-$repo/patches/linux-7.1.4/0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch}
gmu_verifier=$repo/scripts/device/verify-a660-gmu-pwrlevels-patch.sh
firmware_verifier=$repo/scripts/device/verify-a660-firmware-request-only-patch.sh
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_source=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
expected_release=7.1.4-rog5-a660reg1
repro_source_dir=/root/src/linux-7.1.4
repro_output_dir=/root/build/rog5-linux-7.1.4-a660-registration
work_source=/tmp/rog5-a660-registration-source
jobs=${JOBS:-1}
btf_jobs=1

[ "$source_dir" = "$repro_source_dir" ] || {
	echo "FAIL SOURCE_DIR must be $repro_source_dir" >&2
	exit 1
}
[ "$output_dir" = "$repro_output_dir" ] || {
	echo "FAIL OUTPUT_DIR must be $repro_output_dir" >&2
	exit 1
}
[ ! -e "$work_source" ] || {
	echo "FAIL temporary source path already exists: $work_source" >&2
	exit 1
}
[ -d "$source_dir/.git" ] || {
	echo "FAIL missing source tree: $source_dir" >&2
	exit 1
}
for input in "$base_fragment" "$network_fragment" \
	"$registration_fragment" "$gmu_patch" "$firmware_patch" \
	"$gmu_verifier" "$firmware_verifier"
do
	[ -r "$input" ]
done
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_source" ]
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ]
[ "$(git -C "$source_dir" rev-parse HEAD^^^^^^^)" = "$expected_base" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ ! -d "$output_dir" ] ||
	[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
		echo 'FAIL output directory is not empty' >&2
		exit 1
	}

"$gmu_verifier" "$source_dir" >/dev/null
"$firmware_verifier" "$firmware_patch" "$source_dir" >/dev/null

mkdir -p "$work_source" "$output_dir"
cleanup() {
	rm -rf "$work_source"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
git -C "$source_dir" archive --format=tar HEAD | tar -x -C "$work_source"
(cd "$work_source" &&
	git apply "$gmu_patch" &&
	git apply "$firmware_patch")

[ "$(sha256sum \
	"$work_source/drivers/gpu/drm/msm/adreno/a6xx_gmu.c" |
	cut -d ' ' -f 1)" = \
	126d1011942083ad63516de0bee1d62f18db4752199a1cbc6cfb5be3230e4ace ]
[ "$(sha256sum "$work_source/drivers/gpu/drm/msm/msm_drv.c" |
	cut -d ' ' -f 1)" = \
	c350e28c18ca723372fc044240a69b452b3698ce57df269a2dad0ad9e2cb569e ]
[ "$(sha256sum "$work_source/drivers/gpu/drm/msm/msm_gpu.h" |
	cut -d ' ' -f 1)" = \
	431f78761bbbfe92eab44f685aba653c6e05b54f140fd24fef1358667f05a6c7 ]
[ "$(sha256sum \
	"$work_source/drivers/gpu/drm/msm/adreno/adreno_device.c" |
	cut -d ' ' -f 1)" = \
	3654f703a3930add3c131e2bc77453fd1bc506a374075168a5ddbcd66f558379 ]

export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s \
	--format=%cD "$expected_source")
export KBUILD_BUILD_TIMESTAMP
export PYTHONHASHSEED=0

make -C "$work_source" O="$output_dir" ARCH=arm64 LLVM=1 \
	KERNELRELEASE="$expected_release" defconfig
(cd "$output_dir" &&
	"$work_source/scripts/kconfig/merge_config.sh" -m -O "$output_dir" \
		"$output_dir/.config" "$base_fragment" "$network_fragment" \
		"$registration_fragment")
make -C "$work_source" O="$output_dir" ARCH=arm64 LLVM=1 \
	KERNELRELEASE="$expected_release" olddefconfig

grep -qx 'CONFIG_DRM_MSM=m' "$output_dir/.config"
grep -qx 'CONFIG_SM_GPUCC_8350=m' "$output_dir/.config"
for symbol in DRM_MSM_KMS DRM_MSM_MDP4 DRM_MSM_MDP5 DRM_MSM_DPU \
	DRM_MSM_DP DRM_MSM_DSI DRM_MSM_HDMI
do
	if grep -Eq "^CONFIG_$symbol=(y|m)$" "$output_dir/.config"; then
		echo "FAIL final config enables CONFIG_$symbol" >&2
		exit 1
	fi
done

make -C "$work_source" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
	KERNELRELEASE="$expected_release" JOBS="$btf_jobs" Image.gz modules

modules_stage=$output_dir/modules-staging
make -C "$work_source" O="$output_dir" ARCH=arm64 LLVM=1 \
	KERNELRELEASE="$expected_release" INSTALL_MOD_PATH="$modules_stage" \
	modules_install
[ "$(cat "$output_dir/include/config/kernel.release")" = \
	"$expected_release" ]

source_date_epoch=$(git -C "$source_dir" show -s \
	--format=%ct "$expected_source")
tar --sort=name --mtime="@$source_date_epoch" --owner=0 --group=0 \
	--numeric-owner -C "$modules_stage" -cf - lib/modules |
	gzip -n >"$output_dir/modules.tar.gz.tmp"
mv "$output_dir/modules.tar.gz.tmp" "$output_dir/modules.tar.gz"

msm_module=$output_dir/drivers/gpu/drm/msm/msm.ko
gpucc_module=$output_dir/drivers/clk/qcom/gpucc-sm8350.ko
mdt_module=$output_dir/drivers/soc/qcom/mdt_loader.ko
for output in "$msm_module" "$gpucc_module" "$mdt_module" \
	"$output_dir/Module.symvers" "$output_dir/modules.tar.gz"
do
	[ -s "$output" ]
done

{
	printf 'kernel_commit=%s\n' "$expected_base"
	printf 'source_commit=%s\n' "$expected_source"
	printf 'source_tree=%s\n' "$expected_tree"
	printf 'kernel_release=%s\n' "$expected_release"
	printf 'compiler=%s\n' "$(clang --version | head -1)"
	printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
	printf 'pahole_jobs=%s\n' "$btf_jobs"
	printf 'base_fragment_sha256=%s\n' \
		"$(sha256sum "$base_fragment" | cut -d ' ' -f 1)"
	printf 'network_fragment_sha256=%s\n' \
		"$(sha256sum "$network_fragment" | cut -d ' ' -f 1)"
	printf 'registration_fragment_sha256=%s\n' \
		"$(sha256sum "$registration_fragment" | cut -d ' ' -f 1)"
	printf 'gmu_patch_sha256=%s\n' \
		"$(sha256sum "$gmu_patch" | cut -d ' ' -f 1)"
	printf 'firmware_patch_sha256=%s\n' \
		"$(sha256sum "$firmware_patch" | cut -d ' ' -f 1)"
	printf 'patched_a6xx_gmu_sha256=%s\n' \
		"$(sha256sum \
			"$work_source/drivers/gpu/drm/msm/adreno/a6xx_gmu.c" |
			cut -d ' ' -f 1)"
	printf 'patched_msm_drv_sha256=%s\n' \
		"$(sha256sum "$work_source/drivers/gpu/drm/msm/msm_drv.c" |
			cut -d ' ' -f 1)"
	printf 'patched_msm_gpu_sha256=%s\n' \
		"$(sha256sum "$work_source/drivers/gpu/drm/msm/msm_gpu.h" |
			cut -d ' ' -f 1)"
	printf 'patched_adreno_device_sha256=%s\n' \
		"$(sha256sum \
			"$work_source/drivers/gpu/drm/msm/adreno/adreno_device.c" |
			cut -d ' ' -f 1)"
	printf 'config_sha256=%s\n' \
		"$(sha256sum "$output_dir/.config" | cut -d ' ' -f 1)"
	printf 'image_sha256=%s\n' \
		"$(sha256sum "$output_dir/arch/arm64/boot/Image" |
			cut -d ' ' -f 1)"
	printf 'image_gz_sha256=%s\n' \
		"$(sha256sum "$output_dir/arch/arm64/boot/Image.gz" |
			cut -d ' ' -f 1)"
	printf 'modules_sha256=%s\n' \
		"$(sha256sum "$output_dir/modules.tar.gz" | cut -d ' ' -f 1)"
	printf 'module_symvers_sha256=%s\n' \
		"$(sha256sum "$output_dir/Module.symvers" | cut -d ' ' -f 1)"
	printf 'gpucc_module_sha256=%s\n' \
		"$(sha256sum "$gpucc_module" | cut -d ' ' -f 1)"
	printf 'mdt_module_sha256=%s\n' \
		"$(sha256sum "$mdt_module" | cut -d ' ' -f 1)"
	printf 'msm_module_sha256=%s\n' \
		"$(sha256sum "$msm_module" | cut -d ' ' -f 1)"
} >"$output_dir/build-meta.txt"

cat "$output_dir/build-meta.txt"
echo 'PASS Linux 7.1.4 storage-disabled A660 firmware-request-only build'
