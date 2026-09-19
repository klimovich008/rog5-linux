#!/usr/bin/bash
# Offline generic ARM64 VM fixture; never install or run on a phone.
set -euo pipefail
read -r cmdline < /proc/cmdline
[[ $$ == 1 && $EUID == 0 && " $cmdline " == *' rog5.logind_fixture=1 '* && -d /sys/bus/virtio/devices ]]
trap 'echo "FAIL PID1 fixture setup line=$LINENO"; /usr/bin/poweroff -ff' ERR
export PATH=/usr/bin LANG=C.UTF-8
# Exercise the exact query argument lists before expensive first-boot setup.
source /run/logind-probe.sh
logind_query_sessions --help >/dev/null
logind_query_scopes --help >/dev/null
echo 'PASS packaged cleanup query parsers'
cp -a /etc /run/fixture-etc
mount --bind /run/fixture-etc /etc
source /run/logind-linker-cache.sh
if prepare_boot_caches; then
    echo 'PASS optional VM caches prepared'
else
    # A subshell EXIT trap can bypass the parent ERR trap. Stop explicitly.
    echo 'FAIL optional VM cache preparation'
    /usr/bin/poweroff -ff
    exit 1
fi
date -u -s '2026-09-13 00:00:00' >/dev/null
awk -F: '$1 == "mobile" || $3 == "1000" {exit 1}' /etc/passwd
awk -F: '$1 == "mobile" || $3 == "1000" {exit 1}' /etc/group
printf 'mobile:x:1000:1000:Public synthetic VM account:/run/mobile-home:/usr/bin/bash\n' >> /etc/passwd
printf 'mobile:x:1000:\n' >> /etc/group
fixture_hash=$(printf '%s' 'rog5-logind-fixture-password' | openssl passwd -6 -stdin)
printf 'mobile:%s:20000:0:99999:7:::\n' "$fixture_hash" >> /etc/shadow
unset fixture_hash
chmod 600 /etc/shadow
cp /usr/bin/unix_chkpwd /run/unix_chkpwd
chown 0:0 /run/unix_chkpwd
chmod 6755 /run/unix_chkpwd
mount --bind /run/unix_chkpwd /usr/bin/unix_chkpwd
mount -t tmpfs -o mode=0755,size=32m tmpfs /var
mkdir -p /var/lib /var/log /var/tmp /run/mobile-home
chmod 1777 /var/tmp
chown 1000:1000 /run/mobile-home
chmod 700 /run/mobile-home
printf '47b22e3177df4db18d6ed283dff17712\n' > /etc/machine-id
printf 'rog5-logind-vm\n' > /etc/hostname
mkdir -p /etc/systemd/system
if [[ -f /run/session-sha256 ]]; then source /run/logind-denial-prepare.sh; fi
cat > /etc/systemd/system/rog5-logind-fixture.target <<'EOF'
[Unit]
Description=Offline logind fixture
Requires=rog5-logind-fixture.service
After=rog5-logind-fixture.service
AllowIsolate=yes
EOF
cat > /etc/systemd/system/rog5-logind-fixture.service <<'EOF'
[Unit]
Description=Offline logind probe
Wants=systemd-logind.service dbus.service systemd-udevd.service
After=systemd-logind.service dbus.service systemd-udevd.service
OnSuccess=poweroff.target
OnFailure=poweroff.target
[Service]
Type=oneshot
ExecStart=/usr/bin/bash /run/logind-probe.sh
TimeoutStartSec=65
StandardOutput=journal+console
StandardError=journal+console
EOF
if [[ -f /run/session-sha256 ]]; then
    sed -i 's/TimeoutStartSec=65/TimeoutStartSec=170/' /etc/systemd/system/rog5-logind-fixture.service
fi
/usr/bin/bash /run/independent-observer.sh &
if [[ -f /run/startup-only ]]; then
    read -r uptime _ < /proc/uptime
    printf 'OBSERVE pid1-handoff boottime=%s\n' "$uptime"
fi
echo 'OBSERVE prepared RAM etc/var; exec actual packaged systemd as PID1' 
exec /usr/lib/systemd/systemd --unit=rog5-logind-fixture.target --log-target=console --log-level=info
