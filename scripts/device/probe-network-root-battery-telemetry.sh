#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	if [ "${early_fail_closed:-0}" -eq 1 ]; then
		if [ -x "${diagnostic:-/nonexistent}" ]; then
			"$diagnostic" emit 200 charging-probe-failed || true
		fi
		sleep 5
		echo b >/proc/sysrq-trigger 2>/dev/null || true
		while :; do sleep 3600; done
	fi
	exit 1
}

[ "${ALLOW_NETWORK_ROOT_BATTERY_PROBE:-}" = 1 ] ||
	fail 'set ALLOW_NETWORK_ROOT_BATTERY_PROBE=1 for one attended RAM-only probe'

requested_mode=${1:-}
early_mode=0
early_fail_closed=0
allow_armed_watchdog=${ROG5_PROBE_ALLOW_ARMED_WATCHDOG:-0}
case $requested_mode in
	adsp|telemetry|charging) mode=$requested_mode ;;
	charging-early)
		mode=charging
		early_mode=1
		;;
	*) fail 'usage: probe-network-root-battery-telemetry.sh adsp|telemetry|charging|charging-early' ;;
esac
case $allow_armed_watchdog in 0|1) ;; *) fail 'invalid outer-watchdog policy' ;; esac
if [ "$mode" = charging ]; then
	[ "${ALLOW_NETWORK_ROOT_CHARGING_PROBE:-}" = 1 ] ||
		fail 'set ALLOW_NETWORK_ROOT_CHARGING_PROBE=1 for full PMIC GLINK/UCSI'
fi
if [ "$early_mode" -eq 1 ]; then
	[ "${ALLOW_NETWORK_ROOT_EARLY_CHARGING_PROBE:-}" = 1 ] ||
		fail 'set ALLOW_NETWORK_ROOT_EARLY_CHARGING_PROBE=1 for PID1 probe'
	early_fail_closed=1
fi

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
if [ "$mode" != adsp ]; then
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
pdr_module=$input_dir/modules/pdr_interface.ko
pdr_module_sha=0b7df05e9fa0bfe224fc74ac93997bb1ee74ab5371bde172c3b0a2fcfe19601b
expected_pmic_sha=fa38f4f8d4ab428bd828601dc0c9805fcabe3d265afe3cdb0ba6ed977ac9c666
# Exact ADSP set extracted read-only from the retained official ASUS
# WW-33.0210.0210.200 vendor image.
expected_firmware_bytes=30900841
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

diagnostic=/run/initramfs/sbin/rog5-early-target-diag
emit_progress() {
	[ "$early_mode" -eq 1 ] || return 0
	"$diagnostic" emit "$1"
}

early_reboot() {
	[ "$early_mode" -eq 1 ] || return 1
	sleep 5
	echo b >/proc/sysrq-trigger 2>/dev/null || true
	while :; do sleep 3600; done
}

for command in awk basename cat comm cut dmesg find findmnt grep head \
	insmod ip kill mktemp modinfo modprobe mount od ps readlink rm rmdir sed \
	setsid sha256sum sleep sort stat systemctl tail tr udevadm uname wc
do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] || fail 'unexpected kernel'
if [ "$early_mode" -eq 0 ]; then
	[ "$(cat /proc/1/comm)" = systemd ] || fail 'PID 1 is not systemd'
	[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
		fail 'systemd is not running'
	for unit in systemd-udev-trigger.service systemd-modules-load.service; do
		[ "$(systemctl is-enabled "$unit" 2>/dev/null || true)" = masked-runtime ] ||
			fail "$unit is not runtime-masked"
	done
	if [ "$allow_armed_watchdog" -eq 1 ]; then
		[ "$mode" = charging ] || fail 'armed outer watchdog is charging-only'
		outer_pid_file=/run/rog5-network-root-watchdog.pid
		[ -s "$outer_pid_file" ] || fail 'armed network-root watchdog PID is absent'
		outer_pid=$(cat "$outer_pid_file")
		case $outer_pid in *[!0-9]*|'') fail 'armed watchdog PID is invalid' ;; esac
		[ "$outer_pid" -ne 1 ] && kill -0 "$outer_pid" 2>/dev/null ||
			fail 'armed network-root watchdog process is absent'
		[ ! -e /run/rog5-network-root-watchdog.disarmed.pid ] ||
			fail 'outer watchdog has a disarm marker'
	else
		[ ! -e /run/rog5-network-root-watchdog.pid ] ||
			fail 'network-root watchdog is still active'
		[ -e /run/rog5-network-root-watchdog.disarmed.pid ] ||
			fail 'missing network-root watchdog disarm marker'
	fi
