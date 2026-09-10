#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-gpucc-ccf-diagnostic-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing SHA-256 manifest}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
module=$artifact_dir/gpucc-sm8350.ko
image=$artifact_dir/Image-7.1.4-network-root
modules=$artifact_dir/modules-7.1.4-network-root.tar.gz
meta=$artifact_dir/build-meta-7.1.4-network-root.txt
expected_image=d6bb0a9a7c4d4496aac8593df1727c916f130a10741b2691eebbf28555527021
expected_modules=b1c2bd02d67773e2b213c8aec2e30378580f8bcc638ff378650182a335f6f5d0
expected_module=3c663bed417bb3bd7438b422ebf3531eca48e53afebc66a4574c7d87f7a8f421

"$repo/scripts/device/verify-network-root-bundle.sh" \
	"$artifact_dir" "$mkbootimg_dir" "$avbtool" "$expected_sums" okay
"$repo/scripts/device/verify-qcom-cc-registration-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0006-qcom-cc-add-attended-registration-trace.patch" \
	"$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch" \
	>/dev/null
"$repo/scripts/device/verify-ccf-registration-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch" \
	>/dev/null

check_exact_hash() {
	label=$1
	file=$2
	expected=$3
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] || {
		echo "FAIL $label is not the reviewed CCF diagnostic build" >&2
		exit 1
	}
}
check_exact_hash wrapper-Image \
	"$artifact_dir/Image-5.4.210-network-root-stage" \
	1ea673e292447e4f03dceb43f8b1d19dd06c6382b279a950fa990f7a4c5fb7b0
check_exact_hash wrapper-config \
	"$artifact_dir/config-5.4.210-network-root-stage" \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
check_exact_hash embedded-stage \
	"$artifact_dir/embedded-kexec-stage-initramfs.cpio.gz" \
	1d84c11edf9867d59dd473c0a958514e33b1f071a36cdda2f6ac39c2d5d48a7d
check_exact_hash wrapper-metadata \
	"$artifact_dir/build-meta-5.4.210-network-root-stage.txt" \
	cd0c821420f4923ecd0c5a8184d96780f0c05493f60cd80caaed513b8a181cd9
check_exact_hash Image "$image" "$expected_image"
check_exact_hash Image.gz \
	"$artifact_dir/Image.gz-7.1.4-network-root" \
	f4138e28b224423eaf0de334344fead6204ac9a0f141dbd8d8f0652d493c73ac
check_exact_hash mainline-config \
	"$artifact_dir/config-7.1.4-network-root" \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f
check_exact_hash modules "$modules" "$expected_modules"
check_exact_hash mainline-metadata "$meta" \
	f0bce6e0a4611c7a7de328fc687bc7453dcf669da8782ef50bfdde05809ded6c
check_exact_hash GPUCC-DTB \
	"$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb" \
	e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5
check_exact_hash target-initramfs \
	"$artifact_dir/rog5-network-root-initramfs.cpio.gz" \
	4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
check_exact_hash staging-initramfs \
	"$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz" \
	1d84c11edf9867d59dd473c0a958514e33b1f071a36cdda2f6ac39c2d5d48a7d
check_exact_hash raw-boot \
	"$artifact_dir/boot-5.4.210-network-root-stage.raw.img" \
	3974476d879e1fa41296e64390324f959043fcd771bea5e166be93bff0796b95
check_exact_hash AVB-boot \
	"$artifact_dir/boot-5.4.210-network-root-stage.avb.img" \
	ed80c46e4d23caa258d3ef07ffddad254d9cba461165751e55476864044fdc42
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
	'ccf_patched_commit=6eef0ab56609f5a5ee6d2de9807178daf1065fa7' \
	"$meta"
grep -qx \
	'patched_tree=743a976fd13c1a5c30d93c7dac9b9b4d1cbc3b11' "$meta"
grep -qx \
	'gpucc_trace_patch_sha256=50ec8d394583951ab00e65c38686775031d0abadc6a3faf1730edda13eb7be94' \
	"$meta"
grep -qx \
	'common_trace_patch_sha256=a6084f1b9f7d72fc984827a9f43559ef6a9a5cb3222a273775249924567f2df5' \
	"$meta"
