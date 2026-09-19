#!/usr/bin/bash
# Offline generic ARM64 VM fixture; never install or run on a phone.
# Extra arguments are used only for the early real-parser --help preflight.
logind_wait_devices() {
    local state=${1:-/run} status=0
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
    printf 'OBSERVE device-readiness phase=begin deadline_seconds=8 devices=%s\n' "${devices[*]}"
    udevadm wait --timeout=8 --initialized=yes "${devices[@]}" || status=$?
    printf 'OBSERVE device-readiness phase=end status=%s\n' "$status"
    return "$status"
}
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
    ((rc == 0)) || mode=abort
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
trap 'echo "FAIL session supervisor line=$LINENO"; cat /run/pam-session.log 2>/dev/null || :; journalctl -b --no-pager -u systemd-logind -u user@1000 -n 80 || :' ERR
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
[[ ! -f /run/session-sha256 ]] || pam_deadline=145
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
