#!/usr/bin/bash
# Offline generic ARM64 VM fixture; never install or run on a phone.
# Extra arguments are used only for the early real-parser --help preflight.
logind_prepare_device_priority() {
    local etc=$1 unit=$2 state=$3
    [[ -f $state/session-sha256 ]] || return 0
    local original='ExecStart=-udevadm trigger --type=all --action=add --prioritized-subsystem=module,block,tpmrm,net,tty,input'
    # The VM consumes DRM, FUSE and a virtio application channel. Coldplug
    # enumeration can finish while their unprioritized events still queue.
    # Preserve packaged priorities and promote these consumers plus ancestors.
    [[ $(grep -c '^ExecStart=' "$unit") == 1 ]] || return 1
    grep -Fx -- "$original" "$unit" >/dev/null || return 1
    mkdir -p "$etc/systemd/system/systemd-udev-trigger.service.d" || return $?
    (set -C; printf '[Service]\nExecStart=\n%s,drm,misc,virtio-ports\n' "$original" > \
        "$etc/systemd/system/systemd-udev-trigger.service.d/rog5-vm-priority.conf")
}
logind_prepare_fuse_diagnostics() {
    local state=$1 etc=$2
    [[ -f $state/session-sha256 ]] || return 0
    mkdir -p "$etc/udev/rules.d" || return $?
    # RAM-only fixture rule, installed before systemd starts coldplug. udev's
    # per-event log level exposes original processing, not just a later retry.
    (set -C; printf 'SUBSYSTEM=="misc", KERNEL=="fuse", OPTIONS="log_level=debug"\n' > \
        "$etc/udev/rules.d/00-rog5-vm-fuse-diagnostic.rules") || return $?
    (set -C; printf 'failure-only diagnostic; never admission\n' > "$state/fuse-event-diagnostic")
}
logind_fuse_event_diagnostic() {
    local status=0 trigger_status=0 initialized_status=0 journal_status=0
    [[ -c /dev/fuse && -d /sys/devices/virtual/misc/fuse ]] || return 1
    echo 'fuse_phase=before-retrigger'
    logind_device_database_snapshot /dev/fuse || status=$?
    # Settle waits for the event UUID, including failed worker completions.
    # Preserve that status separately and ask the real initialization reader.
    timeout -k 1 3 udevadm trigger --action=add --settle /sys/devices/virtual/misc/fuse || trigger_status=$?
    printf 'trigger_status=%s\nfuse_phase=after-retrigger\n' "$trigger_status"
    logind_device_database_snapshot /dev/fuse || status=$?
    udevadm wait --timeout=1 --initialized=yes /dev/fuse || initialized_status=$?
    printf 'initialized_status=%s\n' "$initialized_status"
    journalctl -b --no-pager --output=short-monotonic -u systemd-udevd \
        --grep='fuse|c10:229' -n 100 || journal_status=$?
    printf 'journal_status=%s\n' "$journal_status"
    ((status != 0)) || status=$trigger_status
    ((status != 0)) || status=$initialized_status
    ((status != 0)) || status=$journal_status
    return "$status"
}
logind_device_database_snapshot() {
    local database_root=/run/udev/data
    local metadata device major minor extra database data read_status truncated status=0
    local LC_ALL=C
    # One stat process, then bounded builtin reads. Capture every consumer before
    # slower udev/property queries can exhaust the enclosing 3s snapshot budget.
    metadata=$(LC_ALL=C stat -c '%n %t %T' -- "$@") || status=$?
    printf 'database_stat_status=%s\n' "$status"
    while read -r device major minor extra; do
        [[ -n $device ]] || continue
        if [[ -n $extra || ! $major =~ ^[0-9a-fA-F]{1,8}$ || ! $minor =~ ^[0-9a-fA-F]{1,8}$ ]]; then
            printf 'database_status=invalid-device-metadata\n'
            status=1; continue
        fi
        database=$database_root/c$((16#$major)):$((16#$minor))
        printf 'database_device=%s database_path=%s\n' "$device" "$database"
        if [[ -L $database || ( -e $database && ! -f $database ) ]]; then
            printf 'database_status=refused-nonregular\n'; status=1
        elif [[ ! -e $database ]]; then
            printf 'database_status=absent\n'
        else
            data=; read_status=0; truncated=0
            IFS= read -r -N 1025 data < "$database" || read_status=$?
            if ((${#data} > 1024)); then data=${data:0:1024}; truncated=1; fi
            printf 'database_status=present bytes=%s truncated=%s read_status=%s\n' \
                "${#data}" "$truncated" "$read_status"
            printf '%s\ndatabase_end\n' "$data"
        fi
    done <<< "$metadata"
    # Presence/empty contents/ID_PROCESSING are observations, never admission.
    # The caller encodes this data and retains the original wait failure.
    return "$status"
}
logind_device_snapshot() {
    local device status=0 query_status uptime unused
    logind_device_database_snapshot "$@" || status=1
    for device in "$@"; do
        read -r uptime unused < /proc/uptime || uptime=unavailable
        printf 'device=%s boottime=%s\n' "$device" "$uptime"
        query_status=0
        stat -c 'type=%F rdev=%t:%T mode=%a uid=%u gid=%g' -- "$device" || query_status=$?
        printf 'stat_status=%s\n' "$query_status"
        ((query_status == 0)) || status=1
        query_status=0
        udevadm info --query=property "$device" || query_status=$?
        printf 'query_status=%s\n' "$query_status"
        ((query_status == 0)) || status=1
    done
    query_status=0
    journalctl -b --no-pager -u systemd-udevd -n 40 || query_status=$?
    printf 'journal_status=%s\n' "$query_status"
    ((query_status == 0)) || status=1
    return "$status"
}
logind_capture_bounded() {
    # Keep one extra byte to detect truncation; drain the rest so verbosity
    # cannot SIGPIPE the observed command or change its exit status.
    local status=0 drain_status=0
    head -c 16385 > "$1" || status=$?
    cat > /dev/null || drain_status=$?
    ((status != 0)) || status=$drain_status
    return "$status"
}
logind_publish_diagnostic() {
    local label=$1 status=$2 file=$3 bytes truncated=0 encoded
    bytes=$(stat -c %s -- "$file") || return $?
    ((bytes <= 16385)) || return 1
    if ((bytes > 16384)); then bytes=16384; truncated=1; fi
    encoded=$(head -c 16384 -- "$file" | od -An -v -tx1 | tr -d ' \n') || return $?
    printf 'DIAGNOSTIC_%s status=%s bytes=%s truncated=%s hex=%s\n' \
        "$label" "$status" "$bytes" "$truncated" "$encoded"
}
logind_failure_journal() (
    set -o pipefail
    local temporary status=0 capture_status=0
    local -a pipeline_status
    temporary=$(mktemp -d "${TMPDIR:-/run}/rog5-journal-query.XXXXXXXX") || return $?
    trap 'status=$?; trap - EXIT; rm -rf -- "$temporary" || { ((status != 0)) || status=1; }; exit "$status"' EXIT
    trap 'exit 143' TERM
    trap 'exit 130' INT
    # Use the system journal, independently of the timed-out user-bus query.
    # -b fixes the clock domain to this boot; these are journal receipt times,
    # not guaranteed exact state-transition times. Retain the original filters.
    printf 'OBSERVE session-journal phase=begin deadline_seconds=5 clock=CLOCK_MONOTONIC\n'
    if timeout -k 1 5 stdbuf -oL -e0 journalctl -b --no-pager --output=short-monotonic \
        -u systemd-logind -u user@1000 -n 80 2>&1 |
        logind_capture_bounded "$temporary/journal"; then
        pipeline_status=("${PIPESTATUS[@]}")
    else
        pipeline_status=("${PIPESTATUS[@]}")
    fi
    status=${pipeline_status[0]}
    capture_status=${pipeline_status[1]}
    printf 'OBSERVE session-journal phase=end status=%s capture_status=%s\n' "$status" "$capture_status"
    logind_publish_diagnostic SESSION_JOURNAL "$status" "$temporary/journal" || capture_status=$?
    ((status != 0)) || status=$capture_status
    return "$status"
)
logind_wait_devices() (
    set -o pipefail
    local state=${1:-/run} status=0
    local temporary uptime unused snapshot_status=0 diagnostic_status=0
    local -a pipeline_status
    local -a devices=(/dev/dri/card0 /dev/input/event0 /dev/tty1)
    if [[ -f $state/editor-probe && -f $state/apps-probe ]]; then
        echo 'FAIL conflicting virtual observation modes' >&2
        return 1
    fi
    if [[ -f $state/session-sha256 ]]; then
        # The document portal requires udev's nonroot FUSE permissions.
        devices+=(/dev/fuse)
    elif [[ -f $state/editor-probe || -f $state/apps-probe ]]; then
        echo 'FAIL virtual observation requires a combined session' >&2
        return 1
    fi
    if [[ -f $state/editor-probe || -f $state/apps-probe ]]; then
        # Keyboard/tablet numbering can swap: both are consumed by this mode.
        devices+=(/dev/input/event1 /dev/vport0p1)
    fi
    # Wait for all consumers in one eight-second budget, not unrelated events
    # elsewhere in the udev queue. Initialization is stronger than node presence.
    # Later port identity/ownership, PAM, VT and seat checks remain mandatory.
    temporary=$(mktemp -d "${TMPDIR:-/run}/rog5-device-query.XXXXXXXX") || return $?
    trap 'status=$?; trap - EXIT; rm -rf -- "$temporary" || { ((status != 0)) || status=1; }; exit "$status"' EXIT
    trap 'exit 143' TERM
    trap 'exit 130' INT
    read -r uptime unused < /proc/uptime || uptime=unavailable
    printf 'OBSERVE device-readiness phase=begin deadline_seconds=8 devices=%s boottime=%s\n' "${devices[*]}" "$uptime"
    if SYSTEMD_LOG_TARGET=console SYSTEMD_LOG_LEVEL=debug SYSTEMD_COLORS=0 \
        udevadm wait --timeout=8 --initialized=yes "${devices[@]}" 2>&1 |
        logind_capture_bounded "$temporary/wait"; then
        pipeline_status=("${PIPESTATUS[@]}")
    else
        pipeline_status=("${PIPESTATUS[@]}")
    fi
    status=${pipeline_status[0]}
    diagnostic_status=${pipeline_status[1]}
    read -r uptime unused < /proc/uptime || uptime=unavailable
    printf 'OBSERVE device-readiness phase=end status=%s capture_status=%s boottime=%s\n' "$status" "$diagnostic_status" "$uptime"
    logind_publish_diagnostic DEVICE_WAIT "$status" "$temporary/wait" || diagnostic_status=$?
    if ((status)); then
        # This is a later observation, not the state at the wait's failure.
        # Bound the entire snapshot independently; it never changes admission.
        printf 'OBSERVE device-readiness snapshot=after-failed-wait deadline_seconds=3\n'
        if timeout -k 1 3 bash --noprofile --norc -c \
            'source "$1"; shift; logind_device_snapshot "$@"' \
            snapshot "${BASH_SOURCE[0]}" "${devices[@]}" 2>&1 |
            logind_capture_bounded "$temporary/snapshot"; then
            pipeline_status=("${PIPESTATUS[@]}")
        else
            pipeline_status=("${PIPESTATUS[@]}")
        fi
        snapshot_status=${pipeline_status[0]}
        printf 'OBSERVE device-readiness snapshot-capture-status=%s\n' "${pipeline_status[1]}"
        logind_publish_diagnostic DEVICE_SNAPSHOT "$snapshot_status" "$temporary/snapshot" || :
        if [[ -f $state/fuse-event-diagnostic && -f $state/session-sha256 ]]; then
            # The failed baseline above remains failed even if this one
            # diagnostic retrigger initializes FUSE. No second session attempt.
            printf 'OBSERVE fuse-event phase=diagnostic-only deadline_seconds=10\n'
            if timeout -k 1 10 bash --noprofile --norc -c \
                'source "$1"; logind_fuse_event_diagnostic' \
                diagnostic "${BASH_SOURCE[0]}" 2>&1 |
                logind_capture_bounded "$temporary/fuse"; then
                pipeline_status=("${PIPESTATUS[@]}")
            else
                pipeline_status=("${PIPESTATUS[@]}")
            fi
            printf 'OBSERVE fuse-event capture_status=%s\n' "${pipeline_status[1]}"
            logind_publish_diagnostic FUSE_EVENT "${pipeline_status[0]}" "$temporary/fuse" || :
        fi
    else
        # Failure to retain the observation must not become a successful test.
        status=$diagnostic_status
    fi
    return "$status"
)
logind_startup_timings() (
    set -o pipefail
    local temporary status=0 query_status=0 encoded bytes stderr_encoded stderr_bytes
    local LC_ALL=C
    export LC_ALL
    temporary=$(mktemp -d "${TMPDIR:-/run}/rog5-unit-query.XXXXXXXX") || return $?
    trap 'status=$?; trap - EXIT; rm -rf -- "$temporary" || { ((status != 0)) || status=1; }; exit "$status"' EXIT
    trap 'exit 143' TERM
    trap 'exit 130' INT
    # Keep the existing eight-second command/one-second kill-after bound. Each
    # output file is capped before it enters shell memory; line buffering makes
    # already emitted property rows survive timeout. Debug stderr is evidence,
    # never a source of raw serial success markers.
    (ulimit -f 16 || exit $?
     export SYSTEMD_LOG_LEVEL=debug SYSTEMD_COLORS=0
     exec timeout -k 1 8 stdbuf -oL systemctl show --no-pager \
        -p Id -p LoadState -p ActiveState -p ActiveEnterTimestampMonotonic \
        -p InactiveExitTimestampMonotonic -p ExecMainStartTimestampMonotonic \
        -p ExecMainExitTimestampMonotonic -p ConditionTimestampMonotonic \
        -p ConditionResult -p Result -p ExecMainStatus \
        systemd-hwdb-update.service ldconfig.service \
        systemd-journal-catalog-update.service systemd-tmpfiles-setup.service \
        systemd-tmpfiles-setup-dev-early.service systemd-udevd.service \
        systemd-udev-trigger.service systemd-logind.service sysinit.target) > "$temporary/stdout" 2> "$temporary/stderr" || query_status=$?
    status=$query_status
    bytes=$(stat -c %s -- "$temporary/stdout") || return $?
    stderr_bytes=$(stat -c %s -- "$temporary/stderr") || return $?
    ((bytes <= 16384 && stderr_bytes <= 16384)) || return 1
    ((bytes != 0 || status != 0)) || status=1
    encoded=$(od -An -v -tx1 "$temporary/stdout" | tr -d ' \n') || return $?
    stderr_encoded=$(od -An -v -tx1 "$temporary/stderr" | tr -d ' \n') || return $?
    printf 'DIAGNOSTIC_UNIT_QUERY code=%s bytes=%s hex=%s\n' "$query_status" "$stderr_bytes" "$stderr_encoded"
    if ((status)); then
        printf 'DIAGNOSTIC_UNIT_TIMINGS status=failed code=%s bytes=%s hex=%s\n' "$status" "$bytes" "$encoded"
        return "$status"
    fi
    printf 'DIAGNOSTIC_UNIT_TIMINGS status=read bytes=%s hex=%s\n' "$bytes" "$encoded"
)
logind_query_sessions() {
    timeout -k 1 3 loginctl list-sessions --no-legend --no-pager "$@"
}
logind_query_scopes() {
    timeout -k 1 3 systemctl list-units --all --type=scope --no-legend --no-pager --plain "$@"
}
logind_cleanup_state() {
    local sid=$1 sessions scopes first rest rc
    [[ $sid =~ ^[A-Za-z0-9]+$ ]] || return 2
    sessions=$(logind_query_sessions) || {
        rc=$?; printf 'FAIL cleanup query=loginctl status=%s\n' "$rc" >&2; return 2;
    }
    scopes=$(logind_query_scopes) || {
        rc=$?; printf 'FAIL cleanup query=systemctl status=%s\n' "$rc" >&2; return 2;
    }
    while read -r first rest; do [[ $first != "$sid" ]] || return 1; done <<< "$sessions"
    while read -r first rest; do [[ $first != "session-$sid.scope" ]] || return 1; done <<< "$scopes"
    return 0
}
logind_tty_unowned() {
    local rows tty pid
    rows=$(timeout -k 1 3 ps -eo tty=,pid=) || return 2
    while read -r tty pid; do [[ $tty != tty1 ]] || return 1; done <<< "$rows"
    return 0
}
logind_restore_executable_view() {
    local mode=${1:-normal}
    local -a overlay_options=()
    case $mode in
        normal) ;;
        abort) overlay_options=(--lazy) ;;
        *) return 2 ;;
    esac
    # 2: overlay and alias remain; 1: only alias remains; 0: both released.
    # Advance only after success, so EXIT cleanup cannot repeat an already
    # completed /usr/bin unmount when releasing the alias failed.
    if ((restore_needed == 2)); then
        # An already-failed session can leave users of this owned RAM overlay.
        # Detach it on abort so late shutdown cannot force-unmount its shared
        # 9P alias. Successful-session restoration remains an ordinary unmount;
        # lazy detach neither proves client cleanup nor changes the failure.
        /run/original-bin/umount "${overlay_options[@]}" /usr/bin || return $?
        restore_needed=1
    fi
    if ((restore_needed == 1)); then
        # VM services still hold executable references through this alias, so
        # ordinary unmount returns EBUSY. Detach only this owned bind, preserving
        # open files and excluding it from late shutdown's forced unmounts.
        # MNT_FORCE on a 9P alias can cancel the shared live-root session.
        /usr/bin/umount --lazy /run/original-bin || return $?
        restore_needed=0
    fi
}
logind_finish() {
    local rc=$? cleanup_rc=0 mode=normal
    trap - EXIT
    if ((rc != 0)); then
        mode=abort
        # A subshell function with an EXIT trap can bypass the caller's ERR
        # trap. Collect once here for every failed supervisor exit, while the
        # executable view is still present, without changing the primary error.
        cat /run/pam-session.log 2>/dev/null || :
        logind_failure_journal || :
    fi
    logind_restore_executable_view "$mode" || cleanup_rc=$?
    if ((cleanup_rc)); then
        printf 'FAIL executable view cleanup stage=%s status=%s\n' "$restore_needed" "$cleanup_rc" >&2
        ((rc != 0)) || rc=$cleanup_rc
    fi
    exit "$rc"
}
# Permit tests of the actual query boundary without executing the VM supervisor.
if [[ ${BASH_SOURCE[0]} != "$0" ]]; then return 0; fi
set -euo pipefail
read -r cmdline < /proc/cmdline
[[ $EUID == 0 && " $cmdline " == *' rog5.logind_fixture=1 '* && -d /sys/bus/virtio/devices ]]
trap 'echo "FAIL session supervisor line=$LINENO"' ERR
restore_needed=0
[[ ! -f /run/session-sha256 ]] || restore_needed=2
trap logind_finish EXIT
systemctl is-active systemd-logind.service dbus.service systemd-udevd.service
if [[ -e /run/nologin ]]; then
    echo 'OBSERVE startup nologin present before Permit User Sessions'
    cat /run/nologin
fi
systemctl start systemd-user-sessions.service
systemctl is-active systemd-user-sessions.service
[[ ! -e /run/nologin ]]
echo 'OBSERVE packaged Permit User Sessions removed startup nologin'
logind_wait_devices
# A diagnostic failure must not prevent the independent PAM/cleanup probe.
# Host startup-only qualification still requires a complete timing inventory.
if [[ -f /run/startup-only ]]; then logind_startup_timings || :; fi
if [[ -f /run/editor-probe || -f /run/apps-probe ]]; then
    [[ -c /dev/vport0p1 ]]
    expected_port=rog5.editor
    if [[ -f /run/apps-probe ]]; then
        [[ ! -f /run/editor-probe ]]
        expected_port=rog5.apps
    fi
    [[ $(cat /sys/class/virtio-ports/vport0p1/name) == "$expected_port" ]]
    chown 1000:1000 /dev/vport0p1
    chmod 600 /dev/vport0p1
fi
[[ -c /dev/dri/card0 && -c /dev/input/event0 ]]
udevadm info --query=property /dev/dri/card0
udevadm info --query=property /dev/input/event0
cat > /run/start-local.sh <<'EOF'
#!/usr/bin/bash
exec /run/payload/pam-session > /run/pam-session.log 2>&1
EOF
chmod 755 /run/start-local.sh
logind_tty_unowned || { echo 'FAIL tty1 ownership not proven free'; exit 1; }
# vconsole setup allocates VT1 even without a login process. Claim only this
# proven unused terminal in the isolated fixture, never an operator session.
# tty1 is already the foreground console; preserve its allocation. openvt -s -w
# attempts to deallocate that same active console at exit. Direct exec preserves
# the PAM command status; setsid supplies the session leader expected by -e.
[[ $(fgconsole) == 1 ]]
pam_deadline=45
if [[ -f /run/session-sha256 ]]; then
    pam_deadline=145
    # Full VM:190s Rust child (60s setup +40s portals +60s flow +30s
    # cleanup), plus40s PAM authentication/teardown. Every inner check applies.
    [[ -f /run/startup-only ]] || pam_deadline=230
fi
timeout -k 1 "$pam_deadline" setsid --wait openvt -e -f -c 1 -- /usr/bin/bash /run/start-local.sh
[[ $(fgconsole) == 1 ]]
logind_tty_unowned || { echo 'FAIL tty1 cleanup not proven'; exit 1; }
cat /run/pam-session.log
grep -Fx 'PASS local active tty1 session, user manager and mediated devices' /run/pam-session.log
grep -Fx 'PASS authenticated PAM local session and child execution' /run/pam-session.log
sid=$(cat /run/mobile-home/session-id)
[[ $sid =~ ^[A-Za-z0-9]+$ ]]
for ((i=0;i<10;i++)); do
    if logind_cleanup_state "$sid"; then break; else cleanup=$?; fi
    [[ $cleanup == 1 ]] || { echo 'FAIL cleanup query unavailable'; exit 1; }
    sleep 1
done
logind_cleanup_state "$sid" || { echo 'FAIL local session/scope retained or query failed'; exit 1; }
# Restore canonical executable paths, then release their temporary 9P alias.
logind_restore_executable_view
echo 'PASS authenticated local logind session, mediated devices and removed scope'
