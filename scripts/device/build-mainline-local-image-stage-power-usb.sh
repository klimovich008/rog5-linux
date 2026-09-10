#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
builder=$repo/scripts/device/build-mainline-persistent-root.sh
source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4-local-image-write}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4-local-image-stage-power-usb}

SOURCE_DIR="$source_dir" \
OUTPUT_DIR="$output_dir" \
BASE_FRAGMENT="$repo/configs/kernel/rog5-mainline.fragment" \
DISCOVERY_FRAGMENT="$repo/configs/kernel/rog5-ufs-deferred-probe.fragment" \
ROOT_FRAGMENT="$repo/configs/kernel/rog5-persistent-root.fragment" \
WRITE_FRAGMENT="$repo/configs/kernel/rog5-ufs-local-write.fragment" \
POWER_USB_FRAGMENT="$repo/configs/kernel/rog5-persistent-root-power-usb.fragment" \
UFS_STORAGE_MODE=local-write \
POWER_USB_MODULES=1 \
LINUX_BASE_COMMIT=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 \
LINUX_COMMIT=359318de534f196c1281de7195fbf5868c6f7333 \
LINUX_TREE=8528fcd29e4ad19cf944f79c2ebb3438feee5e0b \
EXPECTED_RELEASE=7.1.4-g359318de534f \
	"$builder"

for symbol in \
	CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y \
	CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=y \
	CONFIG_NVMEM_SPMI_SDAM=y \
	CONFIG_NVMEM_REBOOT_MODE=y; do
	grep -Fqx "$symbol" "$output_dir/.config" || {
		echo "FAIL local-image stage config lacks $symbol" >&2
		exit 1
	}
done
[ "$(find "$output_dir/power-usb-modules" -type f -name '*.ko' | wc -l)" -eq 15 ]
[ "$(find "$output_dir/deferred-ufs-modules" -type f -name '*.ko' | wc -l)" -eq 4 ]

echo 'PASS local-image stage kernel combines bounded UFS write, charging, and reboot-mode support'
