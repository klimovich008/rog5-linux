#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_MAINLINE_A660_UCODE_ALLOCATION:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_A660_UCODE_ALLOCATION=1 for one attended probe'
[ "$(id -u)" -eq 0 ] || fail 'attended probe requires root'

release=7.1.4-rog5-a660reg1
lower=/.rog5/root-ro
module_root=$lower/usr/lib/modules/$release
firmware_root=$lower/usr/lib/firmware
helper=$lower/usr/local/libexec/rog5-a660-ucode-allocation-open
acceptance=$lower/etc/rog5/a660-registration-v3-live.accepted
acceptance_sha=8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f
probe_timeout=${ROG5_PROBE_TIMEOUT:-110}
settle_seconds=${ROG5_PROBE_SETTLE:-20}

case $probe_timeout:$settle_seconds in
	*[!0-9:]*|:*|*:) fail 'probe timeout and settle interval must be integers' ;;
esac
[ "$probe_timeout" -ge 80 ] && [ "$probe_timeout" -le 180 ] ||
	fail 'ROG5_PROBE_TIMEOUT must be between 80 and 180 seconds'
[ "$settle_seconds" -ge 10 ] && [ "$settle_seconds" -le 40 ] ||
	fail 'ROG5_PROBE_SETTLE must be between 10 and 40 seconds'
[ "$probe_timeout" -ge $((settle_seconds + 60)) ] ||
	fail 'probe timeout must exceed settling by at least 60 seconds'

for command in awk basename cat cmp cp cut dmesg find findmnt grep id \
	insmod ip kill mktemp modinfo mount ps readlink rm rmdir sed setsid \
	sha256sum sleep sort stat systemctl tail tr uname uniq wait wc; do
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
	fail 'physical block device is present before ucode-allocation probe'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount is present before ucode-allocation probe'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	fail 'USB network carrier is down before ucode-allocation probe'
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
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	'ucode-allocation MSM module'
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
	fail 'ZAP firmware exists in ucode-allocation root'
[ "$(find "$lower" -xdev -type f \
	\( -name a660_sqe.fw -o -name a660_gmu.bin -o -name a660_zap.mbn \) |
	wc -l)" -eq 2 ] ||
	fail 'A660 firmware file count is not exactly two'
[ "$(find "$module_root" -type f -name '*.ko' | wc -l)" -eq 7 ] ||
	fail 'module count is not exactly seven'

modinfo -p "$msm_module" |
	grep -Fxq \
	'ucode_allocation_only:Allocate and roll back exact A660 ucode once before GPU power (bool)' ||
	fail 'MSM module lacks ucode-allocation parameter'
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
success_marker='A660 ucode-allocation-only passed and rolled back; reject open'
failure_marker='A660 ucode-allocation-only failed:'
fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
fault_pattern='(IOMMU|arm-smmu).*[^[:alnum:]_]fault([^[:alnum:]_]|$)|(context|global)[[:space:]]+fault([^[:alnum:]_]|$)'
for pattern in "$firmware_pattern" "$success_marker" "$failure_marker"; do
	[ "$(dmesg | grep -Ec "$pattern" || true)" -eq 0 ] ||
		fail "ucode-allocation evidence exists before probe: $pattern"
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
trace_active=0
trace_root=/sys/kernel/tracing
trace_snapshot=
trace_events='rog5_ucode_diag
rog5_ucode_diag_ret
rog5_ucode_vma_map
rog5_ucode_vma_map_ret
rog5_ucode_vma_unmap
rog5_ucode_vma_close
rog5_ucode_gem_unpin
rog5_ucode_gem_free
rog5_ucode_get_vaddr
rog5_ucode_put_vaddr
rog5_ucode_kernel_put
rog5_ucode_unload
rog5_ucode_fw_request
rog5_ucode_fw_release
rog5_ucode_pm_resume
rog5_ucode_runtime_resume
rog5_ucode_a6xx_pm_resume
rog5_ucode_gmu_resume
rog5_ucode_hw_init
rog5_ucode_a6xx_hw_init
rog5_ucode_zap_init
rog5_ucode_scm_pas
rog5_ucode_scm_aperture'

