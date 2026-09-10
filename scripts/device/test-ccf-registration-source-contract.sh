#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-}
[ -n "$source_dir" ] || {
	echo 'FAIL set SOURCE_DIR to the pinned Linux 7.1.4 source' >&2
	exit 1
}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
prepare=$repo/scripts/device/prepare-mainline-gpucc-ccf-diagnostic.sh
build=$repo/scripts/device/build-mainline-gpucc-ccf-diagnostic.sh
verifier=$repo/scripts/device/verify-ccf-registration-trace-patch.sh
loader=$repo/scripts/device/load-mainline-network-root.sh
probe=$repo/scripts/device/probe-mainline-coldplug-module.sh
patch=$repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch
clk=$source_dir/drivers/clk/clk.c
regmap=$source_dir/drivers/clk/qcom/clk-regmap.c
common=$source_dir/drivers/clk/qcom/common.c
driver=$source_dir/drivers/clk/qcom/gpucc-sm8350.c
branch=$source_dir/drivers/clk/qcom/clk-branch.c
binding=$source_dir/include/dt-bindings/clock/qcom,gpucc-sm8350.h
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_common=d4bb00313e92514f89bc0a9e7a7dffcb4884834f
expected_ccf=6eef0ab56609f5a5ee6d2de9807178daf1065fa7
expected_tree=743a976fd13c1a5c30d93c7dac9b9b4d1cbc3b11

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_base" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
for file in "$prepare" "$build" "$verifier" "$loader" "$probe"; do
	[ -x "$file" ]
done
for file in "$patch" "$clk" "$regmap" "$common" "$driver" "$branch" \
	"$binding"
do
	[ -r "$file" ]
done

grep -Fq "expected_common=$expected_common" "$prepare"
grep -Fq "expected_ccf=$expected_ccf" "$prepare"
grep -Fq "expected_tree=$expected_tree" "$prepare"
grep -Fq "expected_ccf=$expected_ccf" "$build"
grep -Fq "expected_tree=$expected_tree" "$build"
grep -Fq 'repro_source_dir=/root/src/linux-7.1.4' "$build"
grep -Fq 'repro_output_dir=/root/build/rog5-linux-7.1.4-network-root' "$build"
grep -Fq 'for reproducible vDSO build IDs' "$build"
grep -Fq 'ccf_trace_patch_sha256=' "$build"

[ "$(awk '$1 == "#define" && $2 == "GPU_CC_AHB_CLK" { print $3 }' \
	"$binding")" = 0 ]
[ "$(awk '$1 == "#define" && $2 == "GPU_CC_HUB_AHB_DIV_CLK_SRC" {
	print $3
}' "$binding")" = 17 ]
grep -Fq '[GPU_CC_AHB_CLK] = &gpu_cc_ahb_clk.clkr,' "$driver"
grep -Fq \
	'[GPU_CC_HUB_AHB_DIV_CLK_SRC] = &gpu_cc_hub_ahb_div_clk_src.clkr,' \
	"$driver"

ahb=$(awk '
	/^static struct clk_branch gpu_cc_ahb_clk =/ { found = 1 }
	found { print }
	found && /^};/ { exit }
' "$driver")
[ -n "$ahb" ]
printf '%s\n' "$ahb" | grep -Fq '.halt_reg = 0x1078,'
printf '%s\n' "$ahb" | grep -Fq '.enable_reg = 0x1078,'
printf '%s\n' "$ahb" | grep -Fq '&gpu_cc_hub_ahb_div_clk_src.clkr.hw,'
printf '%s\n' "$ahb" | grep -Fq '.num_parents = 1,'
printf '%s\n' "$ahb" | grep -Fq '.flags = CLK_SET_RATE_PARENT,'
printf '%s\n' "$ahb" | grep -Fq '.ops = &clk_branch2_ops,'
! printf '%s\n' "$ahb" | grep -Fq 'CLK_IS_CRITICAL'

branch_ops=$(awk '
	/^const struct clk_ops clk_branch2_ops =/ { found = 1 }
	found { print }
	found && /^};/ { exit }
' "$branch")
[ -n "$branch_ops" ]
for callback in init get_parent get_phase recalc_rate recalc_accuracy; do
	! printf '%s\n' "$branch_ops" | grep -Eq "^[[:space:]]*[.]$callback[[:space:]]*="
done

descriptor=$(awk '
	/^static const struct qcom_cc_desc gpu_cc_sm8350_desc/ { found = 1 }
	found { print }
	found && /^};/ { exit }
' "$driver")
[ -n "$descriptor" ]
! printf '%s\n' "$descriptor" |
	grep -Eq '^[[:space:]]*[.](use_rpm|driver_data)[[:space:]]*='

assert_order() {
	block=$1
	shift
	previous=0
	for operation in "$@"; do
		line=$(printf '%s\n' "$block" | grep -nF "$operation" |
			sed -n '1s/:.*//p')
		[ -n "$line" ] && [ "$line" -gt "$previous" ]
		previous=$line
	done
}

