#!/usr/bin/bash
# Offline generic ARM64 VM fixture; never install or run on a phone.
logind_cleanup_state() {
    local sid=$1 sessions scopes first rest
    [[ $sid =~ ^[A-Za-z0-9]+$ ]] || return 2
    sessions=$(timeout -k 1 3 loginctl list-sessions --no-legend --no-pager --no-footer) || return 2
    scopes=$(timeout -k 1 3 systemctl list-units --all --type=scope --no-legend --no-pager --plain) || return 2
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
# Permit tests of the actual query boundary without executing the VM supervisor.
if [[ ${BASH_SOURCE[0]} != "$0" ]]; then return 0; fi
set -euo pipefail
read -r cmdline < /proc/cmdline
[[ $EUID == 0 && " $cmdline " == *' rog5.logind_fixture=1 '* && -d /sys/bus/virtio/devices ]]
trap 'echo "FAIL session supervisor line=$LINENO"; cat /run/pam-session.log 2>/dev/null || :; journalctl -b --no-pager -u systemd-logind -u user@1000 -n 80 || :' ERR
systemctl is-active systemd-logind.service dbus.service systemd-udevd.service
if [[ -e /run/nologin ]]; then
    echo 'OBSERVE startup nologin present before Permit User Sessions'
    cat /run/nologin
fi
systemctl start systemd-user-sessions.service
systemctl is-active systemd-user-sessions.service
[[ ! -e /run/nologin ]]
echo 'OBSERVE packaged Permit User Sessions removed startup nologin'
udevadm settle --timeout=8
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
timeout -k 1 45 setsid --wait openvt -e -f -c 1 -- /usr/bin/bash /run/start-local.sh
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
echo 'PASS authenticated local logind session, mediated devices and removed scope'