stop_trace() {
	trace_status=0
	set +e
	printf '0\n' >"$trace_root/tracing_on" || trace_status=1
	if [ -n "$trace_snapshot" ]; then
		cp "$trace_root/trace" "$trace_snapshot" || trace_status=1
	fi
	printf '\n' >"$trace_root/set_event_pid" || trace_status=1
	if [ -d "$trace_root/events/rog5_ucode" ]; then
		printf '0\n' >"$trace_root/events/rog5_ucode/enable" ||
			trace_status=1
	fi
	for event in $trace_events; do
		printf '%s\n' "-:rog5_ucode/$event" \
			>>"$trace_root/kprobe_events" || trace_status=1
	done
	[ ! -d "$trace_root/events/rog5_ucode" ] || trace_status=1
	trace_active=0
	set -e
	[ "$trace_status" -eq 0 ]
}

disarm_watchdog() {
	[ "$probe_safe" = 1 ] || return 0
	set +e
	if [ "$trace_active" = 1 ]; then
		stop_trace
	fi
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
		rm -f "$state_dir/armed" "$state_dir/helper.out" \
			"$state_dir/trace" "$state_dir/gem.before" \
			"$state_dir/gem.after" "$state_dir/maps" \
			"$state_dir/unmaps" "$state_dir/closes" \
			"$state_dir/unpins" "$state_dir/frees" \
			"$state_dir/vmaps" "$state_dir/vunmaps"
		rmdir "$state_dir" 2>/dev/null
	fi
	watchdog_pid=
	log_follower_pid=
	state_dir=
	set -e
}
trap disarm_watchdog EXIT
trap 'exit 1' HUP INT TERM

state_dir=$(mktemp -d /run/rog5-a660-ucode-allocation.XXXXXX)
trace_snapshot=$state_dir/trace
# Positional parameters are intentionally expanded by the child shell.
# shellcheck disable=SC2016
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-a660-ucode-allocation: watchdog expired" >&8
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

echo "BEGIN a660-ucode-allocation watchdog=${probe_timeout}s settle=${settle_seconds}s"
echo 'rog5-a660-ucode-allocation: begin' >/dev/kmsg
dmesg --follow-new &
log_follower_pid=$!
sleep 1
kill -0 "$log_follower_pid" || fail 'live kernel-log follower did not start'

post_fail() {
	reason=$1
	echo "EVIDENCE a660-ucode-allocation reason=$reason"
	echo "EVIDENCE system_state=$(systemctl is-system-running 2>/dev/null ||
		true)"
	echo 'EVIDENCE failed_units_begin'
	systemctl --failed --no-legend --plain 2>/dev/null || true
	echo 'EVIDENCE failed_units_end'
	if [ -s "$trace_snapshot" ]; then
		echo 'EVIDENCE ucode_trace_begin'
		tail -n 260 "$trace_snapshot"
		echo 'EVIDENCE ucode_trace_end'
	elif [ "$trace_active" = 1 ]; then
		echo 'EVIDENCE live_ucode_trace_begin'
		tail -n 260 "$trace_root/trace" 2>/dev/null || true
		echo 'EVIDENCE live_ucode_trace_end'
	fi
	echo 'EVIDENCE new_dmesg_begin'
	dmesg | tail -n +"$dmesg_start" | tail -n 300
	echo 'EVIDENCE new_dmesg_end'
	fail "$reason"
}

echo 'rog5-a660-ucode-allocation: GPUCC load begin' >/dev/kmsg
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
	echo 'rog5-a660-ucode-allocation: exact SMMU reprobe begin' \
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
echo 'rog5-a660-ucode-allocation: MSM load begin' >/dev/kmsg
insmod "$msm_module" separate_gpu_kms=1 ucode_allocation_only=1 ||
	post_fail 'ucode-allocation MSM module load failed'

