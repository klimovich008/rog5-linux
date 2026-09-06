#!/bin/sh
# Minimal framebuffer-console status view; no compositor or GPU userspace.
set -eu

export LC_ALL=C
action=${1:-render}
state_file=${STATE_FILE:-/run/rog5-screen-state}
tty_device=${STATUS_TTY:-/dev/tty1}
net_class=${NET_CLASS:-/sys/class/net}
battery_dir=${BATTERY_DIR:-/sys/class/power_supply/qcom-battmgr-bat}
ip_command=${IP_COMMAND:-/usr/bin/ip}
date_command=${DATE_COMMAND:-/usr/bin/date}
sleep_command=${SLEEP_COMMAND:-/usr/bin/sleep}
poll_seconds=${POLL_SECONDS:-1}
off_poll_seconds=${OFF_POLL_SECONDS:-30}

case $action in
	render|watch|probe) ;;
	*) echo 'usage: status-screen.sh [render|watch|probe]' >&2; exit 2 ;;
esac
case $poll_seconds in ''|*[!0-9]*|0) echo 'ERROR invalid poll interval' >&2; exit 1 ;; esac
case $off_poll_seconds in ''|*[!0-9]*|0) echo 'ERROR invalid off interval' >&2; exit 1 ;; esac

read_field() {
	path=$1
	[ -f "$path" ] && [ ! -L "$path" ] || return 1
	value=$(sed -n '1p' "$path") || return 1
	[ -n "$value" ] || return 1
	printf '%s\n' "$value"
}

numeric_or_unknown() {
	value=$1
	case $value in ''|*[!0-9]*) printf '?\n' ;; *) printf '%s\n' "$value" ;; esac
}

discover_wifi() {
	active=0
	known=0
	selected=
	for wireless in "$net_class"/*/wireless; do
		[ -d "$wireless" ] || continue
		interface=${wireless%/wireless}
		interface=${interface##*/}
		case $interface in ''|*[!A-Za-z0-9_.-]*) continue ;; esac
		known=$((known + 1))
		carrier=$(read_field "$net_class/$interface/carrier" 2>/dev/null || echo 0)
		[ "$carrier" = 1 ] || continue
		active=$((active + 1))
		selected=$interface
	done
	case $active in
		0)
			[ "$known" -gt 0 ] && printf 'offline\n' || printf 'unsupported\n'
			;;
		1)
			address=$("$ip_command" -4 -o address show dev "$selected" scope global 2>/dev/null |
				awk 'NR == 1 { print $4 }')
			case $address in
				''|*[!0-9A-Fa-f:./]*) address=connecting ;;
			esac
			printf '%s %s\n' "$selected" "$address"
			;;
		*) printf 'multiple-active\n' ;;
	esac
}

collect_status() {
	timestamp=$("$date_command" '+%Y-%m-%d %H:%M:%S %Z')
	case $timestamp in *[!A-Za-z0-9_:+.\ -]*) timestamp=unknown ;; esac
	wifi=$(discover_wifi)
	capacity=$(numeric_or_unknown "$(read_field "$battery_dir/capacity" 2>/dev/null || true)")
	status=$(read_field "$battery_dir/status" 2>/dev/null || echo unknown)
	case $status in ''|*[!A-Za-z-]*) status=unknown ;; esac
	voltage=$(numeric_or_unknown "$(read_field "$battery_dir/voltage_now" 2>/dev/null || true)")
	temperature=$(read_field "$battery_dir/temp" 2>/dev/null || true)
	case $temperature in
		''|*[!0-9-]*) temperature_text='?' ;;
		-*)
			temperature=${temperature#-}
			case $temperature in ''|*[!0-9]*) temperature_text='?' ;;
				*) temperature_text="-$((temperature / 10)).$((temperature % 10)) C" ;;
			esac
		;;
		*) temperature_text="$((temperature / 10)).$((temperature % 10)) C" ;;
	esac
	[ "$voltage" = '?' ] || voltage=$((voltage / 1000))
	printf 'ROG Phone 5 Linux\n\nTime:    %s\nWi-Fi:  %s\nBattery: %s%% %s  %s mV  %s\n\nPower button: toggle screen\nServer services remain running\n' \
		"$timestamp" "$wifi" "$capacity" "$status" "$voltage" "$temperature_text"
}

validate_tty() {
	[ ! -L "$tty_device" ] || return 1
	if [ "${ROG5_STATUS_TESTING:-0}" = 1 ]; then
		[ -f "$tty_device" ] || return 1
	else
		[ -c "$tty_device" ] || return 1
	fi
}

render() {
	validate_tty || { echo 'ERROR status tty unavailable' >&2; return 1; }
	status=$(collect_status)
	printf '\033[2J\033[H\033[?25l%s\n' "$status" >"$tty_device"
}

case $action in
	probe) collect_status ;;
	render) render ;;
	watch)
		while :; do
			state=$(read_field "$state_file" 2>/dev/null || echo off)
			if [ "$state" = on ]; then
				render || true
				delay=$poll_seconds
			else
				delay=$off_poll_seconds
			fi
			"$sleep_command" "$delay"
		done
		;;
esac
