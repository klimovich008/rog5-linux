#!/bin/sh
set -u

export LC_ALL=C
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

candidate=${ROG5_POWER_EVIDENCE_CANDIDATE:-}
boot_id=${ROG5_POWER_EVIDENCE_BOOT_ID:-}
reporter=${ROG5_POWER_EVIDENCE_REPORTER:-/sbin/rog5-early-target-diag}
firmware_dir=${ROG5_POWER_FIRMWARE_DIR:-/opt/rog5-charge-firmware}
pdr_module=${ROG5_POWER_PDR_MODULE:-/opt/rog5-charge-modules/pdr_interface.ko}
settle_seconds=${ROG5_POWER_SETTLE_SECONDS:-20}
sequence=0
record_count=0
record_limit=512
direct_output=0
newline='
'

force_reboot() {
	echo b >/proc/sysrq-trigger 2>/dev/null || true
	while :; do sleep 3600; done
}

boottime_ms() {
	awk '{ printf "%.0f\n", $1 * 1000 }' /proc/uptime
}

hex_value() {
	head -c 256 | od -An -tx1 -v | tr -d ' \n'
}

emit() {
	category=$1
	name=$2
	status=$3
	value=$4
	case $category:$name:$status in
		*[!a-z0-9_.:-]*:*|*:*[!a-z0-9_.:-]*:*|*:*:present|*:*:absent|*:*:error) ;;
		*) force_reboot ;;
	esac
	case $value in *[!0-9a-f]*) force_reboot ;; esac
	[ $(( ${#value} % 2 )) -eq 0 ] || force_reboot
	[ "${#value}" -le 512 ] || force_reboot
	record_count=$((record_count + 1))
	[ "$record_count" -le "$record_limit" ] || force_reboot
	sequence=$((sequence + 1))
	if [ "$direct_output" -eq 1 ]; then
		payload="format=rog5-early-power-evidence-v1${newline}candidate=$candidate${newline}boot_id=$boot_id${newline}sequence=$sequence${newline}boottime_ms=$(boottime_ms)${newline}category=$category${newline}name=$name${newline}status=$status${newline}encoding=hex${newline}value=$value${newline}"
		printf '%s:%s,' "${#payload}" "$payload" >&3 || force_reboot
	else
		"$reporter" evidence "$category" "$name" "$status" "$value" ||
			force_reboot
	fi
}

emit_text() {
	emit "$1" "$2" "$3" "$(printf '%s' "$4" | hex_value)"
}

fatal() {
	class=$1
	reason=$2
	emit_text safety "$class" error "$reason" || true
	force_reboot
}

valid_integer() {
	case $1 in ''|'-'|*[!0-9-]*|*-*-) return 1 ;; esac
	return 0
}

emit_file() {
	category=$1
	name=$2
	path=$3
	if [ ! -e "$path" ]; then
		emit "$category" "$name" absent ''
		return
	fi
	if [ -L "$path" ] || [ ! -f "$path" ] || [ ! -r "$path" ]; then
		emit_text "$category" "$name" error unsafe-or-unreadable
		return
	fi
	size=$(wc -c <"$path" 2>/dev/null) || {
		emit_text "$category" "$name" error read-failed
		return
	}
	case $size in ''|*[!0-9]*) emit_text "$category" "$name" error size-invalid; return ;; esac
	if [ "$size" -gt 256 ]; then
		emit_text "$category" "$name" error value-oversize
		return
	fi
	value=$(hex_value <"$path") || {
		emit_text "$category" "$name" error read-failed
		return
	}
	if [ -n "$value" ]; then
		emit "$category" "$name" present "$value"
	else
		emit "$category" "$name" absent ''
	fi
}

physical_storage_count() {
	count=0
	for disk in /sys/class/block/*; do
		[ -e "$disk/device" ] || continue
		[ ! -e "$disk/partition" ] || continue
		count=$((count + 1))
	done
	printf '%s\n' "$count"
}

has_block_backed_mount() {
	mount_inventory=$1
	sys_dev_block=$2
	while read -r _ _ device _ _ _ rest; do
		[ -e "$sys_dev_block/$device" ] || continue
		return 0
	done <"$mount_inventory"
	return 1
}

verify_storage_absent() {
	[ "$(physical_storage_count)" -eq 0 ] || fatal storage physical-block-visible
	! has_block_backed_mount /proc/self/mountinfo /sys/dev/block ||
		fatal storage block-backed-mount
}

single_expected_udc() {
	root=$1
	count=0
	selected=
	for candidate in "$root"/*; do
		[ -e "$candidate" ] || continue
		count=$((count + 1))
		selected=${candidate##*/}
	done
	[ "$count" -eq 1 ] && [ "$selected" = a600000.usb ] || return 1
	printf '%s\n' "$selected"
}

