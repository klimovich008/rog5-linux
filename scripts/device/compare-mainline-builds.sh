#!/bin/sh
set -eu

build_a=${1:?usage: compare-mainline-builds.sh BUILD_A BUILD_B}
build_b=${2:?missing second build directory}
[ -d "$build_a" ] || { echo "FAIL missing build A directory" >&2; exit 1; }
[ -d "$build_b" ] || { echo "FAIL missing build B directory" >&2; exit 1; }
[ "$(stat -Lc '%d:%i' "$build_a")" != "$(stat -Lc '%d:%i' "$build_b")" ] || {
	echo 'FAIL build directories must be distinct' >&2
	exit 1
}

files='
.config
drivers/gpu/drm/msm/generated/a6xx.xml.h
arch/arm64/boot/Image
arch/arm64/boot/Image.gz
modules.tar.gz
build-meta.txt
arch/arm64/boot/dts/qcom/sm8350-hdk.dtb
arch/arm64/boot/dts/qcom/sm8350-microsoft-surface-duo2.dtb
arch/arm64/boot/dts/qcom/sm8350-mtp.dtb
arch/arm64/boot/dts/qcom/sm8350-sony-xperia-sagami-pdx214.dtb
arch/arm64/boot/dts/qcom/sm8350-sony-xperia-sagami-pdx215.dtb
asus-dt/sm8350-asus-rog-phone5.dtb
asus-dt/sm8350-asus-rog-phone5-recovery.dtb
'

for file in $files; do
	[ -f "$build_a/$file" ] || { echo "FAIL missing build A $file" >&2; exit 1; }
	[ -f "$build_b/$file" ] || { echo "FAIL missing build B $file" >&2; exit 1; }
	cmp "$build_a/$file" "$build_b/$file" || {
		echo "FAIL clean-build mismatch: $file" >&2
		exit 1
	}
done

echo 'PASS clean mainline builds are byte-identical'
