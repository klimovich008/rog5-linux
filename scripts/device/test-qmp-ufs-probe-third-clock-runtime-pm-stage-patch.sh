#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0029-phy-qcom-qmp-ufs-stop-sm8350-after-third-clock-with-runtime-pm.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-first-clock-runtime-pm-stage-20260813-r2/linux-source}
expected_source=c732b0b41d8d5fd2f4ccd76e1f4dbff8ff06c087
expected_parent=ad56d4021003b1f1c65ee92f583fda232013e301
explicit_source=${ROG5_LINUX_SOURCE:+1}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ -f $patch && ! -L $patch ]] || fail 'missing QMP-UFS third-clock runtime-PM patch'
[[ $(git apply --numstat "$patch") == $'5\t5\tdrivers/phy/qualcomm/phy-qcom-qmp-ufs.c' ]] ||
	fail 'QMP-UFS patch changes anything except the exact third-clock boundary'
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: third clock with runtime-PM stage complete' "$patch") == 1 ]]
for forbidden in \
	'+\tret = of_clk_add_hw_provider' '+\tdevm_add_action_or_reset' \
	'+\tdevm_phy_create' '+\tphy_set_drvdata' \
	'+\tdevm_of_phy_provider_register' '+\tclk_prepare_enable' \
	'+\tregulator_enable' '+\treadl' '+\twritel'; do
	! grep -Fq "$forbidden" "$patch" ||
		fail "QMP-UFS patch adds a forbidden later operation: $forbidden"
done

if [[ ! -d $source_root ]]; then
	[[ -z $explicit_source ]] || fail 'explicit retained source is unavailable'
	echo 'SKIP retained Generation 44 source integration; committed patch contract passed' >&2
	exit 0
fi

[[ -d $source_root && ! -L $source_root && ! -L $source_root/.git ]] ||
	fail 'retained Generation 44 source is unsafe'
[[ $(git -C "$source_root" rev-parse --is-inside-work-tree) == true ]] ||
	fail 'retained Generation 44 source is not a Git worktree'
[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_source" ]] ||
	fail 'retained Generation 44 source commit changed'
[[ $(git -C "$source_root" rev-parse HEAD^) == "$expected_parent" ]] ||
	fail 'retained Generation 44 source parent changed'
[[ -z $(git -C "$source_root" status --porcelain) ]] ||
	fail 'retained Generation 44 source is dirty'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
patched=$stage/linux-source
git -c advice.detachedHead=false clone -q --shared "$source_root" "$patched"
git -C "$patched" checkout -q "$expected_parent"
git -C "$patched" apply "$patch"
git -C "$patched" diff --check
git -C "$patched" diff --quiet "$expected_source" -- \
	drivers/phy/qualcomm/phy-qcom-qmp-ufs.c ||
	fail 'committed third-clock patch does not reproduce the retained source'

function=$stage/register-clocks
awk '
	/^static int qmp_ufs_register_clocks[(]/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$patched/drivers/phy/qualcomm/phy-qcom-qmp-ufs.c" >"$function"
[[ -s $function ]]

line_of() {
	local occurrence=$1 operation=$2
	grep -nF "$operation" "$function" | sed -n "${occurrence}s/:.*//p"
}

rx0=$(line_of 1 'snprintf(name, sizeof(name), "%s::rx_symbol_0", dev_name(qmp->dev));')
clock0=$(line_of 1 'hw = devm_clk_hw_register_fixed_rate(qmp->dev, name, NULL, 0, 0);')
hws0=$(line_of 1 'clk_data->hws[0] = hw;')
rx1=$(line_of 1 'snprintf(name, sizeof(name), "%s::rx_symbol_1", dev_name(qmp->dev));')
clock1=$(line_of 2 'hw = devm_clk_hw_register_fixed_rate(qmp->dev, name, NULL, 0, 0);')
hws1=$(line_of 1 'clk_data->hws[1] = hw;')
tx0=$(line_of 1 'snprintf(name, sizeof(name), "%s::tx_symbol_0", dev_name(qmp->dev));')
clock2=$(line_of 3 'hw = devm_clk_hw_register_fixed_rate(qmp->dev, name, NULL, 0, 0);')
hws2=$(line_of 1 'clk_data->hws[2] = hw;')
compatible=$(line_of 1 'if (of_device_is_compatible(qmp->dev->of_node,')
stop=$(line_of 1 'return 0;')
provider=$(line_of 1 'ret = of_clk_add_hw_provider(np, of_clk_hw_onecell_get, clk_data);')
cleanup=$(line_of 1 'return devm_add_action_or_reset(qmp->dev, qmp_ufs_clk_release_provider, np);')

previous=0
for line in "$rx0" "$clock0" "$hws0" "$rx1" "$clock1" "$hws1" \
	"$tx0" "$clock2" "$hws2" "$compatible" "$stop" "$provider" "$cleanup"; do
	[[ $line =~ ^[1-9][0-9]*$ && $line -gt $previous ]] ||
		fail 'QMP-UFS third-clock operation order changed'
	previous=$line
done

echo 'PASS QMP-UFS runtime-PM discriminator crosses exactly three fixed-rate clocks before provider publication'
