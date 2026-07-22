#!/bin/sh
set -u

state_file=/run/rog5-screen-state
brightness_file=/run/rog5-screen-brightness
backlight=/sys/class/backlight/panel0-backlight/brightness
display_profile=/usr/local/bin/rog5-display-profile.sh
state=$(cat "$state_file" 2>/dev/null || echo on)

if [ "$state" = on ]; then
    brightness=$(cat "$backlight" 2>/dev/null || echo 512)
    [ "$brightness" -gt 0 ] 2>/dev/null && printf '%s\n' "$brightness" > "$brightness_file"
    printf '0\n' > "$backlight"
    [ ! -x "$display_profile" ] || "$display_profile" dpms-off >/dev/null 2>&1 || true
    printf 'off\n' > "$state_file"
    echo 'Screen off; server remains running'
else
    [ ! -x "$display_profile" ] || "$display_profile" dpms-on >/dev/null 2>&1 || true
    brightness=$(cat "$brightness_file" 2>/dev/null || echo 512)
    [ "$brightness" -gt 0 ] 2>/dev/null || brightness=512
    printf '%s\n' "$brightness" > "$backlight"
    printf 'on\n' > "$state_file"
    echo 'Screen on'
fi
