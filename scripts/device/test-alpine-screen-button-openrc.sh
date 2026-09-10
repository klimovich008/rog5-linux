#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
daemon=${DAEMON:-$repo/scripts/device/alpine-screen-button-daemon.sh}
service=${SERVICE:-$repo/packaging/alpine/rog5-screen-button}
starter=${STARTER:-$repo/scripts/device/alpine-screen-button-openrc-start.sh}
phone_wrapper=${PHONE_WRAPPER:-$repo/scripts/device/alpine-phone-start-wrapper.sh}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ -f "$daemon" ] && [ ! -L "$daemon" ] && [ -x "$daemon" ] ||
	fail 'missing executable Alpine screen-button daemon'
[ -f "$service" ] && [ ! -L "$service" ] && [ -x "$service" ] ||
	fail 'missing executable Alpine OpenRC service'
[ -f "$starter" ] && [ ! -L "$starter" ] && [ -x "$starter" ] ||
	fail 'missing executable Alpine OpenRC starter'
[ -f "$phone_wrapper" ] && [ ! -L "$phone_wrapper" ] &&
	[ -x "$phone_wrapper" ] ||
	fail 'missing executable Alpine phone-start wrapper'

sh -n "$daemon" "$service" "$starter" "$phone_wrapper"
shellcheck -s sh -S warning \
	"$daemon" "$service" "$starter" "$phone_wrapper"

for contract in \
	'SYS_INPUT=${SYS_INPUT:-/sys/class/input}' \
	'DEV_INPUT=${DEV_INPUT:-/dev/input}' \
	'SCREEN_TOGGLE=${SCREEN_TOGGLE:-/usr/local/bin/rog5-screen-toggle.sh}' \
	'EVTEST=${EVTEST:-evtest}' \
	'qpnp_pon' \
	'KEY_POWER' \
	'value 1' \
	'value 0' \
	'--grab' \
	'mkfifo' \
	'trap cleanup EXIT' \
	'kill "$evtest_pid"'
do
	grep -Fq -- "$contract" "$daemon" ||
		fail "Alpine daemon omits: $contract"
done

for contract in \
	'#!/sbin/openrc-run' \
	'supervisor=supervise-daemon' \
	'command=/usr/local/sbin/rog5-screen-button-daemon.sh' \
	'respawn_delay=2' \
	'respawn_max=0' \
	'/usr/local/bin/rog5-screen-toggle.sh off' \
	'need localmount' \
	'after modules'
do
	grep -Fqx -- "$contract" "$service" ||
		fail "Alpine OpenRC service omits: $contract"
done

for contract in \
	'OPENRC_RUNTIME=${OPENRC_RUNTIME:-/run/openrc}' \
	'RC_SERVICE=${RC_SERVICE:-rc-service}' \
	'SCREEN_TOGGLE=${SCREEN_TOGGLE:-/usr/local/bin/rog5-screen-toggle.sh}' \
	'rog5-screen-button' \
	'softlevel' \
	'"$RC_SERVICE" "$service" start' \
	'"$SCREEN_TOGGLE" off'
do
	grep -Fq -- "$contract" "$starter" ||
		fail "Alpine OpenRC starter omits: $contract"
done

for contract in \
	'ROG5_PHONE_START_BASE=${ROG5_PHONE_START_BASE:-/usr/local/libexec/rog5-phone-start-base}' \
	'ROG5_SCREEN_BUTTON_START=${ROG5_SCREEN_BUTTON_START:-/usr/local/sbin/rog5-screen-button-openrc-start.sh}' \
	'ROG5_SCREEN_BUTTON_LOG=${ROG5_SCREEN_BUTTON_LOG:-/var/log/rog5-screen-button.log}' \
	'exec "$phone_start_base" "$@"'
do
	grep -Fq -- "$contract" "$phone_wrapper" ||
		fail "Alpine phone-start wrapper omits: $contract"
