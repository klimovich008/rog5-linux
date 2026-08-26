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
expected_config=6329b42fac5876d3f42557802bd530ba2c077aa73c4543f0bbc37ea65902eeb4
expected_symvers=d897132b20f99921f445f637fee62724dfb1a5a20b2f8761dc03ef367e2000d8
expected_vmlinux=4a539ba93d86153e05118d15899084832ad95d4426ee9608781ebf0dce8dc96d
expected_builder=bdb4bbda79ab38a55c72d23b269f5c3f5cb14d153e373ce50932c17538e9ccaf
expected_module=3fcea56eab46bc5ea006461e3c18c21875c046b7b12db3262bf8cd400f0e16c6
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04

fail() { echo "FAIL $*" >&2; exit 1; }
for command in git install llvm-readelf modinfo podman realpath sha256sum; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
source_dir=$(realpath -e "$source_dir")
kernel_output=$(realpath -e "$kernel_output")
module_output=$(realpath -m "$module_output")
[ -d "$source_dir/.git" ] && [ ! -L "$source_dir" ] || fail 'unsafe source'
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] &&
	[ -z "$(git -C "$source_dir" status --porcelain)" ] || fail 'source changed'
[ -f "$kernel_output/.config" ] && [ ! -L "$kernel_output" ] &&
	[ -f "$kernel_output/Module.symvers" ] &&
	[ "$(cat "$kernel_output/include/config/kernel.release")" = \
		"$expected_release" ] || fail 'unsafe kernel output'
grep -Fqx 'CONFIG_DEBUG_INFO_BTF_MODULES=y' "$kernel_output/.config"
grep -Fqx 'CONFIG_QCOM_WDT=m' "$kernel_output/.config"
[ "$(sha256sum "$kernel_output/.config" | cut -d ' ' -f 1)" = \
	"$expected_config" ] || fail 'running kernel config changed'
[ "$(sha256sum "$kernel_output/Module.symvers" | cut -d ' ' -f 1)" = \
	"$expected_symvers" ] || fail 'Module.symvers changed'
[ -f "$kernel_output/vmlinux" ] && [ ! -L "$kernel_output/vmlinux" ] &&
	[ "$(sha256sum "$kernel_output/vmlinux" | cut -d ' ' -f 1)" = \
	"$expected_vmlinux" ] || fail 'running vmlinux changed'
[ "$(podman image inspect "$builder_image" --format '{{.Id}}')" = \
	"$expected_builder" ] || fail 'exact Clang 18 builder changed'
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
debug_flags="-fdebug-prefix-map=$source_dir=/usr/src/rog5-linux -fdebug-prefix-map=$kernel_output=/usr/src/rog5-linux-build -fdebug-prefix-map=$module_output=/usr/src/rog5-linux/drivers/watchdog -fdebug-compilation-dir=/usr/src/rog5-linux-build"
podman run --rm --userns=keep-id \
	-e KBUILD_BUILD_USER -e KBUILD_BUILD_HOST -e KBUILD_BUILD_VERSION \
	-e KBUILD_BUILD_TIMESTAMP -e KCFLAGS="$debug_flags" \
	-e KAFLAGS="$debug_flags" -e CC_COMPAT="clang $debug_flags" \
	-v "$source_dir:$source_dir:ro" -v "$kernel_output:$kernel_output:ro" \
	-v "$module_output:$module_output:rw" -w "$source_dir" "$builder_image" \
	make -s O="$kernel_output" ARCH=arm64 LLVM=1 M="$module_output" modules

[ "$(modinfo -F vermagic "$module_output/qcom-wdt.ko" | awk '{print $1}')" = \
	"$expected_release" ] || fail 'watchdog module ABI changed'
[ "$(sha256sum "$module_output/qcom-wdt.ko" | cut -d ' ' -f 1)" = \
	"$expected_module" ] || fail 'watchdog module bytes changed'
llvm-readelf -S "$module_output/qcom-wdt.ko" | grep -q '[.]BTF' ||
	fail 'watchdog module lacks running-kernel BTF ABI'
llvm-readelf -S "$module_output/qcom-wdt.ko" |
	grep -Eq '[.]gnu[.]linkonce[.]this_module.*000500 ' ||
	fail 'watchdog module struct module size differs from the running kernel'
[ -z "$(git -C "$source_dir" status --porcelain)" ] || fail 'build dirtied source'
sha256sum "$module_output/qcom-wdt.ko"
echo 'PASS exact running-kernel QCOM watchdog module built outside the source tree'
