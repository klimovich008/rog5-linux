#!/bin/sh
set -u

failures=0
expected_kernel=${EXPECTED_KERNEL:-}

pass() { printf 'PASS %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; failures=$((failures + 1)); }
check_path() { [ -e "$2" ] && pass "$1" || fail "$1"; }

release=$(uname -r)
if [ -z "$expected_kernel" ] || [ "$release" = "$expected_kernel" ]; then
    pass "kernel $release"
else
    fail "kernel $release (expected $expected_kernel)"
fi

check_path 'UFS root block device' /dev/sda
check_path 'DRM card' /dev/dri/card0
check_path 'DSI connector' /sys/class/drm/card0-DSI-1/status
check_path 'panel backlight' /sys/class/backlight/panel0-backlight/brightness
check_path 'real battery supply' /sys/class/power_supply/battery/status
check_path 'USB network interface' /sys/class/net/usb0

touch_event=
for name in /sys/class/input/event*/device/name; do
    if [ "$(cat "$name" 2>/dev/null)" = fts_ts ]; then
        touch_event="/dev/input/$(basename "$(dirname "$(dirname "$name")")")"
        break
    fi
done
[ -n "$touch_event" ] && [ -e "$touch_event" ] && pass "touch $touch_event" || fail 'touch input'

if [ "$(cat /run/rog5-screen-state 2>/dev/null)" = off ] &&
   [ "$(cat /sys/class/backlight/panel0-backlight/brightness 2>/dev/null)" = 0 ]; then
    pass 'screen defaults off'
else
    fail 'screen defaults off'
fi

pgrep -f '[k]win_wayland' >/dev/null 2>&1 && pass 'Wayland compositor' || fail 'Wayland compositor'
pgrep -f '[/]usr/libexec/upowerd' >/dev/null 2>&1 && pass 'UPower' || fail 'UPower'
pgrep -f '[r]og5-screen-button-daemon.sh' >/dev/null 2>&1 && pass 'power-button daemon' || fail 'power-button daemon'

if [ -r /sys/class/power_supply/battery/status ]; then
    for field in status capacity voltage_now current_now temp; do
        value=$(cat "/sys/class/power_supply/battery/$field" 2>/dev/null || echo unavailable)
        printf 'INFO battery_%s=%s\n' "$field" "$value"
    done
fi

printf 'INFO screen_state=%s\n' "$(cat /run/rog5-screen-state 2>/dev/null || echo unavailable)"
printf 'INFO wifi=%s\n' "$([ -e /sys/class/net/wlan0 ] && echo present || echo absent)"
printf 'INFO btf=%s\n' "$([ -e /sys/kernel/btf/vmlinux ] && echo present || echo absent)"
printf 'SUMMARY failures=%s\n' "$failures"
exit "$failures"
