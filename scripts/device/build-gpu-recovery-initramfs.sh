#!/bin/sh
set -eu

base=${1:?usage: build-gpu-recovery-initramfs.sh BASE FIRMWARE_ROOT OUTPUT}
firmware=${2:?missing firmware root}
output=${3:?missing output}
verify=$(dirname "$0")/verify-a660-firmware.sh
epoch=1681862400

[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = \
	bad228341c7a69de46444642f2519ad9c2f51e333f6c8e19660fce12eb000cb5 ]
sh "$verify" "$firmware"

stage=$(mktemp -d)
check=$(mktemp -d)
trap 'rm -rf "$stage" "$check"' EXIT
gzip -dc "$base" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
[ -z "$(find "$stage/lib/firmware" -type f -print -quit)" ]
init_hash=$(sha256sum "$stage/init" | cut -d ' ' -f 1)

install -D -m 0644 "$firmware/qcom/a660_sqe.fw" "$stage/lib/firmware/qcom/a660_sqe.fw"
install -D -m 0644 "$firmware/qcom/a660_gmu.bin" "$stage/lib/firmware/qcom/a660_gmu.bin"
install -D -m 0644 "$firmware/qcom/sm8350/a660_zap.mbn" \
	"$stage/lib/firmware/qcom/sm8350/a660_zap.mbn"

find "$stage" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$stage" && find . -mindepth 1 -print0 | sort -z | \
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) | gzip -n >"$output.tmp"
mv "$output.tmp" "$output"

gzip -dc "$output" | (cd "$check" && cpio -idm --quiet --no-absolute-filenames)
[ "$(sha256sum "$check/init" | cut -d ' ' -f 1)" = "$init_hash" ]
[ "$(find "$check/lib/firmware" -type f | wc -l)" -eq 3 ]
sh "$verify" "$check/lib/firmware"
gzip -t "$output"
sha256sum "$output"
echo 'PASS deterministic recovery initramfs with pinned A660 firmware'
