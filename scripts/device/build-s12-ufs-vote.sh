#!/bin/sh
# Only this module is compiled. Source/config/vmlinux must remain unchanged.
set -eu
[ "$#" = 3 ] || { echo 'usage: build-s12-ufs-vote.sh SOURCE KERNEL_KIT NEW_OUTPUT' >&2; exit 1; }
source_dir=$(realpath "$1")
kit=$(realpath "$2")
output=$3
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
export GIT_OPTIONAL_LOCKS=0
expected=$(sed -n 's/^patched_commit=//p' "$kit/build-meta.txt")
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ "$(sha256sum "$kit/.config" | cut -d ' ' -f1)" = "$(awk '$2 == "/.config" {print $1}' "$kit/build-meta.txt")" ]
[ -x "$kit/tools/bpf/resolve_btfids/resolve_btfids" ]
# Rescue kernels may share the config but omit the server's built-in readback.
awk '$2 == "rpmh_read" { n++; if ($3 != "vmlinux" || $4 != "EXPORT_SYMBOL_GPL" || NF != 4) bad=1 }
     END { exit (n != 1 || bad) }' "$kit/Module.symvers" || {
	echo 'FAIL kernel kit lacks exact built-in rpmh_read; refusing compilation' >&2
	exit 1
}
before=$(sha256sum "$kit/.config" "$kit/vmlinux" "$kit/Module.symvers")
mkdir "$output"
output=$(realpath "$output")
cp "$repo/tools/s12_ufs_vote/Makefile" "$repo/tools/s12_ufs_vote/rog5-s12-ufs-vote.c" "$output/"
export KBUILD_BUILD_USER=rog5-linux KBUILD_BUILD_HOST=rog5-builder KBUILD_BUILD_VERSION=1
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s --format=%cD "$(sed -n 's/^base_commit=//p' "$kit/build-meta.txt")")
export KBUILD_BUILD_TIMESTAMP
export KCFLAGS="-fdebug-prefix-map=$source_dir=/usr/src/rog5-linux -fdebug-prefix-map=$output=/usr/src/rog5-s12-ufs-vote -fdebug-compilation-dir=/usr/src/rog5-linux-build"
export KAFLAGS=$KCFLAGS
make -C "$source_dir" O="$kit" M="$output" ARCH=arm64 LLVM=1 -j2 JOBS=1 modules
[ "$(sha256sum "$kit/.config" "$kit/vmlinux" "$kit/Module.symvers")" = "$before" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
module=$output/rog5-s12-ufs-vote.ko
[ "$(modinfo -F vermagic "$module" | awk '{print $1}')" = "$(cat "$kit/include/config/kernel.release")" ]
readelf -h "$module" | grep -q 'Machine:.*AArch64'
readelf -SW "$module" | grep -q '[.]BTF[[:space:]]'
sha256sum "$module"
echo 'PASS S12 query/mode/held-vote module; kernel and kit unchanged'
