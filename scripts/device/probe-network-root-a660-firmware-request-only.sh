#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_MAINLINE_A660_FIRMWARE_REQUEST_ONLY:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_A660_FIRMWARE_REQUEST_ONLY=1 for one attended probe'
[ "$(id -u)" -eq 0 ] || fail 'attended probe requires root'

release=7.1.4-rog5-a660reg1
lower=/.rog5/root-ro
module_root=$lower/usr/lib/modules/$release
firmware_root=$lower/usr/lib/firmware
helper=$lower/usr/local/libexec/rog5-a660-firmware-request-only-open
acceptance=$lower/etc/rog5/a660-registration-v3-live.accepted
acceptance_sha=8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f
probe_timeout=${ROG5_PROBE_TIMEOUT:-90}
settle_seconds=${ROG5_PROBE_SETTLE:-20}

case $probe_timeout:$settle_seconds in
	*[!0-9:]*|:*|*:) fail 'probe timeout and settle interval must be integers' ;;
esac
[ "$probe_timeout" -ge 60 ] && [ "$probe_timeout" -le 180 ] ||
	fail 'ROG5_PROBE_TIMEOUT must be between 60 and 180 seconds'
[ "$settle_seconds" -ge 10 ] && [ "$settle_seconds" -le 40 ] ||
	fail 'ROG5_PROBE_SETTLE must be between 10 and 40 seconds'
[ "$probe_timeout" -ge $((settle_seconds + 40)) ] ||
	fail 'probe timeout must exceed settling by at least 40 seconds'

for command in awk basename cat cut dmesg find findmnt grep id insmod ip \
	kill mktemp modinfo ps readlink rm rmdir sed setsid sha256sum sleep \
	stat systemctl tail tr uname wait wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
dmesg --help 2>&1 | grep -q -- '--follow-new' ||
	fail 'dmesg lacks follow-new support'

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

[ "$(findmnt -n -o FSTYPE /)" = overlay ] || fail 'root is not OverlayFS'
[ "$(findmnt -n -o SOURCE "$lower")" = 169.254.77.1:/ ] ||
	fail 'unexpected NFS lower source'
findmnt -n -o OPTIONS "$lower" | tr ',' '\n' | grep -qx ro ||
	fail 'NFS lower is not read-only'
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	fail 'physical block device is present before request-only probe'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount is present before request-only probe'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	fail 'USB network carrier is down before request-only probe'
[ "$(ip -4 -o address show dev usb0 |
	awk '$4 == "169.254.77.2/30" { count++ }
		END { print count + 0 }')" -eq 1 ] ||
	fail 'USB network address is not exact'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'systemd already has a failed unit'

[ -f "$acceptance" ] && [ ! -L "$acceptance" ] ||
	fail 'registration-v3 live acceptance marker is absent'
[ "$(stat -c '%u:%g:%a' "$acceptance")" = 0:0:444 ] ||
	fail 'registration-v3 acceptance metadata is not exact'
[ "$(sha256sum "$acceptance" | cut -d ' ' -f 1)" = \
	"$acceptance_sha" ] ||
	fail 'registration-v3 acceptance hash mismatch'
grep -qx \
	'live_report_sha256=2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79' \
	"$acceptance"
grep -qx 'v3_reuse=FORBIDDEN' "$acceptance"

verify_file() {
	file=$1
	mode=$2
	expected=$3
	label=$4
	[ -f "$file" ] && [ ! -L "$file" ] ||
		fail "$label is missing or linked"
	[ "$(stat -c '%u:%g:%a' "$file")" = "0:0:$mode" ] ||
		fail "$label ownership or mode changed"
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ] ||
		fail "$label hash mismatch"
}

gpucc_module=$module_root/kernel/drivers/clk/qcom/gpucc-sm8350.ko
drm_exec_module=$module_root/kernel/drivers/gpu/drm/drm_exec.ko
drm_gpuvm_module=$module_root/kernel/drivers/gpu/drm/drm_gpuvm.ko
gpu_sched_module=$module_root/kernel/drivers/gpu/drm/scheduler/gpu-sched.ko
mdt_module=$module_root/kernel/drivers/soc/qcom/mdt_loader.ko
ubwc_module=$module_root/kernel/drivers/soc/qcom/ubwc_config.ko
msm_module=$module_root/kernel/drivers/gpu/drm/msm/msm.ko

verify_file "$gpucc_module" 644 \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
	'GPUCC module'
verify_file "$drm_exec_module" 644 \
	71c32424623f826bb6b7f217fb84f624721d90e53eb89cc9d205af66aca9f886 \
	'DRM exec module'
verify_file "$drm_gpuvm_module" 644 \
	981d3f322e18c3b815de7dcba0f829d2ca36f25c85347bb233e7e1baa73386f8 \
	'DRM GPUVM module'
