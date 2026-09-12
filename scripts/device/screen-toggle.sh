#!/bin/sh
set -eu

action=${1:-toggle}
state_file=${STATE_FILE:-/run/rog5-screen-state}
brightness_file=${BRIGHTNESS_FILE:-/run/rog5-screen-brightness}
backlight_dir=${BACKLIGHT_DIR:-}
display_profile=${DISPLAY_PROFILE:-/usr/local/bin/rog5-display-profile.sh}
status_screen=${STATUS_SCREEN:-/usr/local/libexec/rog5-status-screen}
power_mode=${DISPLAY_POWER_MODE:-auto}
dpms_file=${DPMS_STATE_FILE:-/sys/class/drm/card0-DSI-1/dpms}
lock_file=${LOCK_FILE:-${state_file}.lock}
temporary=

fail() { echo "ERROR screen transition: $*" >&2; exit 1; }
publish() {
    temporary=$(mktemp "${2}.XXXXXX") || return 1
    printf '%s\n' "$1" > "$temporary" && mv -f -- "$temporary" "$2" || return 1
    temporary=
}
trap '[ -z "$temporary" ] || rm -f -- "$temporary"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

case $action in
    off|on|toggle) ;;
    *) echo 'usage: screen-toggle.sh [off|on|toggle]' >&2; exit 2 ;;
esac
case $power_mode in auto|required|backlight-only) ;; *) fail 'invalid DISPLAY_POWER_MODE' ;; esac
use_dpms=0
if [ "$power_mode" != backlight-only ] && [ -x "$display_profile" ]; then
    use_dpms=1
elif [ "$power_mode" = required ]; then
    fail 'required display-power helper is unavailable'
fi

# Hold one stable lock inode across observation, helpers and publication. Child
# helpers inherit the lock; killing their parent cannot admit an overlapping
# transition before the bounded child exits. Never unlink a shared flock file.
umask 077
mkdir -p "$(dirname "$state_file")" "$(dirname "$brightness_file")" "$(dirname "$lock_file")"
for file in "$state_file" "$brightness_file" "$lock_file"; do
    [ ! -L "$file" ] || fail 'linked state/lock file'
    [ ! -e "$file" ] || [ -f "$file" ] || fail 'nonregular state/lock file'
done
exec 9>>"$lock_file"
flock -w 2 9 || fail 'another screen transition holds the lock'

if [ -z "$backlight_dir" ]; then
    for candidate in /sys/class/backlight/panel0-backlight /sys/class/backlight/*; do
        if [ -w "$candidate/brightness" ] && [ -r "$candidate/max_brightness" ]; then
            backlight_dir=$candidate
            break
        fi
    done
fi
[ -n "$backlight_dir" ] || { echo 'ERROR no writable backlight found' >&2; exit 1; }

backlight=$backlight_dir/brightness
maximum=$(cat "$backlight_dir/max_brightness")
current=$(cat "$backlight")
case $maximum in ''|*[!0-9]*|0) echo 'ERROR invalid maximum brightness' >&2; exit 1 ;; esac
case $current in ''|*[!0-9]*) echo 'ERROR invalid current brightness' >&2; exit 1 ;; esac
[ "$current" -le "$maximum" ] || { echo 'ERROR brightness exceeds maximum' >&2; exit 1; }

# The cache is a record of the last completed operation, not hardware truth.
# Reconcile with connector DPMS only when this invocation controls it. In
# backlight-only mode an independently powered-off connector must not prevent
# toggling a nonzero backlight down to zero.
if [ "$current" -eq 0 ]; then state=off; else state=on; fi
if [ "$use_dpms" -eq 1 ]; then
    reported=$(cat "$dpms_file" 2>/dev/null || true)
    case $reported in Off|off) state=off ;; esac
fi
[ "$action" != toggle ] || action=$([ "$state" = on ] && echo off || echo on)
publish unknown "$state_file" || fail 'cannot publish transition entry'

display_power() {
    [ "$use_dpms" -eq 1 ] || return 0
    if timeout -k 1 3 "$display_profile" "dpms-$action"; then
        return 0
    else
        result=$?
        echo "ERROR requested dpms-$action failed (status $result); state unknown" >&2
        exit "$result"
    fi
}

case $action in
    off)
        if [ "$current" -ne 0 ]; then
            publish "$current" "$brightness_file" || fail 'cannot save brightness'
            printf '0\n' > "$backlight"
        fi
        display_power
        expected_brightness=0
        ;;
    on)
        display_power
        brightness=$(cat "$brightness_file" 2>/dev/null || true)
        case $brightness in
            ''|*[!0-9]*|0) brightness=$((maximum / 2)); [ "$brightness" -gt 0 ] || brightness=1 ;;
        esac
        [ "$brightness" -le "$maximum" ] || brightness=$maximum
        printf '%s\n' "$brightness" > "$backlight"
        expected_brightness=$brightness
        [ ! -x "$status_screen" ] ||
            timeout -k 1 1 "$status_screen" render >/dev/null 2>&1 ||
            echo 'WARN status-screen render failed' >&2
        ;;
esac
[ "$(cat "$backlight")" = "$expected_brightness" ] || fail 'backlight readback differs'
power_result=NOT_RUN
scope=backlight-only
if [ "$use_dpms" -eq 1 ]; then
    scope=backlight-and-dpms-request
    power_result=UNVERIFIED
    reported=$(cat "$dpms_file" 2>/dev/null || true)
    case $reported in
        On|on) reported=on ;;
        Off|off) reported=off ;;
        *) reported=unknown ;;
    esac
    if [ "$reported" != unknown ]; then
        [ "$reported" = "$action" ] || fail 'reported display power disagrees with request'
        power_result=reported-$reported
    fi
fi
publish "$action" "$state_file" || fail 'cannot publish completed transition'
echo "PASS backlight=$action scope=$scope display-power=$power_result"
