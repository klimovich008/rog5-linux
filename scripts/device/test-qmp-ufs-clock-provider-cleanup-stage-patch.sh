#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0030-phy-qcom-qmp-ufs-publish-clock-provider-with-cleanup.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-first-clock-runtime-pm-stage-20260813-r2/linux-source}
expected_source=07858678c59cc4acdb4e2949100225b2320997b9
expected_parent=c732b0b41d8d5fd2f4ccd76e1f4dbff8ff06c087
explicit_source=${ROG5_LINUX_SOURCE:+1}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ -f $patch && ! -L $patch ]] || fail 'missing QMP-UFS clock-provider patch'
[[ $(git apply --numstat "$patch") == $'1\t5\tdrivers/phy/qualcomm/phy-qcom-qmp-ufs.c' ]] ||
	fail 'QMP-UFS patch changes anything except provider publication boundary'
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: OF clock provider with cleanup stage complete' "$patch") == 1 ]] ||
	fail 'QMP-UFS provider completion marker is not exact'
for forbidden in \
	'+\tdevm_phy_create' '+\tphy_set_drvdata' \
	'+\tdevm_of_phy_provider_register' '+\tclk_prepare_enable' \
	'+\tregulator_enable' '+\treadl' '+\twritel'; do
	! grep -Fq "$forbidden" "$patch" ||
		fail "QMP-UFS patch adds a forbidden later operation: $forbidden"
done

if [[ ! -d $source_root ]]; then
	[[ -z $explicit_source ]] || fail 'explicit retained source is unavailable'
	echo 'SKIP retained Generation 45 source integration; committed patch contract passed' >&2
	exit 0
fi

[[ -d $source_root && ! -L $source_root && ! -L $source_root/.git ]] ||
	fail 'retained Generation 45 source is unsafe'
[[ $(git -C "$source_root" rev-parse --is-inside-work-tree) == true ]] ||
	fail 'retained Generation 45 source is not a Git worktree'
if [[ -n $explicit_source ]]; then
	[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_source" ]] ||
		fail 'explicit Generation 45 source is not exact'
else
	git -C "$source_root" merge-base --is-ancestor "$expected_source" HEAD ||
		fail 'current retained source does not descend from Generation 45'
fi
[[ $(git -C "$source_root" rev-parse "$expected_source^") == "$expected_parent" ]] ||
	fail 'retained Generation 45 source parent changed'
[[ -z $(git -C "$source_root" status --porcelain) ]] ||
	fail 'retained Generation 45 source is dirty'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
patched=$stage/linux-source
git -c advice.detachedHead=false clone -q --shared "$source_root" "$patched"
git -C "$patched" checkout -q "$expected_parent"
git -C "$patched" apply "$patch"
git -C "$patched" diff --check
git -C "$patched" diff --quiet "$expected_source" -- \
	drivers/phy/qualcomm/phy-qcom-qmp-ufs.c ||
	fail 'committed provider patch does not reproduce the retained source'

register=$stage/register-clocks
probe=$stage/probe
awk '
	/^static int qmp_ufs_register_clocks[(]/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$patched/drivers/phy/qualcomm/phy-qcom-qmp-ufs.c" >"$register"
awk '
	/^static int qmp_ufs_probe[(]/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$patched/drivers/phy/qualcomm/phy-qcom-qmp-ufs.c" >"$probe"
[[ -s $register && -s $probe ]]

line_of() {
	local file=$1 occurrence=$2 operation=$3
	grep -nF "$operation" "$file" | sed -n "${occurrence}s/:.*//p"
}

provider=$(line_of "$register" 1 'ret = of_clk_add_hw_provider(np, of_clk_hw_onecell_get, clk_data);')
provider_error=$(line_of "$register" 1 'if (ret)')
cleanup=$(line_of "$register" 1 'return devm_add_action_or_reset(qmp->dev, qmp_ufs_clk_release_provider, np);')
[[ $provider =~ ^[1-9][0-9]*$ && $provider_error -gt $provider && $cleanup -gt $provider_error ]] ||
	fail 'OF clock-provider publication is not paired with later devm cleanup'
! grep -Fq '"qcom,sm8350-qmp-ufs-phy"' "$register" ||
	fail 'provider function still contains an SM8350 early return'

register_call=$(line_of "$probe" 1 'ret = qmp_ufs_register_clocks(qmp, np);')
compatible=$(line_of "$probe" 1 'if (of_device_is_compatible(dev->of_node,')
completion=$(line_of "$probe" 1 'ROG5 QMP-UFS diagnostic: OF clock provider with cleanup stage complete')
stop=$(line_of "$probe" 1 'return 0;')
phy=$(line_of "$probe" 1 'qmp->phy = devm_phy_create(dev, np, &qcom_qmp_ufs_phy_ops);')
[[ $register_call =~ ^[1-9][0-9]*$ && $compatible -gt $register_call &&
	$completion -gt $compatible && $stop -gt $completion && $phy -gt $stop ]] ||
	fail 'SM8350 diagnostic does not stop between provider cleanup and PHY creation'

echo 'PASS QMP-UFS discriminator publishes the OF clock provider with cleanup before stopping ahead of PHY creation'