else
	case $(cat /proc/1/comm) in
		rog5-early-cha*) ;;
		*) fail 'early charging probe is not PID 1' ;;
	esac
	[ -x "$diagnostic" ] || fail 'early diagnostic reporter is unavailable'
	emit_progress 142
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
emit_progress 143

dt=/sys/firmware/devicetree/base
adsp_node=$dt/soc@0/remoteproc@3000000
pmic_node=$dt/pmic-glink
adsp_memory=$dt/reserved-memory/memory@86100000
qrtr_memory=$dt/reserved-memory/memory@d7ef7000
channel0_memory=$dt/reserved-memory/memory@d7f00000
channel1_memory=$dt/reserved-memory/memory@d7f80000
hex_property() {
	od -An -tx1 -v "$1" | tr -d ' \n'
}
for reservation in \
	"$adsp_memory:00000000861000000000000002100000:ADSP" \
	"$qrtr_memory:00000000d7ef70000000000000009000:QRTR" \
	"$channel0_memory:00000000d7f000000000000000080000:channel-0" \
	"$channel1_memory:00000000d7f800000000000000080000:channel-1"
do
	path=${reservation%%:*}
	rest=${reservation#*:}
	expected_reg=${rest%%:*}
	label=${rest#*:}
	[ "$(hex_property "$path/reg")" = "$expected_reg" ] ||
		fail "$label reserved-memory geometry is absent"
	[ -e "$path/no-map" ] || fail "$label reserved memory is not no-map"
done
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
	telemetry|charging)
		[ -r "$pmic_node/compatible" ] ||
			fail 'telemetry candidate lacks PMIC GLINK'
		[ "$(tr '\000' ' ' <"$pmic_node/compatible" | sed 's/ $//')" = \
			'qcom,sm8350-pmic-glink qcom,pmic-glink' ] ||
			fail 'unexpected PMIC GLINK compatible'
		[ "$(find "$pmic_node" -mindepth 1 -maxdepth 1 -type d | wc -l)" -eq 0 ] ||
			fail 'PMIC GLINK contains an unreviewed child'
		;;
esac
emit_progress 144

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
emit_progress 145

for module in qcom_q6v5_pas qcom_q6v5 qcom_common qcom_pil_info \
	qcom_glink_smem qrtr qrtr_smd pdr_interface qcom_pdr_msg pmic_glink \
	qcom_battmgr ucsi_glink pmic_glink_altmode qcom_pd_mapper qcom_apr fastrpc
do
	[ ! -d "/sys/module/$module" ] ||
		fail "candidate module is already loaded: $module"
done
[ "$(find /sys/class/power_supply -mindepth 1 -maxdepth 1 2>/dev/null |
	wc -l)" -eq 0 ] || fail 'power-supply device exists before probe'

if [ "$mode" != adsp ]; then
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

	case $mode in
		telemetry)
			qrtr_smd_sha=87e4797a61b75efd02cb52d47e013af5c28cee57affcf484f872ea5a1fb69178
			pd_mapper_sha=7eac8fd204c74f0cae8d28a082dec54c8e30d55d420dfd2418052e7f5c9777f7
			;;
		charging)
			qrtr_smd_sha=87e4797a61b75efd02cb52d47e013af5c28cee57affcf484f872ea5a1fb69178
			pd_mapper_sha=7eac8fd204c74f0cae8d28a082dec54c8e30d55d420dfd2418052e7f5c9777f7
			verify_root_module pdr_interface \
				5b4e60818449d20691275a5a9a2e3359af5d42fd70c2e48a2a53e0e20e6f677d \
				qcom_pdr_msg
			verify_root_module pmic_glink \
				55c1bc5807de58e08932f290ee8f92517b93c3a7ad373ab6eb4f72be8a865bff \
				pdr_interface
			verify_root_module qcom_battmgr \
				2d7d4d386e5198926347dee5a846f3a010dcf2212bdbf8b010b62ab14f7e647f \
				pmic_glink
			verify_root_module typec \
				2dbfedb34d5f45bc474c85028062d9a7d6b187c724810d88f6d70cb955fd4aec ''
			verify_root_module typec_ucsi \
				fc4036e8f6ded725edb74c767cee4b988a47b60eb0c6e06c32f8d0ce8ba727fc \
				typec
			verify_root_module ucsi_glink \
				7d0a696669c4ce455699651876fff58cc9646c8a36d56fbd50a31077001bdc4d \
				'typec_ucsi,pmic_glink,typec'
			[ -f "$pdr_module" ] && [ ! -L "$pdr_module" ] ||
				fail 'reviewed no-BTF PDR override is absent or linked'
			[ "$(sha256sum "$pdr_module" | cut -d ' ' -f 1)" = \
				"$pdr_module_sha" ] || fail 'no-BTF PDR override hash changed'
			[ "$(modinfo -F name "$pdr_module")" = pdr_interface ] &&
				[ "$(modinfo -F depends "$pdr_module")" = qcom_pdr_msg ] &&
				[ "$(modinfo -F vermagic "$pdr_module")" = \
				'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' ] ||
				fail 'no-BTF PDR override ABI changed'
			;;
	esac
	verify_root_module qrtr_smd "$qrtr_smd_sha" qrtr
	verify_root_module qcom_pd_mapper "$pd_mapper_sha" qcom_pdr_msg
