#!/bin/sh
set -eu

source_dir=${1:?usage: verify-a660-gmu-clock-preparation-boundary.sh PINNED_SOURCE}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
v10_report=$repo/test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md
v10_verifier=$repo/scripts/device/verify-a660-gmu-cx-runtime-pm-boundary.sh

expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
expected_v10_report=9ae66678340437c4a38b2d6ee390cc375e661548be97cb108bb8f891a418dee4
expected_v10_verifier=6ba90691000f9369b5fdfdbf235495f9afeba4984c11596888cc1213717d7b06

a6xx_gmu=$source_dir/drivers/gpu/drm/msm/adreno/a6xx_gmu.c
gpucc=$source_dir/drivers/clk/qcom/gpucc-sm8350.c
gdsc=$source_dir/drivers/clk/qcom/gdsc.c
sm8350=$source_dir/arch/arm64/boot/dts/qcom/sm8350.dtsi
clk_bulk=$source_dir/drivers/clk/clk-bulk.c
clk_core=$source_dir/drivers/clk/clk.c
clk_h=$source_dir/include/linux/clk.h

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$2
	label=$3
	[ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] ||
		fail "$label is missing, linked, or unreadable"
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		fail "$label hash mismatch: expected $expected, got $actual"
}

line_once() {
	text=$1
	needle=$2
	label=$3
	stats=$(printf '%s\n' "$text" |
		awk -v needle="$needle" '
			index($0, needle) { count++; line = NR }
			END { print count + 0 ":" line + 0 }
		')
	count=${stats%%:*}
	line=${stats#*:}
	[ "$count" -eq 1 ] ||
		fail "$label count is $count, expected 1"
	printf '%s\n' "$line"
}

require_text() {
	text=$1
	needle=$2
	label=$3
	printf '%s\n' "$text" | grep -Fq "$needle" ||
		fail "$label is missing"
}

for command in awk cut git grep sed sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done

[ -d "$source_dir" ] || fail "missing source directory: $source_dir"
[ "$(git -C "$source_dir" rev-parse --is-inside-work-tree)" = true ] ||
	fail 'source is not a Git worktree'
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] ||
	fail 'pinned source commit changed'
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ] ||
	fail 'pinned source tree changed'
[ -z "$(git -C "$source_dir" status --porcelain)" ] ||
	fail 'pinned source worktree is not clean'

check_hash "$v10_report" "$expected_v10_report" \
	'A660 GMU/CX runtime-PM v10 offline report'
check_hash "$v10_verifier" "$expected_v10_verifier" \
	'A660 GMU/CX runtime-PM v10 boundary verifier'
SKIP_V9_UMBRELLA_RUN=1 "$v10_verifier" "$source_dir" >/dev/null

check_hash "$a6xx_gmu" \
	97b2fc130862f00445b509855b16121b2eba6e5a5228f92457c2923297fd4999 \
	'a6xx_gmu.c'
check_hash "$gpucc" \
	39efbb61d7cc9a59e13f7e1ee9ebab6357d6fc4cbc981e8a89a28aa976b33755 \
	'gpucc-sm8350.c'
check_hash "$gdsc" \
	6c78ba4c8b58b99614fa0d7c3a6023e3d98754fc0fbf059c2bffc4ab431f11fc \
	'gdsc.c'
check_hash "$sm8350" \
	58d28a520a21e21f55703ae968d6e45c6b7750e6a2d3138dcb6cafe2bc6d0a3c \
	'sm8350.dtsi'
check_hash "$clk_bulk" \
	f3170e9895ff60a89aab987db428cc5f50c0cfbe53335c8f0739b5be257ce16d \
	'clk-bulk.c'
check_hash "$clk_core" \
	531f391596179ae4b5925485c1c2b0c405b6defbaf66504505484b00640b5b66 \
	'clk.c'
