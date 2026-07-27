#!/bin/sh
set -eu

build_a=${1:?usage: compare-mainline-a660-gmu-cx-runtime-pm-builds.sh BUILD_A BUILD_B}
build_b=${2:?missing second build directory}

[ -d "$build_a" ] || {
	echo "FAIL missing build A directory: $build_a" >&2
	exit 1
}
[ -d "$build_b" ] || {
	echo "FAIL missing build B directory: $build_b" >&2
	exit 1
}
[ "$(stat -Lc '%d:%i' "$build_a")" != \
	"$(stat -Lc '%d:%i' "$build_b")" ] || {
	echo 'FAIL build directories must be distinct' >&2
	exit 1
}

for file in \
	.config \
	arch/arm64/boot/Image \
	arch/arm64/boot/Image.gz \
	modules.tar.gz \
	Module.symvers \
	drivers/gpu/drm/msm/msm.ko \
	drivers/clk/qcom/gpucc-sm8350.ko \
	drivers/soc/qcom/mdt_loader.ko \
	build-meta.txt
do
	[ -f "$build_a/$file" ] || {
		echo "FAIL missing build A output: $file" >&2
		exit 1
	}
	[ -f "$build_b/$file" ] || {
		echo "FAIL missing build B output: $file" >&2
		exit 1
	}
	cmp "$build_a/$file" "$build_b/$file" || {
		echo "FAIL clean-build mismatch: $file" >&2
		exit 1
	}
done

echo 'PASS two clean A660 GMU/CX runtime-PM builds are byte-identical and the GMU/CX runtime-PM MSM module differs only from its accepted v8 predecessor'
