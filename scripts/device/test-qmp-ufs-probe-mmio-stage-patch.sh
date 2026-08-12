#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0020-phy-qcom-qmp-ufs-stop-sm8350-after-mmio-parse.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-regulator-stage-20260812-r1/linux-source}

[[ -f $patch && ! -L $patch ]] || {
	echo 'FAIL missing QMP-UFS MMIO-stage patch' >&2
	exit 1
}
[[ $(grep -Fc 'qcom,sm8350-qmp-ufs-phy' "$patch") == 2 ]]
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: MMIO parse stage complete' "$patch") == 1 ]]
[[ $(grep -Fc -- $'-\t\t\t   "ROG5 QMP-UFS diagnostic: regulator stage complete' "$patch") == 1 ]]
[[ $(grep -Fc $'+\t\tof_node_put(np);' "$patch") == 1 ]]
[[ $(grep -Fc $'+\t\treturn 0;' "$patch") == 1 ]]
for required in 'qmp_ufs_register_clocks(qmp, np)'; do
	grep -Fq "$required" "$patch" || {
		echo "FAIL MMIO-stage patch omits boundary context: $required" >&2
		exit 1
	}
done
for forbidden in \
	'clk_prepare_enable' 'regulator_enable' 'readl' 'writel' \
	'devm_clk_hw_register_fixed_rate' 'of_clk_add_hw_provider' \
	'devm_phy_create' 'devm_of_phy_provider_register'; do
	! grep -Fq "+$forbidden" "$patch" || {
		echo "FAIL MMIO-stage patch adds forbidden operation: $forbidden" >&2
		exit 1
	}
done
[[ $(grep -Ec '^\+($|[^+])' "$patch") == 8 ]]

if [[ -d $source_root/.git && ! -L $source_root ]]; then
	[[ $(git -C "$source_root" rev-parse HEAD) == \
		d6509d3ddc3db7654271b82f2f718fb671fdfbcf ]] || {
		echo 'FAIL retained regulator-stage source commit changed' >&2
		exit 1
	}
	[[ -z $(git -C "$source_root" status --porcelain) ]] || {
		echo 'FAIL retained regulator-stage source is dirty' >&2
		exit 1
	}
	for downstream in \
		'qmp_ufs_parse_dt(qmp)' \
		'devm_phy_create(dev, np' \
		'devm_of_phy_provider_register(dev'; do
		grep -Fq "$downstream" \
			"$source_root/drivers/phy/qualcomm/phy-qcom-qmp-ufs.c"
	done
	git -C "$source_root" apply --check "$patch"
fi

echo 'PASS QMP-UFS MMIO-stage patch advances only through resource mapping'