grep -qx \
	'ccf_trace_patch_sha256=5f0be38bf3773f0cc541d7a52f930bc05dc979ee1a086198f3148aa14552dbc9' \
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

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
strings "$image" >"$stage/image.strings"
grep -Fxq 'rog5_qcom_cc_probe_trace' "$stage/image.strings"
grep -Fxq \
	'ROG5 QCOM CC diagnostic: phase=%s index=%d ret=%d' \
	"$stage/image.strings"
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
	grep -Fxq "$phase" "$stage/image.strings"
done

grep -Fxq 'rog5_ccf_register_trace' "$stage/image.strings"
grep -Fxq \
	'ROG5 CCF diagnostic: phase=%s clock=%s ret=%d' \
	"$stage/image.strings"
for phase in \
	managed-entry \
	devres-allocation-begin \
	devres-allocation-complete \
	hw-register-begin \
	hw-register-complete \
	devres-commit-begin \
	devres-commit-complete \
	devres-release-begin \
	devres-release-complete \
	managed-exit \
	register-entry \
	init-detach-complete \
	core-allocation-begin \
	core-allocation-complete \
	name-copy-begin \
	name-copy-complete \
	runtime-init-begin \
	runtime-init-complete \
	parent-map-begin \
	parent-map-complete \
	consumer-allocation-begin \
	consumer-allocation-complete \
	consumer-link-begin \
	consumer-link-complete \
	core-init-begin \
	core-init-complete \
	register-exit \
	core-init-entry \
	prepare-lock-begin \
	prepare-lock-complete \
	hw-core-link-complete \
	runtime-get-begin \
	runtime-get-complete \
	duplicate-lookup-begin \
	duplicate-lookup-complete \
	ops-validation-begin \
	ops-validation-complete \
	driver-init-begin \
	driver-init-complete \
	parent-init-begin \
	parent-init-complete \
	topology-insert-begin \
	topology-insert-complete \
	accuracy-begin \
	accuracy-complete \
	phase-begin \
	phase-complete \
	duty-begin \
	duty-complete \
	rate-begin \
	rate-complete \
	critical-begin \
	critical-complete \
	orphan-reparent-begin \
	orphan-reparent-complete \
	runtime-put-begin \
	runtime-put-complete \
	prepare-unlock-begin \
	prepare-unlock-complete \
	debug-register-begin \
	debug-register-complete \
	core-init-exit \
	regmap-device-lookup-begin \
	regmap-device-lookup-complete \
	regmap-device-assign-begin \
	regmap-device-assign-complete \
	regmap-parent-assign-begin \
	regmap-parent-assign-complete \
	regmap-lookup-complete \
	ccf-managed-register-begin \
	ccf-managed-register-complete
do
	grep -Fxq "$phase" "$stage/image.strings"
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

mkdir -p "$stage/staging" "$stage/boot-args"
gzip -dc "$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz" |
	(cd "$stage/staging" && cpio -idm --quiet --no-absolute-filenames)
loader=$stage/staging/usr/local/sbin/rog5-load-mainline-recovery
grep -Fq 'qcom_cc_probe_trace=${ROG5_QCOM_CC_PROBE_TRACE:-0}' "$loader"
grep -Fq 'ccf_register_trace=${ROG5_CCF_REGISTER_TRACE:-0}' "$loader"
[ "$(grep -Fc \
	'command_line="$command_line rog5_qcom_cc_probe_trace=1"' "$loader")" -eq 1 ]
[ "$(grep -Fc \
	'command_line="$command_line rog5_ccf_register_trace=1"' "$loader")" -eq 1 ]

python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$artifact_dir/boot-5.4.210-network-root-stage.raw.img" \
	--out "$stage/boot-args" --format=mkbootimg --null >"$stage/boot.args"
tr '\000' '\n' <"$stage/boot.args" >"$stage/boot.args.lines"
command_line=$(awk '$0 == "--cmdline" { getline; print; exit }' \
	"$stage/boot.args.lines")
for parameter in rog5_qcom_cc_probe_trace rog5_ccf_register_trace; do
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

echo 'PASS exact CCF phase diagnostic bundle; both traces stay opt-in, matching BTF module stays external, and all consumers stay disabled'
