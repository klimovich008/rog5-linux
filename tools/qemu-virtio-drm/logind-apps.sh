#!/usr/bin/bash
# Authenticated VM launcher supervision. Sourcing launches nothing.
logind_apps_record() {
    local state=$1
    shift
    [[ -p $state/evidence/events && ! -L $state/evidence/events ]] || return 1
    timeout -k 1 2 "$logind_apps_writer" record "$*" > "$state/evidence/events"
}
logind_apps_snapshot() {
    local state=$1 log=$2
    [[ -f $log && ! -L $log && -p $state/evidence/events &&
       ! -L $state/evidence/events ]] || return 1
    # Diagnostics are data, never client protocol or completion evidence.
    # Bound the entire pipeline, including a FIFO with no remaining reader.
    timeout -k 1 3 /usr/bin/bash --noprofile --norc -c '
        set -o pipefail
        {
            # Retain early icon and picture stages after noisy frame diagnostics.
            # Framed stage budget leaves room for a small recent tail.
            LC_ALL=C head -c 1048576 -- "$1" |
            LC_ALL=C awk '\''BEGIN {remaining=24576}
                index($0,"ROG5_ICON_STAGE ") || index($0,"ROG5_PICTURE ") {
                    line=substr($0,1,1000); cost=length(line)+19
                    if (cost<=remaining) {print line; remaining-=cost}}
            '\'' || exit $?
            # Existing native audit fields are often older than the recent tail.
            # Keep four latest authorizations and two latest presentation audits,
            # compacted as diagnostic data; no new renderer logging or GL calls.
            LC_ALL=C head -c 1048576 -- "$1" |
            LC_ALL=C awk '\''
                function compact(kind,   result,i,key,value,truncated) {
                    result="RENDER_HANDOFF kind=" kind " time=" substr($1,1,40)
                    truncated=0
                    for(i=1;i<=NF;i++) {
                        key=$i; sub(/=.*/,"",key)
                        if(key ~ /^(sequence|event|view|work_id|serial|age_us|interval_ms|presented_outputs|empty_transactions|frame_damage_empty|buffer_damage_empty|last_frame_damage|last_buffer_damage)$/) {
                            value=substr($i,length(key)+2)
                            if(length(value)>96) {value=substr(value,1,96); truncated=1}
                            result=result " " key "=" value
                        }
                    }
                    return result " value_truncated=" truncated
                }
                {gsub(/\033\[[0-9;]*m/,"")}
                index($0,"bounded render authorization trace") {
                    auth[na%4]=compact("authorization"); na++
                }
                index($0,"Flutter per-output render audit") {
                    present[np%2]=compact("presentation"); np++
                }
                END {
                    remaining=1792
                    for(i=(na>4 ? na-4 : 0);i<na;i++) {
                        line=auth[i%4]; cost=length(line)+19
                        if(cost<=remaining) {print line; remaining-=cost}
                    }
                    for(i=(np>2 ? np-2 : 0);i<np;i++) {
                        line=present[i%2]; cost=length(line)+19
                        if(cost<=remaining) {print line; remaining-=cost}
                    }
                }
            '\'' || exit $?
            LC_ALL=C tail -c 4096 -- "$1"
        } |
        LC_ALL=C awk '\''BEGIN {remaining=30720}
            {line=substr($0,1,2000); cost=length(line)+19
             if (cost<=remaining) {print line; remaining-=cost}}'\'' |
        "$3" prefix DENIAL_DIAGNOSTIC > "$2/evidence/events"
    ' diagnostic-snapshot "$log" "$state" "$logind_apps_writer"
}
prepare_authenticated_apps() {
    local state=${1:-$HOME/launcher-apps} desktops=${2:-/usr/share/applications}
    local wrapper=${3:-/run/logind-apps.sh} text=${4:-/tmp/rog5-text-probe.txt}
    local writer=${5:-/run/evidence-writer} sink=${6:-/dev/vport0p1}
    local token_file=${7:-/run/apps-observe-token} profile=${8:-normal}
    local app prefix manager count=0 value line
    launcher_guest_guard || return $?
    [[ -z ${logind_apps_port:-} ]] || return 1
    [[ -x $writer && ( -c $sink || -p $sink ) && -f $token_file &&
       ! -L $token_file && ! -e $text && ! -L $text ]] || return 1
    read -r logind_apps_token < "$token_file" || return $?
    [[ $logind_apps_token =~ ^ROG5_APPS_DONE_[0-9a-f]{32}$ ]] || return 1
    [[ $profile == normal || $profile == bottom-caret ]] || return 1
    launcher_apps_prepare "$state" "$desktops" "$wrapper" "$text" || return $?
    if [[ $profile == bottom-caret ]]; then
        # A long RAM-only document permits a real pointer-selected low caret.
        # No CLI cursor positioning or host keyboard injection is used.
        for ((line=1;line<=64;line++)); do printf 'line-%02d\n' "$line"; done > "$text"
    fi
    logind_apps_state=$state; logind_apps_writer=$writer; logind_apps_sink=$sink
    # Share the current, tested lifecycle functions verbatim. Never source the
    # main session script: its top-level code starts services and log readers.
    (umask 077
        declare -f prepare_foot_close launch_foot close_foot_normally remove_foot_close \
            reap_owned require_running stop_owned_group > "$state/lifecycle.sh"
    ) || return $?
    [[ -s $state/lifecycle.sh && $(stat -c '%u %a' "$state/lifecycle.sh") == "$EUID 600" ]] || return 1
    printf '%s\n' "$text" > "$state/text-path"
    printf '%s\n' "$writer" > "$state/writer-path"
    # One O_RDWR open owns this duplex virtio-console port. The evidence cat
    # duplicates it for writes; this controller alone reads acknowledgements.
    exec {logind_apps_port}<> "$sink" || return $?
    launcher_evidence_prepare "$state/evidence" "$sink" "$writer" "$logind_apps_port" || return $?
    logind_apps_evidence_owned=1
    for app in mousepad foot; do
        [[ -p $HOME/$app.pipe && ! -L $HOME/$app.pipe ]] || return 1
        prefix=EDITOR_WAYLAND; [[ $app != foot ]] || prefix=FOOT_WAYLAND
        "$writer" prefix "$prefix" < "$HOME/$app.pipe" > "$state/evidence/events" &
        readers+=("$!")
    done
    # Desktop discovery occurs in the systemd-launched mobile compositor.
    timeout -k 1 3 dbus-update-activation-environment --systemd XDG_DATA_HOME || return $?
    manager=$(timeout -k 1 3 systemctl --user show-environment) || return $?
    while IFS= read -r value; do
        if [[ $value == XDG_DATA_HOME=* ]]; then
            ((count+=1)); [[ $value == "XDG_DATA_HOME=$state/data" ]] || return 1
        fi
    done <<< "$manager"
    [[ $count == 1 ]] || return 1
    echo 'PASS authenticated launcher overrides prepared; apps NOT STARTED'
}
logind_apps_owner() {
    local state=$1 app=$2 pid start extra actual
    [[ $app == mousepad || $app == foot ]] || return 1
    [[ -f $state/$app/owner && ! -L $state/$app/owner && ! -e $state/$app/finished ]] || return 1
    read -r pid start extra < "$state/$app/owner" || return 1
    [[ $pid =~ ^[1-9][0-9]*$ && $start =~ ^[1-9][0-9]*$ && -z $extra ]] || return 1
    actual=$(launcher_identity "$pid") || return 1
    [[ $actual == "$start" ]] || return 1
    printf '%s\n' "$pid"
}
logind_apps_close_clock() {
    local state=$1 app=$2 phase=$3 pid=$4 uptime idle
    # /proc/uptime uses the boot clock (including suspend), at 10 ms precision.
    # These samples bracket close/reap plus evidence transport, not signal time.
    read -r uptime idle < /proc/uptime || return $?
    [[ $uptime =~ ^[0-9]+\.[0-9]+$ ]] || return 1
    logind_apps_record "$state" "DENIAL_DIAGNOSTIC app-close app=$app phase=$phase pid=$pid clock=CLOCK_BOOTTIME seconds=$uptime"
}
logind_apps_supervise() (
    set -euo pipefail
    local app=$1 state=${2:-$HOME/launcher-apps} bindir=${3:-/usr/bin}
    local owner=$BASHPID start text command_fd command='' chunk rc=0 controlled=0 child_name
    local close_phase=running last_status=unknown close_pid
    local foot='' editor='' foot_close_owned=0 foot_close_fifo=$HOME/foot-close.pipe
    launcher_guest_guard || exit 1
    [[ $app == mousepad || $app == foot ]] || exit 1
    [[ -d $state/data/applications && -n ${WAYLAND_DISPLAY:-} && -z ${WAYLAND_SOCKET:-} &&
       -f $state/lifecycle.sh && ! -L $state/lifecycle.sh &&
       $(stat -c '%u %a' "$state/lifecycle.sh") == "$EUID 600" ]] || exit 1
    source "$state/lifecycle.sh"
    read -r text < "$state/text-path"
    read -r logind_apps_writer < "$state/writer-path"
    [[ $text == /* && -f $text && ! -L $text && -x $logind_apps_writer ]] || exit 1
    mkdir -m 700 "$state/$app" || exit 1
    start=$(launcher_identity "$owner") || exit 1
    printf '%s %s\n' "$owner" "$start" > "$state/$app/owner.tmp"
    mv -- "$state/$app/owner.tmp" "$state/$app/owner"
    mkfifo -m 600 "$state/$app/command"
    exec {command_fd}<> "$state/$app/command"
    logind_app_finish() {
        local original=$?
        trap - EXIT TERM INT
        if [[ $close_phase != normal-close-recorded ]]; then
            logind_apps_record "$state" "OBSERVE launcher-lifecycle app=$app phase=$close_phase status=$original child_status=$last_status" || {
                [[ $original != 0 ]] || original=1;
            }
        fi
        stop_owned_group cleanup foot editor || { [[ $original != 0 ]] || original=1; }
        remove_foot_close || { [[ $original != 0 ]] || original=1; }
        exec {command_fd}>&-
        printf '%s\n' "$original" > "$state/$app/exit-status.tmp"
        mv -- "$state/$app/exit-status.tmp" "$state/$app/exit-status"
        logind_apps_record "$state" "OBSERVE launcher app=$app exit=$original" || {
            [[ $original != 0 ]] || original=1;
        }
        printf '%s\n' "$original" > "$state/$app/finished.tmp"
        mv -- "$state/$app/finished.tmp" "$state/$app/finished"
        exit "$original"
    }
    trap logind_app_finish EXIT
    trap 'close_phase=signal-TERM; exit 143' TERM
    trap 'close_phase=signal-INT; exit 130' INT
    logind_apps_record "$state" "OBSERVE launcher app=$app owner=$owner start=$start"
    if [[ $app == foot ]]; then
        child_name=foot
        prepare_foot_close
        launch_foot
    else
        child_name=editor
        # timeout must never write its signal diagnostic into a blocked client
        # FIFO before sending the signal. Only its fixed diagnostics use this
        # regular file; the exec preserves the monitored client's PID.
        GDK_BACKEND=wayland WAYLAND_DEBUG=client timeout --verbose -k 2 65 \
            /usr/bin/bash --noprofile --norc -c 'exec "$1" "$2" > "$3" 2>&1' \
            mousepad "$bindir/mousepad" "$text" "$HOME/mousepad.pipe" \
            > "$state/$app/timeout.log" 2>&1 &
        editor=$!
    fi
    while :; do
        # Even early exit0 is failure: only the controller may request close.
        require_running "$child_name" || {
            [[ $last_status == 0 ]] || exit "$last_status"
            exit 1
        }
        chunk=''; rc=0
        IFS= read -r -t .2 -u "$command_fd" chunk || rc=$?
        command+=$chunk
        ((${#command}<=32)) || exit 1
        if ((rc==0)); then
            [[ $command == ROG5_APP_CLOSE_0 ]] || exit 1
            controlled=1; break
        fi
        ((rc>128)) || exit 1
    done
    close_phase=normal-close; rc=0; last_status=unknown
    close_pid=${!child_name}
    logind_apps_close_clock "$state" "$app" begin "$close_pid"
    if [[ $app == foot ]]; then
        close_foot_normally || rc=$?
    elif require_running editor; then
        stop_owned_group normal-close editor || rc=$?
        [[ $last_status == 0 ]] || rc=$last_status
    else
        rc=1; [[ $last_status == 0 ]] || rc=$last_status
    fi
    logind_apps_close_clock "$state" "$app" close-returned "$close_pid" || {
        ((rc!=0)) || rc=1;
    }
    if [[ $app == mousepad ]]; then
        # At most 2 KiB before prefix framing, leaving room for close clocks
        # inside the shared 64 KiB diagnostic limit. The client cannot write
        # here after exec; timeout output never controls qualification.
        timeout -k 1 3 /usr/bin/bash --noprofile --norc -c '
            set -o pipefail
            head -c 2048 -- "$1" | "$3" prefix DENIAL_DIAGNOSTIC > "$2/evidence/events"
        ' timeout-diagnostic "$state/$app/timeout.log" "$state" "$logind_apps_writer" || {
            ((rc!=0)) || rc=1;
        }
    fi
    logind_apps_record "$state" "OBSERVE launcher-lifecycle app=$app phase=normal-close status=$rc child_status=$last_status" || {
        ((rc!=0)) || rc=1;
    }
    close_phase=normal-close-recorded
    ((rc==0)) || exit "$rc"
    [[ $controlled == 1 ]]
)
logind_apps_close() {
    local state=$1 app pid status deadline failed=0
    # Request both closes before waiting, preserving each supervisor's status.
    for app in foot mousepad; do
        pid=$(logind_apps_owner "$state" "$app") || return 1
        [[ -p $state/$app/command && ! -L $state/$app/command ]] || return 1
        timeout -k 1 3 /usr/bin/bash --noprofile --norc -c \
            'printf "%s\n" ROG5_APP_CLOSE_0 > "$1"' apps-close "$state/$app/command" || failed=1
    done
    deadline=$((SECONDS+10))
    for app in foot mousepad; do
        while [[ ! -f $state/$app/finished ]]; do
            logind_apps_owner "$state" "$app" >/dev/null || {
                # Completion may be published between the loop's file check and
                # owner's !finished check. Read its real status below.
                [[ -f $state/$app/finished ]] && break
                return 1
            }
            ((SECONDS<deadline)) || return 124
            sleep .1
        done
        read -r status < "$state/$app/finished" || return 1
        [[ $status == 0 ]] || failed=1
    done
    ((failed==0)) || return 1
    echo 'PASS launcher-owned Foot and editor exited0 after host observation'
}
run_authenticated_apps() {
    local state=${logind_apps_state:?} fd=${logind_apps_port:?} chunk reply='' rc deadline app snapshot_at
    logind_apps_phase=snapshot-initial
    logind_apps_snapshot "$state" "$HOME/denial.log" || return $?
    logind_apps_phase=flow-ready
    logind_apps_record "$state" 'OBSERVE authenticated launcher flow-ready' || return $?
    deadline=$((SECONDS+60))
    snapshot_at=$((SECONDS+5))
    while :; do
        logind_apps_phase=launcher-running
        require_running launcher || { return 1; }
        for app in mousepad foot; do
            logind_apps_phase=owner-$app
            [[ ! -e $state/$app/owner ]] || logind_apps_owner "$state" "$app" >/dev/null || {
                return 1;
            }
        done
        logind_apps_phase=flow-deadline
        ((SECONDS<deadline)) || { return 124; }
        if ((snapshot_at && SECONDS>=snapshot_at)); then
            logind_apps_phase=snapshot-periodic
            logind_apps_snapshot "$state" "$HOME/denial.log" || return $?
            snapshot_at=0
        fi
        logind_apps_phase=acknowledgement
        chunk=''; rc=0
        IFS= read -r -t .2 -u "$fd" chunk || rc=$?
        reply+=$chunk
        ((${#reply}<=200)) || { return 1; }
        if ((rc==0)); then
            [[ $reply == "$logind_apps_token" ]] || return 1
            break
        fi
        ((rc>128)) || { return 1; }
    done
    logind_apps_phase=final-owners
    for app in mousepad foot; do logind_apps_owner "$state" "$app" >/dev/null || return 1; done
    logind_apps_phase=controlled-close
    logind_apps_record "$state" 'OBSERVE authenticated launcher teardown' || return $?
    logind_apps_close "$state"
}
cleanup_authenticated_apps() {
    local state=${logind_apps_state:-} app pid failed=0 deadline
    local original=${1:-0} phase=${logind_apps_phase:-outside-flow}
    [[ -n $state ]] || return 0
    # Publish the controller's cause BEFORE cleanup sends TERM to its clients.
    # The owned O_RDWR keeper prevents FIFO open from waiting for a reader;
    # record() bounds the write. Never replace an existing failure if this
    # additional diagnostic cannot be delivered during partial teardown.
    if [[ $original != 0 && ${logind_apps_evidence_owned:-0} == 1 &&
          ${launcher_evidence_keep:-} =~ ^[0-9]+$ &&
          -e /proc/self/fd/$launcher_evidence_keep ]]; then
        logind_apps_record "$state" "DENIAL_DIAGNOSTIC controller-exit phase=$phase status=$original" ||
            printf 'DENIAL_DIAGNOSTIC controller-exit phase=%s status=%s delivery=failed\n' "$phase" "$original" >&2
    fi
    for app in mousepad foot; do
        [[ ! -f $state/$app/owner || -f $state/$app/finished ]] && continue
        pid=$(logind_apps_owner "$state" "$app") || {
            [[ -f $state/$app/finished ]] || failed=1
            continue
        }
        kill -TERM "$pid" || { [[ -f $state/$app/finished ]] || failed=1; }
    done
    deadline=$((SECONDS+10))
    for app in mousepad foot; do
        while [[ -f $state/$app/owner && ! -f $state/$app/finished ]]; do
            logind_apps_owner "$state" "$app" >/dev/null || break
            ((SECONDS<deadline)) || return 124
            sleep .1
        done
    done
    return "$failed"
}
finish_authenticated_apps() {
    local rc=0
    # Called after app/compositor writers and prefix readers are reaped, including
    # partial preparation. Drain cat before releasing the last port descriptor.
    if [[ ${logind_apps_evidence_owned:-0} == 1 ]]; then
        logind_apps_evidence_owned=0
        launcher_evidence_finish || rc=$?
    fi
    if [[ -n ${logind_apps_port:-} ]]; then
        exec {logind_apps_port}>&- || { ((rc!=0)) || rc=1; }
        unset logind_apps_port
    fi
    return "$rc"
}
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    set -euo pipefail
    [[ $# == 2 && $1 == launch && $EUID == 1000 && -f /run/session-sha256 &&
       -d /sys/bus/virtio/devices ]] || exit 2
    source /run/launcher-apps.sh
    logind_apps_supervise "$2"
fi
