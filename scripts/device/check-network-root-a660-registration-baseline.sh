#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

release=7.1.4-rog5-a660reg1
[ "$(uname -r)" = "$release" ] || fail 'unexpected kernel'
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
zap_dt=$gpu_dt/zap-shader
for node in "$gpucc_dt" "$smmu_dt" "$gpu_dt" "$gmu_dt"; do
	[ "$(tr -d '\000' <"$node/status")" = okay ] ||
		fail "registration device-tree node is not enabled: $node"
done
[ "$(tr '\000' ' ' <"$gpu_dt/compatible" | sed 's/ $//')" = \
	'qcom,adreno-660.1 qcom,adreno' ] ||
	fail 'A660 device-tree identity is unexpected'
[ "$(tr '\000' ' ' <"$gmu_dt/compatible" | sed 's/ $//')" = \
	'qcom,adreno-gmu-660.1 qcom,adreno-gmu' ] ||
	fail 'GMU device-tree identity is unexpected'
[ "$(tr -d '\000' <"$zap_dt/firmware-name")" = \
	qcom/sm8350/a660_zap.mbn ] ||
	fail 'ZAP firmware name is unexpected'

for node in \
	"$dt/soc@0/ufshc@1d84000" \
	"$dt/soc@0/phy@1d87000" \
	"$dt/soc@0/phy@88e8000" \
	"$dt/soc@0/usb@a8f8800" \
	"$dt/soc@0/display-subsystem@ae00000" \
	"$dt/soc@0/remoteproc@3000000" \
	"$dt/soc@0/remoteproc@4080000" \
	"$dt/soc@0/remoteproc@5c00000" \
	"$dt/soc@0/remoteproc@a300000" \
	"$dt/reserved-memory/memory@9b800000"
do
	[ "$(tr -d '\000' <"$node/status")" = disabled ] ||
		fail "contained device-tree node is not disabled: $node"
done

[ ! -d /sys/module/gpucc_sm8350 ] ||
	fail 'GPUCC module is already loaded'
[ ! -d /sys/module/msm ] ||
	fail 'MSM module is already loaded'
for module in drm_exec drm_gpuvm gpu_sched mdt_loader ubwc_config
do
	[ ! -d "/sys/module/$module" ] ||
		fail "registration module is already loaded: $module"
done
[ -d /sys/bus/platform/drivers/arm-smmu ] ||
	fail 'built-in ARM SMMU platform driver is absent'
[ ! -d /sys/bus/platform/drivers/adreno ] ||
	fail 'Adreno driver exists before the guarded module load'

for target in "$gpucc_dt" "$smmu_dt" "$gpu_dt" "$gmu_dt"; do
	device_count=0
	for device in /sys/bus/platform/devices/*; do
		[ -L "$device/of_node" ] || continue
		[ "$(readlink -f "$device/of_node")" = "$target" ] || continue
		device_count=$((device_count + 1))
		[ ! -e "$device/driver" ] ||
			fail "registration device bound before its guarded probe: $target"
	done
	[ "$device_count" -eq 1 ] ||
		fail "registration platform-device count is not one: $target"
done

[ -z "$(find /dev/dri -maxdepth 1 -name 'renderD*' -print 2>/dev/null)" ] ||
	fail 'a /dev/dri/renderD node exists before registration'
for fd in /proc/[0-9]*/fd/*; do
	[ -L "$fd" ] || continue
	case $(readlink "$fd" 2>/dev/null || true) in
		/dev/dri/*) fail 'a process already holds a DRM file descriptor' ;;
	esac
done

firmware_pattern='a660_sqe.fw|a660_gmu.bin|a660_zap.mbn'
firmware_files=$(find /lib/firmware /usr/lib/firmware -type f \
	\( -name a660_sqe.fw -o -name a660_gmu.bin -o -name a660_zap.mbn \) \
	-print 2>/dev/null || true)
[ -z "$firmware_files" ] || fail 'A660 firmware exists in the target root'
[ "$(dmesg | grep -Ec "$firmware_pattern" || true)" -eq 0 ] ||
	fail 'an A660 firmware request already occurred'

fatal='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
fault='(IOMMU|arm-smmu).*[^[:alnum:]_]fault([^[:alnum:]_]|$)|(context|global)[[:space:]]+fault([^[:alnum:]_]|$)'
[ "$(dmesg | grep -Ec "$fatal" || true)" -eq 0 ] ||
	fail 'fatal kernel signature exists'
[ "$(dmesg | grep -Eic "$fault" || true)" -eq 0 ] ||
	fail 'IOMMU fault signature exists'

module_root=/usr/lib/modules/$release
[ -d "$module_root" ] || module_root=/lib/modules/$release
[ -d "$module_root" ] || fail 'exact registration module tree is absent'
module_files=$(find "$module_root" -type f -name '*.ko' | wc -l)
[ "$module_files" -eq 7 ] || fail 'registration module set is not exact'
[ -s "$module_root/modules.dep" ] ||
	fail 'registration module dependency file is absent'
find "$module_root" -type f -name '*.ko' -exec cat {} + >/dev/null

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
printf 'PASS A660-registration baseline storage=0 mounts=0 firmware=0 render=0 drm_fds=0 failed_units=0 thermal_zones=%s thermal_max_mC=%s module_files=%s pstore_records=%s watchdog=armed modules=unloaded\n' \
	"$thermal_count" "$thermal_max" "$module_files" "$pstore_records"
