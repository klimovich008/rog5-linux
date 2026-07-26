#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_MAINLINE_A660_REGISTRATION:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_A660_REGISTRATION=1 for one attended probe'
[ "$(id -u)" -eq 0 ] || fail 'attended probe requires root'

# Replace this source lock with the SHA-256 of a root-owned, mode-0400
# acceptance marker only after the independent v18 SMMU live gate passes.
smmu_acceptance_sha=NOT_ACCEPTED
[ "$smmu_acceptance_sha" != NOT_ACCEPTED ] ||
	fail 'registration remains locked until the v18 SMMU live gate passes'
smmu_acceptance=/run/rog5-adreno-smmu-live.accepted
[ -f "$smmu_acceptance" ] && [ ! -L "$smmu_acceptance" ] ||
	fail 'v18 SMMU live acceptance marker is absent'
[ "$(stat -c '%u:%g:%a' "$smmu_acceptance")" = 0:0:400 ] ||
	fail 'v18 SMMU live acceptance marker metadata is not exact'
[ "$(sha256sum "$smmu_acceptance" | cut -d ' ' -f 1)" = \
	"$smmu_acceptance_sha" ] ||
	fail 'v18 SMMU live acceptance marker hash mismatch'

probe_timeout=${ROG5_PROBE_TIMEOUT:-90}
settle_seconds=${ROG5_PROBE_SETTLE:-30}
case $probe_timeout:$settle_seconds in
	*[!0-9:]*|:*|*:) fail 'probe timeout and settle interval must be integers' ;;
esac
[ "$probe_timeout" -ge 60 ] && [ "$probe_timeout" -le 180 ] ||
	fail 'ROG5_PROBE_TIMEOUT must be between 60 and 180 seconds'
[ "$settle_seconds" -ge 20 ] && [ "$settle_seconds" -le 60 ] ||
	fail 'ROG5_PROBE_SETTLE must be between 20 and 60 seconds'
[ "$probe_timeout" -ge $((settle_seconds + 30)) ] ||
	fail 'probe timeout must exceed settling by at least 30 seconds'

for command in awk basename cat cut dmesg find findmnt grep id insmod ip \
	kill mktemp modinfo ps readlink rm rmdir sed setsid sha256sum sleep \
	stat systemctl tail tr uname wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
dmesg --help 2>&1 | grep -q -- '--follow-new' ||
	fail 'dmesg lacks follow-new support'

release=7.1.4-rog5-a660reg1
[ "$(uname -r)" = "$release" ] || fail 'unexpected kernel'
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
	fail 'physical block device is present before registration'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount is present before registration'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	fail 'USB network carrier is down before registration'
