#!/bin/sh
set -eu

[ "$#" -eq 3 ] || {
	echo 'usage: build-tailscale-netfilter-kernel.sh SOURCE OUTPUT BASELINE_CONFIG' >&2
	exit 1
}
source_dir=$1
output_dir=$2
baseline=$3
repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
expected_baseline=6329b42fac5876d3f42557802bd530ba2c077aa73c4543f0bbc37ea65902eeb4
[ "$(sha256sum "$baseline" | cut -d ' ' -f 1)" = "$expected_baseline" ] || {
	echo 'FAIL deployed V10 baseline config changed' >&2
	exit 1
}
base=$(mktemp)
config_check=$(mktemp -d)
trap 'rm -f "$base"; rm -rf -- "$config_check"' EXIT HUP INT TERM
cp "$baseline" "$config_check/.config"
"$source_dir/scripts/config" --file "$config_check/.config" -e NF_CONNTRACK_MARK
make -s -C "$source_dir" O="$config_check" ARCH=arm64 LLVM=1 olddefconfig
delta=$("$source_dir/scripts/diffconfig" "$baseline" "$config_check/.config")
[ "$delta" = ' NF_CONNTRACK_MARK n -> y' ] || {
	printf 'FAIL prebuild config delta:\n%s\n' "$delta" >&2
	exit 1
}
cat "$repo/configs/kernel/rog5-mainline.fragment" \
	"$repo/configs/kernel/rog5-tailscale-netfilter.fragment" >"$base"
SOURCE_DIR="$source_dir" OUTPUT_DIR="$output_dir" BASE_FRAGMENT="$base" \
DISCOVERY_FRAGMENT="$repo/configs/kernel/rog5-ufs-deferred-probe.fragment" \
ROOT_FRAGMENT="$repo/configs/kernel/rog5-persistent-root.fragment" \
WRITE_FRAGMENT="$repo/configs/kernel/rog5-ufs-local-write.fragment" \
POWER_USB_FRAGMENT="$repo/configs/kernel/rog5-persistent-root-power-usb.fragment" \
UFS_STORAGE_MODE=local-write POWER_USB_MODULES=1 \
LINUX_BASE_COMMIT=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 \
LINUX_COMMIT=359318de534f196c1281de7195fbf5868c6f7333 \
LINUX_TREE=8528fcd29e4ad19cf944f79c2ebb3438feee5e0b \
EXPECTED_RELEASE=7.1.4-g359318de534f \
	"$repo/scripts/device/build-mainline-persistent-root.sh"
delta=$("$source_dir/scripts/diffconfig" "$baseline" "$output_dir/.config")
[ "$delta" = ' NF_CONNTRACK_MARK n -> y' ] || {
	printf 'FAIL unexpected kernel config delta:\n%s\n' "$delta" >&2
	exit 1
}
printf '%s\n' 'PASS clean netfilter kernel; sole config delta NF_CONNTRACK_MARK n -> y' \
	'INFO development output only; rebuild and verify the deployed power/UFS BTF closure before any candidate'
