#!/bin/sh
set -eu

SYS_INPUT=${SYS_INPUT:-/sys/class/input}
DEV_INPUT=${DEV_INPUT:-/dev/input}
SCREEN_TOGGLE=${SCREEN_TOGGLE:-/usr/local/bin/rog5-screen-toggle.sh}
EVTEST=${EVTEST:-evtest}
RETRY_DELAY=${RETRY_DELAY:-2}
RUNTIME_DIR=${RUNTIME_DIR:-/run}
once=${ROG5_SCREEN_BUTTON_ONCE:-0}
event_fifo=
evtest_pid=

case $once in
	0|1) ;;
	*) echo 'ERROR ROG5_SCREEN_BUTTON_ONCE must be 0 or 1' >&2; exit 2 ;;
esac
[ -x "$SCREEN_TOGGLE" ] || {
	echo "ERROR screen toggle is not executable: $SCREEN_TOGGLE" >&2
	exit 1
}
[ -d "$RUNTIME_DIR" ] && [ ! -L "$RUNTIME_DIR" ] || {
	echo "ERROR runtime directory is absent or linked: $RUNTIME_DIR" >&2
	exit 1
}

cleanup() {
	status=$?
	trap - EXIT
	if [ -n "$evtest_pid" ]; then
		kill "$evtest_pid" 2>/dev/null || true
		wait "$evtest_pid" 2>/dev/null || true
	fi
	[ -z "$event_fifo" ] || rm -f -- "$event_fifo"
	exit "$status"
}

terminate() {
	exit 0
}

trap terminate HUP INT TERM
trap cleanup EXIT

discover_event() {
	for name in "$SYS_INPUT"/event*/device/name; do
		[ -r "$name" ] || continue
		[ "$(cat "$name" 2>/dev/null)" = qpnp_pon ] || continue
		event_name=$(basename "$(dirname "$(dirname "$name")")")
		candidate=$DEV_INPUT/$event_name
		[ -e "$candidate" ] || continue
		printf '%s\n' "$candidate"
		return
	done
}

while :; do
	event=$(discover_event)
	if [ -z "$event" ]; then
		[ "$once" = 0 ] || {
			echo 'ERROR qpnp_pon input is absent' >&2
			exit 1
		}
		sleep "$RETRY_DELAY"
		continue
	fi

	event_fifo=$RUNTIME_DIR/rog5-screen-button.$$.events
	[ ! -e "$event_fifo" ] || {
		echo "ERROR event FIFO already exists: $event_fifo" >&2
		exit 1
	}
	umask 077
	mkfifo "$event_fifo"
	"$EVTEST" --grab "$event" >"$event_fifo" 2>/dev/null &
	evtest_pid=$!

	armed=1
	while IFS= read -r line; do
		case $line in
			*"(EV_KEY)"*"(KEY_POWER)"*"value 1"*)
				if [ "$armed" = 1 ]; then
					armed=0
					"$SCREEN_TOGGLE"
				fi
				;;
			*"(EV_KEY)"*"(KEY_POWER)"*"value 0"*)
				armed=1
				;;
		esac
	done <"$event_fifo"
	wait "$evtest_pid" 2>/dev/null || true
	evtest_pid=
	rm -f -- "$event_fifo"
	event_fifo=

	[ "$once" = 0 ] || exit 0
	sleep "$RETRY_DELAY"
done
