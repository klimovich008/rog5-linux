#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0019-phy-qcom-qmp-ufs-stop-sm8350-after-regulator-acquisition.patch
source_root=${ROG5_LINUX_SOURCE:-/home/deck/.local/state/rog5-storage-phase2-20260812-r1/linux-7.1.4-ufs-source}

[[ -f $patch && ! -L $patch ]] || {
	echo 'FAIL missing QMP-UFS regulator-stage patch' >&2
	exit 1
}
[[ $(grep -Fc 'qcom,sm8350-qmp-ufs-phy' "$patch") == 1 ]]
[[ $(grep -Fc 'ROG5 QMP-UFS diagnostic: regulator stage complete' "$patch") == 1 ]]
grep -Fq 'return 0;' "$patch"
for forbidden in \
	'regulator_enable' 'clk_prepare_enable' 'writel' 'readl' \
	'devm_phy_create' 'devm_of_phy_provider_register' 'qmp_ufs_parse_dt'; do
	! grep -Fq "+$forbidden" "$patch" || {
		echo "FAIL diagnostic patch adds forbidden operation: $forbidden" >&2
		exit 1
	}
done
[[ $(grep -Ec '^\+($|[^+])' "$patch") == 7 ]]

# A clean checkout has no ignored 7.1.4 source tree. When the canonical source
# is retained locally, also prove that the hunk applies at the reviewed probe
# boundary rather than merely matching the source-free patch shape above.
if [[ -d $source_root/.git && ! -L $source_root ]]; then
	[[ $(git -C "$source_root" rev-parse HEAD) == \
		cfd385a1c754684dd28b63a4559e04baa5e902b1 ]] || {
		echo 'FAIL retained UFS source commit changed' >&2
		exit 1
	}
	[[ -z $(git -C "$source_root" status --porcelain) ]] || {
		echo 'FAIL retained UFS source is dirty' >&2
		exit 1
	}
	grep -Fq 'ret = devm_regulator_bulk_get_const' \
		"$source_root/drivers/phy/qualcomm/phy-qcom-qmp-ufs.c"
	git -C "$source_root" apply --check "$patch"
fi

echo 'PASS QMP-UFS regulator-stage patch binds only SM8350 and stops before MMIO or provider creation'
