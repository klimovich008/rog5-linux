#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
builder=$repo/scripts/device/build-mainline-persistent-root.sh
stage_builder=$repo/scripts/device/build-mainline-local-image-stage-power-usb.sh

sh -n "$builder" "$stage_builder"
grep -Fq 'if [ "$storage_mode" = local-write ] && [ "$power_usb_modules" -eq 1 ]; then' "$builder"
grep -Fq '"$root_fragment" "$write_fragment" "$power_usb_fragment"' "$builder"
for contract in \
	'UFS_STORAGE_MODE=local-write' \
	'POWER_USB_MODULES=1' \
	'LINUX_COMMIT=359318de534f196c1281de7195fbf5868c6f7333' \
	'EXPECTED_RELEASE=7.1.4-g359318de534f' \
	'CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=y' \
	'CONFIG_NVMEM_REBOOT_MODE=y' \
	"find \"\$output_dir/power-usb-modules\" -type f -name '*.ko'"; do
	grep -Fq "$contract" "$stage_builder"
done

echo 'PASS local-image stage build composes only bounded UFS write, charging, and reboot mode'
