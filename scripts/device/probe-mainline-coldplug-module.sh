#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_MAINLINE_COLDPLUG_PROBE:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_COLDPLUG_PROBE=1 for one attended module probe'

module=${1:-}
case $module in
	authenc|gpucc_sm8350|libdes|nvmem_qcom_spmi_sdam|nvmem_reboot_mode|\
	pinctrl_lpass_lpi|pinctrl_sc7280_lpass_lpi|qcom_pon|\
	qcom_refgen_regulator|qcom_rng|qcom_spmi_adc5|qcom_spmi_temp_alarm|\
	qcom_stats|qcom_vadc_common|qcomtee|qcrypto|rmtfs_mem|rtc_pm8xxx|\
	sha1|sha256|socinfo) ;;
	*) fail 'module is not in the reviewed coldplug allowlist' ;;
esac

probe_timeout=${ROG5_PROBE_TIMEOUT:-75}
settle_seconds=${ROG5_PROBE_SETTLE:-30}
case $probe_timeout:$settle_seconds in
	*[!0-9:]*|:*|*:) fail 'probe timeout and settle interval must be integers' ;;
esac
[ "$probe_timeout" -ge 45 ] && [ "$probe_timeout" -le 180 ] ||
	fail 'ROG5_PROBE_TIMEOUT must be between 45 and 180 seconds'
[ "$settle_seconds" -ge 10 ] && [ "$settle_seconds" -le 60 ] ||
	fail 'ROG5_PROBE_SETTLE must be between 10 and 60 seconds'
[ "$probe_timeout" -ge $((settle_seconds + 20)) ] ||
	fail 'probe timeout must exceed the settle interval by at least 20 seconds'

for command in awk basename cat cut dmesg find findmnt grep ip kill mktemp \
	modinfo modprobe ps readlink rm rmdir setsid sleep sort systemctl tail tr \
	uname wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
if [ "$module" = gpucc_sm8350 ]; then
	for command in insmod sha256sum stat; do
		command -v "$command" >/dev/null ||
			fail "missing GPUCC diagnostic command: $command"
	done
	dmesg --help 2>&1 | grep -q -- '--follow-new' ||
		fail 'dmesg lacks follow-new support'
fi

[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] ||
	fail 'unexpected kernel'
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
if [ "$module" = gpucc_sm8350 ]; then
	trace_count=$(tr ' ' '\n' </proc/cmdline |
		awk '$0 == "rog5_qcom_cc_probe_trace=1" { count++ }
			END { print count + 0 }')
	[ "$trace_count" -eq 1 ] ||
		fail 'common-clock trace boot parameter is not exact'
	core_trace=/sys/module/kernel/parameters/rog5_qcom_cc_probe_trace
	[ -r "$core_trace" ] ||
		fail 'common-clock trace core parameter is absent'
	[ "$(cat "$core_trace")" = Y ] ||
		fail 'common-clock trace core parameter is not enabled'
	[ "$(stat -c %a "$core_trace")" = 400 ] ||
		fail 'common-clock trace core parameter became writable'
	ccf_trace_count=$(tr ' ' '\n' </proc/cmdline |
		awk '$0 == "rog5_ccf_register_trace=1" { count++ }
			END { print count + 0 }')
	[ "$ccf_trace_count" -eq 1 ] ||
		fail 'CCF registration trace boot parameter is not exact'
	ccf_trace=/sys/module/kernel/parameters/rog5_ccf_register_trace
	[ -r "$ccf_trace" ] ||
		fail 'CCF registration trace core parameter is absent'
	[ "$(cat "$ccf_trace")" = Y ] ||
		fail 'CCF registration trace core parameter is not enabled'
	[ "$(stat -c %a "$ccf_trace")" = 400 ] ||
		fail 'CCF registration trace core parameter became writable'
fi

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
	fail 'systemd already has a failed unit'

normalized_module=$(printf '%s\n' "$module" | tr '-' '_')
[ ! -d "/sys/module/$normalized_module" ] ||
	fail 'module is already loaded; use a fresh candidate'
gpucc_module=
gpucc_expected_sha=
gpucc_pinned_sha=0ccb0059ec1960becb3676903aaccb623f105dbc8df08984cbd13a7d1ea6e73c
if [ "$module" = gpucc_sm8350 ]; then
	gpucc_module=${ROG5_GPUCC_MODULE:-}
	gpucc_expected_sha=${ROG5_GPUCC_MODULE_SHA256:-}
	[ "$gpucc_module" = \
		/run/rog5-gpucc-diagnostic/gpucc-sm8350.ko ] ||
		fail 'GPUCC diagnostic module must use the reviewed tmpfs path'
	[ -f "$gpucc_module" ] && [ ! -L "$gpucc_module" ] ||
		fail 'GPUCC diagnostic module is missing or is a symlink'
	[ "$(stat -c '%u:%g:%a' "$gpucc_module")" = 0:0:400 ] ||
		fail 'GPUCC diagnostic module ownership or mode is not exact'
	case $gpucc_expected_sha in
		*[!0-9a-f]*|'') fail 'invalid GPUCC diagnostic module SHA-256' ;;
	esac
	[ "${#gpucc_expected_sha}" -eq 64 ] ||
		fail 'invalid GPUCC diagnostic module SHA-256 length'
	[ "$gpucc_expected_sha" = "$gpucc_pinned_sha" ] ||
		fail 'GPUCC diagnostic module SHA-256 is not the reviewed build'
	[ "$(sha256sum "$gpucc_module" | cut -d ' ' -f 1)" = \
		"$gpucc_expected_sha" ] ||
		fail 'GPUCC diagnostic module hash mismatch'
	[ "$(modinfo -F name "$gpucc_module")" = gpucc_sm8350 ] ||
		fail 'GPUCC diagnostic module name mismatch'
	[ -z "$(modinfo -F depends "$gpucc_module")" ] ||
		fail 'GPUCC diagnostic module has unexpected dependencies'
	[ "$(modinfo -F vermagic "$gpucc_module")" = \
		'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' ] ||
		fail 'GPUCC diagnostic module ABI mismatch'
	modinfo -p "$gpucc_module" |
		grep -Fxq \
		'probe_trace:Emit progress notices for attended SM8350 GPUCC diagnostics (bool)' ||
		fail 'GPUCC diagnostic module lacks the read-only trace parameter'
	module_file=$gpucc_module
else
	module_file=$(modinfo -F filename "$module" 2>/dev/null || true)
fi
case $module_file in
	*.ko|*.ko.*) ;;
	*) fail 'candidate is not a loadable module in this kernel' ;;
