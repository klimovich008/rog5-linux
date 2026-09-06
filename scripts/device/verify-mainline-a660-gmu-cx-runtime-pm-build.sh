#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-a660-gmu-cx-runtime-pm-build.sh BUILD_DIR PINNED_SOURCE FIRMWARE_ROOT ACCEPTED_CONFIG REGISTRATION_BUILD FIRMWARE_ONLY_BUILD UCODE_BUILD RESUME_BUILD}
source_dir=${2:?missing pinned source}
firmware_root=${3:?missing firmware root}
accepted_config=${4:?missing accepted registration config}
registration_build=${5:?missing accepted registration build}
firmware_build=${6:?missing accepted firmware-request-only build}
ucode_build=${7:?missing accepted ucode-allocation v7 build}
resume_build=${8:?missing accepted GMU resume-entry v8 build}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
meta=$output_dir/build-meta.txt
config=$output_dir/.config
image=$output_dir/arch/arm64/boot/Image
image_gz=$output_dir/arch/arm64/boot/Image.gz
archive=$output_dir/modules.tar.gz
symvers=$output_dir/Module.symvers
msm_module=$output_dir/drivers/gpu/drm/msm/msm.ko
gpucc_module=$output_dir/drivers/clk/qcom/gpucc-sm8350.ko
mdt_module=$output_dir/drivers/soc/qcom/mdt_loader.ko
expected_release=7.1.4-rog5-a660reg1
kms_state=CONFIG_DRM_MSM_KMS=n
predecessor_verifier=$repo/scripts/device/verify-mainline-a660-gmu-resume-entry-build.sh
patch=$repo/patches/linux-7.1.4/0016-drm-msm-add-a660-gmu-cx-runtime-pm-diagnostic.patch
patch_verifier=$repo/scripts/device/verify-a660-gmu-cx-runtime-pm-patch.sh
accepted_v8_meta_sha256=116f702a4605363c153cb35a908b1b1031f4e430478993394fe0fdc230db42bc
accepted_v8_archive_sha256=38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7
accepted_v8_msm_sha256=b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861
accepted_cx_meta_sha256=dbc7270338b3c0589863db84fa9bc2abc63a1dfcfb42f83c1394f48122c298cb
accepted_cx_archive_sha256=87e5c3bae7d5034b64aea7212be8372506bf8b28cbdca7fb1b79bb20db50b9d0
accepted_cx_msm_sha256=c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$2
	label=$3
	if [ ! -f "$file" ] || [ -L "$file" ] || [ ! -r "$file" ]; then
		fail "$label is missing, linked, or unreadable: $file"
	fi
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		fail "$label hash mismatch: expected $expected, got $actual"
}

check_meta_hash() {
	label=$1
	file=$2
	expected=$(sed -n "s/^${label}=//p" "$meta")
	[ "$(printf '%s\n' "$expected" |
		awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] ||
		fail "metadata field is missing or duplicated: $label"
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ] ||
		fail "metadata hash does not match $label"
}

for command in awk cmp cut find git grep mkdir mktemp modinfo \
	readelf readlink rm sed sha256sum sort strings tar; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done
for tool in "$predecessor_verifier" "$patch_verifier"; do
	[ -x "$tool" ] || fail "missing executable verifier: $tool"
done
for file in "$meta" "$config" "$image" "$image_gz" "$archive" "$symvers" \
	"$msm_module" "$gpucc_module" "$mdt_module"
do
	[ -s "$file" ] || fail "missing build output: $file"
done

SKIP_V7_UMBRELLA_RUN=1 \
	"$predecessor_verifier" "$resume_build" "$source_dir" \
		"$firmware_root" "$accepted_config" "$registration_build" \
		"$firmware_build" "$ucode_build" >/dev/null
SKIP_V9_UMBRELLA_RUN=1 \
	"$patch_verifier" "$patch" "$source_dir" >/dev/null

for identity in \
	'kernel_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' \
	'source_commit=d9ac316489f4258d389d6298659d5e9c22183400' \
	'source_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	"kernel_release=$expected_release" \
	'accepted_v8_meta_sha256=116f702a4605363c153cb35a908b1b1031f4e430478993394fe0fdc230db42bc' \
	'accepted_v8_archive_sha256=38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7' \
	'accepted_v8_msm_sha256=b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861' \
	'gmu_patch_sha256=0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637' \
	'firmware_patch_sha256=3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054' \
	'ucode_patch_sha256=6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2' \
	'gmu_resume_entry_patch_sha256=a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051' \
	'gmu_cx_runtime_pm_patch_sha256=5eef04eb711443acaaf4295e926577f90073b8ab62414cff3d18de2272d3a152' \
	'patched_a6xx_gmu_sha256=cc76b2865877853f5e9d9508f704d242dc35847625ce94aa4fa14f608743c1a4' \
	'patched_msm_drv_sha256=ec7e4a1820b03b27ba51691a2b6afaa993384a467c68db353fc691adec8b5957' \
	'patched_msm_gpu_sha256=5fa397c9fd1dade1040074ec3dbbf67258eee3a6f23ef4da30169a40b3d4393a' \
	'patched_adreno_device_sha256=2e72b3ce7aa47fad1d5c82d6ab662e6f98895bad15876b631ecafecad0308b45' \
	'patched_a6xx_gpu_sha256=34ba40a1de4705b471a09266c51a1b5d20f06534faea6bff70d2b0025d185ae7' \
	'patched_a6xx_gpu_h_sha256=5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5' \
	'python_hash_seed=0' \
	'pahole_jobs=1'