fi

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
emit_progress 151

firmware_path=/sys/module/firmware_class/parameters/path
[ -w "$firmware_path" ] || fail 'firmware-class path is not writable'
printf '%s\n' "$firmware_dir" >"$firmware_path"
[ "$(cat "$firmware_path")" = "$firmware_dir" ] ||
	fail 'firmware-class path did not select volatile firmware'
emit_progress 152

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
	if [ "$early_mode" -eq 1 ]; then
		"$diagnostic" emit 200 charging-probe-failed || true
		early_reboot
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

emit_evidence() {
	evidence_line="EVIDENCE $*"
	printf '%s\n' "$evidence_line"
	printf 'rog5-power-usb: %s\n' "$evidence_line" \
		2>/dev/null >/dev/kmsg || true
}

emit_typec_snapshot() (
	typec_root=${ROG5_TYPEC_CLASS_ROOT:-/sys/class/typec}
	[ -d "$typec_root" ] && [ ! -L "$typec_root" ] ||
		post_fail 'Type-C class is absent or unsafe'
	port_count=0
	partner_count=0
	for entry in "$typec_root"/port*; do
		[ -e "$entry" ] || continue
		name=$(basename "$entry")
		case $name in
			port[0-9]|port[0-9][0-9]) ;;
			*) continue ;;
		esac
		port_count=$((port_count + 1))
		[ "$port_count" -le 3 ] ||
			post_fail 'UCSI exposed more than three Type-C ports'
		property_modes=
		for property in data_role power_role power_operation_mode; do
			path=$entry/$property
			[ -f "$path" ] && [ ! -L "$path" ] ||
				post_fail "Type-C property is absent or linked: $name/$property"
			property_mode=$(stat -c %a "$path")
			case $property_mode in
				444|644) ;;
				*) post_fail "Type-C property mode is unsupported: $name/$property" ;;
			esac
			property_modes=${property_modes}${property}:${property_mode},
		done
		port_type_path=$entry/port_type
		if [ -e "$port_type_path" ] || [ -L "$port_type_path" ]; then
			[ -f "$port_type_path" ] && [ ! -L "$port_type_path" ] ||
				post_fail "Type-C optional property is linked: $name/port_type"
			property_mode=$(stat -c %a "$port_type_path")
			case $property_mode in
				444|644) ;;
				*) post_fail "Type-C property mode is unsupported: $name/port_type" ;;
			esac
			port_type=$(tr ' ' '_' <"$port_type_path")
			property_modes=${property_modes}port_type:${property_mode},
		else
			port_type=absent
			property_modes=${property_modes}port_type:absent,
		fi
		property_modes=${property_modes%,}
		data_role=$(tr ' ' '_' <"$entry/data_role")
		power_role=$(tr ' ' '_' <"$entry/power_role")
		power_mode=$(tr ' ' '_' <"$entry/power_operation_mode")
		case $data_role:$power_role:$port_type:$power_mode in
			*[!A-Za-z0-9_.:\[\]-]*)
				post_fail "Type-C property contains unsafe bytes: $name" ;;
		esac
		partner=0
		if [ -e "$typec_root/$name-partner" ]; then
			[ -L "$typec_root/$name-partner" ] ||
				post_fail "Type-C partner is not a class link: $name"
			partner=1
			partner_count=$((partner_count + 1))
		fi
		emit_evidence "typec_port=$name data_role=$data_role power_role=$power_role port_type=$port_type power_operation_mode=$power_mode property_modes=$property_modes partner=$partner"
	done
	[ "$port_count" -ge 1 ] || post_fail 'UCSI exposed no Type-C port'
	emit_evidence \
		"typec_port_count=$port_count typec_partner_count=$partner_count"
)

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