verify_file "$gpu_sched_module" 644 \
	f53fba10fe10cfeca45abc6d808ca2f5a116832b9595de8f09af66206204b1f4 \
	'GPU scheduler module'
verify_file "$mdt_module" 644 \
	001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 \
	'MDT-loader module'
verify_file "$ubwc_module" 644 \
	4220552fbf17562128c956c3cfdbb8abd22e26f2c6a7f22e94422ef34b10e587 \
	'UBWC module'
verify_file "$msm_module" 644 \
	eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082 \
	'firmware-request-only MSM module'
verify_file "$helper" 755 \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	'one-open helper'
verify_file "$firmware_root/qcom/a660_sqe.fw" 644 \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	'SQE firmware'
verify_file "$firmware_root/qcom/a660_gmu.bin" 644 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	'GMU firmware'
[ ! -e "$firmware_root/qcom/sm8350/a660_zap.mbn" ] ||
	fail 'ZAP firmware exists in request-only root'
[ "$(find "$lower" -xdev -type f \
	\( -name a660_sqe.fw -o -name a660_gmu.bin -o -name a660_zap.mbn \) |
	wc -l)" -eq 2 ] ||
	fail 'A660 firmware file count is not exactly two'
[ "$(find "$module_root" -type f -name '*.ko' | wc -l)" -eq 7 ] ||
	fail 'module count is not exactly seven'

modinfo -p "$msm_module" |
	grep -Fxq \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)' ||
	fail 'MSM module lacks request-only parameter'
modinfo -p "$msm_module" | grep -Fxq 'separate_gpu_kms: (bool)' ||
	fail 'MSM module lacks separate GPU parameter'
for module in gpucc_sm8350 msm drm_exec drm_gpuvm gpu_sched mdt_loader \
	ubwc_config
do
	[ ! -d "/sys/module/$module" ] ||
		fail "module is already loaded; use a fresh candidate: $module"
done

dt=/sys/firmware/devicetree/base
gpucc_dt=$dt/soc@0/clock-controller@3d90000
smmu_dt=$dt/soc@0/iommu@3da0000
gpu_dt=$dt/soc@0/gpu@3d00000
gmu_dt=$dt/soc@0/gmu@3d6a000
for node in "$gpucc_dt" "$smmu_dt" "$gpu_dt" "$gmu_dt"; do
	[ "$(tr -d '\000' <"$node/status")" = okay ] ||
		fail "GPU diagnostic node is not enabled: $node"
done

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
	[ ! -e "$device/driver" ] || fail 'GPU diagnostic device is already bound'
done
[ -d /sys/bus/platform/drivers/arm-smmu ] ||
	fail 'built-in ARM SMMU driver is absent'
smmu_name=$(basename "$smmu_device")
[ "$smmu_name" = 3da0000.iommu ] ||
	fail 'Adreno SMMU platform-device name is unexpected'
driver_override_check=$lower/usr/local/sbin/rog5-adreno-smmu-driver-override-check
verify_file "$driver_override_check" 755 \
	884dfcd287dd892ec0698bedaa4475045967459282811da640e48f5f7d503e45 \
	'driver_override checker'
driver_override_state=$(
	"$driver_override_check" "$smmu_device/driver_override"
) || fail 'Adreno SMMU driver_override is not the reviewed unset state'
[ "$driver_override_state" = unset-null-representation ] ||
	fail 'Adreno SMMU driver_override classification is unexpected'
[ "$(cat /sys/bus/platform/drivers_autoprobe)" = 1 ] ||
	fail 'platform driver autoprobe is disabled'
drivers_probe=/sys/bus/platform/drivers_probe
[ "$(stat -c '%u:%g:%a' "$drivers_probe")" = 0:0:200 ] &&
	[ -w "$drivers_probe" ] ||
	fail 'platform drivers_probe control is not exact'

[ -z "$(find /dev/dri -maxdepth 1 -name 'renderD*' -print 2>/dev/null)" ] ||
	fail 'render node exists before module load'
