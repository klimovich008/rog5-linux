#!/bin/sh
set -eu

build_a=${1:?usage: compare-mainline-gpucc-parent-diagnostic-builds.sh BUILD_A BUILD_B}
build_b=${2:?missing second build directory}
[ "$(stat -Lc '%d:%i' "$build_a")" != "$(stat -Lc '%d:%i' "$build_b")" ] || {
	echo 'FAIL build directories must be distinct' >&2
	exit 1
}

for file in \
	.config \
	vmlinux \
	System.map \
	Module.symvers \
	modules.order \
	modules.builtin \
	arch/arm64/boot/Image \
	arch/arm64/boot/Image.gz \
	drivers/clk/clk.o \
	drivers/clk/qcom/common.o \
	drivers/clk/qcom/clk-regmap.o \
	drivers/clk/qcom/clk-rcg2.o \
	drivers/clk/qcom/gpucc-sm8350.ko \
	modules.tar.gz \
	build-meta.txt
do
	[ -s "$build_a/$file" ] && [ -s "$build_b/$file" ]
	cmp -s "$build_a/$file" "$build_b/$file" || {
		echo "FAIL GPUCC diagnostic clean-build mismatch: $file" >&2
		exit 1
	}
done

echo 'PASS two clean GPUCC diagnostic builds are byte-identical through BTF, objects, symbols, modules, and metadata'
