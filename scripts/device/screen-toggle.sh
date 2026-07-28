#!/bin/sh
set -eu

action=${1:-toggle}
state_file=${STATE_FILE:-/run/rog5-screen-state}
brightness_file=${BRIGHTNESS_FILE:-/run/rog5-screen-brightness}
backlight_dir=${BACKLIGHT_DIR:-}
display_profile=${DISPLAY_PROFILE:-/usr/local/bin/rog5-display-profile.sh}

case $action in
    off|on|toggle) ;;
    *) echo 'usage: screen-toggle.sh [off|on|toggle]' >&2; exit 2 ;;
esac

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

state=$(cat "$state_file" 2>/dev/null || true)
case $state in
    on|off) ;;
    *) if [ "$current" -eq 0 ]; then state=off; else state=on; fi ;;
esac
[ "$action" != toggle ] || action=$([ "$state" = on ] && echo off || echo on)
mkdir -p "$(dirname "$state_file")" "$(dirname "$brightness_file")"

case $action in
    off)
        if [ "$current" -ne 0 ]; then
            printf '%s\n' "$current" > "$brightness_file"
            printf '0\n' > "$backlight"
        fi
        [ ! -x "$display_profile" ] ||
            "$display_profile" dpms-off >/dev/null 2>&1 || true
        printf 'off\n' > "$state_file"
        echo 'Screen off; server remains running'
        ;;
    on)
        [ ! -x "$display_profile" ] ||
            "$display_profile" dpms-on >/dev/null 2>&1 || true
        brightness=$(cat "$brightness_file" 2>/dev/null || true)
        case $brightness in
            ''|*[!0-9]*|0) brightness=$((maximum / 2)); [ "$brightness" -gt 0 ] || brightness=1 ;;
        esac
        [ "$brightness" -le "$maximum" ] || brightness=$maximum
        printf '%s\n' "$brightness" > "$backlight"
        printf 'on\n' > "$state_file"
        echo 'Screen on'
        ;;
esac
