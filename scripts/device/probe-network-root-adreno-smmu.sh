#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_MAINLINE_ADRENO_SMMU_PROBE:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_ADRENO_SMMU_PROBE=1 for one attended probe'
[ "$(id -u)" -eq 0 ] || fail 'attended probe requires root'

probe_timeout=${ROG5_PROBE_TIMEOUT:-75}
settle_seconds=${ROG5_PROBE_SETTLE:-30}
case $probe_timeout:$settle_seconds in
	*[!0-9:]*|:*|*:) fail 'probe timeout and settle interval must be integers' ;;
esac
[ "$probe_timeout" -ge 45 ] && [ "$probe_timeout" -le 180 ] ||
	fail 'ROG5_PROBE_TIMEOUT must be between 45 and 180 seconds'
[ "$settle_seconds" -ge 20 ] && [ "$settle_seconds" -le 60 ] ||
	fail 'ROG5_PROBE_SETTLE must be between 20 and 60 seconds'
[ "$probe_timeout" -ge $((settle_seconds + 20)) ] ||
	fail 'probe timeout must exceed settling by at least 20 seconds'

for command in awk basename cat cut dmesg find findmnt grep id insmod ip \
	kill mktemp modinfo ps readlink rm rmdir sed setsid sha256sum sleep \
	stat systemctl tail tr uname wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
dmesg --help 2>&1 | grep -q -- '--follow-new' ||
	fail 'dmesg lacks follow-new support'