check_hash "$clk_h" \
	470df6235438d6b05e4f22f36627b7bb74c919ef3ca9a82654f6a982caecaee1 \
	'clk.h'

gmu_resume=$(sed -n '/^int a6xx_gmu_resume(/,/^}/p' "$a6xx_gmu")
gmu_clocks=$(sed -n \
	'/^static int a6xx_gmu_clocks_probe(/,/^}/p' "$a6xx_gmu")
gx_desc=$(sed -n \
	'/^static struct gdsc gpu_gx_gdsc = {/,/^};/p' "$gpucc")
gx_enable=$(sed -n \
	'/^int gdsc_gx_do_nothing_enable(/,/^}/p' "$gdsc")
gdsc_disable=$(sed -n '/^static int gdsc_disable(/,/^}/p' "$gdsc")
bulk_prepare_enable=$(sed -n \
	'/^clk_bulk_prepare_enable(/,/^}/p' "$clk_h")
bulk_disable_unprepare=$(sed -n \
	'/^static inline void clk_bulk_disable_unprepare(/,/^}/p' "$clk_h")
bulk_enable=$(sed -n \
	'/^int __must_check clk_bulk_enable(/,/^}/p' "$clk_bulk")
set_rate=$(sed -n '/^int clk_set_rate(/,/^}/p' "$clk_core")
gmu_node=$(sed -n \
	'/^[[:space:]]*gmu: gmu@3d6a000 {/,/^[[:space:]]*gpucc: clock-controller@3d90000 {/p' \
	"$sm8350")

for block in "$gmu_resume" "$gmu_clocks" "$gx_desc" "$gx_enable" \
	"$gdsc_disable" "$bulk_prepare_enable" "$bulk_disable_unprepare" \
	"$bulk_enable" "$set_rate" "$gmu_node"
do
	[ -n "$block" ] || fail 'one or more GMU clock-boundary blocks are missing'
done

require_text "$gmu_clocks" \
	'devm_clk_bulk_get_all(gmu->dev, &gmu->clocks)' \
	'GMU all-clock acquisition'
require_text "$gmu_clocks" \
	'gmu->core_clk = msm_clk_bulk_get_clock(gmu->clocks,' \
	'GMU core-clock lookup'
require_text "$gmu_clocks" \
	'gmu->hub_clk = msm_clk_bulk_get_clock(gmu->clocks,' \
	'GMU hub-clock lookup'

clock_property=$(printf '%s\n' "$gmu_node" |
	sed -n '/^[[:space:]]*clocks = /,/;$/p')
clock_count=$(printf '%s\n' "$clock_property" |
	grep -o '<&' | wc -l)
[ "$clock_count" -eq 7 ] ||
	fail "SM8350 GMU clock count is $clock_count, expected 7"
for name in gmu cxo axi memnoc ahb hub smmu_vote; do
	printf '%s\n' "$gmu_node" | grep -Fq "\"$name\"" ||
		fail "SM8350 GMU clock name is missing: $name"
done
require_text "$gmu_node" \
	'power-domains = <&gpucc GPU_CX_GDSC>,' \
	'SM8350 GMU CX domain'
require_text "$gmu_node" \
	'<&gpucc GPU_GX_GDSC>;' \
	'SM8350 GMU GX domain'

require_text "$gx_desc" \
	'power_on = gdsc_gx_do_nothing_enable' \
	'SM8350 GX no-op power-on callback'
require_text "$gx_desc" 'PWRSTS_OFF_ON' 'SM8350 GX off/on states'
require_text "$gx_desc" \
	'CLAMP_IO | AON_RESET | POLL_CFG_GDSCR' \
	'SM8350 GX power-off controls'
require_text "$gx_enable" 'gdsc_gx_do_nothing_enable' \
	'GX no-op callback'
require_text "$gx_enable" '/* Do nothing with the GDSC itself */' \
	'GX no-op hardware boundary'