verify_transport() {
	[ "$(single_expected_udc /sys/class/udc)" = a600000.usb ] ||
		fatal transport udc-identity
	[ "$(cat /sys/kernel/config/usb_gadget/rog5-network-root/UDC 2>/dev/null)" = a600000.usb ] ||
		fatal transport gadget-binding
	[ "$(cat /sys/class/net/usb0/carrier 2>/dev/null)" = 1 ] ||
		fatal transport carrier
	[ "$(ip -4 -o address show dev usb0 | awk '$4 == "169.254.77.2/30" { count++ } END { print count + 0 }')" -eq 1 ] ||
		fatal transport address
	route=$(ip -4 route get 169.254.77.1 2>/dev/null) || fatal transport route
	case " $route " in *' via '*) fatal transport route ;; esac
	printf '%s\n' "$route" | grep -Eq '^169[.]254[.]77[.]1 dev usb0 .* src 169[.]254[.]77[.]2( |$)' ||
		fatal transport route
}

verify_rollback() {
	pid_file=/run/rog5-network-root-watchdog.pid
	[ -s "$pid_file" ] || fatal rollback watchdog-pid-absent
	pid=$(cat "$pid_file")
	case $pid in ''|*[!0-9]*) fatal rollback watchdog-pid-invalid ;; esac
	kill -0 "$pid" 2>/dev/null || fatal rollback watchdog-not-running
}

load_module() {
	module=$1
	if [ -d "/sys/module/$module" ]; then
		emit_text module "$module" present already-loaded
		return
	fi
	if output=$(modprobe --first-time "$module" 2>&1); then
		emit_text module "$module" present loaded
	else
		emit_text module "$module" error "${output:-load-failed}"
	fi
}

