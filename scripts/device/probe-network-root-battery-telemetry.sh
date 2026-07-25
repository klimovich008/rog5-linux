#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_NETWORK_ROOT_BATTERY_PROBE:-}" = 1 ] ||
	fail 'set ALLOW_NETWORK_ROOT_BATTERY_PROBE=1 for one attended RAM-only probe'

mode=${1:-}
case $mode in
	adsp|telemetry) ;;
	*) fail 'usage: probe-network-root-battery-telemetry.sh adsp|telemetry' ;;
esac

probe_timeout=${ROG5_PROBE_TIMEOUT:-120}
settle_seconds=${ROG5_PROBE_SETTLE:-20}
telemetry_wait_seconds=${ROG5_TELEMETRY_WAIT:-30}
scm_trace=${ROG5_ADSP_SCM_TRACE:-0}
case $probe_timeout:$settle_seconds:$telemetry_wait_seconds in
	*[!0-9:]*|:*|*:) fail 'probe timeout, settle, and telemetry wait must be integers' ;;
esac
[ "$probe_timeout" -ge 75 ] && [ "$probe_timeout" -le 180 ] ||
	fail 'ROG5_PROBE_TIMEOUT must be between 75 and 180 seconds'
[ "$settle_seconds" -ge 10 ] && [ "$settle_seconds" -le 45 ] ||
	fail 'ROG5_PROBE_SETTLE must be between 10 and 45 seconds'
[ "$telemetry_wait_seconds" -ge 10 ] &&
	[ "$telemetry_wait_seconds" -le 45 ] ||
	fail 'ROG5_TELEMETRY_WAIT must be between 10 and 45 seconds'
if [ "$mode" = telemetry ]; then
	[ "$probe_timeout" -ge \
		$((settle_seconds + telemetry_wait_seconds + 45)) ] ||
		fail 'telemetry probe timeout leaves less than 45 seconds of rollback margin'
else
	[ "$probe_timeout" -ge $((settle_seconds + 45)) ] ||
		fail 'probe timeout must exceed the settle interval by at least 45 seconds'
fi
case $scm_trace in
	0) ;;
	1) [ "$mode" = adsp ] || fail 'SCM tracing is limited to the ADSP-only tier' ;;
	*) fail 'ROG5_ADSP_SCM_TRACE must be 0 or 1' ;;
esac

input_dir=${ROG5_BATTERY_INPUT_DIR:-/run/rog5-battery-inputs}
firmware_dir=$input_dir/firmware
pmic_module=$input_dir/pmic_glink-battery-only.ko
expected_pmic_sha=fa38f4f8d4ab428bd828601dc0c9805fcabe3d265afe3cdb0ba6ed977ac9c666
expected_firmware_bytes=30889541
expected_firmware_files='adsp.b00
adsp.b01
adsp.b02
adsp.b03
adsp.b04
adsp.b05
adsp.b06
adsp.b07
adsp.b08
adsp.b09
adsp.b10
adsp.b11
adsp.b12
adsp.b13
adsp.b14
adsp.b15
adsp.b16
adsp.b17
adsp.b18
adsp.b19
adsp.b20
adsp.b21
adsp.b22
adsp.b23
adsp.b24
adsp.b25
adsp.b26
adsp.mbn
adsp.mdt'

for command in awk basename cat comm cut dmesg find findmnt grep head \
	insmod ip kill mktemp modinfo modprobe mount od ps readlink rm rmdir sed \
	setsid sha256sum sleep sort stat systemctl tail tr udevadm uname wc