assert_same_operation_count() {
	relative_path=$1
	operation=$2
	base_count=$(grep -Fc "$operation" "$source_dir/$relative_path")
	patched_count=$(grep -Fc "$operation" "$PATCHED_SOURCE/$relative_path")
	[ "$base_count" -eq "$patched_count" ]
}

regmap_register=$(awk '
	/^int devm_clk_register_regmap\(/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$regmap")
assert_order "$regmap_register" \
	'dev_get_regmap(dev, NULL)' \
	'rclk->regmap = dev_get_regmap(dev, NULL)' \
	'rclk->regmap = dev_get_regmap(dev->parent, NULL)' \
	'devm_clk_hw_register(dev, &rclk->hw)'

managed_register=$(awk '
	/^int devm_clk_hw_register\(/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$clk")
assert_order "$managed_register" \
	'devres_alloc(devm_clk_hw_unregister_cb' \
	'clk_hw_register(dev, hw)' \
	'devres_add(dev, hwp)' \
	'devres_free(hwp)'

core_register=$(awk '
	/^__clk_register\(/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$clk")
assert_order "$core_register" \
	'hw->init = NULL' \
	'core = kzalloc_obj(*core)' \
	'core->name = kstrdup_const' \
	'clk_pm_runtime_init(core)' \
	'clk_core_populate_parent_map(core, init)' \
	'hw->clk = alloc_clk(core, NULL, NULL)' \
	'clk_core_link_consumer(core, hw->clk)' \
	'ret = __clk_core_init(core)'
[ "$(printf '%s\n' "$core_register" |
	grep -Fc 'ret = __clk_core_init(core);')" -eq 1 ]

core_init=$(awk '
	/^static int __clk_core_init\(/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$clk")
assert_order "$core_init" \
	'clk_prepare_lock()' \
	'core->hw->core = core' \
	'ret = clk_pm_runtime_get(core)' \
	'clk_core_lookup(core->name)' \
	'core->ops->init(core->hw)' \
	'parent = core->parent = __clk_init_parent(core)' \
	'hash_add(clk_hashtable' \
	'clk_core_get_phase(core)' \
	'clk_core_update_duty_cycle_nolock(core)' \
	'core->ops->recalc_rate(core->hw' \
	'if (core->flags & CLK_IS_CRITICAL)' \
	'clk_core_reparent_orphans_nolock()' \
	'clk_pm_runtime_put(core)' \
	'clk_prepare_unlock()' \
	'clk_debug_register(core)'

grep -Fq 'qcom_cc_probe_trace=${ROG5_QCOM_CC_PROBE_TRACE:-0}' "$loader"
grep -Fq 'ccf_register_trace=${ROG5_CCF_REGISTER_TRACE:-0}' "$loader"
grep -Fq \
	'command_line="$command_line rog5_ccf_register_trace=1"' "$loader"
grep -Fq \
	'ccf_trace=/sys/module/kernel/parameters/rog5_ccf_register_trace' "$probe"

"$verifier" "$patch" >/dev/null

if [ -n "${PATCHED_SOURCE:-}" ]; then
	[ -d "$PATCHED_SOURCE/.git" ]
	[ "$(git -C "$PATCHED_SOURCE" rev-parse HEAD^^^)" = "$expected_base" ]
	[ "$(git -C "$PATCHED_SOURCE" rev-parse HEAD^)" = "$expected_common" ]
	[ "$(git -C "$PATCHED_SOURCE" rev-parse HEAD)" = "$expected_ccf" ]
	[ "$(git -C "$PATCHED_SOURCE" rev-parse HEAD^{tree})" = \
		"$expected_tree" ]
	[ -z "$(git -C "$PATCHED_SOURCE" status --porcelain)" ]
	grep -Fq \
		'core_param(rog5_ccf_register_trace, rog5_ccf_register_trace, bool, 0400);' \
		"$PATCHED_SOURCE/drivers/clk/clk.c"
	patched_register=$(awk '
		/^__clk_register\(/ { found = 1 }
		found { print }
		found && /^}/ { exit }
	' "$PATCHED_SOURCE/drivers/clk/clk.c")
	[ "$(printf '%s\n' "$patched_register" |
		grep -Fc 'ret = __clk_core_init(core);')" -eq 1 ]
	for operation in \
		'__clk_core_init(core)' \
		'clk_prepare_lock()' \
		'clk_pm_runtime_get(core)' \
		'clk_core_reparent_orphans_nolock()' \
		'clk_debug_register(core)' \
		'devres_alloc(devm_clk_hw_unregister_cb' \
		'clk_hw_register(dev, hw)' \
		'devres_add(dev, hwp)'
	do
		assert_same_operation_count drivers/clk/clk.c "$operation"
	done
	for operation in \
		'dev_get_regmap(' \
		'devm_clk_hw_register(dev, &rclk->hw)'
	do
		assert_same_operation_count drivers/clk/qcom/clk-regmap.c "$operation"
	done
fi

echo 'PASS index-0 orphan topology, exact single-call CCF order, deterministic source, and dual-trace transport contract'
