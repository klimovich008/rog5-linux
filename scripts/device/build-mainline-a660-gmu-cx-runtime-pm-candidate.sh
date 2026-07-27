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
ucode_patch=${UCODE_PATCH:-$repo/patches/linux-7.1.4/0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch}
resume_patch=${RESUME_PATCH:-$repo/patches/linux-7.1.4/0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch}
cx_patch=${CX_PATCH:-$repo/patches/linux-7.1.4/0016-drm-msm-add-a660-gmu-cx-runtime-pm-diagnostic.patch}
gmu_verifier=$repo/scripts/device/verify-a660-gmu-pwrlevels-patch.sh
firmware_verifier=$repo/scripts/device/verify-a660-firmware-request-only-patch.sh
ucode_verifier=$repo/scripts/device/verify-a660-ucode-allocation-patch.sh
resume_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-patch.sh
cx_verifier=$repo/scripts/device/verify-a660-gmu-cx-runtime-pm-patch.sh
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_source=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
expected_release=7.1.4-rog5-a660reg1
repro_source_dir=/root/src/linux-7.1.4
repro_output_dir=/root/build/rog5-linux-7.1.4-a660-registration
work_source=/tmp/rog5-a660-registration-source
jobs=${JOBS:-1}
btf_jobs=1

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$2
	label=$3
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		fail "$label hash mismatch: expected $expected, got $actual"
}

[ "$source_dir" = "$repro_source_dir" ] ||
	fail "SOURCE_DIR must be $repro_source_dir"
[ "$output_dir" = "$repro_output_dir" ] ||
	fail "OUTPUT_DIR must be $repro_output_dir"
[ ! -e "$work_source" ] ||
	fail "temporary source path already exists: $work_source"
[ -d "$source_dir/.git" ] ||
	fail "missing source tree: $source_dir"
for input in "$base_fragment" "$network_fragment" \
	"$registration_fragment" "$gmu_patch" "$firmware_patch" \
	"$ucode_patch" "$resume_patch" "$cx_patch" "$gmu_verifier" \
	"$firmware_verifier" "$ucode_verifier" "$resume_verifier" \
	"$cx_verifier"
do
	[ -r "$input" ] || fail "missing build input: $input"
done
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_source" ] ||
	fail 'pinned source commit changed'
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ] ||
	fail 'pinned source tree changed'
[ "$(git -C "$source_dir" rev-parse HEAD^^^^^^^)" = "$expected_base" ] ||
	fail 'base Linux commit changed'
[ -z "$(git -C "$source_dir" status --porcelain)" ] ||
	fail 'pinned source worktree is not clean'
[ ! -d "$output_dir" ] ||
	[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] ||
	fail 'output directory is not empty'

"$gmu_verifier" "$source_dir" >/dev/null
"$firmware_verifier" "$firmware_patch" "$source_dir" >/dev/null
"$ucode_verifier" "$ucode_patch" "$source_dir" >/dev/null
SKIP_V7_UMBRELLA_RUN=1 \
	"$resume_verifier" "$resume_patch" "$source_dir" >/dev/null
SKIP_V9_UMBRELLA_RUN=1 \
	"$cx_verifier" "$cx_patch" "$source_dir" >/dev/null

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
	git apply "$firmware_patch" &&
	git apply "$ucode_patch" &&
	git apply "$resume_patch" &&
	git apply "$cx_patch")

check_hash "$work_source/drivers/gpu/drm/msm/adreno/a6xx_gmu.c" \
	cc76b2865877853f5e9d9508f704d242dc35847625ce94aa4fa14f608743c1a4 \
	'patched a6xx_gmu.c'
check_hash "$work_source/drivers/gpu/drm/msm/msm_drv.c" \
	ec7e4a1820b03b27ba51691a2b6afaa993384a467c68db353fc691adec8b5957 \
	'patched msm_drv.c'