do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] || fail 'unexpected kernel'
[ "$(cat /proc/1/comm)" = systemd ] || fail 'PID 1 is not systemd'
[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
	fail 'systemd is not running'
for unit in systemd-udev-trigger.service systemd-modules-load.service; do
	[ "$(systemctl is-enabled "$unit" 2>/dev/null || true)" = masked-runtime ] ||
		fail "$unit is not runtime-masked"
done
[ ! -e /run/rog5-network-root-watchdog.pid ] ||
	fail 'network-root watchdog is still active'
[ -e /run/rog5-network-root-watchdog.disarmed.pid ] ||
	fail 'missing network-root watchdog disarm marker'

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

dt=/sys/firmware/devicetree/base
adsp_node=$dt/soc@0/remoteproc@3000000
pmic_node=$dt/pmic-glink
stock_low=$dt/reserved-memory/memory@cbc00000
stock_memshare=$dt/reserved-memory/memory@d8000000
stock_high=$dt/reserved-memory/memory@edc00000
hex_property() {
	od -An -tx1 -v "$1" | tr -d ' \n'
}
[ "$(hex_property "$stock_low/reg")" = \
	00000000cbc000000000000004400000 ] ||
	fail 'low stock-owned RAM reservation is absent'
[ "$(hex_property "$stock_memshare/reg")" = \
	00000000d80000000000000000800000 ] ||
	fail 'stock memshare reservation is absent'
[ "$(hex_property "$stock_high/reg")" = \
	00000000edc000000000000012000000 ] ||
	fail 'high stock-owned RAM reservation is absent'
[ ! -e "$stock_low/no-map" ] ||
	fail 'low stock-owned RAM reservation changed mapping policy'
[ -e "$stock_memshare/no-map" ] ||
	fail 'stock memshare reservation is not no-map'
[ ! -e "$stock_high/no-map" ] ||
	fail 'high stock-owned RAM reservation changed mapping policy'
[ "$(tr -d '\000' <"$adsp_node/status")" = okay ] ||
	fail 'ADSP node is not enabled'
for node in remoteproc@4080000 remoteproc@5c00000 remoteproc@a300000; do
	[ "$(tr -d '\000' <"$dt/soc@0/$node/status")" = disabled ] ||
		fail "unexpected remote processor is enabled: $node"
done
case $mode in
	adsp)
		[ ! -e "$pmic_node" ] ||
			fail 'ADSP-only candidate unexpectedly contains PMIC GLINK'
		;;
	telemetry)
		[ -r "$pmic_node/compatible" ] ||
			fail 'telemetry candidate lacks PMIC GLINK'
		[ "$(tr '\000' ' ' <"$pmic_node/compatible" | sed 's/ $//')" = \
			'qcom,sm8350-pmic-glink qcom,pmic-glink' ] ||
			fail 'unexpected PMIC GLINK compatible'
		[ "$(find "$pmic_node" -mindepth 1 -maxdepth 1 -type d | wc -l)" -eq 0 ] ||
			fail 'PMIC GLINK contains an unreviewed child'
		;;
esac

[ -d "$firmware_dir" ] && [ ! -L "$firmware_dir" ] ||
	fail 'missing volatile ADSP firmware directory'
actual_firmware_files=$(find "$firmware_dir" -mindepth 1 -maxdepth 1 \
	-type f -printf '%f\n' | sort)
[ "$actual_firmware_files" = "$expected_firmware_files" ] ||
	fail 'volatile ADSP firmware set is not exact'
[ "$(find "$firmware_dir" -mindepth 1 -maxdepth 1 -type l | wc -l)" -eq 0 ] ||
	fail 'volatile ADSP firmware contains a symlink'
[ "$(find "$firmware_dir" -mindepth 1 -maxdepth 1 -type f -printf '%s\n' |
	awk '{ total += $1 } END { print total + 0 }')" -eq "$expected_firmware_bytes" ] ||
	fail 'volatile ADSP firmware size contract failed'
[ -s "$firmware_dir/adsp.mdt" ] && [ -s "$firmware_dir/adsp.mbn" ] ||
	fail 'volatile ADSP firmware headers are empty'
[ ! -s "$firmware_dir/adsp.b26" ] ||
	fail 'stock zero-length ADSP segment changed'

for module in qcom_q6v5_pas qcom_q6v5 qcom_common qcom_pil_info \
	qcom_glink_smem qrtr qrtr_smd pdr_interface qcom_pdr_msg pmic_glink \
	qcom_battmgr ucsi_glink pmic_glink_altmode qcom_pd_mapper qcom_apr fastrpc
do
	[ ! -d "/sys/module/$module" ] ||
		fail "candidate module is already loaded: $module"
done
[ "$(find /sys/class/power_supply -mindepth 1 -maxdepth 1 2>/dev/null |
	wc -l)" -eq 0 ] || fail 'power-supply device exists before probe'