do
	grep -Fqx "$identity" "$meta" ||
		fail "build metadata omits: $identity"
done

check_meta_hash base_fragment_sha256 \
	"$repo/configs/kernel/rog5-mainline.fragment"
check_meta_hash network_fragment_sha256 \
	"$repo/configs/kernel/rog5-network-root.fragment"
check_meta_hash registration_fragment_sha256 \
	"$repo/configs/kernel/rog5-a660-registration.fragment"
check_meta_hash gmu_patch_sha256 \
	"$repo/patches/linux-7.1.4/0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch"
check_meta_hash firmware_patch_sha256 \
	"$repo/patches/linux-7.1.4/0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch"
check_meta_hash ucode_patch_sha256 \
	"$repo/patches/linux-7.1.4/0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch"
check_meta_hash gmu_resume_entry_patch_sha256 \
	"$repo/patches/linux-7.1.4/0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch"
check_meta_hash gmu_cx_runtime_pm_patch_sha256 "$patch"
check_meta_hash config_sha256 "$config"
check_meta_hash image_sha256 "$image"
check_meta_hash image_gz_sha256 "$image_gz"
check_meta_hash modules_sha256 "$archive"
check_meta_hash module_symvers_sha256 "$symvers"
check_meta_hash gpucc_module_sha256 "$gpucc_module"
check_meta_hash mdt_module_sha256 "$mdt_module"
check_meta_hash msm_module_sha256 "$msm_module"

check_hash "$config" \
	d2f3a6f919c3e1abf3d10d99a77165e43de0fc4888fda338f0625bae57cb35e0 \
	'accepted GMU/CX config'
check_hash "$image" \
	52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db \
	'accepted GMU/CX Image'
check_hash "$image_gz" \
	9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307 \
	'accepted GMU/CX Image.gz'
check_hash "$symvers" \
	a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477 \
	'accepted GMU/CX Module.symvers'
check_hash "$gpucc_module" \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
	'accepted GMU/CX GPUCC module'
check_hash "$mdt_module" \
	001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 \
	'accepted GMU/CX MDT module'

if [ "${ALLOW_UNPINNED_BUILD:-0}" != 1 ]; then
	case "$accepted_cx_meta_sha256:$accepted_cx_archive_sha256:$accepted_cx_msm_sha256" in
		*PENDING_V10*)
			fail 'accepted GMU/CX build hashes are not pinned'
			;;
	esac
	check_hash "$meta" "$accepted_cx_meta_sha256" \
		'accepted GMU/CX build metadata'
	check_hash "$archive" "$accepted_cx_archive_sha256" \
		'accepted GMU/CX module archive'
	check_hash "$msm_module" "$accepted_cx_msm_sha256" \
		'accepted GMU/CX MSM module'
fi

for symbol in \
	CONFIG_DRM_MSM=m \
	CONFIG_SM_GPUCC_8350=m
do
	grep -qx "$symbol" "$config" ||
		fail "GMU/CX config omits: $symbol"
done
[ "$kms_state" = CONFIG_DRM_MSM_KMS=n ] ||
	fail 'internal KMS-disabled contract changed'
if grep -Eq '^CONFIG_DRM_MSM_KMS=(y|m)$' "$config"; then
	fail 'GMU/CX config enables CONFIG_DRM_MSM_KMS'
fi

[ "$(modinfo -F name "$msm_module")" = msm ] ||
	fail 'GMU/CX MSM module name changed'
[ "$(modinfo -F vermagic "$msm_module")" = \
	"$expected_release SMP preempt mod_unload aarch64" ] ||
	fail 'GMU/CX MSM module vermagic changed'
for parameter in \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)' \
	'ucode_allocation_only:Allocate and roll back exact A660 ucode once before GPU power (bool)' \
	'gmu_resume_entry_only:Stop one exact A660 open at GMU resume entry before resource activation (bool)' \
	'gmu_cx_runtime_pm_only:Resume and synchronously roll back exact A660 GMU/CX power once before GX (bool)' \
	'separate_gpu_kms: (bool)'
do
	modinfo -p "$msm_module" | grep -Fxq "$parameter" ||
		fail "GMU/CX module parameter is missing: $parameter"