done

if grep -Eq \
	'(^|[^[:alnum:]_])(fastboot|adb|reboot|poweroff|mkfs|fsck|mount|umount|dd)([^[:alnum:]_]|$)|/dev/(block|disk)' \
	"$daemon" "$service" "$starter" "$phone_wrapper"
then
	fail 'Alpine screen service contains a boot or storage action'
fi

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
mkdir -p "$stage/sys/event0/device" "$stage/dev" "$stage/runtime"
printf 'qpnp_pon\n' >"$stage/sys/event0/device/name"
: >"$stage/dev/event0"

cat >"$stage/evtest" <<'EOF'
#!/bin/sh
set -eu
[ "$1" = --grab ]
[ "$2" = "$EXPECTED_EVENT" ]
cat <<'EVENTS'
Event: time 1, type 1 (EV_KEY), code 116 (KEY_POWER), value 1
Event: time 1, type 1 (EV_KEY), code 116 (KEY_POWER), value 2
Event: time 1, type 1 (EV_KEY), code 116 (KEY_POWER), value 1
Event: time 1, type 1 (EV_KEY), code 116 (KEY_POWER), value 0
EVENTS
EOF
cat >"$stage/toggle" <<'EOF'
#!/bin/sh
set -eu
[ "$#" -eq 0 ]
printf 'toggle\n' >>"$TOGGLE_LOG"
EOF
chmod 0755 "$stage/evtest" "$stage/toggle"

EXPECTED_EVENT=$stage/dev/event0 \
TOGGLE_LOG=$stage/toggle.log \
SYS_INPUT=$stage/sys \
DEV_INPUT=$stage/dev \
SCREEN_TOGGLE=$stage/toggle \
EVTEST=$stage/evtest \
RUNTIME_DIR=$stage/runtime \
RETRY_DELAY=0 \
ROG5_SCREEN_BUTTON_ONCE=1 \
	"$daemon"

[ "$(cat "$stage/toggle.log")" = toggle ] ||
	fail 'one held power-button press did not produce exactly one toggle'

printf 'other_input\n' >"$stage/sys/event0/device/name"
set +e
EXPECTED_EVENT=$stage/dev/event0 \
TOGGLE_LOG=$stage/no-device-toggle.log \
SYS_INPUT=$stage/sys \
DEV_INPUT=$stage/dev \
SCREEN_TOGGLE=$stage/toggle \
EVTEST=$stage/evtest \
RUNTIME_DIR=$stage/runtime \
RETRY_DELAY=0 \
ROG5_SCREEN_BUTTON_ONCE=1 \
	"$daemon" >"$stage/no-device.out" 2>&1
no_device_status=$?
set -e
[ "$no_device_status" -ne 0 ] ||
	fail 'one-shot daemon accepted an absent qpnp_pon input'
[ ! -e "$stage/no-device-toggle.log" ] ||
	fail 'an unrelated input device triggered the screen toggle'

printf 'qpnp_pon\n' >"$stage/sys/event0/device/name"
cat >"$stage/blocking-evtest" <<'EOF'
#!/bin/sh
set -eu
[ "$1" = --grab ]
[ "$2" = "$EXPECTED_EVENT" ]
printf '%s\n' "$$" >"$EVTEST_PID_FILE"
trap 'exit 0' HUP INT TERM
while :; do sleep 1; done
EOF
chmod 0755 "$stage/blocking-evtest"

EXPECTED_EVENT=$stage/dev/event0 \
EVTEST_PID_FILE=$stage/evtest.pid \
TOGGLE_LOG=$stage/stopped-toggle.log \
SYS_INPUT=$stage/sys \
DEV_INPUT=$stage/dev \
SCREEN_TOGGLE=$stage/toggle \
EVTEST=$stage/blocking-evtest \
RUNTIME_DIR=$stage/runtime \
RETRY_DELAY=0 \
	"$daemon" >"$stage/stopped.out" 2>&1 &