if [ "$mode" = telemetry ]; then
	[ -f "$pmic_module" ] && [ ! -L "$pmic_module" ] ||
		fail 'missing volatile battery-only PMIC GLINK module'
	[ "$(sha256sum "$pmic_module" | cut -d ' ' -f 1)" = "$expected_pmic_sha" ] ||
		fail 'battery-only PMIC GLINK module hash mismatch'
	[ "$(modinfo -F name "$pmic_module")" = pmic_glink ] ||
		fail 'unexpected PMIC GLINK module name'
	[ "$(modinfo -F vermagic "$pmic_module")" = \
		'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' ] ||
		fail 'PMIC GLINK module ABI mismatch'
	modinfo -p "$pmic_module" |
		grep -Fxq 'battery_only:Expose only the battery client for attended diagnostics (bool)' ||
		fail 'PMIC GLINK battery-only parameter is absent'

	verify_root_module() {
		module_name=$1
		expected_sha=$2
		expected_depends=$3
		module_path=$(modinfo -n "$module_name" 2>/dev/null) ||
			fail "missing reviewed root module: $module_name"
		[ -f "$module_path" ] && [ ! -L "$module_path" ] ||
			fail "reviewed root module is not a regular file: $module_name"
		[ "$(sha256sum "$module_path" | cut -d ' ' -f 1)" = \
			"$expected_sha" ] ||
			fail "reviewed root module hash mismatch: $module_name"
		[ "$(modinfo -F name "$module_path")" = "$module_name" ] ||
			fail "reviewed root module name mismatch: $module_name"
		[ "$(modinfo -F depends "$module_path")" = "$expected_depends" ] ||
			fail "reviewed root module dependency mismatch: $module_name"
		[ "$(modinfo -F vermagic "$module_path")" = \
			'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' ] ||
			fail "reviewed root module ABI mismatch: $module_name"
	}
	verify_root_module qrtr_smd \
		87e4797a61b75efd02cb52d47e013af5c28cee57affcf484f872ea5a1fb69178 \
		qrtr
	verify_root_module qcom_pd_mapper \
		7eac8fd204c74f0cae8d28a082dec54c8e30d55d420dfd2418052e7f5c9777f7 \
		qcom_pdr_msg
fi

fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	fail 'fatal kernel signature exists before probe'
dmesg_start=$(( $(dmesg | wc -l) + 1 ))

probe_safe=0
watchdog_pid=
state_dir=
disarm_watchdog() {
	[ "$probe_safe" = 1 ] || return 0
	set +e
	if [ -n "$watchdog_pid" ]; then
		kill -STOP -- "-$watchdog_pid" 2>/dev/null
		kill -KILL -- "-$watchdog_pid" 2>/dev/null
		wait "$watchdog_pid" 2>/dev/null
	fi
	if [ -n "$state_dir" ]; then
		rm -f "$state_dir/armed" "$state_dir/modules-before"
		rmdir "$state_dir" 2>/dev/null
	fi
	watchdog_pid=
	state_dir=
	set -e
}
trap disarm_watchdog EXIT
trap 'exit 1' HUP INT TERM

state_dir=$(mktemp -d /run/rog5-battery-probe.XXXXXX)
awk '{ print $1 }' /proc/modules | sort >"$state_dir/modules-before"
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-battery-probe: watchdog expired for $3" >&8
	echo b >&9
' sh "$probe_timeout" "$state_dir/armed" "$mode" \
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

firmware_path=/sys/module/firmware_class/parameters/path
[ -w "$firmware_path" ] || fail 'firmware-class path is not writable'
printf '%s\n' "$firmware_dir" >"$firmware_path"
[ "$(cat "$firmware_path")" = "$firmware_dir" ] ||
	fail 'firmware-class path did not select volatile firmware'

remoteproc=
scm_trace_active=0
trace_root=/sys/kernel/tracing
post_fail() {
	reason=$1
	echo "EVIDENCE mode=$mode reason=$reason"
	if [ -n "$remoteproc" ]; then
		echo "EVIDENCE remoteproc_state=$(cat "$remoteproc/state" 2>/dev/null || true)"
	else
		echo 'EVIDENCE remoteproc_state=unregistered'
	fi
	echo 'EVIDENCE new_dmesg_begin'
	dmesg | tail -n +"$dmesg_start" | tail -n 180
	echo 'EVIDENCE new_dmesg_end'
	if [ "$scm_trace_active" = 1 ]; then
		echo 'EVIDENCE scm_trace_begin'
		cat "$trace_root/trace"
		echo 'EVIDENCE scm_trace_end'
	fi
	fail "$reason"
}

