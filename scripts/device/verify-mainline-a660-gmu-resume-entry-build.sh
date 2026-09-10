#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-a660-gmu-resume-entry-build.sh BUILD_DIR PINNED_SOURCE FIRMWARE_ROOT ACCEPTED_CONFIG REGISTRATION_BUILD FIRMWARE_ONLY_BUILD UCODE_BUILD}
source_dir=${2:?missing pinned source}
firmware_root=${3:?missing firmware root}
accepted_config=${4:?missing accepted registration config}
registration_build=${5:?missing accepted registration build}
firmware_build=${6:?missing accepted firmware-request-only build}
ucode_build=${7:?missing accepted ucode-allocation v7 build}
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
predecessor_verifier=$repo/scripts/device/verify-mainline-a660-ucode-allocation-build.sh
patch=$repo/patches/linux-7.1.4/0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch
patch_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-patch.sh
accepted_resume_meta_sha256=116f702a4605363c153cb35a908b1b1031f4e430478993394fe0fdc230db42bc
accepted_resume_archive_sha256=38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7
accepted_resume_msm_sha256=b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861

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

for command in awk cmp cut diff find git grep mkdir mktemp modinfo \
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

"$predecessor_verifier" "$ucode_build" "$source_dir" "$firmware_root" \
	"$accepted_config" "$registration_build" "$firmware_build" >/dev/null
"$patch_verifier" "$patch" "$source_dir" >/dev/null

for identity in \
	'kernel_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' \
	'source_commit=d9ac316489f4258d389d6298659d5e9c22183400' \
	'source_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	"kernel_release=$expected_release" \
	'gmu_patch_sha256=0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637' \
	'firmware_patch_sha256=3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054' \
	'ucode_patch_sha256=6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2' \
	'gmu_resume_entry_patch_sha256=a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051' \
	'patched_a6xx_gmu_sha256=e42eb79a417a6eace46358f5e2666b87dd4138eb8e1af843789b2e99b84fd395' \
	'patched_msm_drv_sha256=43e97deb263e5f845b95249612433ca183d4fd7f55be75e23be93b2a0bc83d26' \
	'patched_msm_gpu_sha256=32dd6be7c82e25cb44377717ffb97cd941a99269c6bf977a2eb49454c0d3cfb4' \
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
check_meta_hash gmu_resume_entry_patch_sha256 "$patch"
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
	'accepted resume-entry config'
check_hash "$image" \
	52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db \
	'accepted resume-entry Image'
check_hash "$image_gz" \
	9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307 \
	'accepted resume-entry Image.gz'
check_hash "$symvers" \
	a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477 \
	'accepted resume-entry Module.symvers'
check_hash "$gpucc_module" \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
	'accepted resume-entry GPUCC module'
check_hash "$mdt_module" \
	001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 \
	'accepted resume-entry MDT module'
check_hash "$msm_module" "$accepted_resume_msm_sha256" \
	'accepted resume-entry MSM module'

if [ "${ALLOW_UNPINNED_BUILD:-0}" != 1 ]; then
	case "$accepted_resume_meta_sha256:$accepted_resume_archive_sha256" in
		*PENDING_FIRST_BUILD*)
			fail 'accepted resume-entry hashes are not pinned'
			;;
	esac
	check_hash "$meta" "$accepted_resume_meta_sha256" \
		'accepted resume-entry build metadata'
	check_hash "$archive" "$accepted_resume_archive_sha256" \
		'accepted resume-entry module archive'
fi

for symbol in \
	CONFIG_DRM_MSM=m \
	CONFIG_SM_GPUCC_8350=m
do
	grep -qx "$symbol" "$config" ||
		fail "resume-entry config omits: $symbol"
done
[ "$kms_state" = CONFIG_DRM_MSM_KMS=n ] ||
	fail 'internal KMS-disabled contract changed'
if grep -Eq '^CONFIG_DRM_MSM_KMS=(y|m)$' "$config"; then
	fail 'resume-entry config enables CONFIG_DRM_MSM_KMS'
fi

[ "$(modinfo -F name "$msm_module")" = msm ] ||
	fail 'resume-entry MSM module name changed'
[ "$(modinfo -F vermagic "$msm_module")" = \
	"$expected_release SMP preempt mod_unload aarch64" ] ||
	fail 'resume-entry MSM module vermagic changed'
for parameter in \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)' \
	'ucode_allocation_only:Allocate and roll back exact A660 ucode once before GPU power (bool)' \
	'gmu_resume_entry_only:Stop one exact A660 open at GMU resume entry before resource activation (bool)' \
	'separate_gpu_kms: (bool)'
do
	modinfo -p "$msm_module" | grep -Fxq "$parameter" ||
		fail "resume-entry module parameter is missing: $parameter"
