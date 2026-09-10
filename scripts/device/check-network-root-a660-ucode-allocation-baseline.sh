#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

release=7.1.4-rog5-a660reg1
lower=/.rog5/root-ro
module_root=$lower/usr/lib/modules/$release
firmware_root=$lower/usr/lib/firmware
helper=$lower/usr/local/libexec/rog5-a660-ucode-allocation-open
seal=$lower/etc/rog5/a660-ucode-allocation-export
acceptance=$lower/etc/rog5/a660-registration-v3-live.accepted

for command in awk basename cat cut dmesg find findmnt grep id ip modinfo \
	readlink sed sha256sum sleep stat systemctl tail tr uname wc zcat; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

[ "$(uname -r)" = "$release" ] || fail 'unexpected kernel'
[ -r /proc/config.gz ] || fail 'running kernel config is unavailable'
for config in CONFIG_KPROBE_EVENTS=y CONFIG_KALLSYMS_ALL=y CONFIG_DEBUG_FS=y; do
	zcat /proc/config.gz | grep -qx "$config" ||
		fail "running kernel config omits: $config"
done
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

[ "$(findmnt -n -o FSTYPE /)" = overlay ] || fail 'root is not OverlayFS'
[ "$(findmnt -n -o SOURCE "$lower")" = 169.254.77.1:/ ] ||
	fail 'unexpected NFS lower source'
findmnt -n -o OPTIONS "$lower" | tr ',' '\n' | grep -qx ro ||
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

for parameter in rog5_qcom_cc_probe_trace rog5_ccf_register_trace \
	rog5_rcg2_parent_trace
do
	trace_path=/sys/module/kernel/parameters/$parameter
	[ -r "$trace_path" ] || fail "$parameter core parameter is absent"
	[ "$(cat "$trace_path")" = N ] ||
		fail "$parameter core parameter is enabled"
	[ "$(stat -c %a "$trace_path")" = 400 ] ||
		fail "$parameter core parameter became writable"
done

[ -f "$seal" ] && [ ! -L "$seal" ] ||
	fail 'ucode-allocation export seal is absent'
[ "$(stat -c '%u:%g:%a' "$seal")" = 0:0:444 ] ||
	fail 'ucode-allocation export seal metadata is not exact'
grep -qx 'diagnostic_generation=v5' "$seal"
grep -qx 'registration_acceptance=ACCEPTED_A660_REGISTRATION_V3' "$seal"
grep -qx 'firmware_policy=SQE_GMU_ONLY_ZAP_ABSENT' "$seal"
grep -qx 'open_policy=EXACTLY_ONE_EUCLEAN' "$seal"
grep -qx 'trace_policy=PID_FILTERED_EXACT_BALANCE' "$seal"
grep -qx 'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' "$seal"

[ -f "$acceptance" ] && [ ! -L "$acceptance" ] ||
	fail 'registration-v3 live acceptance marker is absent'
[ "$(stat -c '%u:%g:%a' "$acceptance")" = 0:0:444 ] ||
	fail 'registration-v3 marker metadata is not exact'
[ "$(sha256sum "$acceptance" | cut -d ' ' -f 1)" = \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f ] ||
	fail 'registration-v3 marker hash mismatch'
grep -qx \
	'live_report_sha256=2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79' \
	"$acceptance"
grep -qx 'v3_reuse=FORBIDDEN' "$acceptance"

check_root_file() {
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

check_root_file "$firmware_root/qcom/a660_sqe.fw" 644 \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	'SQE firmware'
check_root_file "$firmware_root/qcom/a660_gmu.bin" 644 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	'GMU firmware'
[ ! -e "$firmware_root/qcom/sm8350/a660_zap.mbn" ] ||
	fail 'ZAP firmware exists in immutable lower'
[ "$(find "$lower" -xdev -type f \
	\( -name a660_sqe.fw -o -name a660_gmu.bin -o -name a660_zap.mbn \) |
	wc -l)" -eq 2 ] ||
	fail 'immutable lower A660 firmware file count is not two'

check_root_file "$helper" 755 \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	'one-open helper'
[ "$(find "$module_root" -type f -name '*.ko' | wc -l)" -eq 7 ] ||
	fail 'ucode-allocation module set is not exact'
check_root_file \
	"$module_root/kernel/drivers/clk/qcom/gpucc-sm8350.ko" 644 \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
	'GPUCC module'
msm_module=$module_root/kernel/drivers/gpu/drm/msm/msm.ko
check_root_file "$msm_module" 644 \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	'ucode-allocation MSM module'
modinfo -p "$msm_module" |
	grep -Fxq \
	'ucode_allocation_only:Allocate and roll back exact A660 ucode once before GPU power (bool)' ||
	fail 'MSM module lacks the ucode-allocation parameter'
modinfo -p "$msm_module" |
	grep -Fxq \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)' ||
	fail 'MSM module lacks the predecessor request-only parameter'