for module in gpucc_sm8350 msm drm_exec drm_gpuvm gpu_sched mdt_loader \
	ubwc_config
do
	[ -d "/sys/module/$module" ] ||
		post_fail "module did not remain loaded: $module"
done
[ "$(cat /sys/module/msm/parameters/separate_gpu_kms)" = Y ] ||
	post_fail 'separate_gpu_kms is not enabled'
[ "$(cat /sys/module/msm/parameters/ucode_allocation_only)" = Y ] ||
	post_fail 'ucode_allocation_only is not enabled'
[ "$(stat -c %a /sys/module/msm/parameters/ucode_allocation_only)" = 400 ] ||
	post_fail 'ucode_allocation_only became writable'
[ "$(cat /sys/module/msm/parameters/firmware_request_only)" = N ] ||
	post_fail 'firmware_request_only=N is not preserved'
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
		post_fail "premature ucode-allocation evidence appeared: $pattern"
done

debug_root=/sys/kernel/debug
if [ "$(findmnt -n -o FSTYPE "$debug_root" 2>/dev/null || true)" != debugfs ]; then
	mount -t debugfs debugfs "$debug_root" ||
		post_fail 'debugfs mount failed'
fi
[ "$(findmnt -n -o FSTYPE "$debug_root")" = debugfs ] ||
	post_fail 'debugfs is unavailable'
gem_debugfs=$debug_root/dri/128/gem
[ -r "$gem_debugfs" ] || post_fail 'render-minor GEM snapshot is unavailable'
cat "$gem_debugfs" >"$state_dir/gem.before" ||
	post_fail 'pre-open GEM snapshot failed'

if [ "$(findmnt -n -o FSTYPE "$trace_root" 2>/dev/null || true)" != tracefs ]; then
	mount -t tracefs tracefs "$trace_root" ||
		post_fail 'tracefs mount failed'
fi
[ "$(findmnt -n -o FSTYPE "$trace_root")" = tracefs ] ||
	post_fail 'tracefs is unavailable'
[ ! -s "$trace_root/kprobe_events" ] ||
	post_fail 'an unrelated kprobe event already exists'
[ ! -d "$trace_root/events/rog5_ucode" ] ||
	post_fail 'stale ucode-allocation trace group exists'
for symbol in adreno_load_ucode_only msm_gem_vma_map \
	msm_gem_vma_unmap msm_gem_vma_close msm_gem_unpin_iova \
	msm_gem_free_object msm_gem_get_vaddr msm_gem_put_vaddr \
	msm_gem_kernel_put a6xx_ucode_unload msm_gpu_pm_resume \
	adreno_runtime_resume a6xx_pm_resume a6xx_gmu_resume adreno_hw_init \
	a6xx_hw_init a6xx_zap_shader_init
do
	[ "$(grep -Ec \
		"[[:space:]]${symbol}[[:space:]]+\\[msm\\]$" /proc/kallsyms)" -eq 1 ] ||
		post_fail "required MSM trace symbol is not unique: $symbol"
done
for symbol in request_firmware_direct release_firmware \
	qcom_scm_pas_auth_and_reset qcom_scm_set_gpu_smmu_aperture
do
	[ "$(grep -Ec "[[:space:]]$symbol$" /proc/kallsyms)" -eq 1 ] ||
		post_fail "required core trace symbol is not unique: $symbol"
done

