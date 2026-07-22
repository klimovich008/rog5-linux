#!/bin/sh
set -eu

die() { printf 'ERROR %s\n' "$*" >&2; exit 1; }

kwin_pid=$(pgrep -o kwin_wayland 2>/dev/null || true)
[ -n "$kwin_pid" ] || die 'kwin_wayland is not running'

session_uid=$(stat -c %u "/proc/$kwin_pid")
session_user=$(getent passwd "$session_uid" | cut -d: -f1)
runtime=$(tr '\0' '\n' < "/proc/$kwin_pid/environ" | sed -n 's/^XDG_RUNTIME_DIR=//p')
wayland=$(tr '\0' '\n' < "/proc/$kwin_pid/environ" | sed -n 's/^WAYLAND_DISPLAY=//p')
bus=$(tr '\0' '\n' < "/proc/$kwin_pid/environ" | sed -n 's/^DBUS_SESSION_BUS_ADDRESS=//p')

[ -n "$session_user" ] || die 'could not resolve compositor user'
[ -n "$runtime" ] || die 'compositor has no XDG_RUNTIME_DIR'
[ -n "$bus" ] || die 'compositor has no D-Bus session address'
wayland=${wayland:-wayland-0}

for value in "$session_user" "$runtime" "$wayland" "$bus"; do
    case "$value" in *"'"*) die 'unsafe quote in compositor environment' ;; esac
done

run_kscreen() {
    command="DISPLAY= QT_QPA_PLATFORM=wayland WAYLAND_DISPLAY='$wayland' XDG_RUNTIME_DIR='$runtime' DBUS_SESSION_BUS_ADDRESS='$bus' kscreen-doctor $*"
    su -s /bin/sh -c "$command" "$session_user"
}

set_refresh() {
    target_hz=$1
    panel_modes=/sys/class/drm/card0-DSI-1/modes
    [ -r "$panel_modes" ] || die 'DSI mode list is unavailable'

    ordinal=$(awk -v token="x${target_hz}x" 'index($0, token) { print NR; exit }' "$panel_modes")
    [ -n "$ordinal" ] || die "panel has no fixed ${target_hz} Hz mode"

    configuration=$(run_kscreen -j)
    mode_id=$(printf '%s\n' "$configuration" | python3 -c '
import json, sys
ordinal = int(sys.argv[1])
data = json.load(sys.stdin)
outputs = [item for item in data["outputs"] if item.get("name") == "DSI-1" and item.get("connected")]
if len(outputs) != 1:
    raise SystemExit("expected one connected DSI-1 output")
modes = outputs[0]["modes"]
if len(modes) != 4 or not all(mode["size"] == {"width": 1080, "height": 2448} for mode in modes):
    raise SystemExit("KScreen mode list does not match the four-mode panel contract")
print(modes[ordinal - 1]["id"])
' "$ordinal")

    run_kscreen "output.DSI-1.mode.$mode_id"
    current=$(run_kscreen -j | python3 -c '
import json, sys
data = json.load(sys.stdin)
print(next(item["currentModeId"] for item in data["outputs"] if item.get("name") == "DSI-1"))
')
    [ "$current" = "$mode_id" ] || die "mode verification failed: expected $mode_id, got $current"
    printf 'PASS fixed_refresh_hz=%s kscreen_mode_id=%s\n' "$target_hz" "$mode_id"
}

case "${1:-query}" in
    query) run_kscreen -o ;;
    json) run_kscreen -j ;;
    dpms-show) run_kscreen --dpms show ;;
    dpms-on) run_kscreen --dpms on ;;
    dpms-off) run_kscreen --dpms off ;;
    server) set_refresh 60; run_kscreen --dpms off ;;
    battery) set_refresh 60 ;;
    balanced) set_refresh 90 ;;
    performance) set_refresh 120 ;;
    maximum) set_refresh 144 ;;
    *) die 'usage: display-profile.sh [query|json|dpms-show|dpms-on|dpms-off|server|battery|balanced|performance|maximum]' ;;
esac
