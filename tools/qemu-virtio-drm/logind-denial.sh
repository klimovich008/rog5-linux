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
require_fuse_device() {
    local device=${1:-/dev/fuse} helper=${2:-/usr/bin/fusermount3} metadata
    [[ -c $device && -r $device && -w $device ]] || {
        echo 'FAIL accessible FUSE character device required for document portal' >&2; return 1;
    }
    [[ -f $helper && ! -L $helper && -r $helper && -x $helper ]] || {
        echo 'FAIL regular executable FUSE mount helper required' >&2; return 1;
    }
    metadata=$(stat -c '%u %g %a %F' -- "$helper") || return $?
    [[ $metadata == '0 0 4755 regular file' ]] || {
        echo 'FAIL FUSE mount helper must be root:root mode 4755' >&2; return 1;
    }
}
qualify_activated_services() {
    local states mount_record target fstype options extra
    local -a services=(at-spi-dbus-bus.service xdg-document-portal.service
        xdg-desktop-portal-gtk.service xdg-desktop-portal.service)
    timeout -k 1 20 systemctl --user start "${services[@]}" || return $?
    states=$(timeout -k 1 3 systemctl --user is-active "${services[@]}") || return $?
    [[ $states == $'active\nactive\nactive\nactive' ]] || {
        echo 'FAIL activated accessibility/portal services not all active' >&2; return 1;
    }
    mount_record=$(timeout -k 1 3 findmnt --kernel --noheadings --raw \
        --mountpoint "$XDG_RUNTIME_DIR/doc" --output TARGET,FSTYPE,OPTIONS) || return $?
    [[ -n $mount_record && $mount_record != *$'\n'* ]] || return 1
    read -r target fstype options extra <<< "$mount_record"
    [[ $target == "$XDG_RUNTIME_DIR/doc" && -n $options && -z $extra &&
       ( $fstype == fuse || $fstype == fuse.* ) ]] || {
        echo 'FAIL document portal exact FUSE mount not confirmed' >&2; return 1;
    }
    printf 'OBSERVE document portal mount=%s\n' "$mount_record"
    echo 'PASS activated accessibility and portal services with document FUSE mount'
}
publish_cache_environment() {
    local manager key value schema_count=0 data_count=0
    [[ -n ${GSETTINGS_SCHEMA_DIR:-} && -n ${XDG_DATA_DIRS:-} ]] || {
        echo 'FAIL GTK cache environment missing' >&2; return 1;
    }
    [[ -r $GSETTINGS_SCHEMA_DIR/gschemas.compiled && -s $GSETTINGS_SCHEMA_DIR/gschemas.compiled &&
       -r ${XDG_DATA_DIRS%%:*}/mime/mime.cache && -s ${XDG_DATA_DIRS%%:*}/mime/mime.cache ]] || {
        echo 'FAIL GTK schema or MIME cache unavailable' >&2; return 1;
    }
    # Direct clients inherit these exports, but activated services use the
    # already-running user manager/bus. Transfer only the two prepared paths.
    timeout -k 1 3 dbus-update-activation-environment --systemd \
        GSETTINGS_SCHEMA_DIR XDG_DATA_DIRS || return $?
    manager=$(timeout -k 1 3 systemctl --user show-environment) || return $?
    while IFS='=' read -r key value; do
        case $key in
            GSETTINGS_SCHEMA_DIR)
                [[ $value == "$GSETTINGS_SCHEMA_DIR" ]] || return 1
                schema_count=$((schema_count + 1));;
            XDG_DATA_DIRS)
                [[ $value == "$XDG_DATA_DIRS" ]] || return 1
                data_count=$((data_count + 1));;
        esac
    done <<< "$manager"
    [[ $schema_count == 1 && $data_count == 1 ]] || {
        echo 'FAIL activated GTK cache environment not confirmed' >&2; return 1;
    }
    echo 'PASS GTK cache environment transferred and verified in user manager'
}
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
reap_owned() {
    local name=$1 phase=$2 sent=$3 pid status=0
    local -n owned=$name
    pid=$owned
    wait "$pid" || status=$?
    owned=''
    printf 'OBSERVE process=%s phase=%s pid=%s status=%s term_sent=%s\n' \
        "$name" "$phase" "$pid" "$status" "$sent"
    last_status=$status
}
require_running() {
    local name=$1
    local -n owned=$name
    if kill -0 "$owned" 2>/dev/null; then return 0; fi
    reap_owned "$name" readiness no
    # Even an early exit 0 is failure: the client must survive until our stop.
    return 1
}
stop_owned_group() {
    local phase=$1 name failed=0
    shift
    local -A term_sent=()
    # Signal every child before waiting: one slow exit must not keep the other
    # clients or compositor running until the outer session deadline.
    for name in "$@"; do
        local -n owned=$name
        [[ -n $owned ]] || continue
        term_sent[$name]=no
        if kill -TERM "$owned" 2>/dev/null; then term_sent[$name]=yes; fi
    done
    for name in "$@"; do
        [[ -v term_sent[$name] ]] || continue
        # Always wait, including ESRCH and expired timeout(1) clients, retaining
        # the original child status instead of letting set -e skip the rest.
        reap_owned "$name" "$phase" "${term_sent[$name]}"
        [[ ${term_sent[$name]} == yes && ( $last_status == 0 || $last_status == 143 ) ]] || failed=1
    done
    return "$failed"
}
stop_all_owned() {
    local phase=$1 failed=0
    if [[ $phase == stop ]]; then
        # Preserve normal teardown order: clients close before the compositor.
        stop_owned_group "$phase" foot editor || failed=1
        stop_owned_group "$phase" launcher || failed=1
    else
        stop_owned_group "$phase" foot editor launcher || failed=1
    fi
    return "$failed"
}
finish() {
    local rc=$?
    trap - EXIT TERM INT
    stop_all_owned cleanup || { [[ $rc != 0 ]] || rc=1; }
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
require_fuse_device
publish_cache_environment
/usr/bin/denial-mobile-session --check
/usr/bin/denial-mobile-session > "$HOME/denial.pipe" 2>&1 &
launcher=$!
for ((i=0;i<80;i++)); do
    require_running launcher || { cat "$HOME/denial.log"; exit 1; }
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
qualify_activated_services
: > "$HOME/text.txt"
GDK_BACKEND=wayland WAYLAND_DEBUG=client timeout -k 2 65 mousepad "$HOME/text.txt" > "$HOME/mousepad.pipe" 2>&1 &
editor=$!
WAYLAND_DEBUG=client timeout -k 2 65 foot > "$HOME/foot.pipe" 2>&1 &
foot=$!
for ((i=0;i<160;i++)); do
    for name in launcher editor foot; do require_running "$name" || exit 1; done
    if grep -q 'xdg_toplevel.*configure' "$HOME/mousepad.log" && grep -q 'xdg_toplevel.*configure' "$HOME/foot.log"; then break; fi
    sleep 0.25
done
grep -q 'xdg_toplevel.*configure' "$HOME/mousepad.log"
grep -q 'xdg_toplevel.*configure' "$HOME/foot.log"
echo 'PASS two native Wayland clients configured through authenticated session'
sleep 3
stop_all_owned stop
# Require successful enumeration, not a nonzero is-active result that could be an error.
units=$(systemctl --user list-units --all --no-legend --no-pager --plain)
while read -r unit load active rest; do
    case "$unit" in denial-session.target|graphical-session.target) [[ $active == inactive ]];; esac
done <<< "$units"
for pid in "${readers[@]}"; do wait "$pid"; done
readers=()
cat "$HOME/denial.log"
echo 'PASS authenticated Denial launcher and native clients stopped'