dt=/sys/firmware/devicetree/base
gpucc_dt=$dt/soc@0/clock-controller@3d90000
smmu_dt=$dt/soc@0/iommu@3da0000
gpu_dt=$dt/soc@0/gpu@3d00000
gmu_dt=$dt/soc@0/gmu@3d6a000
for node in "$gpucc_dt" "$smmu_dt" "$gpu_dt" "$gmu_dt"; do
	[ "$(tr -d '\000' <"$node/status")" = okay ] ||
		fail "GPU diagnostic node is not enabled: $node"
done
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

for module in gpucc_sm8350 msm drm_exec drm_gpuvm gpu_sched mdt_loader \
	ubwc_config
do
	[ ! -d "/sys/module/$module" ] ||
		fail "diagnostic module is already loaded: $module"
done
[ -d /sys/bus/platform/drivers/arm-smmu ] ||
	fail 'built-in ARM SMMU driver is absent'
[ ! -d /sys/bus/platform/drivers/adreno ] ||
	fail 'Adreno driver exists before guarded module load'
for target in "$gpucc_dt" "$smmu_dt" "$gpu_dt" "$gmu_dt"; do
	count=0
	for device in /sys/bus/platform/devices/*; do
		[ -L "$device/of_node" ] || continue
		[ "$(readlink -f "$device/of_node")" = "$target" ] || continue
		count=$((count + 1))
		[ ! -e "$device/driver" ] ||
			fail "GPU diagnostic device is already bound: $target"
	done
	[ "$count" -eq 1 ] ||
		fail "GPU diagnostic platform-device count is not one: $target"
done

[ -z "$(find /dev/dri -maxdepth 1 -name 'renderD*' -print 2>/dev/null)" ] ||
	fail 'render node exists before registration'
for fd in /proc/[0-9]*/fd/*; do
	[ -L "$fd" ] || continue
	case $(readlink "$fd" 2>/dev/null || true) in
		/dev/dri/*) fail 'a process already holds a DRM descriptor' ;;
	esac
done

trace_root=/sys/kernel/tracing
if [ "$(findmnt -n -o FSTYPE "$trace_root" 2>/dev/null || true)" = tracefs ]; then
	[ ! -s "$trace_root/kprobe_events" ] ||
		fail 'an unrelated kprobe event already exists'
	[ ! -d "$trace_root/events/rog5_ucode" ] ||
		fail 'stale ucode-allocation trace events exist'
fi
for symbol in request_firmware_direct release_firmware \
	qcom_scm_pas_auth_and_reset qcom_scm_set_gpu_smmu_aperture; do
	[ "$(grep -Ec "[[:space:]]$symbol$" /proc/kallsyms)" -eq 1 ] ||
		fail "required core trace symbol is not unique: $symbol"
done

firmware_pattern='a660_sqe.fw|a660_gmu.bin|a660_zap.mbn'
success_marker='A660 ucode-allocation-only passed and rolled back; reject open'
failure_marker='A660 ucode-allocation-only failed:'
for pattern in "$firmware_pattern" "$success_marker" "$failure_marker"; do
	[ "$(dmesg | grep -Ec "$pattern" || true)" -eq 0 ] ||
		fail "ucode-allocation evidence exists before probe: $pattern"
done
fatal='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
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

dmesg_line=$(( $(dmesg | wc -l) + 1 ))
sleep 12
new_log=$(dmesg | tail -n +"$dmesg_line")
if printf '%s\n' "$new_log" |
	grep -Ei "$fatal|$fault|WARNING:|Call trace:|Unhandled fault|page fault"
then
	fail 'kernel log regressed during quiet baseline'
fi

printf 'PASS A660-ucode-allocation baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 failed_units=0 thermal_zones=%s thermal_max_mC=%s module_files=7 helper=exact watchdog=armed\n' \
	"$thermal_count" "$thermal_max"