read_telemetry_property() {
	telemetry_path=$1
	telemetry_name=$2
	if ! telemetry_value=$(cat "$telemetry_path" 2>/dev/null); then
		post_fail "battery telemetry became unreadable: $telemetry_name"
	fi
}

if [ "$scm_trace" = 1 ]; then
	if [ "$(findmnt -n -o FSTYPE "$trace_root" 2>/dev/null || true)" != tracefs ]; then
		mount -t tracefs tracefs "$trace_root"
	fi
	[ "$(findmnt -n -o FSTYPE "$trace_root")" = tracefs ] ||
		fail 'tracefs is unavailable'
	[ ! -s "$trace_root/kprobe_events" ] ||
		fail 'an unrelated kprobe event already exists'
	printf '%s\n' \
		'p:rog5_adsp/pas_outer qcom_scm_pas_init_image pas_id=$arg1:u32 metadata_size=$arg3:u64' \
		'r:rog5_adsp/pas_outer_ret qcom_scm_pas_init_image ret=$retval:s64' \
		'p:rog5_adsp/pas_smc __qcom_scm_pas_init_image pas_id=$arg1:u32 metadata_phys=$arg2:x64' \
		'r:rog5_adsp/pas_smc_ret __qcom_scm_pas_init_image ret=$retval:s64' \
		>>"$trace_root/kprobe_events"
	for event in pas_outer pas_outer_ret pas_smc pas_smc_ret; do
		printf '1\n' >"$trace_root/events/rog5_adsp/$event/enable"
	done
	printf '\n' >"$trace_root/trace"
	printf '1\n' >"$trace_root/tracing_on"
	scm_trace_active=1
fi

udevadm control --stop-exec-queue
echo "BEGIN battery-telemetry mode=$mode watchdog=${probe_timeout}s settle=${settle_seconds}s telemetry_wait=${telemetry_wait_seconds}s"
echo "rog5-battery-probe: begin mode=$mode" >/dev/kmsg
if ! modprobe --first-time qcom_q6v5_pas; then
	post_fail 'ADSP module load failed'
fi
echo 'rog5-battery-probe: qcom_q6v5_pas returned' >/dev/kmsg

for unused in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
	for candidate in /sys/class/remoteproc/remoteproc*; do
		[ -e "$candidate" ] || continue
		[ "$(readlink -f "$candidate/device/of_node")" = \
			"$adsp_node" ] || continue
		remoteproc=$candidate
		break
	done
	[ -n "$remoteproc" ] && [ "$(cat "$remoteproc/state")" = running ] &&
		break
	sleep 1
done
[ -n "$remoteproc" ] || post_fail 'ADSP remoteproc did not register'
[ "$(cat "$remoteproc/state")" = running ] ||
	post_fail 'ADSP did not reach running state'
[ "$(cat "$remoteproc/firmware")" = adsp.mdt ] ||
	post_fail 'ADSP requested unexpected firmware'

for module in qcom_q6v5_pas qcom_q6v5 qcom_common qcom_pil_info \
	qcom_glink_smem qrtr
do
	[ -d "/sys/module/$module" ] || fail "ADSP dependency is absent: $module"
done
for module in pmic_glink qcom_battmgr ucsi_glink pmic_glink_altmode \
	qrtr_smd qcom_pd_mapper qcom_apr fastrpc
do
	[ ! -d "/sys/module/$module" ] ||
		fail "udev loaded an unrequested module: $module"
done