# shellcheck disable=SC2016
if ! printf '%s\n' \
	'p:rog5_ucode/rog5_ucode_diag msm:adreno_load_ucode_only dev=$arg1:x64' \
	'r:rog5_ucode/rog5_ucode_diag_ret msm:adreno_load_ucode_only ret=$retval:s64' \
	'p:rog5_ucode/rog5_ucode_vma_map msm:msm_gem_vma_map vma=$arg1:x64' \
	'r:rog5_ucode/rog5_ucode_vma_map_ret msm:msm_gem_vma_map ret=$retval:s64' \
	'p:rog5_ucode/rog5_ucode_vma_unmap msm:msm_gem_vma_unmap vma=$arg1:x64' \
	'p:rog5_ucode/rog5_ucode_vma_close msm:msm_gem_vma_close vma=$arg1:x64' \
	'p:rog5_ucode/rog5_ucode_gem_unpin msm:msm_gem_unpin_iova obj=$arg1:x64' \
	'p:rog5_ucode/rog5_ucode_gem_free msm:msm_gem_free_object obj=$arg1:x64' \
	'p:rog5_ucode/rog5_ucode_get_vaddr msm:msm_gem_get_vaddr obj=$arg1:x64' \
	'p:rog5_ucode/rog5_ucode_put_vaddr msm:msm_gem_put_vaddr obj=$arg1:x64' \
	'p:rog5_ucode/rog5_ucode_kernel_put msm:msm_gem_kernel_put obj=$arg1:x64' \
	'p:rog5_ucode/rog5_ucode_unload msm:a6xx_ucode_unload gpu=$arg1:x64' \
	'p:rog5_ucode/rog5_ucode_fw_request request_firmware_direct' \
	'p:rog5_ucode/rog5_ucode_fw_release release_firmware fw=$arg1:x64' \
	'p:rog5_ucode/rog5_ucode_pm_resume msm:msm_gpu_pm_resume' \
	'p:rog5_ucode/rog5_ucode_runtime_resume msm:adreno_runtime_resume' \
	'p:rog5_ucode/rog5_ucode_a6xx_pm_resume msm:a6xx_pm_resume' \
	'p:rog5_ucode/rog5_ucode_gmu_resume msm:a6xx_gmu_resume' \
	'p:rog5_ucode/rog5_ucode_hw_init msm:adreno_hw_init' \
	'p:rog5_ucode/rog5_ucode_a6xx_hw_init msm:a6xx_hw_init' \
	'p:rog5_ucode/rog5_ucode_zap_init msm:a6xx_zap_shader_init' \
	'p:rog5_ucode/rog5_ucode_scm_pas qcom_scm_pas_auth_and_reset' \
	'p:rog5_ucode/rog5_ucode_scm_aperture qcom_scm_set_gpu_smmu_aperture' \
	>>"$trace_root/kprobe_events"
then
	post_fail 'ucode-allocation trace registration failed'
fi
[ -d "$trace_root/events/rog5_ucode" ] ||
	post_fail 'ucode-allocation trace group was not created'
printf '1\n' >"$trace_root/events/rog5_ucode/enable" ||
	post_fail 'ucode-allocation trace enable failed'
trace_active=1

open_dmesg_start=$(( $(dmesg | wc -l) + 1 ))
echo 'rog5-a660-ucode-allocation: exact one-open helper begin' >/dev/kmsg
sh -c 'kill -STOP "$$"; exec "$1"' sh "$helper" \
	>"$state_dir/helper.out" 2>&1 &
helper_pid=$!
helper_stopped=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
	if [ -r "/proc/$helper_pid/status" ] &&
		[ "$(awk '/^State:/ { print $2 }' \
			"/proc/$helper_pid/status")" = T ]; then
		helper_stopped=1
		break
	fi
	sleep 1
done
[ "$helper_stopped" -eq 1 ] ||
	post_fail 'one-open helper did not stop at the trace barrier'
printf '%s\n' "$helper_pid" >"$trace_root/set_event_pid" ||
	post_fail 'set_event_pid rejected the exact helper PID'
printf '\n' >"$trace_root/trace" ||
	post_fail 'trace buffer clear failed'
printf '1\n' >"$trace_root/tracing_on" ||
	post_fail 'trace start failed'
kill -CONT "$helper_pid" ||
	post_fail 'one-open helper could not cross the trace barrier'
set +e
wait "$helper_pid"
helper_status=$?
set -e
if ! stop_trace; then
	post_fail 'trace cleanup failed'
