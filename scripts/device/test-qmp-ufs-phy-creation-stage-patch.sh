#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0031-phy-qcom-qmp-ufs-stop-sm8350-after-phy-creation.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-first-clock-runtime-pm-stage-20260813-r2/linux-source}
expected_source=3a0a28dcbbc377a4160eaf0bbe80122931c34b05
expected_parent=07858678c59cc4acdb4e2949100225b2320997b9
explicit_source=${ROG5_LINUX_SOURCE:+1}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ -f $patch && ! -L $patch ]] || fail 'missing QMP-UFS PHY-creation patch'
[[ $(git apply --numstat "$patch") == $'8\t8\tdrivers/phy/qualcomm/phy-qcom-qmp-ufs.c' ]] ||
	fail 'QMP-UFS patch changes anything except the exact PHY-creation boundary'
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: PHY creation stage complete' "$patch") == 1 ]] ||
	fail 'QMP-UFS PHY-creation completion marker is not exact'
for forbidden in \
	'+\tphy_set_drvdata' '+\tdevm_of_phy_provider_register' \
	'+\tclk_prepare_enable' '+\tregulator_enable' '+\treadl' '+\twritel'; do
	! grep -Fq "$forbidden" "$patch" ||
		fail "QMP-UFS patch adds a forbidden later operation: $forbidden"
done

if [[ ! -d $source_root ]]; then
	[[ -z $explicit_source ]] || fail 'explicit retained source is unavailable'
	echo 'SKIP retained Generation 47 source integration; committed patch contract passed' >&2
	exit 0
fi

[[ -d $source_root && ! -L $source_root && ! -L $source_root/.git ]] ||
	fail 'retained Generation 47 source is unsafe'
[[ $(git -C "$source_root" rev-parse --is-inside-work-tree) == true ]] ||
	fail 'retained Generation 47 source is not a Git worktree'
if [[ -n $explicit_source ]]; then
	[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_source" ]] ||
		fail 'explicit Generation 47 source is not exact'
else
	git -C "$source_root" merge-base --is-ancestor "$expected_source" HEAD ||
		fail 'current retained source does not descend from Generation 47'
fi
[[ $(git -C "$source_root" rev-parse "$expected_source^") == "$expected_parent" ]] ||
	fail 'retained Generation 47 source parent changed'
[[ -z $(git -C "$source_root" status --porcelain) ]] ||
	fail 'retained Generation 47 source is dirty'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
patched=$stage/linux-source
git -c advice.detachedHead=false clone -q --shared "$source_root" "$patched"
git -C "$patched" checkout -q "$expected_parent"
git -C "$patched" apply "$patch"
git -C "$patched" diff --check
git -C "$patched" diff --quiet "$expected_source" -- \
	drivers/phy/qualcomm/phy-qcom-qmp-ufs.c ||
	fail 'committed PHY-creation patch does not reproduce the retained source'

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

register=$(line_of 1 'ret = qmp_ufs_register_clocks(qmp, np);')
create=$(line_of 1 'qmp->phy = devm_phy_create(dev, np, &qcom_qmp_ufs_phy_ops);')
create_error=$(line_of 1 'if (IS_ERR(qmp->phy))')
compatible=$(line_of 1 'if (of_device_is_compatible(dev->of_node,')
completion=$(line_of 1 'ROG5 QMP-UFS diagnostic: PHY creation stage complete')
stop=$(line_of 1 'return 0;')
drvdata=$(line_of 1 'phy_set_drvdata(qmp->phy, qmp);')
provider=$(line_of 1 'phy_provider = devm_of_phy_provider_register(dev, of_phy_simple_xlate);')

previous=0
for line in "$register" "$create" "$create_error" "$compatible" "$completion" \
	"$stop" "$drvdata" "$provider"; do
	[[ $line =~ ^[1-9][0-9]*$ && $line -gt $previous ]] ||
		fail 'QMP-UFS PHY-creation operation order changed'
	previous=$line
done

echo 'PASS QMP-UFS discriminator crosses PHY creation before stopping ahead of drvdata and provider registration'
