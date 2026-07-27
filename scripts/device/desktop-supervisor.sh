#!/bin/sh
set -u

action=${1:-run}
desktop_start=${ROG5_DESKTOP_START:-/usr/local/sbin/rog5-desktop-start}
interval=${ROG5_DESKTOP_SUPERVISOR_INTERVAL:-30}
max_cycles=${ROG5_DESKTOP_SUPERVISOR_MAX_CYCLES:-0}
runtime=${ROG5_DESKTOP_SUPERVISOR_RUNTIME:-/run/rog5-desktop-supervisor}
pidfile=$runtime/pid
lockfile=$runtime/lock
logfile=$runtime/log
script_path=$(readlink -f "$0" 2>/dev/null || printf '%s' "$0")

case $runtime in
	/*) ;;
	*)
		echo 'ERROR supervisor runtime path must be absolute' >&2
		exit 2
		;;
esac

process_matches() {
	pid=$1
	case $pid in ''|*[!0-9]*) return 1 ;; esac
	[ -r "/proc/$pid/cmdline" ] || return 1
	kill -0 "$pid" 2>/dev/null || return 1
	command_line=$(tr '\000' ' ' <"/proc/$pid/cmdline")
	case $command_line in
		*"$script_path run"*) return 0 ;;
		*) return 1 ;;
	esac
}

running_pid() {
	[ -r "$pidfile" ] || return 1
	IFS= read -r pid <"$pidfile" || return 1
	process_matches "$pid" || return 1
	printf '%s' "$pid"
}

desktop_healthy() {
	pgrep -x Xvnc >/dev/null 2>&1 &&
		pgrep -f '[w]ebsockify.*127.0.0.1:6080' >/dev/null 2>&1 &&
		pgrep -u browser -f '[k]win_wayland.*--socket wayland-1' >/dev/null 2>&1 &&
		pgrep -u browser -x plasmashell >/dev/null 2>&1 &&
		pgrep -u browser -f '[c]hromium.*--remote-debugging-port=9222' >/dev/null 2>&1 &&
		pgrep -u browser -f '[t]tyd.*127.0.0.1.*7681' >/dev/null 2>&1
}

run_supervisor() {
	case $interval in
		''|*[!0-9]*|0)
			echo 'ERROR supervisor interval must be a positive integer' >&2
			exit 2
			;;
	esac
	case $max_cycles in
		''|*[!0-9]*)
			echo 'ERROR supervisor cycle limit must be a non-negative integer' >&2
			exit 2
			;;
	esac
	[ -x "$desktop_start" ] || {
		echo "ERROR desktop launcher is not executable: $desktop_start" >&2
		exit 1
	}

	mkdir -p "$runtime"
	chmod 0700 "$runtime"
	exec 9>"$lockfile"
	flock -n 9 || exit 0
	printf '%s\n' "$$" >"$pidfile"

	cleanup() {
		if [ -r "$pidfile" ]; then
			IFS= read -r recorded_pid <"$pidfile" || recorded_pid=
			[ "$recorded_pid" != "$$" ] || rm -f "$pidfile"
		fi
	}
	trap 'cleanup; exit 0' HUP INT TERM
	trap cleanup EXIT

	cycles=0
	while :; do
		if ! desktop_healthy; then
			"$desktop_start" ||
				echo 'WARN desktop launcher failed; retrying next cycle' >&2
		fi

		cycles=$((cycles + 1))
		[ "$max_cycles" -eq 0 ] ||
			[ "$cycles" -lt "$max_cycles" ] ||
			exit 0
		sleep "$interval"
	done
}

start_supervisor() {
	mkdir -p "$runtime"
	chmod 0700 "$runtime"
	if running_pid >/dev/null 2>&1; then
		return 0
	fi
	rm -f "$pidfile"
	nohup "$script_path" run </dev/null >>"$logfile" 2>&1 &
	started_pid=$!

	i=0
	while [ "$i" -lt 30 ]; do
		active_pid=$(running_pid 2>/dev/null || true)
		[ "$active_pid" != "$started_pid" ] || return 0
		kill -0 "$started_pid" 2>/dev/null || break
		i=$((i + 1))
		sleep 0.1
	done
	echo 'ERROR desktop supervisor did not start' >&2
	return 1
}

stop_supervisor() {
	pid=$(running_pid 2>/dev/null || true)
	if [ -z "$pid" ]; then
		rm -f "$pidfile"
		return 0
	fi
	kill -TERM "$pid"
	i=0
	while [ "$i" -lt 30 ] && kill -0 "$pid" 2>/dev/null; do
		i=$((i + 1))
		sleep 0.1
	done
	! kill -0 "$pid" 2>/dev/null || {
		echo 'ERROR desktop supervisor did not stop' >&2
		return 1
	}
	rm -f "$pidfile"
}

case $action in
	run) run_supervisor ;;
	start) start_supervisor ;;
	stop) stop_supervisor ;;
	status) running_pid ;;
	*)
		echo 'usage: rog5-desktop-supervisor [start|run|stop|status]' >&2
		exit 2
		;;
esac
