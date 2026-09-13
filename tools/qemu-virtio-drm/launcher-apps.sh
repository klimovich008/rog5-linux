#!/usr/bin/env bash
# VM diagnostic wrappers. Sourcing defines functions; it never launches apps.
launcher_guest_guard() {
    local cmdline
    read -r cmdline < /proc/cmdline
    [[ " $cmdline " == *' rog5.virtual_drm=1 '* ]]
}
launcher_identity() {
    local stat tail
    local -a fields
    [[ $1 =~ ^[1-9][0-9]*$ && -r /proc/$1/stat ]] || return 1
    read -r stat < "/proc/$1/stat" || return 1
    tail=${stat##*) }
    # comm may contain spaces/parentheses; starttime is field 22 (tail field 20).
    read -ra fields <<< "$tail"
    [[ ${fields[0]} != Z ]] || return 1
    printf '%s\n' "${fields[19]}"
}
launcher_apps_prepare() {
    launcher_guest_guard || { echo 'FAIL launcher requires virtual guest marker' >&2; return 1; }
    local state=${1:-/run/launcher-apps} desktops=${2:-/usr/share/applications}
    local wrapper=${3:-/run/launcher-apps.sh} text=${4:-/tmp/rog5-text-probe.txt}
    local file app line section count
    [[ $state == /* && $wrapper == /* && $wrapper != *[[:space:]]* ]] || return 1
    mkdir -m 700 "$state" || return 1
    mkdir -p "$state/data/applications" || return 1
    for app in mousepad foot; do
        file=foot.desktop
        [[ $app != mousepad ]] || file=org.xfce.mousepad.desktop
        section='' count=0
        while IFS= read -r line || [[ -n $line ]]; do
            [[ $line != '['* ]] || section=$line
            if [[ $section == '[Desktop Entry]' && $line == Exec=* ]]; then
                line="Exec=/usr/bin/bash $wrapper launch $app"
                count=$((count+1))
            fi
            printf '%s\n' "$line"
        done < "$desktops/$file" > "$state/data/applications/$file"
        [[ $count == 1 ]] || { echo "FAIL ambiguous desktop Exec: $file" >&2; return 1; }
    done
    : > "$text"
    export XDG_DATA_HOME="$state/data"
    echo 'PASS launcher desktop overrides prepared; apps NOT STARTED'
}
launcher_app_run() (
    set -euo pipefail
    launcher_guest_guard || { echo 'FAIL launcher requires virtual guest marker' >&2; exit 1; }
    local app=$1 state=${2:-/run/launcher-apps} bindir=${3:-/usr/bin}
    local sink=${4:-/dev/stdout} writer=${5:-}
    # Denial intentionally launches desktop commands with null stdio. The
    # guarded CLI supplies the guest console; host fixtures supply a private
    # sink. Only this supervisor changes descriptors, never its caller.
    exec >> "$sink" 2>&1
    launcher_record() {
        if [[ -n $writer ]]; then "$writer" record "$1"; else printf '%s\n' "$1"; fi
    }
    local prefix child='' logger='' status start owner=$BASHPID
    local -a args
    case $app in
        mousepad) prefix=EDITOR_WAYLAND; args=(mousepad /tmp/rog5-text-probe.txt) ;;
        foot) prefix=FOOT_WAYLAND; args=(foot) ;;
        *) echo 'FAIL unsupported launcher app' >&2; exit 1 ;;
    esac
    [[ -d $state/data/applications && -n ${WAYLAND_DISPLAY:-} && -z ${WAYLAND_SOCKET:-} ]] || exit 1
    # One lifetime per app in this bounded observation; never attach to an
    # existing single-instance app or overwrite another supervisor's record.
    mkdir -m 700 "$state/$app" || exit 1
    start=$(launcher_identity "$owner")
    printf '%s %s\n' "$owner" "$start" > "$state/$app/owner"
    launcher_app_finish() {
        trap - EXIT TERM INT
        if [[ -n $child ]]; then
            # GNU timeout owns its own process group and forwards TERM to the
            # app/descendants; --kill-after bounds a client ignoring TERM.
            kill -TERM "$child" 2>/dev/null || true
            wait "$child" 2>/dev/null || true
        fi
        if [[ -n $logger ]]; then
            kill -TERM "$logger" 2>/dev/null || true
            wait "$logger" 2>/dev/null || true
        fi
        printf '%s\n' finished > "$state/$app/finished"
    }
    trap launcher_app_finish EXIT
    trap 'exit 143' TERM
    trap 'exit 130' INT
    mkfifo -m 600 "$state/$app/stderr"
    # Drain after the cap rather than blocking or SIGPIPE-killing the client.
    # The host additionally bounds the aggregate serial log.
    if [[ -n $writer ]]; then
        "$writer" prefix "$prefix" < "$state/$app/stderr" &
    else
    LC_ALL=C awk -v prefix="$prefix" 'BEGIN { remaining=1048576 }
        { if (remaining > 0) { line=prefix " " $0 "\n";
            piece=substr(line,1,remaining); printf "%s",piece; fflush();
            remaining-=length(piece);
            if (remaining == 0) { print "\nFAIL launcher client log limit"; fflush(); }
        } }' < "$state/$app/stderr" &
    fi
    logger=$!
    launcher_record "OBSERVE launcher app=$app owner=$owner start=$start"
    timeout --preserve-status --kill-after=2 95 env GDK_BACKEND=wayland \
        WAYLAND_DEBUG=client "$bindir/${args[0]}" "${args[@]:1}" \
        > "$state/$app/stderr" 2>&1 &
    child=$!
    printf '%s\n' "$child" > "$state/$app/timeout-pid"
    status=0
    wait "$child" || status=$?
    child=''
    local log_status=0
    wait "$logger" || log_status=$?
    [[ $status != 0 ]] || status=$log_status
    logger=''
    printf '%s\n' "$status" > "$state/$app/exit-status"
    launcher_record "OBSERVE launcher app=$app exit=$status"
    exit "$status"
)
launcher_apps_cleanup() {
    local state=${1:-/run/launcher-apps} app pid start current attempt failed=0
    for app in mousepad foot; do
        [[ -f $state/$app/owner && ! -f $state/$app/finished ]] || continue
        read -r pid start < "$state/$app/owner" || continue
        current=$(launcher_identity "$pid") || continue
        [[ $current == "$start" ]] || { echo "FAIL stale launcher owner: $app" >&2; failed=1; continue; }
        kill -TERM "$pid" 2>/dev/null || true
        for ((attempt=0; attempt<35; attempt++)); do
            current=$(launcher_identity "$pid") || break
            [[ $current == "$start" ]] || break
            sleep 0.1
        done
        if current=$(launcher_identity "$pid") && [[ $current == "$start" ]]; then
            echo "FAIL launcher cleanup deadline: $app" >&2
            return 1
        fi
    done
    [[ $failed == 0 ]] || return 1
    echo 'PASS launcher apps cleanup'
}
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    set -euo pipefail
    [[ $# == 2 && $1 == launch ]] || { echo 'usage: launcher-apps.sh launch mousepad|foot' >&2; exit 2; }
    launcher_guest_guard || exit 1
    if [[ -p /run/launcher-evidence/events ]]; then
        [[ -x /run/evidence-writer ]] || exit 1
        launcher_app_run "$2" /run/launcher-apps /usr/bin /run/launcher-evidence/events /run/evidence-writer
    else
        [[ ! -f /run/mobile-launcher || $(cat /run/mobile-launcher) != apps ]] || exit 1
        [[ -c /dev/console ]] || exit 1
        launcher_app_run "$2" /run/launcher-apps /usr/bin /dev/console
    fi
fi
