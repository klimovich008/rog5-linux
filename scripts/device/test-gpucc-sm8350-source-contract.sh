#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-}
[ -n "$source_dir" ] || {
	echo 'FAIL set SOURCE_DIR to the pinned Linux 7.1.4 source' >&2
	exit 1
}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
build=$repo/scripts/device/build-mainline-gpucc-diagnostic.sh
driver=$source_dir/drivers/clk/qcom/gpucc-sm8350.c
common=$source_dir/drivers/clk/qcom/common.c
pll=$source_dir/drivers/clk/qcom/clk-alpha-pll.c
pll_header=$source_dir/drivers/clk/qcom/clk-alpha-pll.h
gdsc=$source_dir/drivers/clk/qcom/gdsc.c
dtsi=$source_dir/arch/arm64/boot/dts/qcom/sm8350.dtsi

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = \
	7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
for source in "$driver" "$common" "$pll" "$pll_header" "$gdsc" "$dtsi"; do
	[ -r "$source" ]
done
[ -x "$build" ]
grep -Fq 'expected_release=7.1.4-g7a5cef0db479' "$build"
[ "$(grep -Fc 'KERNELRELEASE="$expected_release"' "$build")" -eq 4 ]
grep -Fq 'include/config/kernel.release' "$build"
grep -Fq 'repro_source_dir=/root/src/linux-7.1.4' "$build"
grep -Fq 'repro_output_dir=/root/build/rog5-linux-7.1.4-network-root' "$build"
grep -Fq 'for reproducible vDSO build IDs' "$build"

grep -Fq '{ .compatible = "qcom,sm8350-gpucc" }' "$driver"
grep -Fq '.max_register = 0x8030,' "$driver"
[ "$(grep -Fc '.regs = clk_alpha_pll_regs[CLK_ALPHA_PLL_TYPE_LUCID],' \
	"$driver")" -eq 2 ]
[ "$(grep -Fc '.ops = &clk_alpha_pll_lucid_5lpe_ops,' "$driver")" -eq 2 ]
grep -Fq '#define clk_lucid_pll_configure(pll, regmap, config)' "$pll_header"
grep -Fq 'clk_trion_pll_configure(pll, regmap, config)' "$pll_header"

probe=$(awk '
	/^static int gpu_cc_sm8350_probe\(/ { found = 1 }
	found { print }
	found && /^}$/ { exit }
' "$driver")
[ -n "$probe" ]
probe_lines=$(printf '%s\n' "$probe" | nl -ba)
map_line=$(printf '%s\n' "$probe_lines" |
	awk '/qcom_cc_map\(pdev/ { print $1; exit }')
pll0_line=$(printf '%s\n' "$probe_lines" |
	awk '/clk_lucid_pll_configure\(&gpu_cc_pll0/ { print $1; exit }')
pll1_line=$(printf '%s\n' "$probe_lines" |
	awk '/clk_lucid_pll_configure\(&gpu_cc_pll1/ { print $1; exit }')
register_line=$(printf '%s\n' "$probe_lines" |
	awk '/qcom_cc_really_probe\(/ { print $1; exit }')
[ "$map_line" -lt "$pll0_line" ]
[ "$pll0_line" -lt "$pll1_line" ]
[ "$pll1_line" -lt "$register_line" ]

grep -Fq 'base = devm_platform_ioremap_resource(pdev, 0);' "$common"
grep -Fq 'return devm_regmap_init_mmio(dev, base, desc->config);' "$common"
grep -Fq 'ret = gdsc_register(scd, &reset->rcdev, regmap);' "$common"
grep -Fq 'ret = regmap_read(sc->regmap, reg, &val);' "$gdsc"
grep -Fq 'regmap_update_bits(sc->regmap, sc->gdscr, mask, val);' "$gdsc"
grep -Fq '.gdscr = 0x106c,' "$driver"
grep -Fq '.gds_hw_ctrl = 0x1540,' "$driver"
grep -Fq '.flags = VOTABLE,' "$driver"
grep -Fq '.gdscr = 0x100c,' "$driver"
grep -Fq '.clamp_io_ctrl = 0x1508,' "$driver"
grep -Fq '.flags = CLAMP_IO | AON_RESET | POLL_CFG_GDSCR,' "$driver"

gpucc_block=$(sed -n \
	'/gpucc: clock-controller@3d90000 {/,/^[[:space:]]*};/p' "$dtsi")
printf '%s\n' "$gpucc_block" |
	grep -Fq 'compatible = "qcom,sm8350-gpucc";'
printf '%s\n' "$gpucc_block" |
	grep -Fq 'reg = <0 0x03d90000 0 0x9000>;'
! printf '%s\n' "$gpucc_block" | grep -q 'status = '

gpu_block=$(sed -n '/gpu: gpu@3d00000 {/,/gpu_zap_shader:/p' "$dtsi")
printf '%s\n' "$gpu_block" | grep -Fq 'status = "disabled";'
gmu_block=$(sed -n '/gmu: gmu@3d6a000 {/,/gmu_opp_table:/p' "$dtsi")
! printf '%s\n' "$gmu_block" | grep -q 'status = '
smmu_block=$(sed -n \
	'/adreno_smmu: iommu@3da0000 {/,/^[[:space:]]*};/p' "$dtsi")
! printf '%s\n' "$smmu_block" | grep -q 'status = '

if [ -n "${V1_DTB:-}" ]; then
	[ -s "$V1_DTB" ]
	[ -z "$(fdtget -t s "$V1_DTB" \
		/soc@0/clock-controller@3d90000 status 2>/dev/null || true)" ]
	[ -z "$(fdtget -t s "$V1_DTB" \
		/soc@0/gmu@3d6a000 status 2>/dev/null || true)" ]
	[ -z "$(fdtget -t s "$V1_DTB" \
		/soc@0/iommu@3da0000 status 2>/dev/null || true)" ]
fi

if [ -n "${VENDOR_SOURCE:-}" ]; then
	vendor=$VENDOR_SOURCE/drivers/clk/qcom/gpucc-lahaina.c
	[ "$(sha256sum "$vendor" | cut -d ' ' -f 1)" = \
		8afd5da244af298e987f5e4cce7aa79a1e63a0c356d8469705a9d952f6c8f080 ]
	grep -Fq 'static DEFINE_VDD_REGULATORS(vdd_mx,' "$vendor"
	grep -Fq 'static DEFINE_VDD_REGULATORS(vdd_cx,' "$vendor"
	grep -Fq '.clk_regulators = gpu_cc_lahaina_regulators,' "$vendor"
	grep -Fq 'clk_lucid_5lpe_pll_configure(&gpu_cc_pll0' "$vendor"
	! grep -q 'gdsc_register\|gpu_cc_lahaina_gdscs' "$vendor"
fi

if [ -n "${STOCK_DTB:-}" ]; then
	[ -s "$STOCK_DTB" ]
	node=/soc/qcom,gpucc@3d90000
	[ "$(fdtget -t s "$STOCK_DTB" "$node" compatible)" = \
		'qcom,lahaina-gpucc syscon' ]
	[ "$(fdtget -t x "$STOCK_DTB" "$node" reg)" = '3d90000 9000' ]
	fdtget -p "$STOCK_DTB" "$node" | grep -qx 'vdd_cx-supply'
	fdtget -p "$STOCK_DTB" "$node" | grep -qx 'vdd_mx-supply'
fi

[ -r "$repo/dts/qcom/sm8350-asus-rog-phone5-gpucc-diagnostic.dtso" ]

echo 'PASS pinned GPUCC probe boundary, upstream power-domain accesses, vendor reference, and prior consumer exposure are source-audited'