done
for marker in \
	'A660 firmware-only passed; reject open' \
	'A660 ucode-allocation-only passed and rolled back; reject open' \
	'A660 GMU resume entry reached before resource activation; reject resume' \
	'A660 GMU resume entry passed and rolled back; reject open'
do
	strings "$msm_module" | grep -Fq "$marker" ||
		fail "diagnostic module marker is missing: $marker"
done
readelf -S "$msm_module" | grep -Eq '[[:space:]][.]BTF[[:space:]]' ||
	fail 'resume-entry MSM module has no BTF section'

firmware_pattern='a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
if tar -tzf "$archive" | grep -Eq "$firmware_pattern"; then
	fail 'A660 firmware exists in the resume-entry module archive'
fi
if find "$output_dir" -type f -printf '%f\n' |
	grep -Eq "$firmware_pattern"
then
	fail 'A660 firmware exists in the resume-entry build'
fi

check_hash "$ucode_build/build-meta.txt" \
	9fced0679b2fa0a4a434fba7ff4b6e33ded021d7376e19c08dd09926689b8654 \
	'accepted v7 build metadata'
check_hash "$ucode_build/modules.tar.gz" \
	ad3c4b441db6d2701e0e6bb945c1a4bf52d284e209873cb4b9250014386da680 \
	'accepted v7 module archive'
check_hash "$ucode_build/drivers/gpu/drm/msm/msm.ko" \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	'accepted v7 MSM module'

for rel in \
	.config \
	arch/arm64/boot/Image \
	arch/arm64/boot/Image.gz \
	Module.symvers \
	drivers/clk/qcom/gpucc-sm8350.ko \
	drivers/soc/qcom/mdt_loader.ko
do
	cmp "$output_dir/$rel" "$ucode_build/$rel" ||
		fail "accepted v7 artifact changed: $rel"
done
if cmp -s "$msm_module" "$ucode_build/drivers/gpu/drm/msm/msm.ko"; then
	fail 'resume-entry MSM module differs contract was not met'
fi
if cmp -s "$archive" "$ucode_build/modules.tar.gz"; then
	fail 'resume-entry module archive does not differ from accepted v7'
fi

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/v7" "$stage/resume-entry"
tar -xzf "$ucode_build/modules.tar.gz" -C "$stage/v7"
tar -xzf "$archive" -C "$stage/resume-entry"
module_rel=lib/modules/$expected_release/kernel/drivers/gpu/drm/msm/msm.ko
cmp "$stage/v7/$module_rel" \
	"$ucode_build/drivers/gpu/drm/msm/msm.ko" ||
	fail 'accepted v7 archive MSM module differs from build output'
cmp "$stage/resume-entry/$module_rel" "$msm_module" ||
	fail 'resume-entry archive MSM module differs from build output'

(cd "$stage/v7" && find "lib/modules/$expected_release" -type f \
	-printf '%P\n' | sort) >"$stage/v7-files"
(cd "$stage/resume-entry" && find "lib/modules/$expected_release" -type f \
	-printf '%P\n' | sort) >"$stage/resume-entry-files"
cmp "$stage/v7-files" "$stage/resume-entry-files" ||
	fail 'module archive file lists differ'

different=0
while IFS= read -r rel; do
	v7_file=$stage/v7/lib/modules/$expected_release/$rel
	resume_file=$stage/resume-entry/lib/modules/$expected_release/$rel
	if cmp -s "$v7_file" "$resume_file"; then
		continue
	fi
	[ "$rel" = kernel/drivers/gpu/drm/msm/msm.ko ] ||
		fail "unexpected module archive difference: $rel"
	different=$((different + 1))
done <"$stage/v7-files"
[ "$different" -eq 1 ] ||
	fail "module archives have $different changed files, expected 1"

(cd "$stage/v7" && find "lib/modules/$expected_release" -type l \
	-printf '%P %l\n' | sort) >"$stage/v7-links"
(cd "$stage/resume-entry" && find "lib/modules/$expected_release" -type l \
	-printf '%P %l\n' | sort) >"$stage/resume-entry-links"
cmp "$stage/v7-links" "$stage/resume-entry-links" ||
	fail 'module archive symlink targets differ'
[ "$(readlink \
	"$stage/resume-entry/lib/modules/$expected_release/build")" = \
	/root/build/rog5-linux-7.1.4-a660-registration ] ||
	fail 'resume-entry archive build link is not reproducible'

echo 'PASS accepted v7 Image is unchanged'
echo 'PASS resume-entry MSM module differs only from its accepted v7 predecessor'
echo 'PASS A660 GMU resume-entry build is exact-stack, modular, firmware-clean, BTF-bearing, and archive-isolated'
