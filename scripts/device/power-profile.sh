#!/bin/sh
set -eu

profile=${1:-server}
display_profile=${DISPLAY_PROFILE:-/usr/local/bin/rog5-display-profile.sh}

case "$profile" in
    server|battery|balanced|performance|maximum) ;;
    *) echo 'usage: power-profile.sh [server|battery|balanced|performance|maximum]' >&2; exit 2 ;;
esac

for governor in /sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do
    [ -w "$governor" ] || continue
    [ "$(cat "$governor")" = schedutil ] || printf 'schedutil\n' > "$governor"
done

[ -x "$display_profile" ] || { echo "ERROR missing $display_profile" >&2; exit 1; }
"$display_profile" "$profile"

printf 'PASS power_profile=%s cpu_governor=schedutil\n' "$profile"