if [ "$early_mode" -eq 0 ]; then
	udevadm control --stop-exec-queue
fi
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
emit_progress 153

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

if [ "$mode" != adsp ]; then
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

	case $mode in
		charging)
			if ! insmod "$pdr_module"; then
				post_fail 'no-BTF protection-domain restart helper load failed'
			fi
			;;
		*)
			if ! modprobe --first-time pdr_interface; then
				post_fail 'protection-domain restart helper load failed'
			fi
			;;
	esac
	emit_progress 154
	case $mode in
		telemetry)
			if ! insmod "$pmic_module" battery_only=1; then
				post_fail 'battery-only PMIC GLINK load failed'
			fi
			[ "$(cat /sys/module/pmic_glink/parameters/battery_only)" = Y ] ||
				post_fail 'PMIC GLINK did not enter battery-only mode'
			;;
		charging)
			if ! modprobe --first-time pmic_glink; then
				post_fail 'full PMIC GLINK load failed'
			fi
			[ ! -e /sys/module/pmic_glink/parameters/battery_only ] ||
				post_fail 'charging candidate contains the diagnostic PMIC module'
			;;
	esac
	[ "$(find /sys/bus/auxiliary/devices -mindepth 1 -maxdepth 1 \
		-name 'pmic_glink.power-supply.*' | wc -l)" -eq 1 ] ||
		post_fail 'PMIC GLINK did not expose exactly one battery auxiliary device'
	emit_progress 155
	if [ "$mode" = telemetry ]; then
		[ "$(find /sys/bus/auxiliary/devices -mindepth 1 -maxdepth 1 \
			\( -name 'pmic_glink.ucsi.*' -o -name 'pmic_glink.altmode.*' \) |
			wc -l)" -eq 0 ] ||
			post_fail 'PMIC GLINK exposed a USB-C control auxiliary device'
	else
		[ "$(find /sys/bus/auxiliary/devices -mindepth 1 -maxdepth 1 \
			-name 'pmic_glink.ucsi.*' | wc -l)" -eq 1 ] ||
			post_fail 'PMIC GLINK did not expose exactly one UCSI device'
		[ "$(find /sys/bus/auxiliary/devices -mindepth 1 -maxdepth 1 \
			-name 'pmic_glink.altmode.*' | wc -l)" -eq 1 ] ||
			post_fail 'PMIC GLINK did not expose exactly one altmode device'
	fi

	if ! modprobe --first-time qcom_battmgr; then
		post_fail 'battery-manager load failed'
	fi
	emit_progress 156
	if [ "$mode" = charging ]; then
		if ! modprobe --first-time ucsi_glink; then
			post_fail 'PMIC GLINK UCSI load failed'
		fi
		ucsi_ready=0
		ucsi_waited=0
		while [ "$ucsi_waited" -lt "$telemetry_wait_seconds" ]; do
			[ "$(find /sys/class/typec -mindepth 1 -maxdepth 1 \
				-name 'port*' 2>/dev/null | wc -l)" -ge 1 ] && {
				ucsi_ready=1
				break
			}
			ucsi_waited=$((ucsi_waited + 1))
			sleep 1
		done
		[ "$ucsi_ready" -eq 1 ] || post_fail 'UCSI did not expose a Type-C port'
		emit_typec_snapshot
		emit_progress 157
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
	emit_progress 158

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
	if [ "$mode" = telemetry ]; then
		for supply in "$battery" "$usb" "$wls"; do
			[ ! -e "$supply/charge_control_start_threshold" ] &&
				[ ! -e "$supply/charge_control_end_threshold" ] ||
				post_fail 'a charge-control threshold became writable'
		done
	fi
	for property in voltage_now voltage_max current_now current_max \
		input_current_limit usb_type; do
		[ -f "$usb/$property" ] && [ ! -L "$usb/$property" ] &&
			[ "$(stat -c %a "$usb/$property")" = 444 ] ||
			post_fail "USB property is absent, linked, or writable: $property"
	done

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
	read_telemetry_property "$usb/voltage_now" usb_voltage_now
	usb_voltage_now=$telemetry_value
	read_telemetry_property "$usb/voltage_max" usb_voltage_max
	usb_voltage_max=$telemetry_value
	read_telemetry_property "$usb/current_now" usb_current_now
	usb_current_now=$telemetry_value
	read_telemetry_property "$usb/current_max" usb_current_max
	usb_current_max=$telemetry_value
	read_telemetry_property "$usb/input_current_limit" usb_input_current_limit
	usb_input_current_limit=$telemetry_value
	read_telemetry_property "$usb/usb_type" usb_type
	usb_type=$(printf '%s' "$telemetry_value" | tr ' ' '_')
	read_telemetry_property "$wls/online" wls_online
	wls_online=$telemetry_value
	case $capacity:$voltage_now:$current_now:$temperature:$usb_online:$usb_voltage_now:$usb_voltage_max:$usb_current_now:$usb_current_max:$usb_input_current_limit:$wls_online in
		*[!0-9:-]*|:*|*:) post_fail 'telemetry returned a non-integer value' ;;
	esac
	case $usb_type in
		''|*[!A-Za-z0-9_.:\[\]-]*) post_fail 'USB type contains unsafe bytes' ;;
	esac
	[ "$capacity" -ge 0 ] && [ "$capacity" -le 100 ] ||
		post_fail 'battery capacity is outside 0..100 percent'
	[ "$voltage_now" -ge 2500000 ] && [ "$voltage_now" -le 10000000 ] ||
		post_fail 'battery voltage is outside the diagnostic range'
	[ "$current_now" -ge -20000000 ] && [ "$current_now" -le 20000000 ] ||
		post_fail 'battery current is outside the diagnostic range'
	[ "$temperature" -ge -200 ] && [ "$temperature" -le 1000 ] ||
		post_fail 'battery temperature is outside the diagnostic range'
	[ "$usb_voltage_now" -ge 0 ] && [ "$usb_voltage_now" -le 30000000 ] &&
		[ "$usb_voltage_max" -ge 0 ] && [ "$usb_voltage_max" -le 30000000 ] ||
		post_fail 'USB voltage is outside the diagnostic range'
	[ "$usb_current_now" -ge -20000000 ] &&
		[ "$usb_current_now" -le 20000000 ] &&
		[ "$usb_current_max" -ge 0 ] && [ "$usb_current_max" -le 20000000 ] &&
		[ "$usb_input_current_limit" -ge 0 ] &&
		[ "$usb_input_current_limit" -le 20000000 ] ||
		post_fail 'USB current is outside the diagnostic range'
	case $status in
		Unknown|Charging|Discharging|'Not charging'|Full) ;;
		*) post_fail 'battery status is unknown' ;;
	esac
	[ "$usb_online" -eq 0 ] || [ "$usb_online" -eq 1 ] ||
		post_fail 'USB online state is not boolean'
	[ "$wls_online" -eq 0 ] || [ "$wls_online" -eq 1 ] ||
		post_fail 'wireless online state is not boolean'
	if [ "$mode" = charging ]; then
		[ "$usb_online" -eq 1 ] || post_fail 'full UCSI did not detect USB input'
		emit_progress 159
	fi

	for module in qcom_battmgr pmic_glink pdr_interface qcom_pdr_msg \
		qrtr_smd qcom_pd_mapper
	do
		[ -d "/sys/module/$module" ] ||
			post_fail "telemetry dependency is absent: $module"
	done
	for module in pmic_glink_altmode qcom_apr fastrpc; do
		[ ! -d "/sys/module/$module" ] ||
			post_fail "unreviewed module loaded during telemetry: $module"
	done
	if [ "$mode" = telemetry ]; then
		[ ! -d /sys/module/ucsi_glink ] ||
			post_fail 'unreviewed UCSI module loaded during telemetry'
		[ "$(find /sys/class/typec -mindepth 1 -maxdepth 1 2>/dev/null |
			wc -l)" -eq 0 ] || post_fail 'Type-C control device appeared'
	else
		for module in typec typec_ucsi ucsi_glink; do
			[ -d "/sys/module/$module" ] ||
				post_fail "charging dependency is absent: $module"
		done
	fi

	emit_evidence "capacity_percent=$capacity voltage_uV=$voltage_now current_uA=$current_now temp_dC=$temperature status=$status usb_online=$usb_online usb_voltage_uV=$usb_voltage_now usb_voltage_max_uV=$usb_voltage_max usb_current_uA=$usb_current_now usb_current_max_uA=$usb_current_max usb_input_current_limit_uA=$usb_input_current_limit usb_type=$usb_type wls_online=$wls_online"
