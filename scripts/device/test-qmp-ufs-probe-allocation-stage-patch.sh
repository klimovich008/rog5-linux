#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0024-phy-qcom-qmp-ufs-stop-sm8350-after-clock-allocation.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-first-fixed-clock-stage-20260812-r1/linux-source}

[[ -f $patch && ! -L $patch ]] || {
	echo 'FAIL missing QMP-UFS allocation-stage patch' >&2
	exit 1
}
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: clock-data allocation stage complete' "$patch") == 1 ]]
[[ $(grep -Fc -- $'-\t\t\t   "ROG5 QMP-UFS diagnostic: first fixed-rate symbol clock stage complete' "$patch") == 1 ]]
for required in \
	'clk_data->num = UFS_SYMBOL_CLOCKS;' \
	'snprintf(name, sizeof(name), "%s::rx_symbol_0", dev_name(qmp->dev));' \
	'of_device_is_compatible(qmp->dev->of_node,'; do
	grep -Fq "$required" "$patch" || {
		echo "FAIL allocation-stage patch omits boundary context: $required" >&2
		exit 1
	}
done
for forbidden in \
	'dev_name(qmp->dev)' 'devm_clk_hw_register_fixed_rate' \
	'of_clk_add_hw_provider' 'devm_add_action_or_reset' \
	'devm_phy_create' 'phy_set_drvdata' 'devm_of_phy_provider_register' \
	'clk_prepare_enable' 'regulator_enable' 'readl' 'writel'; do
	! grep -Fq "+$forbidden" "$patch" || {
		echo "FAIL allocation-stage patch adds forbidden operation: $forbidden" >&2
		exit 1
	}
done

if [[ -e $source_root/.git && ! -L $source_root/.git && ! -L $source_root ]]; then
	[[ $(git -C "$source_root" rev-parse HEAD) == \
		e09bdc38dccd64c04a9143accb4b220b5c06fd3b ]] || {
		echo 'FAIL retained first-fixed-clock source commit changed' >&2
		exit 1
	}
	[[ -z $(git -C "$source_root" status --porcelain) ]] || {
		echo 'FAIL retained first-fixed-clock source is dirty' >&2
		exit 1
	}
	git -C "$source_root" apply --check "$patch"
fi

echo 'PASS QMP-UFS allocation stage stops before the first clock registration'
