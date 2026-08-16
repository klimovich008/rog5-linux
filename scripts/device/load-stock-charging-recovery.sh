#!/bin/sh
set -eu

payload=${PAYLOAD:-/opt/rog5-stock-charging-recovery}
sys_devices=${SYS_DEVICES:-/sys/devices}
image=$payload/Image
dtb=$payload/board.dtb
initramfs=$payload/initramfs.cpio.gz
cmdline=$payload/cmdline
manifest=$payload/SHA256SUMS

[ "$(wc -l <"$manifest")" -eq 4 ]
actual_names=$(awk '{ print $2 }' "$manifest" | LC_ALL=C sort)
expected_names=$(printf '%s\n' Image board.dtb cmdline initramfs.cpio.gz)
[ "$actual_names" = "$expected_names" ]
(cd "$payload" && sha256sum -c SHA256SUMS)
gzip -t "$initramfs"

[ "$(wc -l <"$cmdline")" -eq 1 ]
! grep -q "$(printf '\r')" "$cmdline"
LC_ALL=C grep -Eq '^[ -~]+$' "$cmdline"
command_line=$(cat "$cmdline")
for required in \
	console=ttyMSM0,115200n8 \
	androidboot.hardware=qcom \
	androidboot.usbcontroller=a600000.dwc3 \
	service_locator.enable=1 \
	androidboot.mode=charger \
	rdinit=/init \
	panic=10 \
	oops=panic; do
	[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
		grep -Fxc "$required")" -eq 1 ]
done
[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -c '^androidboot\.mode=')" -eq 1 ]
! printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -Eq '^(androidboot\.force_normal_boot=1|root=|init=)'

control_count=0
# Sysfs paths cannot contain whitespace.
# shellcheck disable=SC2044
for file in $(find "$sys_devices" -type f -name disable 2>/dev/null); do
	parent=${file%/disable}
	driver=$(basename "$(readlink -f "$parent/driver" 2>/dev/null)")
	[ "$driver" = hh-watchdog ] || continue
	[ -r "$parent/of_node/compatible" ] || continue
	tr '\000' '\n' <"$parent/of_node/compatible" |
		grep -qx 'qcom,hh-watchdog' || continue
	echo 1 >"$file"
	[ "$(cat "$file")" = 1 ]
	control_count=$((control_count + 1))
done
[ "$control_count" -eq 1 ]
! dmesg | grep -q 'Failed to deactivate secure wdog'

kexec -c -l "$image" \
	--dtb="$dtb" \
	--initrd="$initramfs" \
	--command-line="$command_line"

echo 'PASS stock charging recovery loaded; run kexec -e only during the bounded charging rescue'
