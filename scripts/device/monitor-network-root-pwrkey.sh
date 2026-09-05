#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_PWRKEY_MONITOR:-}" = 1 ] ||
	fail 'set ALLOW_PWRKEY_MONITOR=1 for one attended short-press test'
monitor_timeout=${1:-120}
case $monitor_timeout in
	*[!0-9]*|'') fail 'timeout must be an integer' ;;
esac
[ "$monitor_timeout" -ge 30 ] && [ "$monitor_timeout" -le 300 ] ||
	fail 'timeout must be between 30 and 300 seconds'
for command in findmnt ip python3 systemctl systemd-inhibit timeout; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] || fail 'unexpected kernel'
[ "$(cat /proc/1/comm)" = systemd ] || fail 'PID 1 is not systemd'
[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
	fail 'systemd is not running'
! grep -q 'systemd.mask=' /proc/cmdline ||
	fail 'physical input acceptance requires normal unmasked mode'
[ "$(findmnt -n -o FSTYPE /)" = overlay ] || fail 'root is not OverlayFS'
[ "$(findmnt -n -o SOURCE /.rog5/root-ro)" = 169.254.77.1:/ ] ||
	fail 'unexpected NFS lower source'
findmnt -n -o OPTIONS /.rog5/root-ro | tr ',' '\n' | grep -qx ro ||
	fail 'NFS lower is not read-only'
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	fail 'physical block device is present'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount is present'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	fail 'USB network carrier is down'
ip -4 -o address show dev usb0 |
	awk '$4 == "169.254.77.2/30" { found=1 } END { exit !found }' ||
	fail 'USB network address is unexpected'
[ "$(systemctl --failed --no-legend --plain |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'systemd has failed units'
[ ! -e /run/rog5-network-root-watchdog.pid ] ||
	fail 'network-root rollback watchdog is still armed'
[ -s /run/rog5-network-root-watchdog.disarmed.pid ] ||
	fail 'network-root rollback has no disarm marker'

dt=/sys/firmware/devicetree/base
rtc_node=$dt/soc@0/spmi@c440000/pmic@0/rtc@6100
[ "$(tr -d '\000' <"$rtc_node/status")" = disabled ] ||
	fail 'RTC node is not disabled'
[ ! -d /sys/module/rtc_pm8xxx ] || fail 'RTC module is loaded'
[ "$(find /sys/class/rtc -mindepth 1 -maxdepth 1 -name 'rtc*' 2>/dev/null |
	wc -l)" -eq 0 ] || fail 'RTC device is registered'
[ -d /sys/module/qcom_pon ] || fail 'qcom_pon is not loaded'

event_path=
event_count=0
for event in /sys/class/input/event*; do
	[ -r "$event/device/name" ] || continue
	device=$event/device/device
	[ -L "$device/driver" ] || continue
	[ "$(basename "$(readlink -f "$device/driver")")" = \
		pm8941-pwrkey ] || continue
	[ "$(cat "$event/device/name")" = pmic_pwrkey ] ||
		fail 'power key has an unexpected input name'
	tr '\000' '\n' <"$device/of_node/compatible" |
		grep -qx 'qcom,pmk8350-pwrkey' ||
		fail 'power key has an unexpected device-tree identity'
	[ "$(cat "$device/power/wakeup")" = enabled ] ||
		fail 'power key wakeup is not enabled'
	set -- $(cat "$event/device/capabilities/key")
	[ "$#" -ge 2 ] || fail 'power-key capability bitmap is too short'
	while [ "$#" -gt 2 ]; do
		shift
	done
	key_power_word=$1
	case $key_power_word in
		*[!0-9a-fA-F]*|'') fail 'invalid power-key capability bitmap' ;;
	esac
	[ $((0x$key_power_word & 0x10000000000000)) -ne 0 ] ||
		fail 'input event does not advertise KEY_POWER'
	event_path=/dev/input/${event##*/}
	event_count=$((event_count + 1))
done
[ "$event_count" -eq 1 ] || fail 'expected exactly one power-key event'
[ -r "$event_path" ] || fail 'power-key event is not readable'

fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	fail 'fatal kernel signature is present'

exec systemd-inhibit \
	--what=handle-power-key \
	--mode=block \
	--why='ROG5 attended low-level input test' \
	timeout "$monitor_timeout" python3 - "$event_path" <<'PY'
import struct
import sys

event_struct = struct.Struct("@llHHi")
if event_struct.size != 24:
    raise RuntimeError("unexpected AArch64 input_event size")

pressed = False
with open(sys.argv[1], "rb", buffering=0) as source:
    print("READY low-level power-key monitor and logind inhibitor are active", flush=True)
    while True:
        data = source.read(event_struct.size)
        if len(data) != event_struct.size:
            raise RuntimeError("short input_event read")
        _, _, event_type, code, value = event_struct.unpack(data)
        if event_type != 1 or code != 116:
            continue
        if value == 1:
            pressed = True
            print("PASS physical KEY_POWER press event observed", flush=True)
        elif value == 0 and pressed:
            print("PASS physical KEY_POWER release event observed", flush=True)
            break
PY