[ "$(ip -4 -o address show dev usb0 |
	awk '$4 == "169.254.77.2/30" { count++ }
		END { print count + 0 }')" -eq 1 ] ||
	fail 'USB network address is not exact'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'systemd already has a failed unit'

module_root=/usr/lib/modules/$release
[ -d "$module_root" ] || module_root=/lib/modules/$release
[ -d "$module_root" ] || fail 'exact registration module tree is absent'
gpucc_module=$module_root/kernel/drivers/clk/qcom/gpucc-sm8350.ko
drm_exec_module=$module_root/kernel/drivers/gpu/drm/drm_exec.ko
drm_gpuvm_module=$module_root/kernel/drivers/gpu/drm/drm_gpuvm.ko
gpu_sched_module=$module_root/kernel/drivers/gpu/drm/scheduler/gpu-sched.ko
mdt_module=$module_root/kernel/drivers/soc/qcom/mdt_loader.ko
ubwc_module=$module_root/kernel/drivers/soc/qcom/ubwc_config.ko
msm_module=$module_root/kernel/drivers/gpu/drm/msm/msm.ko
vermagic="$release SMP preempt mod_unload aarch64"

verify_module() {
	file=$1
	name=$2
	hash=$3
	depends=$4
	[ -f "$file" ] && [ ! -L "$file" ] ||
		fail "module is missing or is a symlink: $name"
	[ "$(stat -c '%u:%g:%a' "$file")" = 0:0:644 ] ||
		fail "module ownership or mode is not exact: $name"
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$hash" ] ||
		fail "module hash mismatch: $name"
	[ "$(modinfo -F name "$file")" = "$name" ] ||
		fail "module name mismatch: $name"
	[ "$(modinfo -F depends "$file")" = "$depends" ] ||
		fail "module dependency mismatch: $name"
	[ "$(modinfo -F vermagic "$file")" = "$vermagic" ] ||
		fail "module ABI mismatch: $name"
}

verify_module "$gpucc_module" gpucc_sm8350 \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 ''
verify_module "$drm_exec_module" drm_exec \
	71c32424623f826bb6b7f217fb84f624721d90e53eb89cc9d205af66aca9f886 ''
verify_module "$drm_gpuvm_module" drm_gpuvm \
	981d3f322e18c3b815de7dcba0f829d2ca36f25c85347bb233e7e1baa73386f8 \
	drm_exec
verify_module "$gpu_sched_module" gpu_sched \
	f53fba10fe10cfeca45abc6d808ca2f5a116832b9595de8f09af66206204b1f4 ''
verify_module "$mdt_module" mdt_loader \
	001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 ''
verify_module "$ubwc_module" ubwc_config \
	4220552fbf17562128c956c3cfdbb8abd22e26f2c6a7f22e94422ef34b10e587 ''
verify_module "$msm_module" msm \
	f7c69c399dea567ad8a1f0ecc10c61259dd76052230f61ae69165c711e24ac24 \
	'drm_exec,drm_gpuvm,gpu-sched,mdt_loader,ubwc_config'
modinfo -p "$gpucc_module" |
	grep -Fxq \
	'probe_trace:Emit progress notices for attended SM8350 GPUCC diagnostics (bool)' ||
	fail 'GPUCC module lacks its read-only trace parameter'
modinfo -p "$msm_module" | grep -Fxq 'separate_gpu_kms: (bool)' ||
	fail 'MSM module lacks its separate GPU parameter'

for module in gpucc_sm8350 msm drm_exec drm_gpuvm gpu_sched \
	mdt_loader ubwc_config
do
	[ ! -d "/sys/module/$module" ] ||
		fail "module is already loaded; use a fresh candidate: $module"
done

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

platform_device() {
	target=$1
	found=
	count=0
	for device in /sys/bus/platform/devices/*; do
		[ -L "$device/of_node" ] || continue
		[ "$(readlink -f "$device/of_node")" = "$target" ] || continue
		count=$((count + 1))
		found=$device
	done
	[ "$count" -eq 1 ] ||
		fail "platform-device count is not one: $target"
	printf '%s\n' "$found"
}

gpucc_device=$(platform_device "$gpucc_dt")
smmu_device=$(platform_device "$smmu_dt")
gpu_device=$(platform_device "$gpu_dt")
gmu_device=$(platform_device "$gmu_dt")
for device in "$gpucc_device" "$smmu_device" "$gpu_device" "$gmu_device"; do
	[ ! -e "$device/driver" ] ||
		fail 'registration device is already bound'
done
[ -d /sys/bus/platform/drivers/arm-smmu ] ||
	fail 'built-in ARM SMMU driver is absent'
[ -z "$(find /dev/dri -maxdepth 1 -name 'renderD*' -print 2>/dev/null)" ] ||
	fail 'a /dev/dri/renderD node exists before registration'
for fd in /proc/[0-9]*/fd/*; do
	[ -L "$fd" ] || continue
	case $(readlink "$fd" 2>/dev/null || true) in
		/dev/dri/*) fail 'a process holds a DRM descriptor before registration' ;;
	esac
done

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
	fail 'fatal kernel signature exists before registration'
[ "$(dmesg | grep -Eic "$fault_pattern" || true)" -eq 0 ] ||
	fail 'IOMMU fault signature exists before registration'
dmesg_start=$(( $(dmesg | wc -l) + 1 ))

registration_safe=0
watchdog_pid=
state_dir=
log_follower_pid=
disarm_watchdog() {
	[ "$registration_safe" = 1 ] || return 0
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

state_dir=$(mktemp -d /run/rog5-a660-registration.XXXXXX)
# Positional parameters are intentionally expanded by the child shell.
# shellcheck disable=SC2016
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-a660-registration: watchdog expired" >&8
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

echo "BEGIN a660-registration watchdog=${probe_timeout}s settle=${settle_seconds}s"
echo 'rog5-a660-registration: begin' >/dev/kmsg
dmesg --follow-new &
log_follower_pid=$!
sleep 1
kill -0 "$log_follower_pid" ||
	fail 'live kernel-log follower did not start'

post_fail() {
	reason=$1
	echo "EVIDENCE a660-registration reason=$reason"
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
	dmesg | tail -n +"$dmesg_start" | tail -n 240
	echo 'EVIDENCE new_dmesg_end'
	fail "$reason"
}

echo 'rog5-a660-registration: GPUCC load begin' >/dev/kmsg
if ! insmod "$gpucc_module" probe_trace=1; then
	post_fail 'GPUCC module load failed'
fi
[ -d /sys/module/gpucc_sm8350 ] ||
	post_fail 'GPUCC module did not remain loaded'
gpucc_parameter=/sys/module/gpucc_sm8350/parameters/probe_trace
[ "$(cat "$gpucc_parameter")" = Y ] ||
	post_fail 'GPUCC trace parameter is not enabled'
[ "$(stat -c %a "$gpucc_parameter")" = 400 ] ||
	post_fail 'GPUCC trace parameter became writable'
[ -e "$gpucc_device/driver" ] ||
	post_fail 'GPUCC did not bind'
[ "$(readlink -f "$gpucc_device/driver")" = \
	/sys/bus/platform/drivers/sm8350-gpucc ] ||
	post_fail 'GPUCC bound an unexpected driver'
[ -e "$smmu_device/driver" ] ||
	post_fail 'Adreno SMMU did not bind after GPUCC'
[ "$(readlink -f "$smmu_device/driver")" = \
	/sys/bus/platform/drivers/arm-smmu ] ||
	post_fail 'Adreno SMMU bound an unexpected driver'

echo 'rog5-a660-registration: dependency loads begin' >/dev/kmsg
insmod "$drm_exec_module" || post_fail 'drm_exec load failed'
insmod "$drm_gpuvm_module" || post_fail 'drm_gpuvm load failed'
insmod "$gpu_sched_module" || post_fail 'gpu_sched load failed'
insmod "$mdt_module" || post_fail 'mdt_loader load failed'
insmod "$ubwc_module" || post_fail 'ubwc_config load failed'
echo 'rog5-a660-registration: MSM load begin' >/dev/kmsg
if ! insmod "$msm_module" separate_gpu_kms=1; then
	post_fail 'MSM registration module load failed'
fi
echo 'rog5-a660-registration: MSM load returned' >/dev/kmsg

for module in gpucc_sm8350 msm drm_exec drm_gpuvm gpu_sched \
	mdt_loader ubwc_config
do
	[ -d "/sys/module/$module" ] ||
		post_fail "module did not remain loaded: $module"
done
msm_parameter=/sys/module/msm/parameters/separate_gpu_kms
[ "$(cat "$msm_parameter")" = Y ] ||
	post_fail 'separate_gpu_kms is not enabled'
[ "$(stat -c %a "$msm_parameter")" = 400 ] ||
	post_fail 'separate_gpu_kms became writable'
[ -e "$gpu_device/driver" ] ||
	post_fail 'A660 platform device did not bind'
[ "$(readlink -f "$gpu_device/driver")" = \
	/sys/bus/platform/drivers/adreno ] ||
	post_fail 'A660 bound an unexpected driver'
[ ! -e "$gmu_device/driver" ] ||
	post_fail 'GMU unexpectedly acquired a separate platform driver'

for runtime_path in "$smmu_device/power/runtime_status" \
	"$gmu_device/power/runtime_status"
do
	[ -r "$runtime_path" ] ||
		post_fail "runtime status is unreadable: $runtime_path"
	runtime_status=$(cat "$runtime_path")
	if [ "$runtime_status" != suspended ]; then
		for _ in 1 2 3 4 5 6 7 8 9 10; do
			sleep 1
			runtime_status=$(cat "$runtime_path")
			[ "$runtime_status" != suspended ] || break
		done
	fi
	[ "$runtime_status" = suspended ] ||
		post_fail "device did not reach runtime suspend: $runtime_path"
done

gpu_group_count=0
gmu_group_count=0
for grouped in /sys/kernel/iommu_groups/*/devices/*; do
	[ -e "$grouped" ] || continue
	[ -L "$grouped/of_node" ] || continue
	grouped_node=$(readlink -f "$grouped/of_node")
	case $grouped_node in
		"$gpu_dt") gpu_group_count=$((gpu_group_count + 1)) ;;
		"$gmu_dt") gmu_group_count=$((gmu_group_count + 1)) ;;
	esac
done
[ "$gpu_group_count" -eq 1 ] ||
	post_fail 'A660 IOMMU attachment count is not one'
[ "$gmu_group_count" -eq 1 ] ||
	post_fail 'GMU IOMMU attachment count is not one'

render_count=$(find /dev/dri -maxdepth 1 -type c -name 'renderD*' \
	-print 2>/dev/null | wc -l)
[ "$render_count" -eq 1 ] ||
	post_fail 'registration did not create exactly one /dev/dri/renderD node'
[ "$(find /sys/class/drm -mindepth 1 -maxdepth 1 -name 'card*-*' \
	-print 2>/dev/null | wc -l)" -eq 0 ] ||
	post_fail 'headless registration created a display connector'

check_no_drm_fds() {
	for fd in /proc/[0-9]*/fd/*; do
		[ -L "$fd" ] || continue
		case $(readlink "$fd" 2>/dev/null || true) in
			/dev/dri/*) return 1 ;;
		esac
	done
	return 0
}
check_no_drm_fds ||
	post_fail 'a process opened a DRM node during registration'
[ "$(dmesg | tail -n +"$dmesg_start" |
	grep -Ec "$firmware_pattern" || true)" -eq 0 ] ||
	post_fail 'an A660 firmware request appeared during registration'

sleep "$settle_seconds"
check_no_drm_fds ||
	post_fail 'a process opened a DRM node during settling'
[ "$(dmesg | tail -n +"$dmesg_start" |
	grep -Ec "$firmware_pattern" || true)" -eq 0 ] ||
	post_fail 'an A660 firmware request appeared during settling'

system_state=$(systemctl is-system-running 2>/dev/null || true)
[ "$system_state" = running ] ||
	post_fail 'systemd regressed after registration'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	post_fail 'a systemd unit failed after registration'
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
	post_fail 'thermal state is not safe after registration'

[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	post_fail 'fatal kernel signature appeared'
[ "$(dmesg | tail -n +"$dmesg_start" |
	grep -Eic "$fault_pattern|WARNING:|Call trace:|Unhandled fault|page fault" ||
	true)" -eq 0 ] ||
	post_fail 'new warning or fault appeared'

registration_safe=1
disarm_watchdog
trap - EXIT HUP INT TERM
printf 'PASS A660 registration GPUCC=1 SMMU=1 GPU=1 GMU=1 iommu=2 render=1 drm_fds=0 firmware=0 storage=0 mounts=0 failed_units=0 thermal_zones=%s thermal_max_mC=%s watchdog=disarmed\n' \
	"$thermal_count" "$thermal_max"
