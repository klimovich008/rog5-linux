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

systemd_diagnostic=${ROG5_SYSTEMD_DIAGNOSTIC:-0}
case $systemd_diagnostic in
	0|1) ;;
	*) exit 1 ;;
esac

qcom_cc_probe_trace=${ROG5_QCOM_CC_PROBE_TRACE:-0}
case $qcom_cc_probe_trace in
	0|1) ;;
	*) exit 1 ;;
esac

ccf_register_trace=${ROG5_CCF_REGISTER_TRACE:-0}
case $ccf_register_trace in
	0|1) ;;
	*) exit 1 ;;
esac

recovery_timeout=${ROG5_RECOVERY_TIMEOUT:-600}
case $recovery_timeout in
	*[!0-9]*|'') exit 1 ;;
esac
if [ "$recovery_timeout" -lt 60 ] || [ "$recovery_timeout" -gt 900 ]; then
	exit 1
fi

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

command_line='console=ttyMSM0,115200n8 rdinit=/init panic=10 oops=panic loglevel=8 ignore_loglevel printk.always_kmsg_dump=Y rog5.netroot=1'
for argument in $(cat "$proc_cmdline"); do
	case $argument in
		ramoops.*=*) command_line="$command_line $argument" ;;
	esac
done
command_line="$command_line rog5.recovery_timeout=$recovery_timeout"
if [ "$systemd_diagnostic" = 1 ]; then
	command_line="$command_line systemd.mask=systemd-udev-trigger.service"
	command_line="$command_line systemd.mask=systemd-modules-load.service"
fi
if [ "$qcom_cc_probe_trace" = 1 ]; then
	command_line="$command_line rog5_qcom_cc_probe_trace=1"
fi
if [ "$ccf_register_trace" = 1 ]; then
	command_line="$command_line rog5_ccf_register_trace=1"
fi

[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -c '^rog5\.netroot=1$')" -eq 1 ]
[ "$(printf '%s\n' "$command_line" |
	grep -o 'ramoops\.[a-z_]*=' | sort -u | wc -l)" -eq 7 ]
trace_count=$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	awk '$0 == "rog5_qcom_cc_probe_trace=1" { count++ }
		END { print count + 0 }')
[ "$trace_count" -eq "$qcom_cc_probe_trace" ]
ccf_trace_count=$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	awk '$0 == "rog5_ccf_register_trace=1" { count++ }
		END { print count + 0 }')
[ "$ccf_trace_count" -eq "$ccf_register_trace" ]

kexec -c -l "$image" \
	--dtb="$dtb" \
	--initrd="$initramfs" \
	--command-line="$command_line"

echo 'PASS mainline network-root payload loaded; run kexec -e only during an attended test'
