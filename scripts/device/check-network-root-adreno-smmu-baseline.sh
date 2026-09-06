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
gpucc_dt=$dt/soc@0/clock-controller@3d90000
smmu_dt=$dt/soc@0/iommu@3da0000
gpu_dt=$dt/soc@0/gpu@3d00000
gmu_dt=$dt/soc@0/gmu@3d6a000
[ "$(tr -d '\000' <"$gpucc_dt/status")" = okay ] ||
	fail 'GPUCC device-tree node is not enabled'
[ "$(tr -d '\000' <"$smmu_dt/status")" = okay ] ||
	fail 'Adreno SMMU device-tree node is not enabled'
compatible=$(tr '\000' ' ' <"$smmu_dt/compatible" | sed 's/ $//')
[ "$compatible" = \
	'qcom,sm8350-smmu-500 qcom,adreno-smmu qcom,smmu-500 arm,mmu-500' ] ||
	fail 'Adreno SMMU device-tree identity is unexpected'
for node in \
	"$gpu_dt" \
	"$gmu_dt" \
	"$dt/soc@0/ufshc@1d84000" \
	"$dt/soc@0/phy@1d87000" \
	"$dt/soc@0/remoteproc@3000000" \
	"$dt/soc@0/remoteproc@4080000" \
	"$dt/soc@0/remoteproc@5c00000" \
	"$dt/soc@0/remoteproc@a300000" \
	"$dt/reserved-memory/memory@9b800000"
do
	[ "$(tr -d '\000' <"$node/status")" = disabled ] ||
		fail "device-tree node is not disabled: $node"
done

[ ! -d /sys/module/gpucc_sm8350 ] || fail 'GPUCC module is already loaded'
[ -d /sys/bus/platform/drivers/arm-smmu ] ||
	fail 'built-in ARM SMMU platform driver is absent'
smmu_devices=0
smmu_device=
for device in /sys/bus/platform/devices/*; do
	[ -L "$device/of_node" ] || continue
	[ "$(readlink -f "$device/of_node")" = "$smmu_dt" ] || continue
	smmu_devices=$((smmu_devices + 1))
	smmu_device=$device
done
[ "$smmu_devices" -eq 1 ] ||
	fail 'Adreno SMMU platform device count is not one'
smmu_name=$(basename "$smmu_device")
[ "$smmu_name" = 3da0000.iommu ] ||
	fail 'Adreno SMMU platform device name is unexpected'
[ ! -e "$smmu_device/driver" ] ||
	fail 'Adreno SMMU bound before guarded GPUCC registration'
[ -r "$smmu_device/driver_override" ] ||
	fail 'Adreno SMMU driver_override is unreadable'
driver_override_check=/run/rog5-gpucc-diagnostic/check-adreno-smmu-driver-override-state.sh
[ -f "$driver_override_check" ] && [ ! -L "$driver_override_check" ] &&
	[ -x "$driver_override_check" ] ||
	fail 'Adreno SMMU driver_override checker is not exact'
driver_override_state=$(
	"$driver_override_check" "$smmu_device/driver_override"
) || fail 'Adreno SMMU driver_override is not the reviewed unset state'
[ "$driver_override_state" = unset-null-representation ] ||
	fail 'Adreno SMMU driver_override classification is unexpected'
[ "$(cat /sys/bus/platform/drivers_autoprobe)" = 1 ] ||
	fail 'platform driver autoprobe is disabled'
drivers_probe=/sys/bus/platform/drivers_probe
[ "$(stat -c '%u:%g:%a' "$drivers_probe")" = 0:0:200 ] ||
	fail 'platform drivers_probe control is not exact'
[ -w "$drivers_probe" ] ||
	fail 'platform drivers_probe control is unavailable'
[ ! -e /sys/bus/platform/drivers/arm-smmu/bind ] &&
	[ ! -e /sys/bus/platform/drivers/arm-smmu/unbind ] ||
	fail 'ARM SMMU force-bind controls unexpectedly exist'

waiting_for_supplier=unavailable
if [ -r "$smmu_device/waiting_for_supplier" ]; then
	waiting_for_supplier=$(cat "$smmu_device/waiting_for_supplier")
	case $waiting_for_supplier in
		0|1) ;;
		*) fail 'Adreno SMMU waiting_for_supplier is invalid' ;;
	esac
fi
deferred_entries=unavailable
if [ -r /sys/kernel/debug/devices_deferred ]; then
	deferred_entries=$(awk -v name="$smmu_name" \
		'$1 == name { count++ } END { print count + 0 }' \
		/sys/kernel/debug/devices_deferred)
	[ "$deferred_entries" -le 1 ] ||
		fail 'Adreno SMMU has duplicate deferred-probe entries'
fi
supplier_links=0
for link in "$smmu_device"/supplier:*; do
	[ -L "$link" ] || continue
	supplier_links=$((supplier_links + 1))
done
for device in /sys/bus/platform/devices/*; do
	[ -L "$device/of_node" ] || continue
	of_node=$(readlink -f "$device/of_node")
	case $of_node in
		"$gpu_dt"|"$gmu_dt")
			[ ! -e "$device/driver" ] ||
				fail 'disabled GPU or GMU is already bound'
			;;
	esac
done
[ -z "$(find /dev/dri -maxdepth 1 -name 'renderD*' -print 2>/dev/null)" ] ||
	fail 'a render node exists before the Adreno SMMU probe'

firmware_pattern='a660_sqe.fw|a660_gmu.bin|a660_zap.mbn'
firmware_files=$(find /lib/firmware /usr/lib/firmware -type f \
	\( -name a660_sqe.fw -o -name a660_gmu.bin -o -name a660_zap.mbn \) \
	-print 2>/dev/null || true)
[ -z "$firmware_files" ] || fail 'A660 firmware exists in the target root'
[ "$(dmesg | grep -Ec "$firmware_pattern" || true)" -eq 0 ] ||
	fail 'an A660 firmware request already occurred'

fatal='(^|[^[:alnum:]_])(Kernel panic|Oops:|BUG:|watchdog[[:space:]_-]+bite|Kernel fault|Unable to handle kernel|Synchronous External Abort)([^[:alnum:]_]|$)'
fault='(IOMMU|arm-smmu).*[^[:alnum:]_]fault([^[:alnum:]_]|$)|(context|global)[[:space:]]+fault([^[:alnum:]_]|$)'
[ "$(dmesg | grep -Ec "$fatal" || true)" -eq 0 ] ||
	fail 'fatal kernel signature exists'
[ "$(dmesg | grep -Eic "$fault" || true)" -eq 0 ] ||
	fail 'IOMMU fault signature exists'

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
	grep -Ei "$fatal|$fault|WARNING:|Call trace:|Unhandled fault|page fault"
then
	fail 'kernel log regressed during quiet baseline'
fi

pstore_records=$(find /sys/fs/pstore -mindepth 1 -maxdepth 1 -type f \
	2>/dev/null | wc -l)
printf 'PASS Adreno-SMMU baseline storage=0 mounts=0 firmware=0 render=0 failed_units=0 thermal_zones=%s thermal_max_mC=%s module_files=%s pstore_records=%s watchdog=armed smmu=unbound smmu_name=%s driver_override=%s waiting_for_supplier=%s deferred_entries=%s supplier_links=%s drivers_probe=locked\n' \
	"$thermal_count" "$thermal_max" "$module_files" "$pstore_records" \
	"$smmu_name" "$driver_override_state" "$waiting_for_supplier" "$deferred_entries" \
	"$supplier_links"
