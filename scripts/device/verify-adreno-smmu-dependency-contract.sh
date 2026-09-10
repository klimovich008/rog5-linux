#!/bin/sh
set -eu

source_dir=${1:?usage: verify-adreno-smmu-dependency-contract.sh PINNED_SOURCE}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92

dtsi=$source_dir/arch/arm64/boot/dts/qcom/sm8350.dtsi
smmu=$source_dir/drivers/iommu/arm/arm-smmu/arm-smmu.c
qcom_smmu=$source_dir/drivers/iommu/arm/arm-smmu/arm-smmu-qcom.c
binding=$source_dir/Documentation/devicetree/bindings/iommu/arm,smmu.yaml
gpucc=$source_dir/drivers/clk/qcom/gpucc-sm8350.c
recovery=$repo/dts/qcom/sm8350-asus-rog-phone5-recovery.dtso

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ]
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]

check_hash() {
	file=$1
	expected=$2
	[ -f "$file" ] && [ ! -L "$file" ]
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ]
}

check_hash "$dtsi" \
	58d28a520a21e21f55703ae968d6e45c6b7750e6a2d3138dcb6cafe2bc6d0a3c
check_hash "$smmu" \
	580bcc9326837da0607e45843f4906694c28a0a5b68ca9297bc516747704d55f
check_hash "$qcom_smmu" \
	a8ba34c18e75740495d64a15ad6ff94fec4265814f96d7068b9f4c5e45eb3663
check_hash "$binding" \
	9c3282286063d71ef9865fd276de5de48f924c8b1dd3404de5b4e21dda62bdb1
check_hash "$gpucc" \
	39efbb61d7cc9a59e13f7e1ee9ebab6357d6fc4cbc981e8a89a28aa976b33755

smmu_block=$(sed -n \
	'/adreno_smmu: iommu@3da0000 {/,/^[[:space:]]*};/p' "$dtsi")
[ -n "$smmu_block" ]
for property in \
	'compatible = "qcom,sm8350-smmu-500", "qcom,adreno-smmu",' \
	'"qcom,smmu-500", "arm,mmu-500";' \
	'reg = <0 0x03da0000 0 0x20000>;' \
	'#iommu-cells = <2>;' \
	'#global-interrupts = <2>;' \
	'power-domains = <&gpucc GPU_CX_GDSC>;' \
	'dma-coherent;'
do
	printf '%s\n' "$smmu_block" | grep -Fq "$property"
done
[ "$(printf '%s\n' "$smmu_block" | grep -o 'GIC_SPI' | wc -l)" -eq 12 ]
[ "$(printf '%s\n' "$smmu_block" |
	sed -n '/^[[:space:]]*clocks = /,/;$/p' |
	grep -o '<&' | wc -l)" -eq 7 ]
clock_names=$(printf '%s\n' "$smmu_block" |
	sed -n '/^[[:space:]]*clock-names = /,/;$/p' |
	sed 's/.*= //' | tr -d '";,' | tr '\n\t' '  ' |
	tr -s ' ' | sed 's/^ //; s/ $//')
[ "$clock_names" = \
	'bus iface ahb hlos1_vote_gpu_smmu cx_gmu hub_cx_int hub_aon' ]
if printf '%s\n' "$smmu_block" |
	grep -Eq 'status[[:space:]]*=|firmware|memory-region|interconnect|supply|regulator'
then
	echo 'FAIL upstream Adreno SMMU node has an unreviewed property' >&2
	exit 1
fi

gpu_block=$(sed -n '/gpu: gpu@3d00000 {/,/gpu_zap_shader:/p' "$dtsi")
printf '%s\n' "$gpu_block" | grep -Fq 'status = "disabled";'
printf '%s\n' "$gpu_block" |
	grep -Fq 'iommus = <&adreno_smmu 0 0x400>, <&adreno_smmu 1 0x400>;'
gmu_block=$(sed -n '/gmu: gmu@3d6a000 {/,/gmu_opp_table:/p' "$dtsi")
printf '%s\n' "$gmu_block" | grep -Fq 'iommus = <&adreno_smmu 5 0x400>;'
if printf '%s\n' "$gmu_block" | grep -q 'status = '; then
	echo 'FAIL upstream GMU status assumption changed' >&2
	exit 1
fi

for label in gpucc gpu gmu adreno_smmu; do
	[ "$(grep -c "^&$label {" "$recovery")" -eq 1 ]
done
[ "$(grep -c 'status = "disabled";' "$recovery")" -eq 5 ]

grep -Fq \
	'{ .compatible = "qcom,sm8350-smmu-500", .data = &qcom_smmu_500_impl0_data },' \
	"$qcom_smmu"
grep -Fq '.name			= "arm-smmu",' "$smmu"
for behavior in \
	'devm_clk_bulk_get_all(dev, &smmu->clks);' \
	'clk_bulk_prepare_enable(smmu->num_clks, smmu->clks);' \
	'devm_request_irq(dev, irq, global_fault, IRQF_SHARED,' \
	'devm_request_threaded_irq(smmu->dev, irq, NULL,' \
	'iommu_device_register(&smmu->iommu, &arm_smmu_ops,' \
	'pm_runtime_set_active(dev);' \
	'pm_runtime_enable(dev);' \
	'pm_runtime_set_autosuspend_delay(smmu->dev, 20);'
do
	grep -Fq "$behavior" "$smmu"
done

probe=$(sed -n \
	'/^static int arm_smmu_device_probe(/,/^}$/p' "$smmu" | nl -ba)
impl_line=$(printf '%s\n' "$probe" |
	awk '/arm_smmu_impl_init\(smmu\)/ { print $1; exit }')
clocks_line=$(printf '%s\n' "$probe" |
	awk '/devm_clk_bulk_get_all/ { print $1; exit }')
enable_line=$(printf '%s\n' "$probe" |
	awk '/clk_bulk_prepare_enable/ { print $1; exit }')
register_line=$(printf '%s\n' "$probe" |
	awk '/iommu_device_register/ { print $1; exit }')
runtime_line=$(printf '%s\n' "$probe" |
	awk '/pm_runtime_set_active/ { print $1; exit }')
[ "$impl_line" -lt "$clocks_line" ]
[ "$clocks_line" -lt "$enable_line" ]
[ "$enable_line" -lt "$register_line" ]
[ "$register_line" -lt "$runtime_line" ]

binding_block=$(sed -n \
	'/^[[:space:]]*- if:$/,/^[[:space:]]*- if:$/p' "$binding" |
	awk '
		/qcom,sm8350-smmu-500/ { keep = 1 }
		keep { print }
		keep && /maxItems: 7/ { exit }
	')
for name in \
	bus iface ahb hlos1_vote_gpu_smmu cx_gmu hub_cx_int hub_aon
do
	printf '%s\n' "$binding_block" | grep -Fq -- "- const: $name"
done
printf '%s\n' "$binding_block" | grep -Fq 'minItems: 7'
printf '%s\n' "$binding_block" | grep -Fq 'maxItems: 7'

if grep -Fq request_firmware "$smmu" "$qcom_smmu"; then
	echo 'FAIL ARM SMMU source acquired a firmware path' >&2
	exit 1
fi
grep -Fq '.gdscr = 0x106c,' "$gpucc"
grep -Fq '.flags = VOTABLE,' "$gpucc"

echo 'PASS pinned Linux 7.1.4 graph: GPUCC plus Adreno SMMU has seven clocks, one CX domain, twelve IRQs, runtime PM, and no firmware path'
