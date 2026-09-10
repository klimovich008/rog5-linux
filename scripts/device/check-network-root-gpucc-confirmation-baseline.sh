#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] || fail 'unexpected kernel'
[ "$(cat /proc/1/comm)" = systemd ] || fail 'PID 1 is not systemd'
[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
	fail 'systemd is not running'
[ "$(systemctl is-enabled systemd-udev-trigger.service 2>/dev/null ||
	true)" = masked-runtime ] || fail 'udev coldplug is not runtime-masked'
[ "$(systemctl is-enabled systemd-modules-load.service 2>/dev/null ||
	true)" = masked-runtime ] || fail 'module loading is not runtime-masked'

pid_file=/run/rog5-network-root-watchdog.pid
[ -s "$pid_file" ] || fail 'network-root watchdog is absent'
[ ! -e /run/rog5-network-root-watchdog.disarmed.pid ] ||
	fail 'network-root watchdog is already disarmed'
pid=$(cat "$pid_file")
case $pid in *[!0-9]*|'') fail 'invalid watchdog PID' ;; esac
[ "$pid" -ne 1 ] && [ -d "/proc/$pid" ] ||
	fail 'network-root watchdog process is absent'
[ "$(cat "/proc/$pid/comm")" = init ] ||
	fail 'network-root watchdog identity is unexpected'
[ "$(awk '{ print $4 }' "/proc/$pid/stat")" = 1 ] ||
	fail 'network-root watchdog is not reparented to PID 1'
[ "$(readlink "/proc/$pid/fd/8")" = /dev/kmsg ] ||
	fail 'network-root watchdog log descriptor is unexpected'
[ "$(readlink "/proc/$pid/fd/9")" = /proc/sysrq-trigger ] ||
	fail 'network-root watchdog reset descriptor is unexpected'

for parameter in \
	rog5_qcom_cc_probe_trace \
	rog5_ccf_register_trace \
	rog5_rcg2_parent_trace
do
	trace_prefix=$parameter=
	trace_count=$(tr ' ' '\n' </proc/cmdline |
		awk -v prefix="$trace_prefix" \
			'index($0, prefix) == 1 { count++ }
			END { print count + 0 }')
	[ "$trace_count" -eq 0 ] ||
		fail "$parameter is present on the command line"
	trace_path=/sys/module/kernel/parameters/$parameter
	[ -r "$trace_path" ] || fail "$parameter core parameter is absent"
	[ "$(cat "$trace_path")" = N ] ||
		fail "$parameter core parameter is enabled"
	[ "$(stat -c %a "$trace_path")" = 400 ] ||
		fail "$parameter core parameter became writable"
done

[ "$(findmnt -n -o FSTYPE /)" = overlay ] || fail 'root is not OverlayFS'
[ "$(findmnt -n -o SOURCE /.rog5/root-ro)" = 169.254.77.1:/ ] ||
	fail 'unexpected NFS lower source'
findmnt -n -o OPTIONS /.rog5/root-ro | tr ',' '\n' | grep -qx ro ||
	fail 'NFS lower is not read-only'
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	fail 'physical block device is present'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount is present'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	fail 'USB network carrier is down'
[ "$(ip -4 -o address show dev usb0 |
	awk '$4 == "169.254.77.2/30" { count++ }
		END { print count + 0 }')" -eq 1 ] ||
	fail 'USB network address is not exact'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'systemd has a failed unit'

dt=/sys/firmware/devicetree/base
[ "$(tr -d '\000' <"$dt/soc@0/clock-controller@3d90000/status")" = okay ] ||
	fail 'GPUCC device-tree node is not enabled'
for node in \
	soc@0/gpu@3d00000 \
	soc@0/gmu@3d6a000 \
	soc@0/iommu@3da0000 \
	soc@0/ufshc@1d84000 \
	soc@0/phy@1d87000 \
	soc@0/remoteproc@3000000 \
	soc@0/remoteproc@4080000 \
	soc@0/remoteproc@5c00000 \
	soc@0/remoteproc@a300000 \
	reserved-memory/memory@9b800000
do
	[ "$(tr -d '\000' <"$dt/$node/status")" = disabled ] ||
		fail "device-tree node is not disabled: $node"
done
[ ! -d /sys/module/gpucc_sm8350 ] || fail 'GPUCC module is already loaded'
[ -z "$(find /dev/dri -maxdepth 1 -name 'renderD*' -print 2>/dev/null)" ] ||
	fail 'a render node exists before the GPUCC-only confirmation'

fatal='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
[ "$(dmesg | grep -Ec "$fatal" || true)" -eq 0 ] ||
	fail 'fatal kernel signature exists'

thermal_count=0
thermal_max=-1000000
for path in /sys/class/thermal/thermal_zone*/temp; do
	[ -r "$path" ] || continue
	value=$(cat "$path" 2>/dev/null || true)
	case $value in -[0-9]*|[0-9]*) ;; *) continue ;; esac
	thermal_count=$((thermal_count + 1))
	[ "$value" -le "$thermal_max" ] || thermal_max=$value
done
[ "$thermal_count" -ge 20 ] && [ "$thermal_max" -lt 50000 ] ||
	fail 'thermal baseline is not safe'

module_root=/usr/lib/modules/$(uname -r)
[ -d "$module_root" ] || module_root=/lib/modules/$(uname -r)
module_files=$(find "$module_root" -type f | wc -l)
[ "$module_files" -gt 100 ] || fail 'module tree is incomplete'
find "$module_root" -type f -exec cat {} + >/dev/null

dmesg_line=$(( $(dmesg | wc -l) + 1 ))
sleep 12
new_log=$(dmesg | tail -n +"$dmesg_line")
if printf '%s\n' "$new_log" |
	grep -Eq "$fatal|WARNING:|Call trace:|Unhandled fault|IOMMU.*fault|page fault"
then
	fail 'kernel log regressed during quiet baseline'
fi

pstore_records=$(find /sys/fs/pstore -mindepth 1 -maxdepth 1 -type f \
	2>/dev/null | wc -l)
printf 'PASS trace-free target baseline physical_storage=0 block_mounts=0 failed_units=0 thermal_zones=%s thermal_max_mC=%s module_files=%s pstore_records=%s watchdog=armed\n' \
	"$thermal_count" "$thermal_max" "$module_files" "$pstore_records"
