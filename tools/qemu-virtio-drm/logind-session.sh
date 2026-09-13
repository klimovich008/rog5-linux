#!/usr/bin/bash
# Offline generic ARM64 VM fixture; never install or run on a phone.
set -euo pipefail
read -r cmdline < /proc/cmdline
[[ $EUID == 0 && " $cmdline " == *' rog5.logind_fixture=1 '* && -d /sys/bus/virtio/devices ]]
trap 'echo "FAIL session supervisor line=$LINENO"; cat /run/pam-session.log 2>/dev/null || :; journalctl -b --no-pager -u systemd-logind -u user@1000 -n 80 || :' ERR
systemctl is-active systemd-logind.service dbus.service systemd-udevd.service
udevadm settle --timeout=8
[[ -c /dev/dri/card0 && -c /dev/input/event0 ]]
udevadm info --query=property /dev/dri/card0
udevadm info --query=property /dev/input/event0
cat > /run/start-local.sh <<'EOF'
#!/usr/bin/bash
exec /run/payload/pam-session > /run/pam-session.log 2>&1
EOF
chmod 755 /run/start-local.sh
owners=$(ps -t tty1 -o pid=) || [[ -z $owners ]]
[[ -z $owners ]] || { echo "FAIL tty1 has attached processes: $owners"; exit 1; }
# vconsole setup allocates VT1 even without a login process. Claim only this
# proven unused terminal in the isolated fixture, never an operator session.
timeout -k 1 45 openvt -f -c 1 -s -w -- /usr/bin/bash /run/start-local.sh
cat /run/pam-session.log
grep -Fx 'PASS local active tty1 session, user manager and mediated devices' /run/pam-session.log
grep -Fx 'PASS authenticated PAM local session and child execution' /run/pam-session.log
sid=$(cat /run/mobile-home/session-id)
[[ $sid =~ ^[A-Za-z0-9]+$ ]]
for ((i=0;i<10;i++)); do
    if ! loginctl show-session "$sid" >/dev/null 2>&1; then break; fi
    sleep 1
done
if loginctl show-session "$sid" >/dev/null 2>&1; then echo 'FAIL local session retained'; exit 1; fi
if systemctl is-active --quiet "session-$sid.scope"; then echo 'FAIL local scope retained'; exit 1; fi
echo 'PASS authenticated local logind session, mediated devices and removed scope'
