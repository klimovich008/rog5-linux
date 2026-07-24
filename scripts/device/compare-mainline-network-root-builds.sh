#!/bin/sh
set -eu

build_a=${1:?usage: compare-mainline-network-root-builds.sh BUILD_A BUILD_B}
build_b=${2:?missing second build directory}
[ "$(stat -Lc '%d:%i' "$build_a")" != "$(stat -Lc '%d:%i' "$build_b")" ] || {
	echo 'FAIL build directories must be distinct' >&2
	exit 1
}

for file in \
	.config \
	arch/arm64/boot/Image \
	arch/arm64/boot/Image.gz \
	modules.tar.gz \
	build-meta.txt; do
	[ -f "$build_a/$file" ] && [ -f "$build_b/$file" ]
	cmp "$build_a/$file" "$build_b/$file" || {
		echo "FAIL clean-build mismatch: $file" >&2
		exit 1
	}
done

echo 'PASS two clean network-root kernel builds are byte-identical'
