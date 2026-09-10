#!/bin/sh
set -eu

OPENRC_RUNTIME=${OPENRC_RUNTIME:-/run/openrc}
RC_SERVICE=${RC_SERVICE:-rc-service}
SCREEN_TOGGLE=${SCREEN_TOGGLE:-/usr/local/bin/rog5-screen-toggle.sh}
service=${ROG5_SCREEN_SERVICE:-rog5-screen-button}

case $OPENRC_RUNTIME in
	/*) ;;
	*) echo 'ERROR OpenRC runtime path must be absolute' >&2; exit 2 ;;
esac
command -v "$RC_SERVICE" >/dev/null 2>&1 || {
	echo "ERROR rc-service is unavailable: $RC_SERVICE" >&2
	exit 1
}
[ -x "$SCREEN_TOGGLE" ] || {
	echo "ERROR screen toggle is not executable: $SCREEN_TOGGLE" >&2
	exit 1
}

mkdir -p "$OPENRC_RUNTIME"
[ -d "$OPENRC_RUNTIME" ] && [ ! -L "$OPENRC_RUNTIME" ] || {
	echo "ERROR OpenRC runtime is absent or linked: $OPENRC_RUNTIME" >&2
	exit 1
}
[ -e "$OPENRC_RUNTIME/softlevel" ] ||
	: >"$OPENRC_RUNTIME/softlevel"

if ! "$RC_SERVICE" "$service" status >/dev/null 2>&1; then
	"$RC_SERVICE" "$service" start
fi
"$RC_SERVICE" "$service" status >/dev/null
"$SCREEN_TOGGLE" off

echo 'PASS Alpine screen-button OpenRC service is active with screen off'