else
	[ "$(find /sys/class/power_supply -mindepth 1 -maxdepth 1 2>/dev/null |
		wc -l)" -eq 0 ] || fail 'ADSP-only probe created a power-supply device'
fi

sleep "$settle_seconds"

if [ "$mode" = charging ]; then
	read_telemetry_property "$battery/voltage_now" final_voltage_now
	final_voltage_now=$telemetry_value
	read_telemetry_property "$battery/current_now" final_current_now
	final_current_now=$telemetry_value
	read_telemetry_property "$battery/temp" final_temperature
	final_temperature=$telemetry_value
	read_telemetry_property "$battery/status" final_status
	final_status=$telemetry_value
	read_telemetry_property "$usb/online" final_usb_online
	final_usb_online=$telemetry_value
	case $final_voltage_now:$final_current_now:$final_temperature:$final_usb_online in
		*[!0-9:-]*|:*|*:) post_fail 'final charging sample is not integer-valued' ;;
	esac
	[ "$final_voltage_now" -ge 2500000 ] && [ "$final_voltage_now" -le 10000000 ] ||
		post_fail 'final battery voltage is outside the diagnostic range'
	[ "$final_current_now" -ge -20000000 ] && [ "$final_current_now" -le 20000000 ] ||
		post_fail 'final battery current is outside the diagnostic range'
	[ "$final_temperature" -ge -200 ] && [ "$final_temperature" -le 1000 ] ||
		post_fail 'final battery temperature is outside the diagnostic range'
	[ "$final_usb_online" -eq 1 ] || post_fail 'USB input disappeared during settle'
	case $final_status in
		Unknown|Charging|Discharging|'Not charging'|Full) ;;
		*) post_fail 'final battery status is unknown' ;;
	esac
	emit_evidence "final_voltage_uV=$final_voltage_now final_current_uA=$final_current_now final_temp_dC=$final_temperature final_status=$final_status final_usb_online=$final_usb_online"
