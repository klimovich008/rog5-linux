#!/bin/sh
set -u

root=${ROG5_METRICS_ROOT:-}
systemctl_command=${ROG5_METRICS_SYSTEMCTL:-systemctl}

case $root in
	''|/*) ;;
	*)
		echo 'ERROR ROG5_METRICS_ROOT must be empty or absolute' >&2
		exit 2
		;;
esac

kv() {
	printf '%s=%s\n' "$1" "$2"
}

metric_path() {
	printf '%s%s' "$root" "$1"
}

read_value() {
	path=$1
	if [ -r "$path" ]; then
		IFS= read -r value <"$path" || true
		printf '%s' "${value:-unavailable}"
	else
		printf 'unavailable'
	fi
}

read_metric() {
	read_value "$(metric_path "$1")"
}

read_meminfo() {
	key=$1
	path=$(metric_path /proc/meminfo)
	awk -v key="$key:" '
		$1 == key {
			print $2
			found = 1
			exit
		}
		END {
			if (!found)
				print "unavailable"
		}
	' "$path" 2>/dev/null
}

is_unsigned_integer() {
	case $1 in
		''|*[!0-9]*) return 1 ;;
		*) return 0 ;;
	esac
}

is_integer() {
	value=$1
	case $value in -*) value=${value#-} ;; esac
	is_unsigned_integer "$value"
}

subtract_metrics() {
	left=$1
	right=$2
	if is_unsigned_integer "$left" && is_unsigned_integer "$right"; then
		printf '%s' "$((left - right))"
	else
		printf 'unavailable'
	fi
}

presence() {
	[ -e "$(metric_path "$1")" ] && printf 'yes' || printf 'no'
}

systemctl_value() {
	property=$1
	value=$(
		"$systemctl_command" show rog5-chromium-headless.service \
			"--property=$property" --value 2>/dev/null || true
	)
	IFS='
' read -r value <<EOF
$value
EOF
	case $value in ''|'[not set]') value=unavailable ;; esac
	printf '%s' "$value"
}

systemctl_state() {
	unit=$1
	value=$("$systemctl_command" is-active "$unit" 2>/dev/null || true)
	IFS='
' read -r value <<EOF
$value
EOF
	printf '%s' "${value:-unavailable}"
}

mem_total=$(read_meminfo MemTotal)
mem_available=$(read_meminfo MemAvailable)
swap_total=$(read_meminfo SwapTotal)
swap_free=$(read_meminfo SwapFree)

kv kernel "$(uname -r)"
kv machine "$(uname -m)"
kv uptime_seconds "$(awk 'NR == 1 { print $1 }' "$(metric_path /proc/uptime)" 2>/dev/null || printf 'unavailable')"
kv load_1m "$(awk 'NR == 1 { print $1 }' "$(metric_path /proc/loadavg)" 2>/dev/null || printf 'unavailable')"
kv runnable_tasks "$(awk 'NR == 1 { split($4, tasks, "/"); print tasks[1] }' "$(metric_path /proc/loadavg)" 2>/dev/null || printf 'unavailable')"
kv memory_total_kib "$mem_total"
kv memory_available_kib "$mem_available"
kv memory_used_kib "$(subtract_metrics "$mem_total" "$mem_available")"
kv swap_total_kib "$swap_total"
kv swap_free_kib "$swap_free"
kv swap_used_kib "$(subtract_metrics "$swap_total" "$swap_free")"

cpu_total=$(
	awk '$1 == "cpu" {
		total = 0
		for (field = 2; field <= NF; field++)
			total += $field
		print total
		exit
	}' "$(metric_path /proc/stat)" 2>/dev/null || true
)
cpu_idle=$(
	awk '$1 == "cpu" {
		print $5 + $6
		exit
	}' "$(metric_path /proc/stat)" 2>/dev/null || true
)
kv cpu_total_ticks "${cpu_total:-unavailable}"
kv cpu_idle_ticks "${cpu_idle:-unavailable}"

battery=
legacy_battery=$(metric_path /sys/class/power_supply/battery)
if [ -e "$legacy_battery" ]; then
	battery=$legacy_battery
else
	for candidate in "$(metric_path /sys/class/power_supply)"/*; do
		[ -e "$candidate" ] || continue
		[ "$(read_value "$candidate/type")" = Battery ] || continue
		if [ -n "$battery" ]; then
			battery=
			break
		fi
		battery=$candidate
	done
fi

if [ -n "$battery" ]; then
	kv battery_present yes
	kv battery_status "$(read_value "$battery/status")"
	kv battery_capacity_percent "$(read_value "$battery/capacity")"
	kv battery_voltage_uv "$(read_value "$battery/voltage_now")"
	kv battery_current_ua "$(read_value "$battery/current_now")"
	kv battery_temp_deci_c "$(read_value "$battery/temp")"
else
	kv battery_present no
	kv battery_status unavailable
	kv battery_capacity_percent unavailable
	kv battery_voltage_uv unavailable
	kv battery_current_ua unavailable
	kv battery_temp_deci_c unavailable
fi

thermal_count=0
thermal_max=
for thermal_path in "$(metric_path /sys/class/thermal)"/thermal_zone*/temp; do
	[ -r "$thermal_path" ] || continue
	thermal_value=$(read_value "$thermal_path")
	is_integer "$thermal_value" || continue
	thermal_count=$((thermal_count + 1))
	if [ -z "$thermal_max" ] || [ "$thermal_value" -gt "$thermal_max" ]; then
		thermal_max=$thermal_value
	fi
