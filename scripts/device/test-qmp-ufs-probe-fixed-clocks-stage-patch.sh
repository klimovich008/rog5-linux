#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0022-phy-qcom-qmp-ufs-stop-sm8350-after-fixed-clocks.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-clock-provider-stage-20260812-r1/linux-source}

[[ -f $patch && ! -L $patch ]] || {
	echo 'FAIL missing QMP-UFS fixed-clocks-stage patch' >&2
	exit 1
}
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: fixed-rate symbol clocks stage complete' "$patch") == 1 ]]
[[ $(grep -Fc -- $'-\t\t\t   "ROG5 QMP-UFS diagnostic: clock provider stage complete' "$patch") == 1 ]]
for required in \
	'clk_data->hws[2] = hw;' \
	'of_device_is_compatible(qmp->dev->of_node,' \
	'of_clk_add_hw_provider(np, of_clk_hw_onecell_get, clk_data)'; do
	grep -Fq "$required" "$patch" || {
		echo "FAIL fixed-clocks patch omits boundary context: $required" >&2
		exit 1
	}
done
for forbidden in \
	'dev_name(qmp->dev)' 'devm_clk_hw_register_fixed_rate' \
	'of_clk_add_hw_provider' 'devm_add_action_or_reset' \
	'devm_phy_create' 'phy_set_drvdata' 'devm_of_phy_provider_register' \
	'clk_prepare_enable' 'regulator_enable' 'readl' 'writel'; do
	! grep -Fq "+$forbidden" "$patch" || {
		echo "FAIL fixed-clocks patch adds forbidden operation: $forbidden" >&2
		exit 1
	}
done

if [[ -e $source_root/.git && ! -L $source_root/.git && ! -L $source_root ]]; then
	[[ $(git -C "$source_root" rev-parse HEAD) == \
		a2947ed3ea474b61d2f4affd6488d149acfb1fa3 ]] || {
		echo 'FAIL retained clock-provider-stage source commit changed' >&2
		exit 1
	}
	[[ -z $(git -C "$source_root" status --porcelain) ]] || {
		echo 'FAIL retained clock-provider-stage source is dirty' >&2
		exit 1
	}
	git -C "$source_root" apply --check "$patch"
fi

echo 'PASS QMP-UFS fixed symbol clocks stop before OF provider publication'