snapshot_class() {
	category=$1
	root=$2
	if [ ! -d "$root" ]; then
		emit "$category" class absent ''
		return
	fi
	entry_count=0
	for entry in "$root"/*; do
		[ -e "$entry" ] || continue
		base=$(basename "$entry")
		case $base in *[!A-Za-z0-9_.:-]*) continue ;; esac
		entry_count=$((entry_count + 1))
		[ "$entry_count" -le 16 ] || {
			emit_text "$category" class error too-many-entries
			break
		}
		property_count=0
		for property in "$entry"/*; do
			[ -e "$property" ] || continue
			[ -f "$property" ] || continue
			property_name=$(basename "$property")
			case $property_name in *[!A-Za-z0-9_.:-]*) continue ;; esac
			property_count=$((property_count + 1))
			[ "$property_count" -le 96 ] || {
				emit_text "$category" "$base" error too-many-properties
				break
			}
			emit_file "$category" "$base:$property_name" "$property"
		done
	done
	[ "$entry_count" -gt 0 ] || emit "$category" class absent ''
}

snapshot_remoteproc() {
	count=0
	for entry in /sys/class/remoteproc/remoteproc*; do
		[ -e "$entry" ] || continue
		name=$(basename "$entry")
		count=$((count + 1))
		for property in name state firmware recovery; do
			emit_file remoteproc "$name:$property" "$entry/$property"
		done
	done
	[ "$count" -gt 0 ] || emit remoteproc class absent ''
}

snapshot_auxiliary() {
	count=0
	for entry in /sys/bus/auxiliary/devices/pmic_glink.*; do
		[ -e "$entry" ] || continue
		name=$(basename "$entry")
		count=$((count + 1))
		emit_text pmic_glink "$name" present published
	done
	[ "$count" -gt 0 ] || emit pmic_glink class absent ''
}

read_number() {
	path=$1
	[ -r "$path" ] && value=$(cat "$path" 2>/dev/null) && valid_integer "$value" || return 1
	printf '%s\n' "$value"
}

check_battery_safety() {
	battery=/sys/class/power_supply/qcom-battmgr-bat
	voltage=$(read_number "$battery/voltage_now") || return 0
	temperature=$(read_number "$battery/temp") || return 0
	[ "$voltage" -ge 5500000 ] && [ "$voltage" -le 9200000 ] ||
		fatal unsafe battery-voltage
	[ "$temperature" -ge 0 ] && [ "$temperature" -lt 600 ] ||
		fatal unsafe battery-temperature
}

snapshot_dmesg() {
	file=/run/rog5-early-power-dmesg
	dmesg | tail -n 160 >"$file" || {
		emit_text dmesg capture error unavailable
		return
	}
	line_number=0
	while IFS= read -r line; do
		line_number=$((line_number + 1))
		emit_text dmesg "line:$line_number" present "$line"
	done <"$file"
}

self_test() {
	candidate=headless-power-usb-observer-v99
	boot_id=01234567-89ab-cdef-0123-456789abcdef
	direct_output=1
	exec 3>&1
	emit_text battery capacity present 50
	emit typec port0 absent ''
	emit_text summary result present complete
	exit 0
}

[ "${1:-}" != --self-test ] || self_test
[ "${ALLOW_NETWORK_ROOT_EARLY_POWER_OBSERVER:-}" = 1 ] || exit 1
case $candidate in ''|.*|*..*|*[!a-z0-9.-]*) exit 1 ;; esac
case $boot_id in ????????-????-????-????-????????????) ;; *) exit 1 ;; esac
case $settle_seconds in ''|*[!0-9]*) exit 1 ;; esac
[ "$settle_seconds" -ge 5 ] && [ "$settle_seconds" -le 45 ] || exit 1
[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] || force_reboot
[ -x "$reporter" ] && [ -f "$reporter" ] && [ ! -L "$reporter" ] ||
	force_reboot

emit_text observer state present started
verify_storage_absent
verify_transport
verify_rollback
emit_text identity kernel present "$(uname -r)"

firmware_path=/sys/module/firmware_class/parameters/path
if [ -d "$firmware_dir" ] && [ -w "$firmware_path" ] &&
	printf '%s\n' "$firmware_dir" >"$firmware_path" 2>/dev/null; then
	emit_text firmware path present "$firmware_dir"
else
	emit_text firmware path error unavailable
fi

load_module qcom_q6v5_pas
load_module qrtr_smd
load_module qcom_pd_mapper
if [ -f "$pdr_module" ] && [ ! -L "$pdr_module" ]; then
	if output=$(insmod "$pdr_module" 2>&1); then
		emit_text module pdr_interface present loaded
	else
		emit_text module pdr_interface error "${output:-load-failed}"
	fi
else
	emit module pdr_interface absent ''
fi
load_module pmic_glink
load_module qcom_battmgr
load_module ucsi_glink

waited=0
while [ "$waited" -lt 20 ]; do
	[ -e /sys/class/power_supply/qcom-battmgr-bat ] &&
		[ -e /sys/class/typec/port0 ] && break
	waited=$((waited + 1))
	sleep 1
done

check_battery_safety
snapshot_remoteproc
snapshot_auxiliary
snapshot_class power_supply /sys/class/power_supply
snapshot_class typec /sys/class/typec

battery=/sys/class/power_supply/qcom-battmgr-bat
usb=/sys/class/power_supply/qcom-battmgr-usb
initial_voltage=$(read_number "$battery/voltage_now" 2>/dev/null || true)
initial_current=$(read_number "$battery/current_now" 2>/dev/null || true)
sleep "$settle_seconds"
verify_storage_absent
verify_transport
verify_rollback
check_battery_safety
final_voltage=$(read_number "$battery/voltage_now" 2>/dev/null || true)
final_current=$(read_number "$battery/current_now" 2>/dev/null || true)
usb_online=$(read_number "$usb/online" 2>/dev/null || true)

if [ -n "$initial_voltage" ] && [ -n "$final_voltage" ]; then
	emit_text summary voltage-trend present "$initial_voltage:$final_voltage"
else
	emit_text summary voltage-trend error telemetry-unavailable
fi
if [ -n "$initial_current" ] && [ -n "$final_current" ] &&
	[ "$initial_current" -gt 0 ] && [ "$final_current" -gt 0 ] &&
	[ "${usb_online:-0}" -eq 1 ]; then
	emit_text summary net-positive present "$initial_current:$final_current"
elif [ -n "$initial_current" ] && [ -n "$final_current" ]; then
	emit_text summary net-positive absent "$initial_current:$final_current"
else
	emit_text summary net-positive error telemetry-unavailable
fi

snapshot_dmesg
emit_text summary result present complete
sleep 1
force_reboot
