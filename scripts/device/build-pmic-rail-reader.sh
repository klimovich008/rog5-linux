#!/bin/sh
set -eu
out=${1:?usage: build-pmic-rail-reader.sh NEW_OUTPUT_DIRECTORY}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
mkdir "$out"
out=$(realpath "$out")
clang --target=aarch64-linux-gnu -fuse-ld=lld -Os -ffreestanding -fno-builtin \
 -fno-stack-protector -fno-pie -nostdlib -static -Wl,--build-id=none \
 -Wall -Wextra -Werror -Wl,-e,_start \
 "$repo/tools/pmic_rail_reader/rog5-pmic-rail-readonly.c" \
 -o "$out/rog5-pmic-rail-readonly"
readelf -h "$out/rog5-pmic-rail-readonly" | grep -q 'Machine:.*AArch64'
! readelf -l "$out/rog5-pmic-rail-readonly" | grep -q INTERP
! readelf -d "$out/rog5-pmic-rail-readonly" | grep -q NEEDED
sha256sum "$out/rog5-pmic-rail-readonly"
