#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0027-phy-qcom-qmp-ufs-stop-sm8350-after-first-clock-with-runtime-pm.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-first-clock-name-stage-20260813-r1/linux-source}
expected_source=d327b6f0251129e0c80f32fe9309f8278e800db7

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ -f $patch && ! -L $patch ]] || fail 'missing QMP-UFS first-clock runtime-PM patch'
[[ $(git apply --numstat "$patch") == $'5\t5\tdrivers/phy/qualcomm/phy-qcom-qmp-ufs.c' ]] ||
	fail 'QMP-UFS patch changes anything except the exact PHY boundary'
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: first clock with runtime-PM stage complete' "$patch") == 1 ]]
for forbidden in \
	'+\tof_clk_add_hw_provider' '+\tdevm_add_action_or_reset' \
	'+\tdevm_phy_create' '+\tphy_set_drvdata' \
	'+\tdevm_of_phy_provider_register' '+\tclk_prepare_enable' \
	'+\tregulator_enable' '+\treadl' '+\twritel'; do
	! grep -Fq "$forbidden" "$patch" ||
		fail "QMP-UFS patch adds a forbidden later operation: $forbidden"
done

[[ -d $source_root && ! -L $source_root && ! -L $source_root/.git ]] ||
	fail 'retained Generation 41 source is unavailable'
[[ $(git -C "$source_root" rev-parse --is-inside-work-tree) == true ]] ||
	fail 'retained Generation 41 source is not a Git worktree'
[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_source" ]] ||
	fail 'retained Generation 41 source commit changed'
[[ -z $(git -C "$source_root" status --porcelain) ]] ||
	fail 'retained Generation 41 source is dirty'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
patched=$stage/linux-source
git -c advice.detachedHead=false clone -q --shared "$source_root" "$patched"
git -C "$patched" apply "$patch"
git -C "$patched" diff --check

function=$stage/register-clocks
awk '
	/^static int qmp_ufs_register_clocks[(]/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$patched/drivers/phy/qualcomm/phy-qcom-qmp-ufs.c" >"$function"
[[ -s $function ]]

assert_order() {
	local previous=0 line operation
	for operation in "$@"; do
		line=$(grep -nF "$operation" "$function" | sed -n '1s/:.*//p')
		[[ -n $line && $line -gt $previous ]] ||
			fail "QMP-UFS operation order changed: $operation"
		previous=$line
	done
}

assert_order \
	'snprintf(name, sizeof(name), "%s::rx_symbol_0", dev_name(qmp->dev));' \
	'hw = devm_clk_hw_register_fixed_rate(qmp->dev, name, NULL, 0, 0);' \
	'if (IS_ERR(hw))' \
	'clk_data->hws[0] = hw;' \
	'if (of_device_is_compatible(qmp->dev->of_node,' \
	'return 0;' \
	'snprintf(name, sizeof(name), "%s::rx_symbol_1", dev_name(qmp->dev));'
[[ $(grep -Fc 'devm_clk_hw_register_fixed_rate(qmp->dev, name, NULL, 0, 0);' "$function") == 3 ]]
[[ $(grep -Fc 'of_clk_add_hw_provider(np, of_clk_hw_onecell_get, clk_data);' "$function") == 1 ]]

echo 'PASS QMP-UFS runtime-PM discriminator crosses exactly the first fixed-rate clock before returning'