if printf '%s\n' "$gx_enable" | grep -Fq 'gdsc_toggle_logic'; then
	fail 'SM8350 GX power-on unexpectedly toggles the GDSC'
fi
require_text "$gdsc_disable" \
	'gdsc_toggle_logic(sc, GDSC_OFF, domain->synced_poweroff)' \
	'GX rollback power-off path'

cx_line=$(line_once "$gmu_resume" 'pm_runtime_get_sync(gmu->dev);' \
	'GMU/CX runtime-PM get')
gx_line=$(line_once "$gmu_resume" 'pm_runtime_get_sync(gmu->gxpd);' \
	'GX runtime-PM get')
core_rate_line=$(line_once "$gmu_resume" \
	'clk_set_rate(gmu->core_clk, 200000000);' \
	'GMU core-clock rate')
hub_rate_line=$(line_once "$gmu_resume" \
	'clk_set_rate(gmu->hub_clk,' 'GMU hub-clock rate')
bulk_line=$(line_once "$gmu_resume" \
	'clk_bulk_prepare_enable(gmu->nr_clocks, gmu->clocks);' \
	'GMU bulk clock enable')
secure_line=$(line_once "$gmu_resume" \
	'ret = a6xx_gmu_secure_init(a6xx_gpu);' 'GMU secure init')
irq_line=$(line_once "$gmu_resume" 'enable_irq(gmu->gmu_irq);' \
	'GMU IRQ enable')
firmware_line=$(line_once "$gmu_resume" \
	'ret = a6xx_gmu_fw_start(gmu, status);' 'GMU firmware start')
hfi_line=$(line_once "$gmu_resume" \
	'ret = a6xx_hfi_start(gmu, status);' 'GMU HFI start')
if [ "$cx_line" -ge "$gx_line" ] ||
	[ "$gx_line" -ge "$core_rate_line" ] ||
	[ "$core_rate_line" -ge "$hub_rate_line" ] ||
	[ "$hub_rate_line" -ge "$bulk_line" ] ||
	[ "$bulk_line" -ge "$secure_line" ] ||
	[ "$secure_line" -ge "$irq_line" ] ||
	[ "$irq_line" -ge "$firmware_line" ] ||
	[ "$firmware_line" -ge "$hfi_line" ]
then
	fail 'GMU clock-preparation order changed'
fi

require_text "$bulk_prepare_enable" \
	'ret = clk_bulk_prepare(num_clks, clks);' \
	'bulk clock prepare'
require_text "$bulk_prepare_enable" \
	'ret = clk_bulk_enable(num_clks, clks);' \
	'bulk clock enable'
require_text "$bulk_prepare_enable" \
	'clk_bulk_unprepare(num_clks, clks);' \
	'bulk enable-failure unwind'
require_text "$bulk_disable_unprepare" \
	'clk_bulk_disable(num_clks, clks);' \
	'bulk clock disable'
require_text "$bulk_disable_unprepare" \
	'clk_bulk_unprepare(num_clks, clks);' \
	'bulk clock unprepare'
require_text "$bulk_enable" \
	'clk_bulk_disable(i, clks);' \
	'partial bulk-enable rollback'
require_text "$set_rate" 'return ret;' 'clock-rate error propagation'

for candidate_operation in \
	'clk_get_rate(gmu->core_clk)' \
	'clk_get_rate(gmu->hub_clk)' \
	'clk_bulk_disable_unprepare(gmu->nr_clocks, gmu->clocks)' \
	'pm_runtime_put_sync_suspend(gmu->gxpd)' \
	'pm_runtime_put_sync_suspend(gmu->dev)'
do
	: "$candidate_operation"
done

printf '%s\n' \
	'PASS A660 GMU clock-preparation boundary is v10-dependent, exact-SM8350, seven-clock, GX-no-op-aware, bulk-unwind-capable, rollback-defined, and before secure init, MMIO, IRQ, firmware start, or HFI'
