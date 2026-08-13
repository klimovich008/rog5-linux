#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0032-phy-qcom-qmp-ufs-publish-of-phy-provider.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-first-clock-runtime-pm-stage-20260813-r2/linux-source}
expected_source=ae717d919f87b47ea9ed2173ea96660186b62a66
expected_parent=3a0a28dcbbc377a4160eaf0bbe80122931c34b05
explicit_source=${ROG5_LINUX_SOURCE:+1}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ -f $patch && ! -L $patch ]] || fail 'missing QMP-UFS PHY-provider patch'
[[ $(git apply --numstat "$patch") == $'7\t8\tdrivers/phy/qualcomm/phy-qcom-qmp-ufs.c' ]] ||
	fail 'QMP-UFS patch changes anything except the exact PHY-provider boundary'
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: OF PHY provider registration stage complete' "$patch") == 1 ]] ||
	fail 'QMP-UFS PHY-provider completion marker is not exact'
for forbidden in \
	'+\tqmp_ufs_init' '+\tphy_power_on' '+\tclk_prepare_enable' \
	'+\tregulator_enable' '+\treadl' '+\twritel'; do
	! grep -Fq "$forbidden" "$patch" ||
		fail "QMP-UFS patch adds a forbidden later operation: $forbidden"
done

if [[ ! -d $source_root ]]; then
	[[ -z $explicit_source ]] || fail 'explicit retained source is unavailable'
	echo 'SKIP retained Generation 48 source integration; committed patch contract passed' >&2
	exit 0
fi

[[ -d $source_root && ! -L $source_root && ! -L $source_root/.git ]] ||
	fail 'retained Generation 48 source is unsafe'
[[ $(git -C "$source_root" rev-parse --is-inside-work-tree) == true ]] ||
	fail 'retained Generation 48 source is not a Git worktree'
if [[ -n $explicit_source ]]; then
	[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_source" ]] ||
		fail 'explicit Generation 48 source is not exact'
else
	git -C "$source_root" merge-base --is-ancestor "$expected_source" HEAD ||
		fail 'current retained source does not descend from Generation 48'
fi
[[ $(git -C "$source_root" rev-parse "$expected_source^") == "$expected_parent" ]] ||
	fail 'retained Generation 48 source parent changed'
[[ -z $(git -C "$source_root" status --porcelain) ]] ||
	fail 'retained Generation 48 source is dirty'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
patched=$stage/linux-source
git -c advice.detachedHead=false clone -q --shared "$source_root" "$patched"
git -C "$patched" checkout -q "$expected_parent"
git -C "$patched" apply "$patch"
git -C "$patched" diff --check
git -C "$patched" diff --quiet "$expected_source" -- \
	drivers/phy/qualcomm/phy-qcom-qmp-ufs.c ||
	fail 'committed PHY-provider patch does not reproduce the retained source'

probe=$stage/probe
awk '
	/^static int qmp_ufs_probe[(]/ { found = 1 }
	found { print }
	found && /^}/ { exit }
' "$patched/drivers/phy/qualcomm/phy-qcom-qmp-ufs.c" >"$probe"
[[ -s $probe ]]

line_of() {
	local occurrence=$1 operation=$2
	grep -nF "$operation" "$probe" | sed -n "${occurrence}s/:.*//p"
}

create=$(line_of 1 'qmp->phy = devm_phy_create(dev, np, &qcom_qmp_ufs_phy_ops);')
drvdata=$(line_of 1 'phy_set_drvdata(qmp->phy, qmp);')
node_put=$(line_of 1 'of_node_put(np);')
provider=$(line_of 1 'phy_provider = devm_of_phy_provider_register(dev, of_phy_simple_xlate);')
compatible=$(line_of 1 'if (of_device_is_compatible(dev->of_node,')
provider_success=$(line_of 1 '!IS_ERR(phy_provider)')
completion=$(line_of 1 'ROG5 QMP-UFS diagnostic: OF PHY provider registration stage complete')
stop=$(line_of 1 'return 0;')
provider_result=$(line_of 1 'return PTR_ERR_OR_ZERO(phy_provider);')

previous=0
for line in "$create" "$drvdata" "$node_put" "$provider" "$compatible" \
	"$provider_success" "$completion" "$stop" "$provider_result"; do
	[[ $line =~ ^[1-9][0-9]*$ && $line -gt $previous ]] ||
		fail 'QMP-UFS PHY-provider operation order changed'
	previous=$line
done

echo 'PASS QMP-UFS discriminator publishes the OF PHY provider after drvdata and stops before any UFS consumer'
