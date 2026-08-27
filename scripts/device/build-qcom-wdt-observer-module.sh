#!/bin/sh
set -eu

[ "$#" -eq 3 ] || {
	echo 'usage: build-qcom-wdt-observer-module.sh LINUX_SOURCE KERNEL_OUTPUT MODULE_OUTPUT' >&2
	exit 1
}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
source_dir=$(realpath -e "$1")
kernel_output=$(realpath -e "$2")
module_output=$(realpath -m "$3")
observer=$repo/tools/qcom_wdt_observer
expected_commit=359318de534f196c1281de7195fbf5868c6f7333
expected_release=7.1.4-g359318de534f
expected_config=6329b42fac5876d3f42557802bd530ba2c077aa73c4543f0bbc37ea65902eeb4
expected_symvers=d897132b20f99921f445f637fee62724dfb1a5a20b2f8761dc03ef367e2000d8
expected_vmlinux=4a539ba93d86153e05118d15899084832ad95d4426ee9608781ebf0dce8dc96d
expected_builder=bdb4bbda79ab38a55c72d23b269f5c3f5cb14d153e373ce50932c17538e9ccaf
expected_source=891b579eda88a3bd7a75cb3d4df79fe2d3cca51f4579e0927c2696733710b1a0
expected_makefile=9702cb94d9baa70c500918d5f816296085cd7e53e14d80288a1cf63b37412695
expected_module=b06271c62e22292e043b082c3c5f2da46f8d98f36f3521c16ec389dcb40036d1
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04

fail() { echo "FAIL $*" >&2; exit 1; }
for command in git install llvm-readelf modinfo podman realpath sha256sum; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] &&
	[ -z "$(git -C "$source_dir" status --porcelain)" ] || fail 'source changed'
[ "$(cat "$kernel_output/include/config/kernel.release")" = "$expected_release" ] ||
	fail 'kernel release changed'
[ "$(sha256sum "$kernel_output/.config" | cut -d ' ' -f 1)" = "$expected_config" ] ||
	fail 'running kernel config changed'
[ "$(sha256sum "$kernel_output/Module.symvers" | cut -d ' ' -f 1)" = "$expected_symvers" ] ||
	fail 'Module.symvers changed'
[ "$(sha256sum "$kernel_output/vmlinux" | cut -d ' ' -f 1)" = "$expected_vmlinux" ] ||
	fail 'running vmlinux changed'
[ "$(sha256sum "$observer/rog5-qcom-wdt-observer.c" | cut -d ' ' -f 1)" = "$expected_source" ] &&
	[ "$(sha256sum "$observer/Makefile" | cut -d ' ' -f 1)" = "$expected_makefile" ] ||
	fail 'observer source changed'
[ "$(podman image inspect "$builder_image" --format '{{.Id}}')" = "$expected_builder" ] ||
	fail 'exact Clang 18 builder changed'
[ ! -e "$module_output" ] && [ ! -L "$module_output" ] || fail 'output exists'

install -d -m 0700 "$module_output"
install -m 0644 "$observer/rog5-qcom-wdt-observer.c" "$observer/Makefile" "$module_output/"
export KBUILD_BUILD_USER=rog5-linux KBUILD_BUILD_HOST=rog5-builder KBUILD_BUILD_VERSION=1
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s --format=%cD 7a5cef0db4795d9d453a12e0f61b5b7634fc4d40)
export KBUILD_BUILD_TIMESTAMP
debug_flags="-fdebug-prefix-map=$source_dir=/usr/src/rog5-linux -fdebug-prefix-map=$kernel_output=/usr/src/rog5-linux-build -fdebug-prefix-map=$module_output=/usr/src/rog5-linux/drivers/watchdog -fdebug-compilation-dir=/usr/src/rog5-linux-build"
podman run --rm --userns=keep-id -e KBUILD_BUILD_USER -e KBUILD_BUILD_HOST \
	-e KBUILD_BUILD_VERSION -e KBUILD_BUILD_TIMESTAMP -e KCFLAGS="$debug_flags" \
	-e KAFLAGS="$debug_flags" -e CC_COMPAT="clang $debug_flags" \
	-v "$source_dir:$source_dir:ro" -v "$kernel_output:$kernel_output:ro" \
	-v "$module_output:$module_output:rw" -w "$source_dir" "$builder_image" \
	make -s O="$kernel_output" ARCH=arm64 LLVM=1 M="$module_output" modules

module=$module_output/rog5-qcom-wdt-observer.ko
[ "$(modinfo -F vermagic "$module" | awk '{print $1}')" = "$expected_release" ] &&
	[ "$(sha256sum "$module" | cut -d ' ' -f 1)" = "$expected_module" ] ||
	fail 'observer module identity changed'
llvm-readelf -S "$module" | grep -q '[.]BTF' || fail 'observer lacks running BTF ABI'
llvm-readelf -S "$module" | grep -Eq '[.]gnu[.]linkonce[.]this_module.*000500 ' ||
	fail 'observer struct module size changed'
[ -z "$(git -C "$source_dir" status --porcelain)" ] || fail 'build dirtied source'
sha256sum "$module"
echo 'PASS read-only watchdog observer module built against exact running ABI'
