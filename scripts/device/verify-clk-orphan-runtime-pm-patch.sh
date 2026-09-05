#!/bin/sh
set -eu

patch=${1:?usage: verify-clk-orphan-runtime-pm-patch.sh PATCH PINNED_V14_SOURCE}
source_dir=${2:?missing pinned v14 source}
expected_sha=a309fe55dc6221f4475c22beb43018dde0f2eb107fa60e84f8e43f28e17a4a25
expected_parent=6e40861cc51c067f9989c4513003e8fbd046c22f
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
patched=$stage/linux-7.1.4

[ -r "$patch" ]
patch=$(CDPATH= cd -- "$(dirname "$patch")" && pwd)/$(basename "$patch")
if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	[ "$(sha256sum "$patch" | cut -d ' ' -f 1)" = "$expected_sha" ]
fi
[ "$(git apply --numstat "$patch" | wc -l)" -eq 1 ]
git apply --numstat "$patch" |
	grep -Eq '^[0-9]+[[:space:]]+[0-9]+[[:space:]]+drivers/clk/clk[.]c$'

[ "$(grep -Ec '^[+][[:space:]]*ret = clk_pm_runtime_get_all[(][)];$' \
	"$patch")" -eq 3 ]
[ "$(grep -Ec '^[+][[:space:]]*clk_pm_runtime_put_all[(][)];$' \
	"$patch")" -eq 3 ]
[ "$(grep -Ec '^[+][[:space:]]*of_clk_del_provider[(]np[)];$' \
	"$patch")" -eq 2 ]
[ "$(grep -Ec '^-[[:space:]]*ret = clk_pm_runtime_get[(]core[)];$' \
	"$patch")" -eq 1 ]
[ "$(grep -Ec '^-[[:space:]]*clk_pm_runtime_put[(]core[)];$' \
	"$patch")" -eq 1 ]
[ "$(grep -Ec '^[+-][[:space:]]*clk_core_reparent_orphans(_nolock)?' \
	"$patch")" -eq 0 ]

for contract in \
	'"runtime-get-all-begin"' \
	'"runtime-get-all-complete"' \
	'"runtime-put-all-begin"' \
	'"runtime-put-all-complete"'
do
	[ "$(grep -Fc "$contract" "$patch")" -eq 1 ]
done

added=$(sed -n 's/^+//p' "$patch")
if printf '%s\n' "$added" |
	grep -Eiq '(^|[^[:alnum:]_])pm_runtime_|regmap_(read|write|update_bits)|read[ql][(]|write[ql][(]|clk_(prepare_)?enable[(]|regulator_|reset_control_|gdsc_|of_device_is_compatible|qcom|sm8350|disp_cc|gpu_cc|fastboot|/dev/|mount[[:space:]]|status[[:space:]]*=[[:space:]]*"okay"'
then
	echo 'FAIL CCF runtime-PM patch adds direct PM, device-specific, hardware, or persistent control' >&2
	exit 1
fi

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_parent" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
git -C "$source_dir" apply --check "$patch"

mkdir -p "$patched/drivers/clk/qcom"
cp "$source_dir/drivers/clk/clk.c" "$patched/drivers/clk/clk.c"
cp "$source_dir/drivers/clk/qcom/clk-rcg2.c" \
	"$patched/drivers/clk/qcom/clk-rcg2.c"
git -C "$patched" apply "$patch"

checkpatch=$source_dir/scripts/checkpatch.pl
if [ -x "$checkpatch" ]; then
	"$checkpatch" --no-tree --strict --terse "$patch" >/dev/null
fi

extract_function() {
	start=$1
	output=$2
	awk -v start="$start" '
		index($0, start) == 1 { found = 1 }
		found { print }
		found && /^}/ { exit }
	' "$patched/drivers/clk/clk.c" >"$output"
	[ -s "$output" ]
}

