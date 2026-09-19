#!/usr/bin/bash
# Run the actual mobile entry after real PAM/logind authentication, in a VM only.
set -euo pipefail
[[ $EUID == 1000 && -d /sys/bus/virtio/devices && -f /run/session-sha256 ]]
export GSETTINGS_SCHEMA_DIR=/run/gtk-runtime/schemas
export XDG_DATA_DIRS=/run/gtk-runtime:/usr/local/share:/usr/share
export GTK_IM_MODULE_FILE=/run/gtk-runtime/immodules.cache
export DENIA_RENDER_AUDIT=1
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
[[ -S /run/user/1000/bus ]]
cd "$HOME"
launcher='' foot='' editor=''
foot_close_owned=0
foot_close_fifo=$HOME/foot-close.pipe
readers=()
if [[ -f /run/editor-probe ]]; then source /run/logind-editor.sh; fi
if [[ -f /run/apps-probe ]]; then
    [[ ! -f /run/editor-probe ]]
    source /run/launcher-apps.sh
    source /run/launcher-evidence.sh
    source /run/logind-apps.sh
fi
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
service_clock() {
    local phase=$1 value status=0
    value=$(LC_ALL=C timeout -k 1 2 lsclocks --time CLOCK_MONOTONIC --no-discover-dynamic) || status=$?
    if ((status != 0)); then
        printf 'OBSERVE service-clock phase=%s status=%s\n' "$phase" "$status" >&2
        return "$status"
    fi
    [[ $value =~ ^[0-9]+\.[0-9]{9}$ ]] || {
        echo 'FAIL invalid monotonic clock observation' >&2; return 1;
    }
    printf 'OBSERVE service-clock phase=%s clock=CLOCK_MONOTONIC seconds=%s\n' "$phase" "$value" >&2
}
service_snapshot() {
    local status=0
    echo 'OBSERVE service-snapshot phase=begin deadline_seconds=3' >&2
    # Query only lifecycle properties of the requested units and their known
    # permission-store dependency. Preserve the start command status regardless
    # of diagnostic failure. Line-buffer stdout so timeout cannot discard
    # completed unit replies still held in systemctl's stdio buffer. Keep stderr
    # unbuffered (even incomplete error lines must survive). Flush the
    # bounded relay too. No environment, command lines or secrets are read.
    (set -o pipefail
        timeout -k 1 3 stdbuf -oL -e0 systemctl --user show "$@" xdg-permission-store.service \
            --property=Id --property=ActiveState --property=SubState --property=Result \
            --property=BusName --property=MainPID --property=Job \
            --property=ExecMainStartTimestampMonotonic --property=ActiveEnterTimestampMonotonic \
            --property=StateChangeTimestampMonotonic --property=CPUUsageNSec 2>&1 |
        LC_ALL=C awk 'BEGIN {remaining=65536}
            {line=$0 "\n"; if (length(line)>remaining) {overflow=1; next}
             if (!overflow) {printf "%s",line; remaining-=length(line); fflush()}}
            END {if (overflow) exit 42}'
    ) >&2 || status=$?
    printf 'OBSERVE service-snapshot phase=end status=%s\n' "$status" >&2
}
qualify_activated_services() {
    local states mount_record target fstype options extra started rc clock_rc
    local -a services=(at-spi-dbus-bus.service xdg-document-portal.service
        xdg-desktop-portal-gtk.service xdg-desktop-portal.service)
    service_clock before-start || return $?
    # Exact-clock VM evidence placed successful completion at19.70s and
    # readiness only0.44s before the former20s lower cutoff. Allow5s fixture
    # scheduling headroom; all user/PAM/service/VM outer limits stay unchanged.
    started=$SECONDS; rc=0
    echo 'OBSERVE stage=service-start phase=begin deadline_seconds=25' >&2
    timeout -k 1 25 systemctl --user start "${services[@]}" || rc=$?
    printf 'OBSERVE stage=service-start phase=end status=%s elapsed_seconds=%s\n' "$rc" "$((SECONDS-started))" >&2
    # These samples bracket the external timeout invocation. The first sample
    # plus25s is a lower bound on the actual timeout cutoff, not its exact arm
    # timestamp; include process/observer latency in any near-boundary inference.
    clock_rc=0; service_clock after-start || clock_rc=$?
    service_snapshot "${services[@]}"
    ((rc == 0)) || return "$rc"
    ((clock_rc == 0)) || return "$clock_rc"
    started=$SECONDS; rc=0
    echo 'OBSERVE stage=service-state phase=begin deadline_seconds=3' >&2
    states=$(timeout -k 1 3 systemctl --user is-active "${services[@]}") || rc=$?
    printf 'OBSERVE stage=service-state phase=end status=%s elapsed_seconds=%s\n' "$rc" "$((SECONDS-started))" >&2
    ((rc == 0)) || return "$rc"
    [[ $states == $'active\nactive\nactive\nactive' ]] || {
        echo 'FAIL activated accessibility/portal services not all active' >&2; return 1;
    }
    started=$SECONDS; rc=0
    echo 'OBSERVE stage=document-mount phase=begin deadline_seconds=3' >&2
    mount_record=$(timeout -k 1 3 findmnt --kernel --noheadings --raw \
        --mountpoint "$XDG_RUNTIME_DIR/doc" --output TARGET,FSTYPE,OPTIONS) || rc=$?
    printf 'OBSERVE stage=document-mount phase=end status=%s elapsed_seconds=%s\n' "$rc" "$((SECONDS-started))" >&2
    ((rc == 0)) || return "$rc"
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
    local manager key value schema_count=0 data_count=0 im_count=0
    [[ -n ${GSETTINGS_SCHEMA_DIR:-} && -n ${XDG_DATA_DIRS:-} && -n ${GTK_IM_MODULE_FILE:-} ]] || {
        echo 'FAIL GTK cache environment missing' >&2; return 1;
    }
    [[ -r $GSETTINGS_SCHEMA_DIR/gschemas.compiled && -s $GSETTINGS_SCHEMA_DIR/gschemas.compiled &&
       -r ${XDG_DATA_DIRS%%:*}/mime/mime.cache && -s ${XDG_DATA_DIRS%%:*}/mime/mime.cache &&
       -r $GTK_IM_MODULE_FILE && -s $GTK_IM_MODULE_FILE ]] || {
        echo 'FAIL GTK schema, MIME or input-method cache unavailable' >&2; return 1;
    }
    # Direct clients inherit these exports, but activated services use the
    # already-running user manager/bus. Transfer only the three prepared paths.
    timeout -k 1 3 dbus-update-activation-environment --systemd \
        GSETTINGS_SCHEMA_DIR XDG_DATA_DIRS GTK_IM_MODULE_FILE || return $?
    manager=$(timeout -k 1 3 systemctl --user show-environment) || return $?
    while IFS='=' read -r key value; do
        case $key in
            GSETTINGS_SCHEMA_DIR)
                [[ $value == "$GSETTINGS_SCHEMA_DIR" ]] || return 1
                schema_count=$((schema_count + 1));;
            XDG_DATA_DIRS)
                [[ $value == "$XDG_DATA_DIRS" ]] || return 1
                data_count=$((data_count + 1));;
            GTK_IM_MODULE_FILE)
                [[ $value == "$GTK_IM_MODULE_FILE" ]] || return 1
                im_count=$((im_count + 1));;
        esac
    done <<< "$manager"
    [[ $schema_count == 1 && $data_count == 1 && $im_count == 1 ]] || {
        echo 'FAIL activated GTK cache environment not confirmed' >&2; return 1;
    }
    echo 'PASS GTK cache environment transferred and verified in user manager'
}
start_log() {
    local name=$1
    mkfifo "$HOME/$name.pipe"
    if [[ -f /run/apps-probe && ( $name == mousepad || $name == foot ) ]]; then
        # Authenticated launcher preparation owns the attributed prefix readers.
        : > "$HOME/$name.log"
        return 0
    fi
    if [[ $name == mousepad && -f /run/editor-probe ]]; then
        drain_editor_protocol < "$HOME/$name.pipe" > "$HOME/$name.log" &
        readers+=("$!")
        return 0
    fi
    if [[ $name == denial ]]; then
        # Keep the bounded ordinary prefix, but continue collecting terminal
        # counters and errors across the entire stream. Verbose frame tracing
        # must not hide the qualification result. A separate 64 KiB diagnostic
        # reserve is fail-closed on overflow; keep draining to release writers.
        LC_ALL=C awk 'BEGIN {head=1048576; reserve=65536}
            {
                line=$0 "\n"
                if (head >= length(line)) {
                    printf "%s",line; head-=length(line); fflush(); next
                }
                if (!capped) {print "OBSERVE Denial ordinary log capped; retaining terminal/error records"; capped=1}
                head=0
                plain=$0
                gsub(/\033\[[0-?]*[ -/]*[@-~]/,"",plain)
                lower=tolower(plain)
                if (lower ~ /independently clocked flutter kms session complete|error|fail|exception|could not/) {
                    if (reserve >= length(line)) {printf "%s",line; reserve-=length(line); fflush()}
                    else overflow=1
                }
            }
            END {if (overflow) {print "FAIL Denial diagnostic log overflow"; exit 42}}
        ' < "$HOME/$name.pipe" > "$HOME/$name.log" &
        readers+=("$!")
        return 0
    fi
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
prepare_foot_close() {
    [[ ! -e $foot_close_fifo && ! -L $foot_close_fifo ]] || return 1
    mkfifo -m 600 -- "$foot_close_fifo" || return $?
    foot_close_owned=1
    [[ -p $foot_close_fifo && -O $foot_close_fifo && $(stat -c %a -- "$foot_close_fifo") == 600 ]]
}
remove_foot_close() {
    if ((${foot_close_owned:-0})); then
        [[ -p $foot_close_fifo && ! -L $foot_close_fifo && -O $foot_close_fifo ]] || return 1
        rm -- "$foot_close_fifo" || return $?
        foot_close_owned=0
    fi
}
launch_foot() {
    WAYLAND_DEBUG=client timeout -k 2 65 foot /usr/bin/bash --noprofile --norc -c '
        printf "ROG5 controlled terminal: waiting for normal close\n"
        IFS= read -r token < "$1" || exit 1
        [[ $token == ROG5_FOOT_EXIT_0 ]] || exit 1
        printf "PASS controlled terminal child exit requested\n"
        exit 0
    ' rog5-terminal-child "$foot_close_fifo" > "$HOME/foot.pipe" 2>&1 &
    foot=$!
}
close_foot_normally() {
    local deadline
    require_running foot || return 1
    [[ ${foot_close_owned:-0} == 1 && -p $foot_close_fifo && ! -L $foot_close_fifo ]] || return 1
    # Opening a FIFO with no reader blocks too: bound the writer independently.
    timeout -k 1 3 /usr/bin/bash --noprofile --norc -c 'printf "%s\n" ROG5_FOOT_EXIT_0 > "$1"' \
        rog5-terminal-close "$foot_close_fifo" || return $?
    deadline=$((SECONDS + 5))
    while kill -0 "$foot" 2>/dev/null; do
        ((SECONDS < deadline)) || {
            echo 'FAIL controlled Foot exit deadline' >&2; return 124;
        }
        sleep 0.1
    done
    reap_owned foot normal-close no
    [[ $last_status == 0 ]] || return "$last_status"
    remove_foot_close || return $?
    echo 'PASS Foot exited normally and owned close FIFO removed'
}
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
    if [[ -f /run/apps-probe ]]; then cleanup_authenticated_apps "$rc" || { [[ $rc != 0 ]] || rc=1; }; fi
    stop_all_owned cleanup || { [[ $rc != 0 ]] || rc=1; }
    remove_foot_close || { [[ $rc != 0 ]] || rc=1; }
    for pid in "${readers[@]}"; do kill -TERM "$pid" 2>/dev/null || :; wait "$pid" 2>/dev/null || :; done
    if [[ -f /run/apps-probe ]]; then finish_authenticated_apps || { [[ $rc != 0 ]] || rc=1; }; fi
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
if [[ -f /run/apps-probe ]]; then
    if [[ -f /run/bottom-caret-probe ]]; then
        prepare_authenticated_apps "$HOME/launcher-apps" /usr/share/applications \
            /run/logind-apps.sh /tmp/rog5-text-probe.txt /run/evidence-writer \
            /dev/vport0p1 /run/apps-observe-token bottom-caret
    else
        prepare_authenticated_apps
    fi
fi
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
if [[ -f /run/apps-probe ]]; then
    run_authenticated_apps
    logind_apps_phase=flow-complete
    stop_all_owned stop
elif [[ -f /run/editor-probe ]]; then
    run_authenticated_editor
    stop_all_owned stop
else
: > "$HOME/text.txt"
GDK_BACKEND=wayland WAYLAND_DEBUG=client timeout -k 2 65 mousepad "$HOME/text.txt" > "$HOME/mousepad.pipe" 2>&1 &
editor=$!
prepare_foot_close
launch_foot
for ((i=0;i<160;i++)); do
    for name in launcher editor foot; do require_running "$name" || exit 1; done
    if grep -q 'xdg_toplevel.*configure' "$HOME/mousepad.log" && grep -q 'xdg_toplevel.*configure' "$HOME/foot.log"; then break; fi
    sleep 0.25
done
grep -q 'xdg_toplevel.*configure' "$HOME/mousepad.log"
grep -q 'xdg_toplevel.*configure' "$HOME/foot.log"
echo 'PASS two native Wayland clients configured through authenticated session'
sleep 3
close_foot_normally
stop_all_owned stop
# Require successful enumeration, not a nonzero is-active result that could be an error.
fi
units=$(systemctl --user list-units --all --no-legend --no-pager --plain)
while read -r unit load active rest; do
    case "$unit" in denial-session.target|graphical-session.target) [[ $active == inactive ]];; esac
done <<< "$units"
for pid in "${readers[@]}"; do wait "$pid"; done
readers=()
if [[ -f /run/apps-probe ]]; then finish_authenticated_apps; fi
cat "$HOME/denial.log"
echo 'PASS authenticated Denial launcher and native clients stopped'
