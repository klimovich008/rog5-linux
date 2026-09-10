#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-}
[ -n "$source_dir" ] || {
	echo 'FAIL set SOURCE_DIR to the pinned Linux 7.1.4 source' >&2
	exit 1
}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
build=$repo/scripts/device/build-mainline-gpucc-common-diagnostic.sh
prepare=$repo/scripts/device/prepare-mainline-gpucc-common-diagnostic.sh
verifier=$repo/scripts/device/verify-qcom-cc-registration-trace-patch.sh
loader=$repo/scripts/device/load-mainline-network-root.sh
probe=$repo/scripts/device/probe-mainline-coldplug-module.sh
gpucc_patch=$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch
common_patch=$repo/patches/linux-7.1.4/0006-qcom-cc-add-attended-registration-trace.patch
common=$source_dir/drivers/clk/qcom/common.c
driver=$source_dir/drivers/clk/qcom/gpucc-sm8350.c
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_gpucc=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea
expected_common=d4bb00313e92514f89bc0a9e7a7dffcb4884834f
expected_tree=3b185820802b882d05830b9c6aee35bff984e07b

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_base" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
for file in "$build" "$prepare" "$verifier" "$loader" "$probe"; do
	[ -x "$file" ]
done
for file in "$common" "$driver" "$gpucc_patch" "$common_patch"; do
	[ -r "$file" ]
done

grep -Fq 'repro_source_dir=/root/src/linux-7.1.4' "$build"
grep -Fq \
	'repro_output_dir=/root/build/rog5-linux-7.1.4-network-root' "$build"
grep -Fq "expected_base=$expected_base" "$build"
grep -Fq "expected_gpucc=$expected_gpucc" "$build"
grep -Fq "expected_common=$expected_common" "$build"
grep -Fq "expected_tree=$expected_tree" "$build"
grep -Fq 'expected_release=7.1.4-g7a5cef0db479' "$build"
grep -Fq 'for reproducible vDSO build IDs' "$build"
[ "$(grep -Fc 'KERNELRELEASE="$expected_release"' "$build")" -eq 4 ]
grep -Fq 'gpucc_trace_patch_sha256=' "$build"
grep -Fq 'common_trace_patch_sha256=' "$build"

gpucc_apply=$(grep -nF 'git -C "$target_source" apply "$gpucc_patch"' \
	"$prepare" | cut -d : -f 1)
common_apply=$(grep -nF 'git -C "$target_source" apply "$common_patch"' \
	"$prepare" | cut -d : -f 1)
[ -n "$gpucc_apply" ] && [ -n "$common_apply" ]
[ "$gpucc_apply" -lt "$common_apply" ]
grep -Fq "expected_gpucc=$expected_gpucc" "$prepare"
grep -Fq "expected_common=$expected_common" "$prepare"
grep -Fq "expected_common_tree=$expected_tree" "$prepare"