fi
helper_output=$(cat "$state_dir/helper.out")
[ "$helper_status" -eq 117 ] ||
	post_fail "one-open helper returned status $helper_status"
[ "$helper_output" = OPEN_ERRNO=117 ] ||
	post_fail 'one-open helper output is not exact'

event_count() {
	event=$1
	grep -c "$event:" "$trace_snapshot" 2>/dev/null || true
}

require_event_count() {
	event=$1
	expected=$2
	label=$3
	actual=$(event_count "$event")
	[ "$actual" -eq "$expected" ] ||
		post_fail "$label trace count is $actual, expected $expected"
}

extract_field() {
	event=$1
	field=$2
	awk -v marker="$event:" -v wanted="$field=" '
		index($0, marker) {
			for (i = 1; i <= NF; i++) {
				if (index($i, wanted) == 1) {
					sub(wanted, "", $i)
					print $i
				}
			}
		}
	' "$trace_snapshot" | sort
}

[ -s "$trace_snapshot" ] || post_fail 'PID-filtered trace is empty'
require_event_count rog5_ucode_diag 1 'diagnostic entry'
require_event_count rog5_ucode_diag_ret 1 'diagnostic return'
[ "$(grep -c 'rog5_ucode_diag_ret:.*ret=0' "$trace_snapshot" || true)" -eq 1 ] ||
	post_fail 'diagnostic return is not exactly zero'
require_event_count rog5_ucode_vma_map 3 'VMA map'
require_event_count rog5_ucode_vma_map_ret 3 'VMA map return'
[ "$(grep -c 'rog5_ucode_vma_map_ret:.*ret=0' \
	"$trace_snapshot" || true)" -eq 3 ] ||
	post_fail 'one or more VMA maps failed'
require_event_count rog5_ucode_vma_unmap 3 'VMA unmap'
require_event_count rog5_ucode_vma_close 3 'VMA close'
require_event_count rog5_ucode_gem_unpin 3 'GEM unpin'
require_event_count rog5_ucode_gem_free 3 'GEM free'
require_event_count rog5_ucode_get_vaddr 4 'CPU vmap'
require_event_count rog5_ucode_put_vaddr 4 'CPU vunmap'
require_event_count rog5_ucode_kernel_put 2 'kernel GEM put'
require_event_count rog5_ucode_unload 1 'ucode unload'
require_event_count rog5_ucode_fw_request 2 'firmware request'
require_event_count rog5_ucode_fw_release 2 'firmware release'
for forbidden_event in rog5_ucode_pm_resume rog5_ucode_runtime_resume \
	rog5_ucode_a6xx_pm_resume rog5_ucode_gmu_resume rog5_ucode_hw_init \
	rog5_ucode_a6xx_hw_init rog5_ucode_zap_init rog5_ucode_scm_pas \
	rog5_ucode_scm_aperture
do
	require_event_count "$forbidden_event" 0 'forbidden power/HFI/ZAP/SCM'
done

extract_field rog5_ucode_vma_map vma >"$state_dir/maps"
extract_field rog5_ucode_vma_unmap vma >"$state_dir/unmaps"
extract_field rog5_ucode_vma_close vma >"$state_dir/closes"
extract_field rog5_ucode_gem_unpin obj >"$state_dir/unpins"
extract_field rog5_ucode_gem_free obj >"$state_dir/frees"
extract_field rog5_ucode_get_vaddr obj >"$state_dir/vmaps"
extract_field rog5_ucode_put_vaddr obj >"$state_dir/vunmaps"
for exact in maps unmaps closes unpins frees; do
	[ "$(wc -l <"$state_dir/$exact")" -eq 3 ] ||
		post_fail "$exact pointer count is not three"
	[ "$(uniq "$state_dir/$exact" | wc -l)" -eq 3 ] ||
		post_fail "$exact pointers are not unique"
done
[ "$(wc -l <"$state_dir/vmaps")" -eq 4 ] &&
	[ "$(wc -l <"$state_dir/vunmaps")" -eq 4 ] ||
	post_fail 'CPU vmap pointer count is not balanced'
