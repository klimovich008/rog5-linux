#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-adreno-smmu-dependency-contract.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable Adreno SMMU dependency verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	58d28a520a21e21f55703ae968d6e45c6b7750e6a2d3138dcb6cafe2bc6d0a3c \
	580bcc9326837da0607e45843f4906694c28a0a5b68ca9297bc516747704d55f \
	a8ba34c18e75740495d64a15ad6ff94fec4265814f96d7068b9f4c5e45eb3663 \
	9c3282286063d71ef9865fd276de5de48f924c8b1dd3404de5b4e21dda62bdb1 \
	39efbb61d7cc9a59e13f7e1ee9ebab6357d6fc4cbc981e8a89a28aa976b33755 \
	'qcom,sm8350-smmu-500' \
	'qcom,adreno-smmu' \
	'reg = <0 0x03da0000 0 0x20000>;' \
	'#iommu-cells = <2>;' \
	'#global-interrupts = <2>;' \
	'hlos1_vote_gpu_smmu' \
	'power-domains = <&gpucc GPU_CX_GDSC>;' \
	'dma-coherent;' \
	'devm_clk_bulk_get_all' \
	'clk_bulk_prepare_enable' \
	'pm_runtime_set_autosuspend_delay(smmu->dev, 20)' \
	'devm_request_irq' \
	'devm_request_threaded_irq' \
	'status = "disabled";' \
	'request_firmware'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL dependency verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot|adb|/dev/(block|disk)|[[:space:]]mount[[:space:]]|[[:space:]]dd[[:space:]]' \
	"$verifier"
then
	echo 'FAIL dependency verifier contains a device-control path' >&2
	exit 1
fi

if [ -n "${SOURCE_DIR:-}" ]; then
	"$verifier" "$SOURCE_DIR"
fi

echo 'PASS exact Linux 7.1.4 Adreno SMMU dependency graph is source-audited'