really_probe=$(awk '
	/^int qcom_cc_really_probe\(/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$common")
[ -n "$really_probe" ]
previous=0
for operation in \
	'devm_kzalloc(dev, sizeof(*cc), GFP_KERNEL)' \
	'devm_pm_domain_attach_list(dev, NULL, &cc->pd_list)' \
	'if (desc->use_rpm)' \
	'if (desc->driver_data)' \
	'devm_reset_controller_register(dev, &reset->rcdev)' \
	'gdsc_register(scd, &reset->rcdev, regmap)' \
	'devm_add_action_or_reset(dev, qcom_cc_gdsc_unregister' \
	'qcom_cc_register_rcg_dfs(regmap' \
	'qcom_cc_drop_protected(dev, cc)' \
	'devm_clk_hw_register(dev, clk_hws[i])' \
	'devm_clk_register_regmap(dev, rclks[i])' \
	'devm_of_clk_add_hw_provider(dev, qcom_cc_clk_hw_get, cc)' \
	'qcom_cc_icc_register(dev, desc)'
do
	line=$(printf '%s\n' "$really_probe" |
		grep -nF "$operation" | sed -n '1s/:.*//p')
	[ -n "$line" ]
	[ "$line" -gt "$previous" ]
	previous=$line
done

clocks=$(awk '
	/^static struct clk_regmap \*gpu_cc_sm8350_clocks\[\]/ { found = 1 }
	found { print }
	found && /^};/ { exit }
' "$driver")
resets=$(awk '
	/^static const struct qcom_reset_map gpu_cc_sm8350_resets\[\]/ {
		found = 1
	}
	found { print }
	found && /^};/ { exit }
' "$driver")
gdscs=$(awk '
	/^static struct gdsc \*gpu_cc_sm8350_gdscs\[\]/ { found = 1 }
	found { print }
	found && /^};/ { exit }
' "$driver")
descriptor=$(awk '
	/^static const struct qcom_cc_desc gpu_cc_sm8350_desc/ { found = 1 }
	found { print }
	found && /^};/ { exit }
' "$driver")
[ "$(printf '%s\n' "$clocks" |
	grep -Ec '^[[:space:]]*\[GPU_CC_[A-Z0-9_]+\][[:space:]]*=')" -eq 27 ]
[ "$(printf '%s\n' "$resets" |
	grep -Ec '^[[:space:]]*\[GPUCC_GPU_CC_[A-Z0-9_]+\][[:space:]]*=')" -eq 8 ]
[ "$(printf '%s\n' "$gdscs" |
	grep -Ec '^[[:space:]]*\[GPU_[A-Z0-9_]+_GDSC\][[:space:]]*=')" -eq 2 ]
for field in config clks num_clks resets num_resets gdscs num_gdscs; do
	printf '%s\n' "$descriptor" | grep -Eq "^[[:space:]]*[.]$field[[:space:]]*="
done
! printf '%s\n' "$descriptor" |
	grep -Eq '^[[:space:]]*[.](driver_data|use_rpm|clk_hws|num_clk_hws|icc_clocks|num_icc_clocks)[[:space:]]*='

grep -Fq 'qcom_cc_probe_trace=${ROG5_QCOM_CC_PROBE_TRACE:-0}' "$loader"
[ "$(grep -Fc \
	'command_line="$command_line rog5_qcom_cc_probe_trace=1"' "$loader")" -eq 1 ]
grep -Fq 'ramoops.*=*) command_line="$command_line $argument"' "$loader"
grep -Fq \
	'core_trace=/sys/module/kernel/parameters/rog5_qcom_cc_probe_trace' \
	"$probe"
grep -Fq \
	'awk '\''$0 == "rog5_qcom_cc_probe_trace=1" { count++ }' "$probe"

"$verifier" "$common_patch" "$gpucc_patch" "$source_dir" >/dev/null

if [ -n "${PATCHED_SOURCE:-}" ]; then
	[ -d "$PATCHED_SOURCE/.git" ]
	[ "$(git -C "$PATCHED_SOURCE" rev-parse HEAD^^)" = "$expected_base" ]
	[ "$(git -C "$PATCHED_SOURCE" rev-parse HEAD^)" = "$expected_gpucc" ]
	[ "$(git -C "$PATCHED_SOURCE" rev-parse HEAD)" = "$expected_common" ]
	[ "$(git -C "$PATCHED_SOURCE" rev-parse HEAD^{tree})" = \
		"$expected_tree" ]
	[ -z "$(git -C "$PATCHED_SOURCE" status --porcelain)" ]
	grep -Fq \
		'core_param(rog5_qcom_cc_probe_trace, rog5_qcom_cc_probe_trace, bool, 0400);' \
		"$PATCHED_SOURCE/drivers/clk/qcom/common.c"
fi

echo 'PASS common-clock phase order, exact GPUCC topology, deterministic source, and trace transport contract'