if [ "$mode" = telemetry ]; then
	if ! modprobe --first-time qrtr_smd; then
		post_fail 'ADSP IPCRTR transport load failed'
	fi
	[ "$(find /sys/bus/rpmsg/drivers/qcom_smd_qrtr \
		-mindepth 1 -maxdepth 1 -type l ! -name module 2>/dev/null |
		wc -l)" -eq 1 ] ||
		post_fail 'ADSP IPCRTR transport did not bind exactly one endpoint'

	if ! modprobe --first-time qcom_pd_mapper; then
		post_fail 'SM8350 protection-domain mapper load failed'
	fi
	pdm_bound=0
	for pdm_device in \
		/sys/bus/auxiliary/devices/qcom_common.pd-mapper.*
	do
		[ -L "$pdm_device/driver" ] || continue
		[ "$(basename "$(readlink -f "$pdm_device/driver")")" = \
			qcom_pd_mapper.qcom-pdm-mapper ] || continue
		pdm_bound=$((pdm_bound + 1))
	done
	[ "$pdm_bound" -eq 1 ] ||
		post_fail 'SM8350 protection-domain mapper did not bind exactly once'

	if ! modprobe --first-time pdr_interface; then
		post_fail 'protection-domain restart helper load failed'
	fi
	if ! insmod "$pmic_module" battery_only=1; then
		post_fail 'battery-only PMIC GLINK load failed'
	fi
	[ "$(cat /sys/module/pmic_glink/parameters/battery_only)" = Y ] ||
		post_fail 'PMIC GLINK did not enter battery-only mode'
	[ "$(find /sys/bus/auxiliary/devices -mindepth 1 -maxdepth 1 \
		-name 'pmic_glink.power-supply.*' | wc -l)" -eq 1 ] ||
		post_fail 'PMIC GLINK did not expose exactly one battery auxiliary device'
	[ "$(find /sys/bus/auxiliary/devices -mindepth 1 -maxdepth 1 \
		\( -name 'pmic_glink.ucsi.*' -o -name 'pmic_glink.altmode.*' \) |
		wc -l)" -eq 0 ] ||
		post_fail 'PMIC GLINK exposed a USB-C control auxiliary device'

	if ! modprobe --first-time qcom_battmgr; then
		post_fail 'battery-manager load failed'
	fi
	telemetry_ready=0
	telemetry_waited=0
	while [ "$telemetry_waited" -lt "$telemetry_wait_seconds" ]; do
		[ -r /sys/class/power_supply/qcom-battmgr-bat/capacity ] &&
			cat /sys/class/power_supply/qcom-battmgr-bat/capacity \
				>/dev/null 2>&1 && {
				telemetry_ready=1
				break
			}
		telemetry_waited=$((telemetry_waited + 1))
		sleep 1
	done
	[ "$telemetry_ready" -eq 1 ] ||
		post_fail 'battery telemetry did not become readable'

	actual_supplies=$(find /sys/class/power_supply -mindepth 1 -maxdepth 1 \
		-printf '%f\n' | sort)
	expected_supplies='qcom-battmgr-bat
qcom-battmgr-usb
qcom-battmgr-wls'
	[ "$actual_supplies" = "$expected_supplies" ] ||
		post_fail 'battery manager did not expose the exact SM8350 supplies'

	battery=/sys/class/power_supply/qcom-battmgr-bat
	usb=/sys/class/power_supply/qcom-battmgr-usb
	wls=/sys/class/power_supply/qcom-battmgr-wls
	for property in capacity voltage_now current_now temp status; do
		[ "$(stat -c %a "$battery/$property")" = 444 ] ||
			post_fail "battery property is not read-only: $property"
	done
	for supply in "$battery" "$usb" "$wls"; do
		[ ! -e "$supply/charge_control_start_threshold" ] &&
			[ ! -e "$supply/charge_control_end_threshold" ] ||
			post_fail 'a charge-control threshold became writable'
	done
	[ "$(stat -c %a "$usb/input_current_limit")" = 444 ] ||
		post_fail 'USB input-current limit is not read-only'

	read_telemetry_property "$battery/capacity" capacity
	capacity=$telemetry_value
	read_telemetry_property "$battery/voltage_now" voltage_now
	voltage_now=$telemetry_value
	read_telemetry_property "$battery/current_now" current_now
	current_now=$telemetry_value
	read_telemetry_property "$battery/temp" temperature
	temperature=$telemetry_value
	read_telemetry_property "$battery/status" status
	status=$telemetry_value
	read_telemetry_property "$usb/online" usb_online
	usb_online=$telemetry_value
	read_telemetry_property "$wls/online" wls_online
	wls_online=$telemetry_value
	case $capacity:$voltage_now:$current_now:$temperature:$usb_online:$wls_online in
		*[!0-9:-]*|:*|*:) post_fail 'telemetry returned a non-integer value' ;;
	esac
	[ "$capacity" -ge 0 ] && [ "$capacity" -le 100 ] ||
		post_fail 'battery capacity is outside 0..100 percent'
	[ "$voltage_now" -ge 2500000 ] && [ "$voltage_now" -le 10000000 ] ||
		post_fail 'battery voltage is outside the diagnostic range'
	[ "$current_now" -ge -20000000 ] && [ "$current_now" -le 20000000 ] ||
		post_fail 'battery current is outside the diagnostic range'
	[ "$temperature" -ge -200 ] && [ "$temperature" -le 1000 ] ||
		post_fail 'battery temperature is outside the diagnostic range'
	case $status in
		Unknown|Charging|Discharging|'Not charging'|Full) ;;
		*) post_fail 'battery status is unknown' ;;
	esac
	[ "$usb_online" -eq 0 ] || [ "$usb_online" -eq 1 ] ||
		post_fail 'USB online state is not boolean'
	[ "$wls_online" -eq 0 ] || [ "$wls_online" -eq 1 ] ||
		post_fail 'wireless online state is not boolean'

	for module in qcom_battmgr pmic_glink pdr_interface qcom_pdr_msg \
		qrtr_smd qcom_pd_mapper
	do
		[ -d "/sys/module/$module" ] ||
			post_fail "telemetry dependency is absent: $module"
	done
	for module in ucsi_glink pmic_glink_altmode qcom_apr fastrpc; do
		[ ! -d "/sys/module/$module" ] ||
			post_fail "unreviewed module loaded during telemetry: $module"
	done
	[ "$(find /sys/class/typec -mindepth 1 -maxdepth 1 2>/dev/null |
		wc -l)" -eq 0 ] || post_fail 'Type-C control device appeared'

	echo "EVIDENCE capacity_percent=$capacity voltage_uV=$voltage_now current_uA=$current_now temp_dC=$temperature status=$status usb_online=$usb_online wls_online=$wls_online"
