#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/screen-toggle.sh}
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/backlight" "$stage/run"
printf '1000\n' > "$stage/backlight/max_brightness"
printf '500\n' > "$stage/backlight/brightness"
cat > "$stage/display-profile" <<EOF
#!/bin/sh
printf '%s\n' "\$1" >> "$stage/display.log"
EOF
chmod +x "$stage/display-profile"
cat > "$stage/status-screen" <<EOF
#!/bin/sh
printf '%s\n' "\$1" >> "$stage/status.log"
EOF
chmod +x "$stage/status-screen"

run_toggle() {
    STATE_FILE=$stage/run/state \
        BRIGHTNESS_FILE=$stage/run/brightness \
        BACKLIGHT_DIR=$stage/backlight \
        DISPLAY_PROFILE=$stage/display-profile \
        STATUS_SCREEN=$stage/status-screen \
        "$target" "$1" >/dev/null 2>&1
}

run_toggle off
grep -qx 0 "$stage/backlight/brightness"
grep -qx 500 "$stage/run/brightness"
grep -qx off "$stage/run/state"
run_toggle off
run_toggle on
grep -qx 500 "$stage/backlight/brightness"
grep -qx on "$stage/run/state"
printf '200\n' > "$stage/backlight/brightness"
run_toggle toggle
grep -qx 0 "$stage/backlight/brightness"
run_toggle toggle
grep -qx 200 "$stage/backlight/brightness"
test "$(grep -c '^dpms-off$' "$stage/display.log")" -eq 3
test "$(grep -c '^dpms-on$' "$stage/display.log")" -eq 2
test "$(grep -c '^render$' "$stage/status.log")" -eq 2

set +e
run_toggle invalid
status=$?
set -e
[ "$status" -eq 2 ]

echo 'PASS idempotent screen off/on/toggle test'
