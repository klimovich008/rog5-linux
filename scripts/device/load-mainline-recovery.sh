#!/bin/sh
set -eu

payload=${PAYLOAD:-/opt/rog5-recovery}
sys_devices=${SYS_DEVICES:-/sys/devices}
proc_cmdline=${PROC_CMDLINE:-/proc/cmdline}
image=$payload/Image
dtb=$payload/board.dtb
initramfs=$payload/initramfs.cpio.gz
manifest=$payload/SHA256SUMS

[ -r "$manifest" ]
(cd "$payload" && sha256sum -c SHA256SUMS)
gzip -t "$initramfs"

control_count=0
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

recovery_timeout=${ROG5_RECOVERY_TIMEOUT:-}
case $recovery_timeout in
	''|*[!0-9]*) [ -z "$recovery_timeout" ] || exit 1 ;;
esac
if [ -n "$recovery_timeout" ] &&
	{ [ "$recovery_timeout" -lt 30 ] || [ "$recovery_timeout" -gt 900 ]; }; then
	exit 1
fi

command_line='console=ttyMSM0,115200n8 rdinit=/init panic=10 oops=panic loglevel=8 ignore_loglevel initcall_debug printk.always_kmsg_dump=Y dyndbg="func deferred_probe_work_func +p"'
for argument in $(cat "$proc_cmdline"); do
	case $argument in
		rog5.recovery_timeout=*)
			[ -n "$recovery_timeout" ] ||
				command_line="$command_line $argument"
			;;
		rog5.recovery_cidr=*|rog5.recovery_gateway=*|ramoops.*=*)
			command_line="$command_line $argument"
			;;
	esac
done
[ -z "$recovery_timeout" ] ||
	command_line="$command_line rog5.recovery_timeout=$recovery_timeout"

[ "$(printf '%s\n' "$command_line" |
	grep -o 'ramoops\.[a-z_]*=' | sort -u | wc -l)" -eq 7 ]

kexec -c -l "$image" \
	--dtb="$dtb" \
	--initrd="$initramfs" \
	--command-line="$command_line"

echo 'PASS mainline recovery payload loaded; run kexec -e only during an attended test'
