#!/usr/bin/bash
# Run the actual mobile entry after real PAM/logind authentication, in a VM only.
set -euo pipefail
[[ $EUID == 1000 && -d /sys/bus/virtio/devices && -f /run/session-sha256 ]]
export GSETTINGS_SCHEMA_DIR=/run/gtk-runtime/schemas
export XDG_DATA_DIRS=/run/gtk-runtime:/usr/local/share:/usr/share
export DENIA_RENDER_AUDIT=1
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
[[ -S /run/user/1000/bus ]]
cd "$HOME"
launcher='' foot='' editor=''
readers=()
start_log() {
    local name=$1
    mkfifo "$HOME/$name.pipe"
    # Drain after the cap. RLIMIT_FSIZE would also cap the client's memfd/shm
    # buffers, which is unrelated to log storage and broke the real Foot run.
    LC_ALL=C awk 'BEGIN {remaining=1048576}
        {if (remaining>0) {line=$0 "\n"; piece=substr(line,1,remaining);
          printf "%s",piece; fflush(); remaining-=length(piece)}}' \
        < "$HOME/$name.pipe" > "$HOME/$name.log" &
    readers+=("$!")
}
start_log denial
start_log foot
start_log mousepad
finish() {
    local rc=$?
    trap - EXIT TERM INT
    for pid in "$foot" "$editor" "$launcher"; do
        [[ -z $pid ]] || kill -TERM "$pid" 2>/dev/null || :
    done
    for pid in "$foot" "$editor" "$launcher"; do
        [[ -z $pid ]] || wait "$pid" 2>/dev/null || :
    done
    for pid in "${readers[@]}"; do kill -TERM "$pid" 2>/dev/null || :; wait "$pid" 2>/dev/null || :; done
    if [[ $rc != 0 ]]; then
        echo "FAIL combined user session status=$rc"
        for name in denial foot mousepad; do echo "OBSERVE last $name log"; tail -n 100 "$HOME/$name.log" || :; done
    fi
    exit "$rc"
}
trap finish EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
/usr/bin/denial-mobile-session --check
/usr/bin/denial-mobile-session > "$HOME/denial.pipe" 2>&1 &
launcher=$!
for ((i=0;i<80;i++)); do
    kill -0 "$launcher" || { cat "$HOME/denial.log"; exit 1; }
    if systemctl --user is-active --quiet denial-session.target graphical-session.target; then break; fi
    sleep 0.25
done
target_states=$(systemctl --user is-active denial-session.target graphical-session.target)
[[ $target_states == $'active\nactive' ]]
manager=$(systemctl --user show-environment)
while IFS='=' read -r key value; do
    case $key in WAYLAND_DISPLAY|DENIAL_SOCKET) export "$key=$value";; esac
done <<< "$manager"
[[ ${WAYLAND_DISPLAY:-} == wayland-* && $WAYLAND_DISPLAY != */* && -S $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY ]]
[[ ${DENIAL_SOCKET:-} == "$XDG_RUNTIME_DIR/"* && -S $DENIAL_SOCKET ]]
printf 'OBSERVE activated local Denial wayland=%s socket=%s\n' "$WAYLAND_DISPLAY" "$DENIAL_SOCKET"
: > "$HOME/text.txt"
GDK_BACKEND=wayland WAYLAND_DEBUG=client timeout -k 2 65 mousepad "$HOME/text.txt" > "$HOME/mousepad.pipe" 2>&1 &
editor=$!
WAYLAND_DEBUG=client timeout -k 2 65 foot > "$HOME/foot.pipe" 2>&1 &
foot=$!
for ((i=0;i<160;i++)); do
    kill -0 "$launcher" && kill -0 "$editor" && kill -0 "$foot"
    if grep -q 'xdg_toplevel.*configure' "$HOME/mousepad.log" && grep -q 'xdg_toplevel.*configure' "$HOME/foot.log"; then break; fi
    sleep 0.25
done
grep -q 'xdg_toplevel.*configure' "$HOME/mousepad.log"
grep -q 'xdg_toplevel.*configure' "$HOME/foot.log"
echo 'PASS two native Wayland clients configured through authenticated session'
sleep 3
kill -TERM "$foot" "$editor"
wait "$foot" || [[ $? == 143 ]]; foot=''
wait "$editor" || [[ $? == 143 ]]; editor=''
kill -TERM "$launcher"
wait "$launcher" || [[ $? == 143 ]]; launcher=''
# Require successful enumeration, not a nonzero is-active result that could be an error.
units=$(systemctl --user list-units --all --no-legend --no-pager --plain)
while read -r unit load active rest; do
    case "$unit" in denial-session.target|graphical-session.target) [[ $active == inactive ]];; esac
done <<< "$units"
for pid in "${readers[@]}"; do wait "$pid"; done
readers=()
cat "$HOME/denial.log"
echo 'PASS authenticated Denial launcher and native clients stopped'