done
for marker in \
	'A660 firmware-only passed; reject open' \
	'A660 ucode-allocation-only passed and rolled back; reject open' \
	'A660 GMU resume entry reached before resource activation; reject resume' \
	'A660 GMU resume entry passed and rolled back; reject open' \
	'A660 GMU/CX runtime PM resumed and synchronously suspended; reject resume' \
	'A660 GMU/CX runtime PM passed and GPU load rolled back; reject open'
do
	strings "$msm_module" | grep -Fq "$marker" ||
		fail "diagnostic module marker is missing: $marker"
done
readelf -S "$msm_module" | grep -Eq '[[:space:]][.]BTF[[:space:]]' ||
	fail 'GMU/CX MSM module has no BTF section'

firmware_pattern='a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
if tar -tzf "$archive" | grep -Eq "$firmware_pattern"; then
	fail 'A660 firmware exists in the GMU/CX module archive'
fi
if find "$output_dir" -type f -printf '%f\n' |
	grep -Eq "$firmware_pattern"
then
	fail 'A660 firmware exists in the GMU/CX build'
fi

check_hash "$resume_build/build-meta.txt" "$accepted_v8_meta_sha256" \
	'accepted v8 build metadata'
check_hash "$resume_build/modules.tar.gz" "$accepted_v8_archive_sha256" \
	'accepted v8 module archive'
check_hash "$resume_build/drivers/gpu/drm/msm/msm.ko" \
	"$accepted_v8_msm_sha256" 'accepted v8 MSM module'

for rel in \
	.config \
	arch/arm64/boot/Image \
	arch/arm64/boot/Image.gz \
	Module.symvers \
	drivers/clk/qcom/gpucc-sm8350.ko \
	drivers/soc/qcom/mdt_loader.ko
do
	cmp "$output_dir/$rel" "$resume_build/$rel" ||
		fail "accepted v8 artifact changed: $rel"
done
if cmp -s "$msm_module" "$resume_build/drivers/gpu/drm/msm/msm.ko"; then
	fail 'GMU/CX runtime-PM MSM module differs contract was not met'
fi
if cmp -s "$archive" "$resume_build/modules.tar.gz"; then
	fail 'GMU/CX module archive does not differ from accepted v8'
fi

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/v8" "$stage/gmu-cx"
tar -xzf "$resume_build/modules.tar.gz" -C "$stage/v8"
tar -xzf "$archive" -C "$stage/gmu-cx"
module_rel=lib/modules/$expected_release/kernel/drivers/gpu/drm/msm/msm.ko
cmp "$stage/v8/$module_rel" \
	"$resume_build/drivers/gpu/drm/msm/msm.ko" ||
	fail 'accepted v8 archive MSM module differs from build output'
cmp "$stage/gmu-cx/$module_rel" "$msm_module" ||
	fail 'GMU/CX archive MSM module differs from build output'

(cd "$stage/v8" && find "lib/modules/$expected_release" -type f \
	-printf '%P\n' | sort) >"$stage/v8-files"
(cd "$stage/gmu-cx" && find "lib/modules/$expected_release" -type f \
	-printf '%P\n' | sort) >"$stage/gmu-cx-files"
cmp "$stage/v8-files" "$stage/gmu-cx-files" ||
	fail 'module archive file lists differ'

different=0
while IFS= read -r rel; do
	v8_file=$stage/v8/lib/modules/$expected_release/$rel
	cx_file=$stage/gmu-cx/lib/modules/$expected_release/$rel
	if cmp -s "$v8_file" "$cx_file"; then
		continue
	fi
	[ "$rel" = kernel/drivers/gpu/drm/msm/msm.ko ] ||
		fail "unexpected module archive difference: $rel"
	different=$((different + 1))
done <"$stage/v8-files"
[ "$different" -eq 1 ] ||
	fail "module archives have $different changed files, expected 1"

(cd "$stage/v8" && find "lib/modules/$expected_release" -type l \
	-printf '%P %l\n' | sort) >"$stage/v8-links"
(cd "$stage/gmu-cx" && find "lib/modules/$expected_release" -type l \
	-printf '%P %l\n' | sort) >"$stage/gmu-cx-links"
cmp "$stage/v8-links" "$stage/gmu-cx-links" ||
	fail 'module archive symlink targets differ'
[ "$(readlink \
	"$stage/gmu-cx/lib/modules/$expected_release/build")" = \
	/root/build/rog5-linux-7.1.4-a660-registration ] ||
	fail 'GMU/CX archive build link is not reproducible'

echo 'PASS accepted v8 Image is unchanged'
echo 'PASS GMU/CX runtime-PM MSM module differs only from its accepted v8 predecessor'
echo 'PASS A660 GMU/CX runtime-PM build is exact-stack, modular, firmware-clean, BTF-bearing, archive-isolated, and offline-only'