cmp "$state_dir/maps" "$state_dir/unmaps" ||
	post_fail 'mapped and unmapped VMA pointer sets differ'
cmp "$state_dir/maps" "$state_dir/closes" ||
	post_fail 'mapped and closed VMA pointer sets differ'
cmp "$state_dir/unpins" "$state_dir/frees" ||
	post_fail 'unpinned and freed GEM pointer sets differ'
cmp "$state_dir/vmaps" "$state_dir/vunmaps" ||
	post_fail 'CPU vmap and vunmap pointer multisets differ'

open_log=$(dmesg | tail -n +"$open_dmesg_start")
[ "$(printf '%s\n' "$open_log" | grep -Fc "$success_marker")" -eq 1 ] ||
	post_fail 'ucode-allocation success marker count is not one'
[ "$(printf '%s\n' "$open_log" | grep -Fc "$failure_marker")" -eq 0 ] ||
	post_fail 'ucode-allocation failure marker appeared'
[ "$(printf '%s\n' "$open_log" | grep -Fc a660_sqe.fw)" -eq 1 ] ||
	post_fail 'SQE firmware request count is not one'
[ "$(printf '%s\n' "$open_log" | grep -Fc a660_gmu.bin)" -eq 1 ] ||
	post_fail 'GMU firmware request count is not one'
forbidden_open='a660_zap[.]mbn|qcom_scm|pas_auth|zap.shader|HFI|a6xx_gmu_start|GPU hardware init|GPU fault|RBBM|CP_SQE'
if printf '%s\n' "$open_log" | grep -Ei "$forbidden_open"; then
	post_fail 'open crossed the ucode-allocation hardware boundary'
fi
check_no_drm_fds ||
	post_fail 'a DRM descriptor survived the failed open'

sleep "$settle_seconds"
cat "$gem_debugfs" >"$state_dir/gem.after" ||
	post_fail 'post-open GEM snapshot failed'
cmp "$state_dir/gem.before" "$state_dir/gem.after" ||
	post_fail 'pre/post GEM snapshots differ'
settled_log=$(dmesg | tail -n +"$open_dmesg_start")
[ "$(printf '%s\n' "$settled_log" |
	grep -Fc "$success_marker")" -eq 1 ] ||
	post_fail 'ucode-allocation success marker changed during settling'
[ "$(printf '%s\n' "$settled_log" |
	grep -Fc "$failure_marker")" -eq 0 ] ||
	post_fail 'ucode-allocation failure marker appeared during settling'
if printf '%s\n' "$settled_log" | grep -Ei "$forbidden_open"; then
	post_fail 'later work crossed the ucode-allocation hardware boundary'
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
	post_fail 'systemd regressed after ucode-allocation open'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	post_fail 'a systemd unit failed after ucode-allocation open'
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
	post_fail 'thermal state is not safe after ucode-allocation open'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	post_fail 'fatal kernel signature appeared'
[ "$(dmesg | tail -n +"$dmesg_start" |
	grep -Eic "$fault_pattern|WARNING:|Call trace:|Unhandled fault|page fault" ||
	true)" -eq 0 ] ||
	post_fail 'new warning or fault appeared'

probe_safe=1
disarm_watchdog
trap - EXIT HUP INT TERM
printf 'PASS A660 ucode-allocation open_invocations=1 open_errno=117 firmware_requests=2 firmware_releases=2 success_markers=1 maps=3 unmaps=3 closes=3 gem_frees=3 cpu_vmaps=4 cpu_vunmaps=4 gem_snapshot=equal zap=absent power=0 hfi=0 scm=0 drm_fds=0 storage=0 mounts=0 failed_units=0 iommu=2 render=1 thermal_zones=%s thermal_max_mC=%s exact_reprobe=%s driver_override=%s watchdog=disarmed\n' \
	"$thermal_count" "$thermal_max" "$reprobe_attempted" \
	"$driver_override_state"