assert_order() {
	file=$1
	shift
	previous=0
	for operation in "$@"; do
		line=$(grep -nF "$operation" "$file" | sed -n '1s/:.*//p')
		[ -n "$line" ] && [ "$line" -gt "$previous" ]
		previous=$line
	done
}

core=$stage/core
provider=$stage/provider
hw_provider=$stage/hw-provider
orphans=$stage/orphans
rcg=$stage/rcg
extract_function 'static int __clk_core_init(struct clk_core *core)' "$core"
extract_function 'int of_clk_add_provider(struct device_node *np,' "$provider"
extract_function 'int of_clk_add_hw_provider(struct device_node *np,' \
	"$hw_provider"
extract_function \
	'clk_core_reparent_orphans_nolock(const struct clk_core *rog5_trigger)' \
	"$orphans"
awk '
	/^static u8 clk_rcg2_get_parent[(]struct clk_hw [*]hw[)]/ {
		found = 1
	}
	found { print }
	found && /^}/ { exit }
' "$patched/drivers/clk/qcom/clk-rcg2.c" >"$rcg"
[ -s "$rcg" ]

[ "$(grep -Fc 'ret = clk_pm_runtime_get_all();' "$core")" -eq 1 ]
[ "$(grep -Fc 'clk_pm_runtime_put_all();' "$core")" -eq 1 ]
[ "$(grep -Fc 'clk_pm_runtime_get(core)' "$core")" -eq 0 ]
[ "$(grep -Fc 'clk_pm_runtime_put(core)' "$core")" -eq 0 ]
[ "$(grep -Fc 'clk_core_reparent_orphans_nolock(core);' "$core")" -eq 1 ]
assert_order "$core" \
	'"runtime-get-all-begin"' \
	'ret = clk_pm_runtime_get_all();' \
	'"runtime-get-all-complete"' \
	'if (ret) {' \
	'return ret;' \
	'"prepare-lock-begin"' \
	'clk_prepare_lock();' \
	'clk_core_reparent_orphans_nolock(core);' \
	'"prepare-unlock-begin"' \
	'clk_prepare_unlock();' \
	'"prepare-unlock-complete"' \
	'"runtime-put-all-begin"' \
	'clk_pm_runtime_put_all();' \
	'"runtime-put-all-complete"' \
	'"debug-register-begin"'

for function in "$provider" "$hw_provider"; do
	[ "$(grep -Fc 'ret = clk_pm_runtime_get_all();' "$function")" -eq 1 ]
	[ "$(grep -Fc 'clk_pm_runtime_put_all();' "$function")" -eq 1 ]
	[ "$(grep -Fc 'clk_core_reparent_orphans();' "$function")" -eq 1 ]
	[ "$(grep -Fc 'of_clk_del_provider(np);' "$function")" -eq 2 ]
	assert_order "$function" \
		'ret = clk_pm_runtime_get_all();' \
		'if (ret) {' \
		'of_clk_del_provider(np);' \
		'return ret;' \
		'clk_core_reparent_orphans();' \
		'clk_pm_runtime_put_all();' \
		'ret = of_clk_set_defaults(np, true);'
done

[ "$(grep -Fc '__clk_init_parent(orphan, rog5_trigger,' "$orphans")" -eq 1 ]
[ "$(grep -Fc 'hlist_for_each_entry_safe(orphan, tmp2,' "$orphans")" -eq 1 ]
[ "$(grep -Fc 'clk_core_reparent_orphans_nolock(core);' \
	"$patched/drivers/clk/clk.c")" -eq 1 ]
[ "$(grep -Fc 'clk_core_reparent_orphans();' \
	"$patched/drivers/clk/clk.c")" -eq 2 ]
[ "$(grep -Fc \
	'ret = regmap_read(rcg->clkr.regmap, RCG_CFG_OFFSET(rcg), &cfg);' \
	"$rcg")" -eq 1 ]

echo 'PASS CCF orphan reparenting acquires balanced provider PM references only outside prepare_lock'