fi

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
[ "$(find /sys/class/udc -mindepth 1 -maxdepth 1 -printf '%f\n')" = \
	a600000.usb ] || post_fail 'side-port UDC identity changed after UCSI'
[ "$(cat /sys/kernel/config/usb_gadget/rog5-network-root/UDC)" = \
	a600000.usb ] || post_fail 'side-port gadget binding changed after UCSI'
[ "$(ip -4 -o address show dev usb0 |
	awk '$4 == "169.254.77.2/30" { count++ } END { print count + 0 }')" -eq 1 ] ||
	post_fail 'USB network address changed after UCSI'
route_state=$(ip -4 route get 169.254.77.1 2>/dev/null) ||
	post_fail 'USB network route changed after UCSI'
case " $route_state " in
	*' via '*) post_fail 'USB network route changed after UCSI' ;;
esac
set -- $route_state
[ "${1:-}" = 169.254.77.1 ] && [ "${2:-}" = dev ] &&
	[ "${3:-}" = usb0 ] ||
	post_fail 'USB network route changed after UCSI'
route_source=
while [ "$#" -gt 1 ]; do
	if [ "$1" = src ]; then
		route_source=$2
		break
	fi
	shift
done
[ "$route_source" = 169.254.77.2 ] ||
	post_fail 'USB network route changed after UCSI'
