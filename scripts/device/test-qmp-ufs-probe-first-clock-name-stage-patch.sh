#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0025-phy-qcom-qmp-ufs-stop-sm8350-after-first-clock-name.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-qmp-ufs-allocation-stage-20260813-r1/linux-source}

[[ -f $patch && ! -L $patch ]] || {
	echo 'FAIL missing QMP-UFS first-clock-name-stage patch' >&2
	exit 1
}
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: first symbol-clock name stage complete' "$patch") == 1 ]]
[[ $(grep -Fc -- $'-\t\t\t   "ROG5 QMP-UFS diagnostic: clock-data allocation stage complete' "$patch") == 1 ]]
for required in \
	'clk_data->num = UFS_SYMBOL_CLOCKS;' \
	'snprintf(name, sizeof(name), "%s::rx_symbol_0", dev_name(qmp->dev));' \
	'of_device_is_compatible(qmp->dev->of_node,'; do
	grep -Fq "$required" "$patch" || {
		echo "FAIL first-clock-name patch omits boundary context: $required" >&2
		exit 1
	}
done
for forbidden in \
	'+\thw = devm_clk_hw_register_fixed_rate' \
	'+\tret = of_clk_add_hw_provider' '+\tdevm_add_action_or_reset' \
	'+\tqmp->phy = devm_phy_create' '+\tphy_set_drvdata' \
	'+\tphy_provider = devm_of_phy_provider_register' \
	'+\tclk_prepare_enable' '+\tregulator_enable' '+\treadl' '+\twritel'; do
	! grep -Fq "$forbidden" "$patch" || {
		echo "FAIL first-clock-name patch adds forbidden operation: $forbidden" >&2
		exit 1
	}
done

if [[ -e $source_root/.git && ! -L $source_root/.git && ! -L $source_root ]]; then
	[[ $(git -C "$source_root" rev-parse HEAD) == \
		858db0ad4f9a3b9b6532443e3f8f9509203a920c ]] || {
		echo 'FAIL retained allocation-stage source commit changed' >&2
		exit 1
	}
	[[ -z $(git -C "$source_root" status --porcelain) ]] || {
		echo 'FAIL retained allocation-stage source is dirty' >&2
		exit 1
	}
	git -C "$source_root" apply --check "$patch"
fi

echo 'PASS QMP-UFS first symbol-clock name stage stops before clock registration'
