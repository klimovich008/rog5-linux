#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-a660-ucode-allocation-build.sh BUILD_DIR PINNED_SOURCE FIRMWARE_ROOT ACCEPTED_CONFIG REGISTRATION_BUILD FIRMWARE_ONLY_BUILD}
source_dir=${2:?missing pinned source}
firmware_root=${3:?missing firmware root}
accepted_config=${4:?missing accepted registration config}
registration_build=${5:?missing accepted registration build}
firmware_build=${6:?missing accepted firmware-request-only build}
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
predecessor_verifier=$repo/scripts/device/verify-mainline-a660-firmware-request-only-build.sh
patch=$repo/patches/linux-7.1.4/0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch
patch_verifier=$repo/scripts/device/verify-a660-ucode-allocation-patch.sh
accepted_meta_sha256=9fced0679b2fa0a4a434fba7ff4b6e33ded021d7376e19c08dd09926689b8654
accepted_archive_sha256=ad3c4b441db6d2701e0e6bb945c1a4bf52d284e209873cb4b9250014386da680
accepted_msm_sha256=fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45

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

for command in awk cmp cut diff find git grep mkdir mktemp modinfo mv \
	readelf readlink rm sed sha256sum strings tar; do
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

"$predecessor_verifier" "$firmware_build" "$source_dir" "$firmware_root" \
	"$accepted_config" "$registration_build" >/dev/null
"$patch_verifier" "$patch" "$source_dir" >/dev/null

for identity in \
	'kernel_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' \
	'source_commit=d9ac316489f4258d389d6298659d5e9c22183400' \
	'source_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	"kernel_release=$expected_release" \
	'gmu_patch_sha256=0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637' \
	'firmware_patch_sha256=3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054' \
	'ucode_patch_sha256=6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2' \
	'patched_a6xx_gmu_sha256=126d1011942083ad63516de0bee1d62f18db4752199a1cbc6cfb5be3230e4ace' \
	'patched_msm_drv_sha256=bf109068950c2e04d6121a5aea8bee7c20d7c3535a05107728e197351fc6e3c6' \
	'patched_msm_gpu_sha256=d3312f908da1702a4f0e63b3e9aed9f77ed7fe352381c2e31647b8225e2993ec' \
	'patched_adreno_device_sha256=0954e9cc45a948c02dbecca34d41f1343f004880a983403baa668b3c96a095c2' \
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
check_meta_hash ucode_patch_sha256 "$patch"
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
	'accepted ucode-allocation config'
check_hash "$image" \
	52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db \
	'accepted ucode-allocation Image'
check_hash "$image_gz" \
	9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307 \
	'accepted ucode-allocation Image.gz'
check_hash "$symvers" \
	a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477 \
	'accepted ucode-allocation Module.symvers'
check_hash "$gpucc_module" \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
	'accepted ucode-allocation GPUCC module'
check_hash "$mdt_module" \
	001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 \
	'accepted ucode-allocation MDT module'

if [ "${ALLOW_UNPINNED_BUILD:-0}" != 1 ]; then
	case "$accepted_meta_sha256:$accepted_archive_sha256:$accepted_msm_sha256" in
		*PENDING_FIRST_BUILD*)
			fail 'accepted ucode-allocation hashes are not pinned'
			;;
	esac
	check_hash "$meta" "$accepted_meta_sha256" \
		'accepted ucode-allocation build metadata'
	check_hash "$archive" "$accepted_archive_sha256" \
		'accepted ucode-allocation module archive'
	check_hash "$msm_module" "$accepted_msm_sha256" \
		'accepted ucode-allocation MSM module'
fi

for symbol in \
	CONFIG_DRM_MSM=m \
	CONFIG_SM_GPUCC_8350=m
do
	grep -qx "$symbol" "$config" ||
		fail "ucode-allocation config omits: $symbol"
done
[ "$kms_state" = CONFIG_DRM_MSM_KMS=n ] ||
	fail 'internal KMS-disabled contract changed'
if grep -Eq '^CONFIG_DRM_MSM_KMS=(y|m)$' "$config"; then
	fail 'ucode-allocation config enables CONFIG_DRM_MSM_KMS'
fi

[ "$(modinfo -F name "$msm_module")" = msm ] ||
	fail 'ucode-allocation MSM module name changed'
[ "$(modinfo -F vermagic "$msm_module")" = \
	"$expected_release SMP preempt mod_unload aarch64" ] ||
	fail 'ucode-allocation MSM module vermagic changed'
modinfo -p "$msm_module" |
	grep -Fxq \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)' ||
	fail 'firmware_request_only module parameter is missing'
modinfo -p "$msm_module" |
	grep -Fxq \
	'ucode_allocation_only:Allocate and roll back exact A660 ucode once before GPU power (bool)' ||
	fail 'ucode_allocation_only module parameter is missing'
