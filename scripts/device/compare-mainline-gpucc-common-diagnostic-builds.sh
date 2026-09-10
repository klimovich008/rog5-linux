#!/bin/sh
set -eu

build_a=${1:?usage: compare-mainline-gpucc-common-diagnostic-builds.sh BUILD_A BUILD_B}
build_b=${2:?missing second build directory}
[ "$(stat -Lc '%d:%i' "$build_a")" != "$(stat -Lc '%d:%i' "$build_b")" ] || {
	echo 'FAIL build directories must be distinct' >&2
	exit 1
}

for file in \
	.config \
	arch/arm64/boot/Image \
	arch/arm64/boot/Image.gz \
	drivers/clk/qcom/gpucc-sm8350.ko \
	modules.tar.gz \
	build-meta.txt
do
	[ -f "$build_a/$file" ] && [ -f "$build_b/$file" ]
	cmp "$build_a/$file" "$build_b/$file" || {
		echo "FAIL GPUCC/common-clock clean-build mismatch: $file" >&2
		exit 1
	}
done

echo 'PASS two clean GPUCC/common-clock diagnostic builds are byte-identical'