esac

gpucc_dt=/sys/firmware/devicetree/base/soc@0/clock-controller@3d90000
gpu_dt=/sys/firmware/devicetree/base/soc@0/gpu@3d00000
gmu_dt=/sys/firmware/devicetree/base/soc@0/gmu@3d6a000
smmu_dt=/sys/firmware/devicetree/base/soc@0/iommu@3da0000
if [ "$module" = gpucc_sm8350 ]; then
	[ "$(tr '\000' '\n' <"$gpucc_dt/status")" = okay ] ||
		fail 'GPUCC device-tree node is not explicitly enabled'
	tr '\000' '\n' <"$gpucc_dt/compatible" |
		grep -qx 'qcom,sm8350-gpucc' ||
		fail 'GPUCC device-tree identity is unexpected'
	for node in "$gpu_dt" "$gmu_dt" "$smmu_dt"; do
		[ "$(tr '\000' '\n' <"$node/status")" = disabled ] ||
			fail 'a GPUCC consumer is not explicitly disabled'
	done
	for device in /sys/bus/platform/devices/*; do
		[ -L "$device/of_node" ] || continue
		of_node=$(readlink -f "$device/of_node")
		case $of_node in
			"$gpu_dt"|"$gmu_dt"|"$smmu_dt")
				[ ! -e "$device/driver" ] ||
					fail 'a disabled GPUCC consumer is already bound'
				;;
		esac
	done
	[ -z "$(find /dev/dri -maxdepth 1 -name 'renderD*' -print \
		2>/dev/null)" ] ||
		fail 'a render node exists before the GPUCC-only probe'
fi

dependency_parent=
case $module in
	pinctrl_lpass_lpi) dependency_parent=pinctrl_sc7280_lpass_lpi ;;
	qcom_vadc_common) dependency_parent=qcom_spmi_adc5 ;;
	authenc|libdes|sha1|sha256) dependency_parent=qcrypto ;;
esac
if [ -n "$dependency_parent" ]; then
	modprobe --show-depends "$dependency_parent" 2>/dev/null |
		grep -Fq "$module_file" ||
		fail 'module is not a dependency of its reviewed parent'
else
	alias_match=0
	for alias_file in $(find /sys/devices -type f -name modalias 2>/dev/null); do
		alias=$(cat "$alias_file")
		if modprobe -R "$alias" 2>/dev/null | grep -qx "$module"; then
			alias_match=$((alias_match + 1))
		fi
	done
	[ "$alias_match" -gt 0 ] || fail 'no live device resolves to this module'
fi

fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	fail 'fatal kernel signature exists before probe'
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
		# Freeze both the shell and its sleep child before terminating the
		# process group, so child exit cannot race into the reset branch.
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

state_dir=$(mktemp -d /run/rog5-coldplug-probe.XXXXXX)
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-coldplug-probe: watchdog expired for $3" >&8
	echo b >&9
' sh "$probe_timeout" "$state_dir/armed" "$module" \
	</dev/null >/dev/null 2>&1 &
watchdog_pid=$!

watchdog_pgid=$(ps -o pgid= -p "$watchdog_pid" | tr -d ' ')
[ "$watchdog_pgid" = "$watchdog_pid" ] ||
	fail 'probe watchdog is not in an independent process group'
armed=0
for unused in 1 2 3 4 5; do
	if [ -s "$state_dir/armed" ] && kill -0 "$watchdog_pid" 2>/dev/null; then
		armed=1
		break
	fi
	sleep 1
done
[ "$armed" -eq 1 ] || fail 'probe watchdog did not arm'

echo "BEGIN coldplug module=$module watchdog=${probe_timeout}s settle=${settle_seconds}s"
echo "rog5-coldplug-probe: begin module=$module" >/dev/kmsg
if [ "$module" = gpucc_sm8350 ]; then
	dmesg --follow-new &
	log_follower_pid=$!
	sleep 1
	kill -0 "$log_follower_pid" ||
		fail 'GPUCC live kernel-log follower did not start'
	echo "rog5-coldplug-probe: external module load begin module=$module" \
		>/dev/kmsg
	insmod "$module_file" probe_trace=1
else
	modprobe --first-time "$module"
fi
echo "rog5-coldplug-probe: modprobe returned module=$module" >/dev/kmsg
sleep "$settle_seconds"

post_fail() {
	reason=$1
	echo "EVIDENCE coldplug module=$module reason=$reason"
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
		for trip in "$zone"/trip_point_*_temp; do
			[ -r "$trip" ] || continue
			printf '  %s=%s\n' "$(basename "$trip")" "$(cat "$trip")"
		done
	done
	echo 'EVIDENCE thermal_zones_end'
	echo 'EVIDENCE new_dmesg_begin'
	dmesg | tail -n +"$dmesg_start" | tail -n 160
	echo 'EVIDENCE new_dmesg_end'
	fail "$reason"
}

[ -d "/sys/module/$normalized_module" ] ||
	post_fail 'module did not remain loaded'
if [ "$module" = gpucc_sm8350 ]; then
	parameter=/sys/module/gpucc_sm8350/parameters/probe_trace
	[ "$(cat "$parameter")" = Y ] ||
		post_fail 'GPUCC trace parameter is not enabled'
	[ "$(stat -c %a "$parameter")" = 400 ] ||
		post_fail 'GPUCC trace parameter became writable'
	driver=/sys/bus/platform/drivers/sm8350-gpucc
	[ -d "$driver" ] ||
		post_fail 'GPUCC platform driver is absent'
	bound=0
	for link in "$driver"/*; do
		[ -L "$link" ] || continue
		[ "$(basename "$link")" = module ] && continue
		bound=$((bound + 1))
	done
	[ "$bound" -eq 1 ] ||
		post_fail 'GPUCC did not bind exactly one platform device'
	for device in /sys/bus/platform/devices/*; do
		[ -L "$device/of_node" ] || continue
		of_node=$(readlink -f "$device/of_node")
		case $of_node in
			"$gpu_dt"|"$gmu_dt"|"$smmu_dt")
				[ ! -e "$device/driver" ] ||
					post_fail 'a disabled GPUCC consumer bound after registration'
				;;
		esac
	done
	[ -z "$(find /dev/dri -maxdepth 1 -name 'renderD*' -print \
		2>/dev/null)" ] ||
		post_fail 'a render node appeared during the GPUCC-only probe'
fi
if [ "$module" = rtc_pm8xxx ]; then
	[ "$(find /sys/class/rtc -mindepth 1 -maxdepth 1 -name 'rtc*' |
		wc -l)" -eq 1 ] ||
		post_fail 'RTC module did not register exactly one RTC'
	rtc=/sys/class/rtc/rtc0
	[ -r "$rtc/device/of_node/compatible" ] ||
		post_fail 'RTC has no device-tree identity'
	tr '\000' '\n' <"$rtc/device/of_node/compatible" |
		grep -qx 'qcom,pmk8350-rtc' ||
		post_fail 'RTC bound to an unexpected device-tree node'
	cat "$rtc/date" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' ||
		post_fail 'RTC date is unreadable'
	cat "$rtc/time" | grep -Eq '^[0-9]{2}:[0-9]{2}:[0-9]{2}$' ||
		post_fail 'RTC time is unreadable'
fi
system_state=
for unused in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
	system_state=$(systemctl is-system-running 2>/dev/null || true)
	[ "$system_state" != running ] || break
	case $system_state in
		starting|initializing) sleep 1 ;;
		*) break ;;
	esac
done
[ "$system_state" = running ] ||
	post_fail 'systemd regressed after module load'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	post_fail 'a systemd unit failed after module load'
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	post_fail 'physical block device appeared after module load'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	post_fail 'block-backed mount appeared after module load'
[ "$(findmnt -n -o SOURCE /.rog5/root-ro)" = 169.254.77.1:/ ] ||
	post_fail 'NFS lower disappeared after module load'
findmnt -n -o OPTIONS /.rog5/root-ro | tr ',' '\n' | grep -qx ro ||
	post_fail 'NFS lower became writable after module load'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	post_fail 'USB network carrier dropped after module load'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	post_fail 'fatal kernel signature appeared after module load'
[ "$(dmesg | tail -n +"$dmesg_start" |
	grep -Ec 'WARNING:|Call trace:|Unhandled fault|IOMMU.*fault|page fault' ||
	true)" -eq 0 ] ||
	post_fail 'new warning or fault appeared after module load'

probe_safe=1
disarm_watchdog
trap - EXIT HUP INT TERM
echo "PASS coldplug module=$module remained stable and watchdog was disarmed"