check_hash "$work_source/drivers/gpu/drm/msm/msm_gpu.h" \
	5fa397c9fd1dade1040074ec3dbbf67258eee3a6f23ef4da30169a40b3d4393a \
	'patched msm_gpu.h'
check_hash "$work_source/drivers/gpu/drm/msm/adreno/adreno_device.c" \
	2e72b3ce7aa47fad1d5c82d6ab662e6f98895bad15876b631ecafecad0308b45 \
	'patched adreno_device.c'
check_hash "$work_source/drivers/gpu/drm/msm/adreno/a6xx_gpu.c" \
	34ba40a1de4705b471a09266c51a1b5d20f06534faea6bff70d2b0025d185ae7 \
	'patched a6xx_gpu.c'
check_hash "$work_source/drivers/gpu/drm/msm/adreno/a6xx_gpu.h" \
	5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5 \
	'patched a6xx_gpu.h'

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

grep -qx 'CONFIG_DRM_MSM=m' "$output_dir/.config" ||
	fail 'final config omits CONFIG_DRM_MSM=m'
grep -qx 'CONFIG_SM_GPUCC_8350=m' "$output_dir/.config" ||
	fail 'final config omits CONFIG_SM_GPUCC_8350=m'
for symbol in DRM_MSM_KMS DRM_MSM_MDP4 DRM_MSM_MDP5 DRM_MSM_DPU \
	DRM_MSM_DP DRM_MSM_DSI DRM_MSM_HDMI
do
	if grep -Eq "^CONFIG_$symbol=(y|m)$" "$output_dir/.config"; then
		fail "final config enables CONFIG_$symbol"
	fi
done

make -C "$work_source" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
	KERNELRELEASE="$expected_release" JOBS="$btf_jobs" Image.gz modules

modules_stage=$output_dir/modules-staging
make -C "$work_source" O="$output_dir" ARCH=arm64 LLVM=1 \
	KERNELRELEASE="$expected_release" INSTALL_MOD_PATH="$modules_stage" \
	modules_install
[ "$(cat "$output_dir/include/config/kernel.release")" = \
	"$expected_release" ] || fail 'kernel release changed'

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
	[ -s "$output" ] || fail "missing build output: $output"
done

{
	printf 'kernel_commit=%s\n' "$expected_base"
	printf 'source_commit=%s\n' "$expected_source"
	printf 'source_tree=%s\n' "$expected_tree"
	printf 'kernel_release=%s\n' "$expected_release"
	printf 'compiler=%s\n' "$(clang --version | head -1)"
	printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
	printf 'pahole_jobs=%s\n' "$btf_jobs"
	printf 'accepted_v8_meta_sha256=%s\n' \
		116f702a4605363c153cb35a908b1b1031f4e430478993394fe0fdc230db42bc
	printf 'accepted_v8_archive_sha256=%s\n' \
		38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7
	printf 'accepted_v8_msm_sha256=%s\n' \
		b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861
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
	printf 'ucode_patch_sha256=%s\n' \
		"$(sha256sum "$ucode_patch" | cut -d ' ' -f 1)"
	printf 'gmu_resume_entry_patch_sha256=%s\n' \
		"$(sha256sum "$resume_patch" | cut -d ' ' -f 1)"
	printf 'gmu_cx_runtime_pm_patch_sha256=%s\n' \
		"$(sha256sum "$cx_patch" | cut -d ' ' -f 1)"
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
	printf 'patched_a6xx_gpu_sha256=%s\n' \
		"$(sha256sum \
			"$work_source/drivers/gpu/drm/msm/adreno/a6xx_gpu.c" |
			cut -d ' ' -f 1)"
	printf 'patched_a6xx_gpu_h_sha256=%s\n' \
		"$(sha256sum \
			"$work_source/drivers/gpu/drm/msm/adreno/a6xx_gpu.h" |
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
echo 'PASS Linux 7.1.4 storage-disabled A660 GMU/CX runtime-PM build'