[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] || fail 'unexpected kernel'
[ "$(cat /proc/1/comm)" = systemd ] || fail 'PID 1 is not systemd'
[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
	fail 'systemd is not running'
[ "$(systemctl is-enabled systemd-udev-trigger.service 2>/dev/null ||
	true)" = masked-runtime ] || fail 'udev coldplug is not runtime-masked'
[ "$(systemctl is-enabled systemd-modules-load.service 2>/dev/null ||
	true)" = masked-runtime ] || fail 'module loading is not runtime-masked'
[ ! -e /run/rog5-network-root-watchdog.pid ] ||
	fail 'network-root watchdog is still active'
[ -e /run/rog5-network-root-watchdog.disarmed.pid ] ||
	fail 'missing network-root watchdog disarm marker'

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
		fail "$parameter boot argument is present"
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
	fail 'physical block device is present before probe'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount is present before probe'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	fail 'USB network carrier is down before probe'
[ "$(ip -4 -o address show dev usb0 |
	awk '$4 == "169.254.77.2/30" { count++ }
		END { print count + 0 }')" -eq 1 ] ||
	fail 'USB network address is not exact'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'systemd already has a failed unit'

module_file=/run/rog5-gpucc-diagnostic/gpucc-sm8350.ko
module_sha=9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a
[ ! -d /sys/module/gpucc_sm8350 ] ||
	fail 'GPUCC module is already loaded; use a fresh candidate'
[ -f "$module_file" ] && [ ! -L "$module_file" ] ||
	fail 'GPUCC diagnostic module is missing or is a symlink'
[ "$(stat -c '%u:%g:%a' "$module_file")" = 0:0:400 ] ||
	fail 'GPUCC diagnostic module ownership or mode is not exact'
[ "$(sha256sum "$module_file" | cut -d ' ' -f 1)" = "$module_sha" ] ||
	fail 'GPUCC diagnostic module hash mismatch'
[ "$(modinfo -F name "$module_file")" = gpucc_sm8350 ] ||
	fail 'GPUCC diagnostic module name mismatch'
[ -z "$(modinfo -F depends "$module_file")" ] ||
	fail 'GPUCC diagnostic module has unexpected dependencies'
[ "$(modinfo -F vermagic "$module_file")" = \
	'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' ] ||
	fail 'GPUCC diagnostic module ABI mismatch'
modinfo -p "$module_file" |
	grep -Fxq \
	'probe_trace:Emit progress notices for attended SM8350 GPUCC diagnostics (bool)' ||
	fail 'GPUCC diagnostic module lacks its read-only trace parameter'

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
	fail 'Adreno SMMU identity is unexpected'
for node in "$gpu_dt" "$gmu_dt"; do
	[ "$(tr -d '\000' <"$node/status")" = disabled ] ||
		fail 'GPU or GMU is not explicitly disabled'
done
[ -d /sys/bus/platform/drivers/arm-smmu ] ||
	fail 'built-in ARM SMMU driver is absent'

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
[ ! -e "$smmu_device/driver" ] ||
	fail 'Adreno SMMU is already bound'
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
	fail 'a render node exists before probe'

firmware_pattern='a660_sqe.fw|a660_gmu.bin|a660_zap.mbn'
firmware_files=$(find /lib/firmware /usr/lib/firmware -type f \
	\( -name a660_sqe.fw -o -name a660_gmu.bin -o -name a660_zap.mbn \) \
	-print 2>/dev/null || true)
[ -z "$firmware_files" ] || fail 'A660 firmware exists in the target root'
[ "$(dmesg | grep -Ec "$firmware_pattern" || true)" -eq 0 ] ||
	fail 'an A660 firmware request already occurred'

fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
fault_pattern='IOMMU.*fault|arm-smmu.*fault|context fault|global fault'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	fail 'fatal kernel signature exists before probe'
[ "$(dmesg | grep -Eic "$fault_pattern" || true)" -eq 0 ] ||
	fail 'IOMMU fault signature exists before probe'
dmesg_start=$(( $(dmesg | wc -l) + 1 ))

probe_safe=0
watchdog_pid=
state_dir=
log_follower_pid=
disarm_watchdog() {
	[ "$probe_safe" = 1 ] || return 0
	set +e
	if [ -n "$log_follower_pid" ]; then
		kill "$log_follower_pid" 2>/dev/null
		wait "$log_follower_pid" 2>/dev/null
	fi
	if [ -n "$watchdog_pid" ]; then
		kill -STOP -- "-$watchdog_pid" 2>/dev/null
		kill -KILL -- "-$watchdog_pid" 2>/dev/null
		wait "$watchdog_pid" 2>/dev/null
	fi
	if [ -n "$state_dir" ]; then
		rm -f "$state_dir/armed"
		rmdir "$state_dir" 2>/dev/null
	fi
	watchdog_pid=
	log_follower_pid=
	state_dir=
	set -e
}
trap disarm_watchdog EXIT
trap 'exit 1' HUP INT TERM

state_dir=$(mktemp -d /run/rog5-adreno-smmu-probe.XXXXXX)
# Positional parameters are intentionally expanded by the child shell.
# shellcheck disable=SC2016
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-adreno-smmu-probe: watchdog expired" >&8
	echo b >&9
' sh "$probe_timeout" "$state_dir/armed" \
	</dev/null >/dev/null 2>&1 &
watchdog_pid=$!

watchdog_pgid=$(ps -o pgid= -p "$watchdog_pid" | tr -d ' ')
[ "$watchdog_pgid" = "$watchdog_pid" ] ||
	fail 'probe watchdog is not in an independent process group'
armed=0
for _ in 1 2 3 4 5; do
	if [ -s "$state_dir/armed" ] && kill -0 "$watchdog_pid" 2>/dev/null; then
		armed=1
		break
	fi
	sleep 1
done
[ "$armed" -eq 1 ] || fail 'probe watchdog did not arm'

echo "BEGIN adreno-smmu watchdog=${probe_timeout}s settle=${settle_seconds}s"
echo 'rog5-adreno-smmu-probe: begin' >/dev/kmsg
dmesg --follow-new &
log_follower_pid=$!
sleep 1
kill -0 "$log_follower_pid" ||
	fail 'live kernel-log follower did not start'
echo 'rog5-adreno-smmu-probe: external GPUCC load begin' >/dev/kmsg
insmod "$module_file" probe_trace=1
echo 'rog5-adreno-smmu-probe: insmod returned' >/dev/kmsg
sleep "$settle_seconds"

post_fail() {
	reason=$1
	echo "EVIDENCE adreno-smmu reason=$reason"
	echo "EVIDENCE system_state=$(systemctl is-system-running 2>/dev/null ||
		true)"
	echo 'EVIDENCE failed_units_begin'
	systemctl --failed --no-legend --plain 2>/dev/null || true
	echo 'EVIDENCE failed_units_end'
	echo 'EVIDENCE thermal_zones_begin'
	for zone in /sys/class/thermal/thermal_zone*; do
		[ -d "$zone" ] || continue
		type=$(cat "$zone/type" 2>/dev/null || echo unreadable)
		temp=$(cat "$zone/temp" 2>/dev/null || echo unreadable)
		printf 'zone=%s type=%s temp_mC=%s\n' \
			"$(basename "$zone")" "$type" "$temp"
	done
	echo 'EVIDENCE thermal_zones_end'
	echo 'EVIDENCE new_dmesg_begin'
	dmesg | tail -n +"$dmesg_start" | tail -n 200
	echo 'EVIDENCE new_dmesg_end'
	fail "$reason"
}

[ -d /sys/module/gpucc_sm8350 ] ||
	post_fail 'GPUCC module did not remain loaded'
parameter=/sys/module/gpucc_sm8350/parameters/probe_trace
[ "$(cat "$parameter")" = Y ] ||
	post_fail 'GPUCC trace parameter is not enabled'
[ "$(stat -c %a "$parameter")" = 400 ] ||
	post_fail 'GPUCC trace parameter became writable'

gpucc_driver=/sys/bus/platform/drivers/sm8350-gpucc
[ -d "$gpucc_driver" ] || post_fail 'GPUCC platform driver is absent'
gpucc_bound=0
for link in "$gpucc_driver"/*; do
	[ -L "$link" ] || continue
	[ "$(basename "$link")" = module ] && continue
	gpucc_bound=$((gpucc_bound + 1))
done
[ "$gpucc_bound" -eq 1 ] ||
	post_fail 'GPUCC did not bind exactly one platform device'

[ -e "$smmu_device/driver" ] ||
	post_fail 'Adreno SMMU did not bind after GPUCC registration'
[ "$(readlink -f "$smmu_device/driver")" = \
	/sys/bus/platform/drivers/arm-smmu ] ||
	post_fail 'Adreno SMMU bound an unexpected driver'
smmu_bound=0
for link in /sys/bus/platform/drivers/arm-smmu/*; do
	[ -L "$link/of_node" ] || continue
	[ "$(readlink -f "$link/of_node")" = "$smmu_dt" ] || continue
	smmu_bound=$((smmu_bound + 1))
done
[ "$smmu_bound" -eq 1 ] ||
	post_fail 'exact Adreno SMMU bind count is not one'

runtime_status_path=$smmu_device/power/runtime_status
[ -r "$runtime_status_path" ] ||
	post_fail 'Adreno SMMU power/runtime_status is unreadable'
runtime_status=$(cat "$runtime_status_path")
if [ "$runtime_status" != suspended ]; then
	for _ in 1 2 3 4 5; do
		sleep 1
		runtime_status=$(cat "$runtime_status_path")
		[ "$runtime_status" != suspended ] || break
	done
fi
[ "$runtime_status" = suspended ] ||
	post_fail 'Adreno SMMU did not reach runtime suspended state'

for grouped in /sys/kernel/iommu_groups/*/devices/*; do
	[ -e "$grouped" ] || continue
	[ -L "$grouped/of_node" ] || continue
	grouped_node=$(readlink -f "$grouped/of_node")
	case $grouped_node in
		"$gpu_dt"|"$gmu_dt")
			post_fail 'disabled GPU or GMU joined an IOMMU group'
			;;
	esac
done
for device in /sys/bus/platform/devices/*; do
	[ -L "$device/of_node" ] || continue
	of_node=$(readlink -f "$device/of_node")
	case $of_node in
		"$gpu_dt"|"$gmu_dt")
			[ ! -e "$device/driver" ] ||
				post_fail 'disabled GPU or GMU bound after SMMU registration'
			;;
	esac
done
[ -z "$(find /dev/dri -maxdepth 1 -name 'renderD*' -print 2>/dev/null)" ] ||
	post_fail 'a render node appeared during the SMMU-only probe'
[ "$(dmesg | tail -n +"$dmesg_start" |
	grep -Ec "$firmware_pattern" || true)" -eq 0 ] ||
	post_fail 'an A660 firmware request appeared'

system_state=
for _ in 1 2 3 4 5 6 7 8 9 10; do
	system_state=$(systemctl is-system-running 2>/dev/null || true)
	[ "$system_state" != running ] || break
	case $system_state in
		starting|initializing) sleep 1 ;;
		*) break ;;
	esac
done
[ "$system_state" = running ] ||
	post_fail 'systemd regressed after SMMU registration'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	post_fail 'a systemd unit failed after SMMU registration'
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	post_fail 'physical block device appeared'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	post_fail 'block-backed mount appeared'
[ "$(findmnt -n -o SOURCE /.rog5/root-ro)" = 169.254.77.1:/ ] ||
	post_fail 'NFS lower disappeared'
findmnt -n -o OPTIONS /.rog5/root-ro | tr ',' '\n' | grep -qx ro ||
	post_fail 'NFS lower became writable'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	post_fail 'USB network carrier dropped'

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
	post_fail 'thermal state is not safe after SMMU registration'

[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	post_fail 'fatal kernel signature appeared'
[ "$(dmesg | tail -n +"$dmesg_start" |
	grep -Eic "$fault_pattern|WARNING:|Call trace:|Unhandled fault|page fault" ||
	true)" -eq 0 ] ||
	post_fail 'new warning or fault appeared'

probe_safe=1
disarm_watchdog
trap - EXIT HUP INT TERM
printf 'PASS Adreno-SMMU probe GPUCC=1 SMMU=1 runtime=%s firmware=0 render=0 storage=0 mounts=0 failed_units=0 thermal_zones=%s thermal_max_mC=%s watchdog=disarmed\n' \
	"$runtime_status" "$thermal_count" "$thermal_max"