else
	[ "$(find /sys/class/power_supply -mindepth 1 -maxdepth 1 2>/dev/null |
		wc -l)" -eq 0 ] || fail 'ADSP-only probe created a power-supply device'
fi

sleep "$settle_seconds"

[ "$(cat "$remoteproc/state")" = running ] ||
	post_fail 'ADSP stopped during settle'
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
	post_fail 'USB carrier dropped'
[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
	post_fail 'systemd regressed'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	post_fail 'a systemd unit failed'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	post_fail 'fatal kernel signature appeared'
[ "$(dmesg | tail -n +"$dmesg_start" |
	grep -Ec 'WARNING:|Call trace:|Unhandled fault|IOMMU.*fault|remoteproc.*crash' ||
	true)" -eq 0 ] || post_fail 'warning, fault, or remoteproc crash appeared'

awk '{ print $1 }' /proc/modules | sort >"$state_dir/modules-after"
removed_modules=$(comm -23 "$state_dir/modules-before" "$state_dir/modules-after")
[ -z "$removed_modules" ] || post_fail 'a baseline module disappeared'
new_modules=$(comm -13 "$state_dir/modules-before" "$state_dir/modules-after")
allowed_modules='qcom_q6v5_pas
qcom_q6v5
qcom_common
qcom_pil_info
qcom_glink_smem
qrtr'
if [ "$mode" = telemetry ]; then
	allowed_modules="$allowed_modules
pdr_interface
qcom_pdr_msg
pmic_glink
qcom_battmgr
qrtr_smd
qcom_pd_mapper"
fi
unexpected_modules=$(printf '%s\n' "$new_modules" |
	while IFS= read -r module; do
		[ -z "$module" ] || printf '%s\n' "$allowed_modules" |
			grep -qx "$module" || printf '%s\n' "$module"
	done)
[ -z "$unexpected_modules" ] ||
	post_fail 'an unreviewed module appeared'

if [ "$scm_trace_active" = 1 ]; then
	printf '0\n' >"$trace_root/tracing_on"
	for event in pas_outer pas_outer_ret pas_smc pas_smc_ret; do
		printf '0\n' >"$trace_root/events/rog5_adsp/$event/enable"
	done
	for event in pas_outer pas_outer_ret pas_smc pas_smc_ret; do
		printf '%s\n' "-:rog5_adsp/$event" >>"$trace_root/kprobe_events"
	done
	[ ! -d "$trace_root/events/rog5_adsp" ] ||
		post_fail 'SCM trace probes did not clean up'
	scm_trace_active=0
fi

rm -f "$state_dir/modules-after"
probe_safe=1
disarm_watchdog
trap - EXIT HUP INT TERM
echo "PASS battery-telemetry mode=$mode stayed RAM-only, storage-isolated, USB-C-control-free, and rollback-guarded"
