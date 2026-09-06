#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
builder=$repo/scripts/device/build-mainline-persistent-root.sh
checker=$repo/scripts/device/check-persistent-root-power-usb-composition.sh
source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4-persistent-root-power-usb}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4-persistent-root-power-usb}

SOURCE_DIR="$source_dir" \
OUTPUT_DIR="$output_dir" \
BASE_FRAGMENT="$repo/configs/kernel/rog5-mainline.fragment" \
DISCOVERY_FRAGMENT="$repo/configs/kernel/rog5-ufs-deferred-probe.fragment" \
ROOT_FRAGMENT="$repo/configs/kernel/rog5-persistent-root.fragment" \
UFS_STORAGE_MODE=read-only \
POWER_USB_MODULES=1 \
POWER_USB_FRAGMENT="$repo/configs/kernel/rog5-persistent-root-power-usb.fragment" \
LINUX_BASE_COMMIT=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 \
LINUX_COMMIT=ae717d919f87b47ea9ed2173ea96660186b62a66 \
LINUX_TREE=939729426dcfa3bd72c75d81c0a675c6f0a193da \
EXPECTED_RELEASE=7.1.4-gae717d919f87 \
	"$builder"

ROG5_COMPOSED_SOURCE="$source_dir" \
ROG5_COMPOSED_CONFIG="$output_dir/.config" \
ROG5_COMPOSED_MODULE_ROOT="$output_dir/power-usb-modules" \
	"$checker"
