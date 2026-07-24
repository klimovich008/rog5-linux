#!/bin/sh
set -eu

build_a=${1:?usage: compare-asus-kexec-stage-builds.sh BUILD_ROOT_A BUILD_ROOT_B}
build_b=${2:?missing second build root}
[ "$(stat -Lc '%d:%i' "$build_a")" != "$(stat -Lc '%d:%i' "$build_b")" ] || {
	echo 'FAIL build roots must be distinct' >&2
	exit 1
}

for file in \
	rog5-kexec-stage-initramfs.cpio.gz \
	output/.config \
	output/build-meta.txt \
	output/arch/arm64/boot/Image; do
	[ -s "$build_a/$file" ] && [ -s "$build_b/$file" ]
	cmp "$build_a/$file" "$build_b/$file" || {
		echo "FAIL clean wrapper-build mismatch: $file" >&2
		exit 1
	}
done

python3 - "$build_a/output/arch/arm64/boot/Image" \
	"$build_a/rog5-kexec-stage-initramfs.cpio.gz" <<'PY'
import sys

image = open(sys.argv[1], "rb").read()
initramfs = open(sys.argv[2], "rb").read()
if image.count(initramfs) != 1:
    raise SystemExit("embedded initramfs count is not one")
PY

echo 'PASS two clean ASUS kexec-wrapper builds are byte-identical'
