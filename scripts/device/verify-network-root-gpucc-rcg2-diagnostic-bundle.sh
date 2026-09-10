#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-gpucc-rcg2-diagnostic-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256 EXPECTED_MANIFEST_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing SHA-256 manifest}
expected_manifest=${5:?missing expected manifest SHA-256}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
module=$artifact_dir/gpucc-sm8350.ko
image=$artifact_dir/Image-7.1.4-network-root
modules=$artifact_dir/modules-7.1.4-network-root.tar.gz
meta=$artifact_dir/build-meta-7.1.4-network-root.txt
expected_image=5759d3d15ca60f260aa89731aa78c94acd5d183eca67dc24c3723f8877f213e3
expected_modules=9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1
expected_module=9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a

case $expected_manifest in *[!0-9a-f]*|'') exit 1 ;; esac
[ "${#expected_manifest}" -eq 64 ]
[ -f "$expected_sums" ] && [ ! -L "$expected_sums" ]
[ "$(sha256sum "$expected_sums" | cut -d ' ' -f 1)" = "$expected_manifest" ]
"$repo/scripts/device/verify-network-root-bundle.sh" \
	"$artifact_dir" "$mkbootimg_dir" "$avbtool" "$expected_sums" okay
"$repo/scripts/device/verify-qcom-cc-registration-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0006-qcom-cc-add-attended-registration-trace.patch" \
	"$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch" \
	>/dev/null
"$repo/scripts/device/verify-ccf-registration-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch" \
	>/dev/null
"$repo/scripts/device/verify-ccf-orphan-reparent-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch" \
	>/dev/null
"$repo/scripts/device/verify-ccf-orphan-parent-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0009-clk-trace-attended-SM8350-GPUCC-orphan-parent-lookup.patch" \
	>/dev/null
"$repo/scripts/device/verify-rcg2-parent-read-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0010-clk-qcom-trace-attended-SM8350-DISPCC-RCG-parent-read.patch" \
	>/dev/null
"$repo/scripts/device/test-rcg2-parent-read-trace-budget.sh" >/dev/null

check_exact_hash() {
	label=$1
	file=$2
	expected=$3
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] || {
		echo "FAIL $label is not the reviewed v14 RCG2 diagnostic build" >&2
		exit 1
	}
}

[ -f "$module" ] && [ ! -L "$module" ]
check_exact_hash Image "$image" "$expected_image"
check_exact_hash modules "$modules" "$expected_modules"
check_exact_hash GPUCC-module "$module" "$expected_module"
check_exact_hash mainline-metadata "$meta" \
	beab68a7c0633e84ff5450860fe223ff3dbd85a9edc0023901c2eccbd720c4cc

for identity in \
	'kernel_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' \
	'gpucc_patched_commit=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea' \
	'common_patched_commit=d4bb00313e92514f89bc0a9e7a7dffcb4884834f' \
	'ccf_patched_commit=6eef0ab56609f5a5ee6d2de9807178daf1065fa7' \
	'orphan_patched_commit=b2059b161861d6d7d1aeb9b7d93ad86b13d85048' \
	'parent_patched_commit=f7c0a9d067db77f05a40a5bc242c1e14ac297ac5' \
	'rcg2_patched_commit=6e40861cc51c067f9989c4513003e8fbd046c22f' \
	'patched_tree=49ef6cb95768496b8f926b11e428ea224406464e' \
	'rcg2_trace_patch_sha256=ac7975bf5f4cb2791f45a2fe8b5b811c7e60fd4692f8aff4cd71a2f2150fa3c6' \
	"image_sha256=$expected_image" \
	"modules_sha256=$expected_modules" \
	"gpucc_module_sha256=$expected_module"
do
	grep -Fqx "$identity" "$meta"
done

config=$artifact_dir/config-7.1.4-network-root
for symbol in \
	CONFIG_COMMON_CLK_QCOM=y \
	CONFIG_QCOM_GDSC=y \
	CONFIG_SM_GPUCC_8350=m \
	CONFIG_DRM_MSM=y \
	CONFIG_ARM_SMMU=y
do
	grep -qx "$symbol" "$config"
done

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
strings "$image" >"$stage/image.strings"
for parameter in \
	rog5_qcom_cc_probe_trace \
	rog5_ccf_register_trace \
	rog5_rcg2_parent_trace
do
	grep -Fxq "$parameter" "$stage/image.strings"
done
grep -Fxq \
	'ROG5 CCF diagnostic: phase=%s clock=%s ret=%d' \
	"$stage/image.strings"
grep -Fq \
	'ROG5 RCG2 diagnostic: phase=%s clock=%s ret=%d' \
	"$stage/image.strings"
for marker in \
	orphan-scan-entry \
	orphan-parent-lookup-begin \
	orphan-parent-shape \
	orphan-runtime-state \
	orphan-get-parent-begin \
	orphan-get-parent-complete \
	orphan-parent-cache-begin \
	orphan-parent-cache-complete \
	orphan-parent-lookup-complete \
	orphan-parent-resolved \
	orphan-set-parent-before-begin \
	orphan-set-parent-before-complete \
	orphan-set-parent-after-begin \
	orphan-set-parent-after-complete \
	orphan-accuracy-begin \
	orphan-accuracy-complete \
	orphan-rates-begin \
	orphan-rates-complete \
	orphan-req-rate-complete \
	orphan-scan-complete \
	parent-read-begin \
	parent-read-complete \
	disp_cc_mdss_pclk0_clk_src
do
	grep -Fxq "$marker" "$stage/image.strings"
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

mkdir -p "$stage/staging" "$stage/boot-args"
gzip -dc "$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz" |
	(cd "$stage/staging" && cpio -idm --quiet --no-absolute-filenames)
loader=$stage/staging/usr/local/sbin/rog5-load-mainline-recovery
grep -Fq 'qcom_cc_probe_trace=${ROG5_QCOM_CC_PROBE_TRACE:-0}' "$loader"
grep -Fq 'ccf_register_trace=${ROG5_CCF_REGISTER_TRACE:-0}' "$loader"
grep -Fq 'rcg2_parent_trace=${ROG5_RCG2_PARENT_TRACE:-0}' "$loader"
for command in \
	'command_line="$command_line rog5_qcom_cc_probe_trace=1"' \
	'command_line="$command_line rog5_ccf_register_trace=1"' \
	'command_line="$command_line rog5_rcg2_parent_trace=1"'
do
	[ "$(grep -Fc "$command" "$loader")" -eq 1 ]
done

python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$artifact_dir/boot-5.4.210-network-root-stage.raw.img" \
	--out "$stage/boot-args" --format=mkbootimg --null >"$stage/boot.args"
tr '\000' '\n' <"$stage/boot.args" >"$stage/boot.args.lines"
command_line=$(awk '$0 == "--cmdline" { getline; print; exit }' \
	"$stage/boot.args.lines")
for parameter in \
	rog5_qcom_cc_probe_trace \
	rog5_ccf_register_trace \
	rog5_rcg2_parent_trace
do
	! printf '%s\n' "$command_line" | tr ' ' '\n' |
		grep -q "^$parameter="
done

for archive in \
	"$artifact_dir/rog5-network-root-initramfs.cpio.gz" \
	"$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz"
do
	listing=$(gzip -dc "$archive" | cpio -t 2>/dev/null)
	! printf '%s\n' "$listing" |
		grep -Eq '(^|/)(gpucc-sm8350[.]ko|a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn)$'
done

echo 'PASS exact bounded v14 RCG2 parent-read bundle; two-entry trace remains default-off, external, consumer-free, and rollback-bounded'
