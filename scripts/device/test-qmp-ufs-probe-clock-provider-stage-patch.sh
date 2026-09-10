#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0021-phy-qcom-qmp-ufs-stop-sm8350-after-clock-provider.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-mmio-stage-20260812-r1/linux-source}

[[ -f $patch && ! -L $patch ]] || {
	echo 'FAIL missing QMP-UFS clock-provider-stage patch' >&2
	exit 1
}
[[ $(grep -Fc 'qcom,sm8350-qmp-ufs-phy' "$patch") == 2 ]]
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: clock provider stage complete' "$patch") == 1 ]]
[[ $(grep -Fc -- $'-\t\t\t   "ROG5 QMP-UFS diagnostic: MMIO parse stage complete' "$patch") == 1 ]]
[[ $(grep -Fc $'+\t\tof_node_put(np);' "$patch") == 1 ]]
[[ $(grep -Fc $'+\t\treturn 0;' "$patch") == 1 ]]
for required in \
	'qmp_ufs_register_clocks(qmp, np)' \
	'devm_phy_create(dev, np'; do
	grep -Fq "$required" "$patch" || {
		echo "FAIL clock-provider patch omits boundary context: $required" >&2
		exit 1
	}
done
for forbidden in \
	'devm_phy_create' 'phy_set_drvdata' 'devm_of_phy_provider_register' \
	'clk_prepare_enable' 'regulator_enable' 'readl' 'writel'; do
	! grep -Fq "+$forbidden" "$patch" || {
		echo "FAIL clock-provider patch adds forbidden operation: $forbidden" >&2
		exit 1
	}
done
[[ $(grep -Ec '^\+($|[^+])' "$patch") == 8 ]]

if [[ -e $source_root/.git && ! -L $source_root/.git && ! -L $source_root ]]; then
	[[ $(git -C "$source_root" rev-parse HEAD) == \
		08aa45cd0e4d230ce2f320daf9a6796a01746d8d ]] || {
		echo 'FAIL retained MMIO-stage source commit changed' >&2
		exit 1
	}
	[[ -z $(git -C "$source_root" status --porcelain) ]] || {
		echo 'FAIL retained MMIO-stage source is dirty' >&2
		exit 1
	}
	for downstream in \
		'qmp_ufs_register_clocks(qmp, np)' \
		'devm_phy_create(dev, np' \
		'devm_of_phy_provider_register(dev'; do
		grep -Fq "$downstream" \
			"$source_root/drivers/phy/qualcomm/phy-qcom-qmp-ufs.c"
	done
	git -C "$source_root" apply --check "$patch"
fi

echo 'PASS QMP-UFS clock-provider patch stops before PHY creation'