modinfo -p "$msm_module" | grep -Fxq 'separate_gpu_kms: (bool)' ||
	fail 'separate_gpu_kms module parameter is missing'
for marker in \
	'A660 firmware-only passed; reject open' \
	'A660 firmware-only failed: %d' \
	'A660 ucode-allocation-only passed and rolled back; reject open' \
	'A660 ucode-allocation-only failed: %d'
do
	strings "$msm_module" | grep -Fq "$marker" ||
		fail "diagnostic module marker is missing: $marker"
done
readelf -S "$msm_module" | grep -Eq '[[:space:]][.]BTF[[:space:]]' ||
	fail 'ucode-allocation MSM module has no BTF section'

firmware_pattern='a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
if tar -tzf "$archive" | grep -Eq "$firmware_pattern"; then
	fail 'A660 firmware exists in the ucode-allocation module archive'
fi
if find "$output_dir" -type f -printf '%f\n' |
	grep -Eq "$firmware_pattern"
then
	fail 'A660 firmware exists in the ucode-allocation build'
fi

check_hash "$firmware_build/build-meta.txt" \
	1cf2ea81cfc836f852827a8e0dbe8d8803c288a405f6ae66625de5dca7e51824 \
	'accepted firmware-only build metadata'
check_hash "$firmware_build/.config" \
	d2f3a6f919c3e1abf3d10d99a77165e43de0fc4888fda338f0625bae57cb35e0 \
	'accepted firmware-only config'
check_hash "$firmware_build/arch/arm64/boot/Image" \
	52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db \
	'accepted firmware-only Image'
check_hash "$firmware_build/arch/arm64/boot/Image.gz" \
	9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307 \
	'accepted firmware-only Image.gz'
check_hash "$firmware_build/Module.symvers" \
	a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477 \
	'accepted firmware-only Module.symvers'
check_hash "$firmware_build/modules.tar.gz" \
	04149f41648f12925a6f04261eed96bfecdd6174a10462c82c36213fef0d1bc9 \
	'accepted firmware-only module archive'
check_hash "$firmware_build/drivers/gpu/drm/msm/msm.ko" \
	eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082 \
	'accepted firmware-only MSM module'
check_hash "$firmware_build/drivers/clk/qcom/gpucc-sm8350.ko" \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
	'accepted firmware-only GPUCC module'
check_hash "$firmware_build/drivers/soc/qcom/mdt_loader.ko" \
	001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 \
	'accepted firmware-only MDT module'

cmp "$config" "$firmware_build/.config"
cmp "$image" "$firmware_build/arch/arm64/boot/Image"
cmp "$image_gz" "$firmware_build/arch/arm64/boot/Image.gz"
cmp "$symvers" "$firmware_build/Module.symvers"
cmp "$gpucc_module" \
	"$firmware_build/drivers/clk/qcom/gpucc-sm8350.ko"
cmp "$mdt_module" \
	"$firmware_build/drivers/soc/qcom/mdt_loader.ko"
if cmp -s "$msm_module" \
	"$firmware_build/drivers/gpu/drm/msm/msm.ko"
then
	fail 'ucode-allocation MSM module does not differ from firmware-only'
fi

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/firmware-only" "$stage/ucode-allocation"
tar -xzf "$firmware_build/modules.tar.gz" -C "$stage/firmware-only"
tar -xzf "$archive" -C "$stage/ucode-allocation"
module_rel=lib/modules/$expected_release/kernel/drivers/gpu/drm/msm/msm.ko
cmp "$stage/firmware-only/$module_rel" \
	"$firmware_build/drivers/gpu/drm/msm/msm.ko"
cmp "$stage/ucode-allocation/$module_rel" "$msm_module"
mv "$stage/firmware-only/$module_rel" "$stage/firmware-only-msm.ko"
mv "$stage/ucode-allocation/$module_rel" "$stage/ucode-allocation-msm.ko"
firmware_build_link=$(readlink \
	"$stage/firmware-only/lib/modules/$expected_release/build")
ucode_build_link=$(readlink \
	"$stage/ucode-allocation/lib/modules/$expected_release/build")
[ "$firmware_build_link" = \
	/root/build/rog5-linux-7.1.4-a660-registration ] ||
	fail 'firmware-only module archive build link is not reproducible'
[ "$ucode_build_link" = "$firmware_build_link" ] ||
	fail 'module archive build links differ'
rm "$stage/firmware-only/lib/modules/$expected_release/build" \
	"$stage/ucode-allocation/lib/modules/$expected_release/build"
diff -qr "$stage/firmware-only" "$stage/ucode-allocation" >/dev/null ||
	fail 'module archives differ outside the exact MSM module'

echo 'PASS accepted firmware-only Image is unchanged; ucode-allocation MSM module differs exactly; config, ABI, every other module, storage exclusion, and zero embedded firmware remain accepted'