done
kv thermal_zone_count "$thermal_count"
kv thermal_max_millidegree_c "${thermal_max:-unavailable}"

kv screen_state "$(read_metric /run/rog5-screen-state)"
kv backlight_brightness "$(read_metric /sys/class/backlight/panel0-backlight/brightness)"
kv dsi_status "$(read_metric /sys/class/drm/card0-DSI-1/status)"
dsi_modes=$(
	awk '
		NR == 1 { printf "%s", $0; next }
		{ printf ",%s", $0 }
		END { if (NR > 0) print "" }
	' "$(metric_path /sys/class/drm/card0-DSI-1/modes)" 2>/dev/null || true
)
kv dsi_modes "${dsi_modes:-unavailable}"

plasma_process_count=0
plasma_pss_kib=0
plasma_pss_readable=0
for status in "$(metric_path /proc)"/[0-9]*/status; do
	[ -r "$status" ] || continue
	process_name=$(awk '$1 == "Name:" { print $2; exit }' "$status" 2>/dev/null)
	case $process_name in
		kwin_wayland|plasmashell|krdpserver|Xwayland|kded6|kglobalacceld)
			plasma_process_count=$((plasma_process_count + 1))
			smaps=${status%/status}/smaps_rollup
			[ -r "$smaps" ] || continue
			process_pss=$(awk '$1 == "Pss:" { print $2; exit }' "$smaps" 2>/dev/null)
			is_unsigned_integer "$process_pss" || continue
			plasma_pss_kib=$((plasma_pss_kib + process_pss))
			plasma_pss_readable=$((plasma_pss_readable + 1))
			;;
	esac
done
kv plasma_process_count "$plasma_process_count"
if [ "$plasma_process_count" -eq 0 ] || [ "$plasma_pss_readable" -gt 0 ]; then
	kv plasma_pss_kib "$plasma_pss_kib"
else
	kv plasma_pss_kib unavailable
fi

if command -v "$systemctl_command" >/dev/null 2>&1; then
	default_target=$("$systemctl_command" get-default 2>/dev/null || true)
	kv default_target "${default_target:-unavailable}"
	kv server_inhibitor_state "$(systemctl_state rog5-server-inhibit.service)"
	kv agent_active_state "$(systemctl_value ActiveState)"
	kv agent_memory_current_bytes "$(systemctl_value MemoryCurrent)"
	kv agent_memory_peak_bytes "$(systemctl_value MemoryPeak)"
	kv agent_tasks_current "$(systemctl_value TasksCurrent)"
	kv agent_cpu_usage_nsec "$(systemctl_value CPUUsageNSec)"
	kv agent_restart_count "$(systemctl_value NRestarts)"
else
	kv default_target unavailable
	kv server_inhibitor_state unavailable
	kv agent_active_state unavailable
	kv agent_memory_current_bytes unavailable
	kv agent_memory_peak_bytes unavailable
	kv agent_tasks_current unavailable
	kv agent_cpu_usage_nsec unavailable
	kv agent_restart_count unavailable
fi

interface_metrics() {
	interface=$1
	base="/sys/class/net/$interface"
	if [ -e "$(metric_path "$base")" ]; then
		kv "${interface}_present" yes
		kv "${interface}_operstate" "$(read_metric "$base/operstate")"
		kv "${interface}_rx_bytes" "$(read_metric "$base/statistics/rx_bytes")"
		kv "${interface}_tx_bytes" "$(read_metric "$base/statistics/tx_bytes")"
	else
		kv "${interface}_present" no
		kv "${interface}_operstate" unavailable
		kv "${interface}_rx_bytes" unavailable
		kv "${interface}_tx_bytes" unavailable
	fi
}

for interface in usb0 wlan0 ap0 wg0; do
	interface_metrics "$interface"
done

render_node_count=0
for render_node in "$(metric_path /sys/class/drm)"/renderD*; do
	[ -e "$render_node" ] || continue
	render_node_count=$((render_node_count + 1))
done
kv drm_render_node_count "$render_node_count"
kv btf "$(presence /sys/kernel/btf/vmlinux)"

kgsl=/sys/devices/platform/soc/3d00000.qcom,kgsl-3d0/kgsl/kgsl-3d0
kv gpu_model "$(read_metric "$kgsl/gpu_model")"
kv gpu_reset_count "$(read_metric "$kgsl/reset_count")"
kv gpu_fault_count "$(read_metric "$kgsl/snapshot/faultcount")"

# Kernel command-line, addresses, MACs, SSIDs, serials, and credentials are
# intentionally outside this redacted evidence format.