daemon_pid=$!
attempt=0
while [ "$attempt" -lt 50 ] && [ ! -s "$stage/evtest.pid" ]; do
	attempt=$((attempt + 1))
	sleep 0.1
done
[ -s "$stage/evtest.pid" ] || fail 'daemon did not start its evtest child'
evtest_pid=$(cat "$stage/evtest.pid")
kill -TERM "$daemon_pid"
wait "$daemon_pid"
if kill -0 "$evtest_pid" 2>/dev/null; then
	fail 'daemon stop orphaned its evtest child'
fi
set -- "$stage/runtime"/rog5-screen-button.*.events
[ ! -e "$1" ] || fail 'daemon stop left its event FIFO behind'

mkdir "$stage/openrc"
cat >"$stage/rc-service" <<'EOF'
#!/bin/sh
set -eu
[ "$1" = rog5-screen-button ]
case $2 in
	status) [ -e "$RC_STATE" ] ;;
	start)
		: >"$RC_STATE"
		printf 'start\n' >>"$RC_CALLS"
		;;
	*) exit 2 ;;
esac
EOF
cat >"$stage/starter-toggle" <<'EOF'
#!/bin/sh
set -eu
[ "$1" = off ]
printf 'off\n' >>"$TOGGLE_LOG"
EOF
chmod 0755 "$stage/rc-service" "$stage/starter-toggle"

RC_STATE=$stage/rc-state \
RC_CALLS=$stage/rc-calls \
TOGGLE_LOG=$stage/starter-toggle.log \
OPENRC_RUNTIME=$stage/openrc \
RC_SERVICE=$stage/rc-service \
SCREEN_TOGGLE=$stage/starter-toggle \
	"$starter"
[ -f "$stage/openrc/softlevel" ] ||
	fail 'OpenRC starter did not initialize the volatile runlevel state'
[ "$(cat "$stage/rc-calls")" = start ] ||
	fail 'OpenRC starter did not start a stopped service exactly once'
[ "$(cat "$stage/starter-toggle.log")" = off ] ||
	fail 'OpenRC starter did not force the screen off'

RC_STATE=$stage/rc-state \
RC_CALLS=$stage/rc-calls \
TOGGLE_LOG=$stage/starter-toggle.log \
OPENRC_RUNTIME=$stage/openrc \
RC_SERVICE=$stage/rc-service \
SCREEN_TOGGLE=$stage/starter-toggle \
	"$starter"
[ "$(cat "$stage/rc-calls")" = start ] ||
	fail 'OpenRC starter restarted an already-running service'
[ "$(grep -c '^off$' "$stage/starter-toggle.log")" -eq 2 ] ||
	fail 'OpenRC starter did not enforce screen-off idempotently'

cat >"$stage/failing-starter" <<'EOF'
#!/bin/sh
printf 'starter\n' >>"$WRAPPER_CALLS"
exit 7
EOF
cat >"$stage/phone-start-base" <<'EOF'
#!/bin/sh
printf 'base:%s\n' "$*" >>"$WRAPPER_CALLS"
EOF
chmod 0755 "$stage/failing-starter" "$stage/phone-start-base"
WRAPPER_CALLS=$stage/wrapper-calls \
ROG5_PHONE_START_BASE=$stage/phone-start-base \
ROG5_SCREEN_BUTTON_START=$stage/failing-starter \
ROG5_SCREEN_BUTTON_LOG=$stage/wrapper.log \
	"$phone_wrapper" alpha beta
cat >"$stage/expected-wrapper-calls" <<'EOF'
starter
base:alpha beta
EOF
cmp "$stage/expected-wrapper-calls" "$stage/wrapper-calls" ||
	fail 'phone-start wrapper did not preserve fallback after starter failure'

echo 'PASS Alpine OpenRC screen service is restartable, boot-enabled-ready, storage-free, and power-key precise'
