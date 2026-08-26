#!/bin/sh
set -eu

[ "$#" -eq 3 ] || {
	echo 'usage: build-qcom-wdt-module.sh LINUX_SOURCE KERNEL_OUTPUT MODULE_OUTPUT' >&2
	exit 1
}
source_dir=$1
kernel_output=$2
module_output=$3
expected_commit=359318de534f196c1281de7195fbf5868c6f7333
expected_release=7.1.4-g359318de534f
expected_symvers=d897132b20f99921f445f637fee62724dfb1a5a20b2f8761dc03ef367e2000d8
expected_module=0b83b3b5aecc77390f82f2aabc1e24f3ef590e331986a7772a480f214a7b42c2

fail() { echo "FAIL $*" >&2; exit 1; }
for command in bc clang git install llvm-ar llvm-nm llvm-objcopy \
	llvm-readelf make modinfo sha256sum; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
[ -d "$source_dir/.git" ] && [ ! -L "$source_dir" ] || fail 'unsafe source'
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] &&
	[ -z "$(git -C "$source_dir" status --porcelain)" ] || fail 'source changed'
[ -f "$kernel_output/.config" ] && [ ! -L "$kernel_output" ] &&
	[ -f "$kernel_output/Module.symvers" ] &&
	[ "$(cat "$kernel_output/include/config/kernel.release")" = \
		"$expected_release" ] || fail 'unsafe kernel output'
grep -Fqx 'CONFIG_QCOM_WDT=m' "$kernel_output/.config"
[ "$(sha256sum "$kernel_output/Module.symvers" | cut -d ' ' -f 1)" = \
	"$expected_symvers" ] || fail 'Module.symvers changed'
[ ! -e "$module_output" ] && [ ! -L "$module_output" ] ||
	fail 'module output exists'

install -d -m 0700 "$module_output"
install -m 0644 "$source_dir/drivers/watchdog/qcom-wdt.c" \
	"$module_output/qcom-wdt.c"
cat >"$module_output/Makefile" <<'EOF'
obj-m += qcom-wdt.o
EOF

export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
export KBUILD_BUILD_VERSION=1
export PYTHONHASHSEED=0
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s --format=%cD \
	7a5cef0db4795d9d453a12e0f61b5b7634fc4d40)
export KBUILD_BUILD_TIMESTAMP
debug_flags="-fdebug-prefix-map=$source_dir=/usr/src/rog5-linux -fdebug-prefix-map=$module_output=/usr/src/rog5-linux/drivers/watchdog -fdebug-compilation-dir=/usr/src/rog5-linux-build"
export KCFLAGS=$debug_flags
export KAFLAGS=$debug_flags
export CC_COMPAT="clang $debug_flags"
make -s -C "$source_dir" O="$kernel_output" ARCH=arm64 LLVM=1 \
	M="$module_output" modules

[ "$(modinfo -F vermagic "$module_output/qcom-wdt.ko" | awk '{print $1}')" = \
	"$expected_release" ] || fail 'watchdog module ABI changed'
[ "$(sha256sum "$module_output/qcom-wdt.ko" | cut -d ' ' -f 1)" = \
	"$expected_module" ] || fail 'watchdog module bytes changed'
! llvm-readelf -S "$module_output/qcom-wdt.ko" | grep -q '[.]BTF' ||
	fail 'watchdog module unexpectedly carries build-specific BTF'
[ -z "$(git -C "$source_dir" status --porcelain)" ] || fail 'build dirtied source'
sha256sum "$module_output/qcom-wdt.ko"
echo 'PASS exact no-BTF QCOM watchdog module built outside the source tree'
