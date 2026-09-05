#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-gpucc-common-diagnostic-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing SHA-256 manifest}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
module=$artifact_dir/gpucc-sm8350.ko
image=$artifact_dir/Image-7.1.4-network-root
modules=$artifact_dir/modules-7.1.4-network-root.tar.gz
meta=$artifact_dir/build-meta-7.1.4-network-root.txt
expected_image=c0127c338b6af50a51e51c1e4837961d9806d0be969cd7337c3e597583e2dd62
expected_modules=7c49c648c076326a6f008082f0d38e389bd8bb7c8a867ee0935d83e6a4195224
expected_module=0ccb0059ec1960becb3676903aaccb623f105dbc8df08984cbd13a7d1ea6e73c

"$repo/scripts/device/verify-network-root-bundle.sh" \
	"$artifact_dir" "$mkbootimg_dir" "$avbtool" "$expected_sums" okay
"$repo/scripts/device/verify-qcom-cc-registration-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0006-qcom-cc-add-attended-registration-trace.patch" \
	"$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch" \
	>/dev/null

check_exact_hash() {
	label=$1
	file=$2
	expected=$3
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] || {
		echo "FAIL $label is not the reviewed diagnostic build" >&2
		exit 1
	}
}
check_exact_hash Image "$image" "$expected_image"
check_exact_hash modules "$modules" "$expected_modules"
[ -f "$module" ] && [ ! -L "$module" ]
check_exact_hash GPUCC-module "$module" "$expected_module"

grep -qx \
	'kernel_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' "$meta"
grep -qx \
	'gpucc_patched_commit=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea' \
	"$meta"
grep -qx \
	'common_patched_commit=d4bb00313e92514f89bc0a9e7a7dffcb4884834f' \
	"$meta"
grep -qx \
	'patched_tree=3b185820802b882d05830b9c6aee35bff984e07b' "$meta"
grep -qx \
	'gpucc_trace_patch_sha256=50ec8d394583951ab00e65c38686775031d0abadc6a3faf1730edda13eb7be94' \
	"$meta"
grep -qx \
	'common_trace_patch_sha256=a6084f1b9f7d72fc984827a9f43559ef6a9a5cb3222a273775249924567f2df5' \
	"$meta"
grep -qx "image_sha256=$expected_image" "$meta"
grep -qx "modules_sha256=$expected_modules" "$meta"
grep -qx "gpucc_module_sha256=$expected_module" "$meta"

config=$artifact_dir/config-7.1.4-network-root
for symbol in \
	CONFIG_COMMON_CLK_QCOM=y \
	CONFIG_QCOM_GDSC=y \
	CONFIG_SM_GPUCC_8350=m \
	CONFIG_DRM_MSM=y \
	CONFIG_ARM_SMMU=y; do
	grep -qx "$symbol" "$config"
done

strings "$image" | grep -Fxq 'rog5_qcom_cc_probe_trace'
strings "$image" |
	grep -Fxq 'ROG5 QCOM CC diagnostic: phase=%s index=%d ret=%d'
for phase in \
	entry \
	allocation-complete \
	power-domain-attach-begin \
	power-domain-attach-complete \
	reset-register-begin \
	reset-register-complete \
	gdsc-allocation-begin \
	gdsc-allocation-complete \
	gdsc-register-begin \
	gdsc-register-complete \
	gdsc-action-begin \
	gdsc-action-complete \
	drop-protected-begin \
	drop-protected-complete \
	clock-hw-register-begin \
	clock-hw-register-complete \
	clock-regmap-register-begin \
	clock-regmap-register-complete \
	provider-register-begin \
	provider-register-complete \
	interconnect-register-begin \
	interconnect-register-complete \
	exit
do
	strings "$image" | grep -Fxq "$phase"
done

[ "$(modinfo -F name "$module")" = gpucc_sm8350 ]
[ -z "$(modinfo -F depends "$module")" ]
[ "$(modinfo -F vermagic "$module")" = \
	'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' ]
modinfo -p "$module" |
	grep -Fxq \
	'probe_trace:Emit progress notices for attended SM8350 GPUCC diagnostics (bool)'
readelf -S "$module" | grep -Eq '[[:space:]][.]BTF[[:space:]]'

module_path=$(tar -tzf "$modules" | grep -E '/gpucc-sm8350[.]ko$')
[ "$(printf '%s\n' "$module_path" | wc -l)" -eq 1 ]
[ "$(tar -xOzf "$modules" "$module_path" | sha256sum |
	cut -d ' ' -f 1)" = "$expected_module" ]

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
gpucc=/soc@0/clock-controller@3d90000
[ "$(fdtget -t s "$dtb" "$gpucc" status)" = okay ]
[ "$(fdtget -t s "$dtb" "$gpucc" compatible)" = qcom,sm8350-gpucc ]
[ "$(fdtget -t x "$dtb" "$gpucc" reg)" = '0 3d90000 0 9000' ]
for node in \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/iommu@3da0000 \
	/soc@0/remoteproc@3000000 \
	/soc@0/remoteproc@4080000 \
	/soc@0/remoteproc@5c00000 \
	/soc@0/remoteproc@a300000
do
	[ "$(fdtget -t s "$dtb" "$node" status)" = disabled ]
done

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/staging" "$stage/boot-args"
gzip -dc "$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz" |
	(cd "$stage/staging" && cpio -idm --quiet --no-absolute-filenames)
loader=$stage/staging/usr/local/sbin/rog5-load-mainline-recovery
grep -Fq 'qcom_cc_probe_trace=${ROG5_QCOM_CC_PROBE_TRACE:-0}' "$loader"
[ "$(grep -Fc \
	'command_line="$command_line rog5_qcom_cc_probe_trace=1"' "$loader")" -eq 1 ]

python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$artifact_dir/boot-5.4.210-network-root-stage.raw.img" \
	--out "$stage/boot-args" --format=mkbootimg --null >"$stage/boot.args"
tr '\000' '\n' <"$stage/boot.args" >"$stage/boot.args.lines"
command_line=$(awk '$0 == "--cmdline" { getline; print; exit }' \
	"$stage/boot.args.lines")
! printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -q '^rog5_qcom_cc_probe_trace='

for archive in \
	"$artifact_dir/rog5-network-root-initramfs.cpio.gz" \
	"$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz"
do
	listing=$(gzip -dc "$archive" | cpio -t 2>/dev/null)
	! printf '%s\n' "$listing" |
		grep -Eq '(^|/)(gpucc-sm8350[.]ko|a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn)$'
done

echo 'PASS common-clock phase diagnostic bundle; matching BTF module stays external, consumers stay disabled, and trace boot flag stays opt-in'
