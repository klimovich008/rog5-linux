#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_NETWORK_ROOT_TIME_SYNC:-} == 1 ]] ||
	fail 'set ALLOW_NETWORK_ROOT_TIME_SYNC=1 after the attended storage gate'
ssh_key=${SSH_KEY:-}
known_hosts=${KNOWN_HOSTS:-}
[[ -n $ssh_key && -n $known_hosts ]] ||
	fail 'set SSH_KEY and KNOWN_HOSTS to the dedicated network-root credentials'
[[ -f $ssh_key && ! -L $ssh_key && -r $ssh_key ]] ||
	fail 'SSH_KEY is not a readable regular file'
[[ -f $known_hosts && ! -L $known_hosts && -r $known_hosts ]] ||
	fail 'KNOWN_HOSTS is not a readable regular file'

key_mode=$(stat -c %a "$ssh_key")
known_hosts_mode=$(stat -c %a "$known_hosts")
[[ $key_mode =~ ^[0-7]{3,4}$ && $known_hosts_mode =~ ^[0-7]{3,4}$ ]] ||
	fail 'credential file mode is invalid'
(( (8#$key_mode & 077) == 0 )) ||
	fail 'SSH_KEY must not be accessible to group or other users'
(( (8#$known_hosts_mode & 022) == 0 )) ||
	fail 'KNOWN_HOSTS must not be writable by group or other users'

[[ $(uname -s) == Linux ]] || fail 'this host workflow requires Linux'
for command in date ssh stat timedatectl; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ $(timedatectl show -p NTPSynchronized --value 2>/dev/null) == yes ]] ||
	fail 'host clock is not NTP-synchronized'

host_epoch=$(date -u +%s)
[[ $host_epoch =~ ^[0-9]+$ ]] || fail 'host epoch is invalid'
(( host_epoch >= 1735689600 )) ||
	fail 'host time is implausibly old'

ssh \
	-F /dev/null \
	-i "$ssh_key" \
	-o IdentitiesOnly=yes \
	-o BatchMode=yes \
	-o StrictHostKeyChecking=yes \
	-o UserKnownHostsFile="$known_hosts" \
	-o HostKeyAlias=rog5-network-root \
	-o ConnectTimeout=8 \
	root@169.254.77.2 \
	bash -se -- "$host_epoch" <<'REMOTE'
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

host_epoch=$1
[[ $host_epoch =~ ^[0-9]+$ ]] && (( host_epoch >= 1735689600 )) ||
	fail 'received host epoch is invalid'
[[ $(uname -r) == 7.1.4-g7a5cef0db479 ]] || fail 'unexpected kernel'
[[ $(< /proc/1/comm) == systemd ]] || fail 'PID 1 is not systemd'
[[ $(systemctl is-system-running 2>/dev/null || true) == running ]] ||
	fail 'systemd is not running'
! grep -q 'systemd.mask=' /proc/cmdline ||
	fail 'time bootstrap requires normal unmasked mode'
[[ $(findmnt -n -o FSTYPE /) == overlay ]] || fail 'root is not OverlayFS'
[[ $(findmnt -n -o SOURCE /.rog5/root-ro) == 169.254.77.1:/ ]] ||
	fail 'unexpected NFS lower source'
findmnt -n -o OPTIONS /.rog5/root-ro | tr ',' '\n' | grep -qx ro ||
	fail 'NFS lower is not read-only'
[[ $(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l) -eq 0 ]] ||
	fail 'physical block device is present'
[[ $(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }') -eq 0 ]] ||
	fail 'block-backed mount is present'
[[ $(< /sys/class/net/usb0/carrier) == 1 ]] ||
	fail 'USB network carrier is down'
ip -4 -o address show dev usb0 |
	awk '$4 == "169.254.77.2/30" { found=1 } END { exit !found }' ||
	fail 'USB network address is unexpected'
[[ $(systemctl --failed --no-legend --plain |
	awk 'NF { count++ } END { print count + 0 }') -eq 0 ]] ||
	fail 'systemd has failed units'
[[ -s /run/rog5-network-root-watchdog.pid ]] ||
	fail 'rollback watchdog is not armed'
[[ ! -e /run/rog5-network-root-watchdog.disarmed.pid ]] ||
	fail 'rollback watchdog is already disarmed'

rtc=/sys/firmware/devicetree/base/soc@0/spmi@c440000/pmic@0/rtc@6100
[[ $(tr -d '\000' <"$rtc/status") == disabled ]] ||
	fail 'RTC node is not disabled'
[[ ! -d /sys/module/rtc_pm8xxx ]] || fail 'RTC module is loaded'
[[ $(find /sys/class/rtc -mindepth 1 -maxdepth 1 -name 'rtc*' 2>/dev/null |
	wc -l) -eq 0 ]] || fail 'RTC device is registered'
fatal='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
[[ $(dmesg | grep -Ec "$fatal" || true) -eq 0 ]] ||
	fail 'fatal kernel signature is present'

before=$(date -u +%s)
delta=$((host_epoch - before))
(( delta >= 0 )) || delta=$((-delta))
changed=0
if (( delta > 2 )); then
	date --utc --set="@$host_epoch" >/dev/null
	changed=1
fi
after=$(date -u +%s)
remaining=$((host_epoch - after))
(( remaining >= 0 )) || remaining=$((-remaining))
(( remaining <= 3 )) || fail 'target clock did not converge on host time'

[[ $(tr -d '\000' <"$rtc/status") == disabled ]] ||
	fail 'RTC node changed state'
[[ ! -d /sys/module/rtc_pm8xxx ]] || fail 'RTC module loaded during sync'
[[ $(find /sys/class/rtc -mindepth 1 -maxdepth 1 -name 'rtc*' 2>/dev/null |
	wc -l) -eq 0 ]] || fail 'RTC registered during sync'
[[ $(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l) -eq 0 ]] ||
	fail 'physical storage appeared during sync'
[[ -s /run/rog5-network-root-watchdog.pid ]] ||
	fail 'rollback watchdog disappeared during sync'
[[ ! -e /run/rog5-network-root-watchdog.disarmed.pid ]] ||
	fail 'rollback watchdog changed state during sync'
[[ $(< /sys/class/net/usb0/carrier) == 1 ]] ||
	fail 'USB carrier dropped during sync'
[[ $(systemctl --failed --no-legend --plain |
	awk 'NF { count++ } END { print count + 0 }') -eq 0 ]] ||
	fail 'systemd failed after sync'
[[ $(dmesg | grep -Ec "$fatal" || true) -eq 0 ]] ||
	fail 'fatal kernel signature appeared during sync'

printf 'PASS volatile Linux system clock aligned to synchronized host; changed=%s initial_drift_seconds=%s\n' \
	"$changed" "$delta"
REMOTE