check_no_drm_fds() {
	for fd in /proc/[0-9]*/fd/*; do
		[ -L "$fd" ] || continue
		case $(readlink "$fd" 2>/dev/null || true) in
			/dev/dri/*) return 1 ;;
		esac
	done
	return 0
}
check_no_drm_fds || fail 'a process holds a DRM descriptor before module load'

firmware_pattern='a660_sqe.fw|a660_gmu.bin|a660_zap.mbn'
success_marker='A660 firmware-only passed; reject open'
failure_marker='A660 firmware-only failed:'
fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
fault_pattern='(IOMMU|arm-smmu).*[^[:alnum:]_]fault([^[:alnum:]_]|$)|(context|global)[[:space:]]+fault([^[:alnum:]_]|$)'
for pattern in "$firmware_pattern" "$success_marker" "$failure_marker"; do
	[ "$(dmesg | grep -Ec "$pattern" || true)" -eq 0 ] ||
		fail "request-only evidence exists before probe: $pattern"
done
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	fail 'fatal kernel signature exists before probe'
[ "$(dmesg | grep -Eic "$fault_pattern" || true)" -eq 0 ] ||
	fail 'IOMMU fault signature exists before probe'
dmesg_start=$(( $(dmesg | wc -l) + 1 ))
reprobe_attempted=0

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

state_dir=$(mktemp -d /run/rog5-a660-firmware-request-only.XXXXXX)
# Positional parameters are intentionally expanded by the child shell.
# shellcheck disable=SC2016
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-a660-firmware-request-only: watchdog expired" >&8
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

echo "BEGIN a660-firmware-request-only watchdog=${probe_timeout}s settle=${settle_seconds}s"
echo 'rog5-a660-firmware-request-only: begin' >/dev/kmsg
dmesg --follow-new &
log_follower_pid=$!
sleep 1
kill -0 "$log_follower_pid" || fail 'live kernel-log follower did not start'

post_fail() {
	reason=$1
	echo "EVIDENCE a660-firmware-request-only reason=$reason"
	echo "EVIDENCE system_state=$(systemctl is-system-running 2>/dev/null ||
		true)"
	echo 'EVIDENCE failed_units_begin'
	systemctl --failed --no-legend --plain 2>/dev/null || true
	echo 'EVIDENCE failed_units_end'
	echo 'EVIDENCE new_dmesg_begin'
	dmesg | tail -n +"$dmesg_start" | tail -n 260
	echo 'EVIDENCE new_dmesg_end'
	fail "$reason"
}

echo 'rog5-a660-firmware-request-only: GPUCC load begin' >/dev/kmsg
insmod "$gpucc_module" probe_trace=1 ||
	post_fail 'GPUCC module load failed'
[ -e "$gpucc_device/driver" ] || post_fail 'GPUCC did not bind'
[ "$(readlink -f "$gpucc_device/driver")" = \
	/sys/bus/platform/drivers/sm8350-gpucc ] ||
	post_fail 'GPUCC bound an unexpected driver'

for _ in 1 2 3 4 5; do
	[ ! -e "$smmu_device/driver" ] || break
	sleep 1
done
if [ ! -e "$smmu_device/driver" ]; then
	echo 'rog5-a660-firmware-request-only: exact SMMU reprobe begin' \
		>/dev/kmsg
	printf '%s\n' "$smmu_name" >"$drivers_probe" ||
		post_fail 'exact Adreno SMMU reprobe failed'
	reprobe_attempted=1
fi
[ -e "$smmu_device/driver" ] ||
	post_fail 'Adreno SMMU did not bind after at most one exact reprobe'
[ "$(readlink -f "$smmu_device/driver")" = \
	/sys/bus/platform/drivers/arm-smmu ] ||
	post_fail 'Adreno SMMU bound an unexpected driver'

insmod "$drm_exec_module" || post_fail 'drm_exec load failed'
insmod "$drm_gpuvm_module" || post_fail 'drm_gpuvm load failed'
insmod "$gpu_sched_module" || post_fail 'gpu_sched load failed'
insmod "$mdt_module" || post_fail 'mdt_loader load failed'
insmod "$ubwc_module" || post_fail 'ubwc_config load failed'
echo 'rog5-a660-firmware-request-only: MSM load begin' >/dev/kmsg
insmod "$msm_module" separate_gpu_kms=1 firmware_request_only=1 ||
	post_fail 'request-only MSM module load failed'

for module in gpucc_sm8350 msm drm_exec drm_gpuvm gpu_sched mdt_loader \
	ubwc_config
do
	[ -d "/sys/module/$module" ] ||
		post_fail "module did not remain loaded: $module"
done
[ "$(cat /sys/module/msm/parameters/separate_gpu_kms)" = Y ] ||
	post_fail 'separate_gpu_kms is not enabled'
[ "$(cat /sys/module/msm/parameters/firmware_request_only)" = Y ] ||
	post_fail 'firmware_request_only is not enabled'
[ "$(stat -c %a /sys/module/msm/parameters/firmware_request_only)" = 400 ] ||
	post_fail 'firmware_request_only became writable'
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
	for _ in 1 2 3 4 5 6 7 8 9 10; do
		[ "$runtime_status" != suspended ] || break
		sleep 1
		runtime_status=$(cat "$runtime_path")
	done
	[ "$runtime_status" = suspended ] ||
		post_fail "device did not reach runtime suspend: $runtime_path"
done

gpu_groups=0
gmu_groups=0
for grouped in /sys/kernel/iommu_groups/*/devices/*; do
	[ -e "$grouped" ] || continue
	[ -L "$grouped/of_node" ] || continue
	case $(readlink -f "$grouped/of_node") in
		"$gpu_dt") gpu_groups=$((gpu_groups + 1)) ;;
		"$gmu_dt") gmu_groups=$((gmu_groups + 1)) ;;
	esac
done
[ "$gpu_groups" -eq 1 ] && [ "$gmu_groups" -eq 1 ] ||
	post_fail 'GPU/GMU IOMMU attachment count is not exact'

render_count=$(find /dev/dri -maxdepth 1 -type c -name 'renderD*' \
	-print 2>/dev/null | wc -l)
[ "$render_count" -eq 1 ] || post_fail 'render-node count is not one'
[ -c /dev/dri/renderD128 ] ||
	post_fail 'the sole render node is not /dev/dri/renderD128'
[ "$(find /sys/class/drm -mindepth 1 -maxdepth 1 -name 'card*-*' \
	-print 2>/dev/null | wc -l)" -eq 0 ] ||
	post_fail 'headless registration created a display connector'
check_no_drm_fds ||
	post_fail 'a process opened a DRM node before the helper'
for pattern in "$firmware_pattern" "$success_marker" "$failure_marker"; do
	[ "$(dmesg | tail -n +"$dmesg_start" |
		grep -Ec "$pattern" || true)" -eq 0 ] ||
		post_fail "premature request-only evidence appeared: $pattern"
done

open_dmesg_start=$(( $(dmesg | wc -l) + 1 ))
echo 'rog5-a660-firmware-request-only: exact one-open helper begin' >/dev/kmsg
set +e
helper_output=$("$helper" 2>&1)
helper_status=$?
set -e
[ "$helper_status" -eq 117 ] ||
	post_fail "one-open helper returned status $helper_status"
[ "$helper_output" = OPEN_ERRNO=117 ] ||
	post_fail 'one-open helper output is not exact'

open_log=$(dmesg | tail -n +"$open_dmesg_start")
[ "$(printf '%s\n' "$open_log" | grep -Fc "$success_marker")" -eq 1 ] ||
	post_fail 'request-only success marker count is not one'
[ "$(printf '%s\n' "$open_log" | grep -Fc "$failure_marker")" -eq 0 ] ||
	post_fail 'request-only failure marker appeared'
forbidden_open='a660_zap[.]mbn|qcom_scm|pas_auth|zap.shader|HFI|ucode|a6xx_gmu_start|GMU firmware|GPU hardware init'
if printf '%s\n' "$open_log" | grep -Ei "$forbidden_open"; then
	post_fail 'open crossed the firmware-only hardware boundary'
fi
check_no_drm_fds ||
	post_fail 'a DRM descriptor survived the failed open'

sleep "$settle_seconds"
settled_log=$(dmesg | tail -n +"$open_dmesg_start")
[ "$(printf '%s\n' "$settled_log" |
	grep -Fc "$success_marker")" -eq 1 ] ||
	post_fail 'request-only success marker changed during settling'
[ "$(printf '%s\n' "$settled_log" |
	grep -Fc "$failure_marker")" -eq 0 ] ||
	post_fail 'request-only failure marker appeared during settling'
if printf '%s\n' "$settled_log" | grep -Ei "$forbidden_open"; then
	post_fail 'later work crossed the firmware-only hardware boundary'
fi
check_no_drm_fds ||
	post_fail 'a DRM descriptor appeared during settling'
for runtime_path in "$smmu_device/power/runtime_status" \
	"$gmu_device/power/runtime_status"
do
	[ "$(cat "$runtime_path")" = suspended ] ||
		post_fail "runtime state changed after failed open: $runtime_path"
done

[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
	post_fail 'systemd regressed after request-only open'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	post_fail 'a systemd unit failed after request-only open'
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	post_fail 'physical block device appeared'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	post_fail 'block-backed mount appeared'
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
	post_fail 'thermal state is not safe after request-only open'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	post_fail 'fatal kernel signature appeared'
[ "$(dmesg | tail -n +"$dmesg_start" |
	grep -Eic "$fault_pattern|WARNING:|Call trace:|Unhandled fault|page fault" ||
	true)" -eq 0 ] ||
	post_fail 'new warning or fault appeared'

probe_safe=1
disarm_watchdog
trap - EXIT HUP INT TERM
printf 'PASS A660 firmware-request-only open_invocations=1 open_errno=117 firmware_requests=2 success_markers=1 zap=absent ucode=0 power=0 hfi=0 scm=0 drm_fds=0 storage=0 mounts=0 failed_units=0 iommu=2 render=1 thermal_zones=%s thermal_max_mC=%s exact_reprobe=%s driver_override=%s watchdog=disarmed\n' \
	"$thermal_count" "$thermal_max" "$reprobe_attempted" \
	"$driver_override_state"
