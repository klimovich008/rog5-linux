#!/bin/sh
set -eu

payload=${PAYLOAD:-/opt/rog5-recovery}
sys_devices=${SYS_DEVICES:-/sys/devices}
image=$payload/Image
dtb=$payload/board.dtb
initramfs=$payload/initramfs.cpio.gz
manifest=$payload/SHA256SUMS

[ -r "$manifest" ]
(cd "$payload" && sha256sum -c SHA256SUMS)
gzip -t "$initramfs"

recovery_timeout=${ROG5_RECOVERY_TIMEOUT:-600}
case $recovery_timeout in
	*[!0-9]*|'') exit 1 ;;
esac
if [ "$recovery_timeout" -lt 300 ] ||
	[ "$recovery_timeout" -gt 900 ]; then
	exit 1
fi

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

command_line='console=ttyMSM0,115200n8 rdinit=/init panic=10 oops=panic loglevel=8 ignore_loglevel printk.always_kmsg_dump=Y rog5.ufs_discovery=1 rog5.persistent_ro=1 rog5.p2_entry_diag=1 ramoops.mem_address=0x9b800000 ramoops.mem_size=0x400000 ramoops.record_size=0x100000 ramoops.console_size=0x300000 ramoops.pmsg_size=0 ramoops.ftrace_size=0 ramoops.dump_oops=1'
command_line="$command_line rog5.recovery_timeout=$recovery_timeout"

for required in \
	rog5.ufs_discovery=1 \
	rog5.persistent_ro=1 \
	rog5.p2_entry_diag=1; do
	[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
		grep -Fxc "$required")" -eq 1 ]
done
[ "$(printf '%s\n' "$command_line" |
	grep -o 'ramoops\.[a-z_]*=' | sort -u | wc -l)" -eq 7 ]
for required in \
	ramoops.mem_address=0x9b800000 \
	ramoops.mem_size=0x400000 \
	ramoops.record_size=0x100000 \
	ramoops.console_size=0x300000 \
	ramoops.pmsg_size=0 \
	ramoops.ftrace_size=0 \
	ramoops.dump_oops=1; do
	[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
		grep -Fxc "$required")" -eq 1 ]
done

kexec -c -l "$image" \
	--dtb="$dtb" \
	--initrd="$initramfs" \
	--command-line="$command_line"

echo 'PASS mainline read-only persistent-root payload loaded; early-entry diagnostic only; run kexec -e only during an attended test'
