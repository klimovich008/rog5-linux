#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0026-clk-resume-runtime-pm-providers-around-orphan-walks.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-first-clock-name-stage-20260813-r1/linux-source}
expected_source=d327b6f0251129e0c80f32fe9309f8278e800db7
explicit_source=${ROG5_LINUX_SOURCE:+1}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ -f $patch && ! -L $patch ]] || fail 'missing current-source CCF runtime-PM patch'
[[ $(git apply --numstat "$patch") == $'27\t6\tdrivers/clk/clk.c' ]] ||
	fail 'CCF patch changes anything except the exact clk.c delta'
[[ $(grep -Ec '^[+][[:space:]]*ret = clk_pm_runtime_get_all[(][)];$' "$patch") == 3 ]]
[[ $(grep -Ec '^[+][[:space:]]*clk_pm_runtime_put_all[(][)];$' "$patch") == 3 ]]
[[ $(grep -Ec '^[+][[:space:]]*of_clk_del_provider[(]np[)];$' "$patch") == 2 ]]
[[ $(grep -Ec '^-[[:space:]]*ret = clk_pm_runtime_get[(]core[)];$' "$patch") == 1 ]]
[[ $(grep -Ec '^-[[:space:]]*clk_pm_runtime_put[(]core[)];$' "$patch") == 1 ]]
[[ $(grep -Ec '^[+-][[:space:]]*clk_core_reparent_orphans(_nolock)?[(]' "$patch") == 0 ]]

added=$(sed -n 's/^+//p' "$patch")
if grep -Eiq '(^|[^[:alnum:]_])pm_runtime_|regmap_(read|write|update_bits)|read[ql][(]|write[ql][(]|clk_(prepare_)?enable[(]|regulator_|reset_control_|qcom|sm8350|disp_cc|gpu_cc|fastboot|/dev/|mount[[:space:]]' <<<"$added"; then
	fail 'CCF patch adds direct PM, hardware, device-specific, or storage control'
fi

if [[ ! -d $source_root ]]; then
	[[ -z $explicit_source ]] || fail 'explicit retained source is unavailable'
	echo 'SKIP retained Generation 41 source integration; committed patch contract passed' >&2
	exit 0
fi

[[ -d $source_root && ! -L $source_root && ! -L $source_root/.git ]] ||
	fail 'retained Generation 41 source is unsafe'
[[ $(git -C "$source_root" rev-parse --is-inside-work-tree) == true ]] ||
	fail 'retained Generation 41 source is not a Git worktree'
[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_source" ]] ||
	fail 'retained Generation 41 source commit changed'
[[ -z $(git -C "$source_root" status --porcelain) ]] ||
	fail 'retained Generation 41 source is dirty'

base_clk=$source_root/drivers/clk/clk.c
base_core=$(awk '
	/^static int __clk_core_init[(]struct clk_core [*]core[)]/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$base_clk")
[[ $(grep -Fc 'ret = clk_pm_runtime_get(core);' <<<"$base_core") == 1 ]] ||
	fail 'fail-first base no longer has the unsafe per-core get'
[[ $(grep -Fc 'clk_pm_runtime_put(core);' <<<"$base_core") == 1 ]] ||
	fail 'fail-first base per-core put inventory changed'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
patched=$stage/linux-source
git -c advice.detachedHead=false clone -q --shared "$source_root" "$patched"
git -C "$patched" apply "$patch"
git -C "$patched" diff --check

extract_function() {
	local signature=$1 file=$2 output=$3
	awk -v signature="$signature" '
		index($0, signature) == 1 { found = 1 }
		found { print }
		found && /^}/ { exit }
	' "$file" >"$output"
	[[ -s $output ]]
}

assert_order() {
	local file=$1 previous=0 line operation
	shift
	for operation in "$@"; do
		line=$(grep -nF "$operation" "$file" | sed -n '1s/:.*//p')
		[[ -n $line && $line -gt $previous ]] ||
			fail "CCF operation order changed: $operation"
		previous=$line
	done
}

base_orphans=$stage/base-orphans
patched_orphans=$stage/patched-orphans
core=$stage/core
provider=$stage/provider
hw_provider=$stage/hw-provider
extract_function 'static void clk_core_reparent_orphans_nolock(void)' \
	"$base_clk" "$base_orphans"
extract_function 'static void clk_core_reparent_orphans_nolock(void)' \
	"$patched/drivers/clk/clk.c" "$patched_orphans"
cmp "$base_orphans" "$patched_orphans"
extract_function 'static int __clk_core_init(struct clk_core *core)' \
	"$patched/drivers/clk/clk.c" "$core"
extract_function 'int of_clk_add_provider(struct device_node *np,' \
	"$patched/drivers/clk/clk.c" "$provider"
extract_function 'int of_clk_add_hw_provider(struct device_node *np,' \
	"$patched/drivers/clk/clk.c" "$hw_provider"

[[ $(grep -Fc 'ret = clk_pm_runtime_get_all();' "$core") == 1 ]]
[[ $(grep -Fc 'clk_pm_runtime_put_all();' "$core") == 1 ]]
[[ $(grep -Fc 'clk_pm_runtime_get(core)' "$core") == 0 ]]
[[ $(grep -Fc 'clk_pm_runtime_put(core)' "$core") == 0 ]]
assert_order "$core" \
	'ret = clk_pm_runtime_get_all();' \
	'clk_prepare_lock();' \
	'clk_core_reparent_orphans_nolock();' \
	'clk_prepare_unlock();' \
	'clk_pm_runtime_put_all();' \
	'clk_debug_register(core);'

for function in "$provider" "$hw_provider"; do
	[[ $(grep -Fc 'ret = clk_pm_runtime_get_all();' "$function") == 1 ]]
	[[ $(grep -Fc 'clk_pm_runtime_put_all();' "$function") == 1 ]]
	[[ $(grep -Fc 'of_clk_del_provider(np);' "$function") == 2 ]]
	assert_order "$function" \
		'ret = clk_pm_runtime_get_all();' \
		'if (ret) {' \
		'of_clk_del_provider(np);' \
		'return ret;' \
		'clk_core_reparent_orphans();' \
		'clk_pm_runtime_put_all();' \
		'ret = of_clk_set_defaults(np, true);'
done

echo 'PASS current CCF orphan walks use balanced all-provider runtime PM outside prepare_lock'