if [ "$early_mode" -eq 0 ]; then
	[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
		post_fail 'systemd regressed'
	[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
		awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
		post_fail 'a systemd unit failed'
fi
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	post_fail 'fatal kernel signature appeared'
[ "$(dmesg | tail -n +"$dmesg_start" |
	grep -Ec 'WARNING:|Call trace:|Unhandled fault|IOMMU.*fault|remoteproc.*crash' ||
	true)" -eq 0 ] || post_fail 'warning, fault, or remoteproc crash appeared'

if [ "$early_mode" -eq 1 ]; then
	case $final_status in
		Charging) emit_progress 170 ;;
		'Not charging') emit_progress 171 ;;
		Discharging) emit_progress 172 ;;
		Full) emit_progress 173 ;;
		Unknown) emit_progress 174 ;;
	esac
	if [ "$final_current_now" -gt 0 ]; then
		emit_progress 175
	elif [ "$final_current_now" -eq 0 ]; then
		emit_progress 176
	else
		emit_progress 177
	fi
	if [ "$final_voltage_now" -gt "$voltage_now" ]; then
		emit_progress 180
	elif [ "$final_voltage_now" -eq "$voltage_now" ]; then
		emit_progress 181
	else
		emit_progress 182
	fi
fi

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
if [ "$mode" != adsp ]; then
	allowed_modules="$allowed_modules
pdr_interface
qcom_pdr_msg
pmic_glink
qcom_battmgr
qrtr_smd
qcom_pd_mapper"
	if [ "$mode" = charging ]; then
		allowed_modules="$allowed_modules
typec
typec_ucsi
ucsi_glink"
	fi
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
if [ "$mode" = charging ]; then
	echo 'PASS battery-telemetry mode=charging stayed RAM-only, storage-isolated, full-UCSI, explicit-write-free, and rollback-guarded'
else
	echo "PASS battery-telemetry mode=$mode stayed RAM-only, storage-isolated, USB-C-control-free, and rollback-guarded"
fi
if [ "$early_mode" -eq 1 ]; then
	emit_progress 190
	early_reboot
fi
