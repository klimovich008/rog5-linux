#!/bin/sh
# Observation component only. The coordinator owns signed V9 admission and storage/power gates.
set -eu
export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
umask 077
fail() { printf 'FAIL %s\n' "$*" >&2; exit 1; }
[ "$#" = 5 ] || [ "$#" = 6 ] || fail 'expected new-boot previous-boot key seconds inhibitor-sha256 [--preflight]'
preflight=0
if [ "$#" = 6 ]; then [ "$6" = --preflight ] || fail 'unknown observer mode'; preflight=1; fi
boot=$1 previous=$2 key=$3 seconds=$4 unit_sha=$5
[ "${ALLOW_ROG5_LOCAL_KEY_OBSERVER:-}" = rog5-v9-local-key-observer-v1 ] || fail 'observer guard missing'
[ "$(id -u)" = 0 ] || fail 'target observer requires root'
for uuid in "$boot" "$previous"; do
 printf '%s\n' "$uuid" | grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' || fail 'invalid boot binding'
done
[ "$boot" != "$previous" ] || fail 'successor must have a new boot ID'
printf '%s\n' "$unit_sha" | grep -Eq '^[0-9a-f]{64}$' || fail 'invalid unit digest'
case $seconds in ''|*[!0-9]*) fail 'invalid timeout';; esac
[ "$seconds" -ge 30 ] && [ "$seconds" -le 300 ] || fail 'timeout outside 30-300 seconds'
case $key in
 power) name=pmic_pwrkey; driver=pm8941-pwrkey; node=/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey; compatible=qcom,pmk8350-pwrkey; wake=enabled; bitmap='10000000000000 0'; code=116;;
 volume-down) name=pmic_resin; driver=pm8941-pwrkey; node=/soc@0/spmi@c440000/pmic@0/pon@1300/resin; compatible=qcom,pmk8350-resin; wake=absent; bitmap='4000000000000 0'; code=114;;
 volume-up) name=gpio-keys; driver=gpio-keys; node=/gpio-keys; compatible=gpio-keys; wake=enabled; bitmap='8000000000000 0'; code=115;;
 *) fail 'unknown key';;
esac
for tool in awk base64 busctl cat dd grep id mktemp od readlink sha256sum stat systemctl timeout tr uname sed rm rmdir; do
 command -v "$tool" >/dev/null || fail "missing tool $tool"
done
unit=/etc/systemd/system/rog5-server-inhibit.service
check_runtime() {
 [ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot" ] || fail 'boot changed'
 [ "$(uname -r)" = 7.1.4-gf17befd4ef17 ] || fail 'kernel changed'
 [ "$(cat /proc/1/comm)" = systemd ] || fail 'PID1 changed'
 [ "$(systemctl is-system-running)" = running ] || fail 'systemd is not running'
 [ -z "$(systemctl --failed --no-legend --plain)" ] || fail 'failed units'
 [ "$(systemctl show rog5-server-inhibit.service -p LoadState --value)" = loaded ] || fail 'unit not loaded'
 [ "$(systemctl show rog5-server-inhibit.service -p ActiveState --value)" = active ] || fail 'unit inactive'
 [ "$(systemctl show rog5-server-inhibit.service -p SubState --value)" = running ] || fail 'unit not running'
 [ "$(systemctl show rog5-server-inhibit.service -p FragmentPath --value)" = "$unit" ] || fail 'unit fragment changed'
 [ -f "$unit" ] && [ ! -L "$unit" ] || fail 'unit file unsafe'
 [ "$(sha256sum "$unit" | awk '{print $1}')" = "$unit_sha" ] || fail 'unit bytes changed'
 pid=$(systemctl show rog5-server-inhibit.service -p MainPID --value)
 case $pid in ''|0|*[!0-9]*) fail 'invalid inhibitor PID';; esac
 [ "$(stat -c %u /proc/"$pid")" = 0 ] || fail 'inhibitor process not root'
 # Drop the parenthesized comm first: spaces and parentheses in comm cannot shift field 22.
 start=$(sed 's/^.*) //' /proc/"$pid"/stat | awk '{print $20}')
 case $start in ''|*[!0-9]*) fail 'invalid inhibitor start time';; esac
 lock=$(busctl call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager ListInhibitors)
 [ "$lock" = "a(ssssuu) 1 \"sleep:handle-power-key\" \"rog5-server\" \"keep-server-workloads-running\" \"block\" 0 $pid" ] || fail 'exact logind block inhibitor absent'
 if [ -n "${inhibitor_identity:-}" ]; then
  [ "$pid:$start" = "$inhibitor_identity" ] || fail 'inhibitor process changed'
 else inhibitor_identity=$pid:$start; fi
}
discover() {
 count=0
 for candidate in /sys/class/input/event*; do
  [ -r "$candidate/device/name" ] || continue
  [ "$(cat "$candidate/device/name")" = "$name" ] || continue
  count=$((count + 1)); event=$candidate
 done
 [ "$count" = 1 ] || fail 'input identity not unique'
 parent=$event/device/device
 [ "$(readlink -f "$parent/driver")" = "/sys/bus/platform/drivers/$driver" ] || fail 'input driver changed'
 [ "$(readlink -f "$parent/of_node")" = "/sys/firmware/devicetree/base$node" ] || fail 'input OF node changed'
 [ "$(tr '\000' '\n' < "$parent/of_node/compatible")" = "$compatible" ] || fail 'input compatible changed'
 actual_wake=absent
 if [ -r "$parent/power/wakeup" ]; then actual_wake=$(cat "$parent/power/wakeup"); fi
 [ "$actual_wake" = "$wake" ] || fail 'input wake policy changed'
 [ "$(awk '{$1=$1; print}' "$event/device/capabilities/key")" = "$bitmap" ] || fail 'input capability changed'
 device=/dev/input/${event##*/}
 [ -c "$device" ] && [ ! -L "$device" ] || fail 'input node unsafe'
 sysdev=$(cat "$event/dev")
 case $sysdev in *[!0-9:]*|'') fail 'invalid sysfs device number';; esac
 devhex=$(stat -L -c '%t:%T' "$device")
 major=${devhex%:*}; minor=${devhex#*:}
 [ "$((0x$major)):$((0x$minor))" = "$sysdev" ] || fail 'input sysfs device mismatch'
 identity=$(stat -L -c '%d:%i:%t:%T' "$device")
 syspath=$(readlink -f "$event")
}
check_fd() {
 [ -c /proc/$$/fd/7 ] || fail 'FD is not a character device'
 [ "$(stat -L -c '%d:%i:%t:%T' /proc/$$/fd/7)" = "$identity" ] || fail 'FD identity mismatch'
 flags=$(awk '/^flags:/ {print $2}' /proc/$$/fdinfo/7)
 case $flags in ''|*[!0-7]*) fail 'invalid FD flags';; esac
 # ARM64 UAPI: O_LARGEFILE=0400000, O_CLOEXEC=02000000.
 # Access mode must remain O_RDONLY; all other flags are refused.
 [ "$((flags & ~02400000))" = 0 ] || fail 'FD must be read-only without extra flags'
}
encoded() { base64 | tr -d '\n'; }
snapshot() {
 phase=$1
 check_runtime
 original_identity=$identity original_syspath=$syspath
 discover
 [ "$identity" = "$original_identity" ] && [ "$syspath" = "$original_syspath" ] || fail 'input rebound'
 check_fd
 printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t' "$phase" "$boot" "$key" "$pid" "$start" "$identity" "$sysdev" "$unit_sha" "$syspath" >&2
 printf '%s' "$lock" | encoded >&2
 printf '\t' >&2
 encoded < /proc/interrupts >&2
 printf '\n' >&2
}
check_runtime
discover
exec 7<"$device" || fail 'cannot open input'
check_fd
[ "$(stat -f -c %T /run)" = tmpfs ] || fail 'observer scratch must remain tmpfs'
work=$(mktemp -d /run/rog5-local-key-observer.XXXXXX)
trap 'exec 7<&-; rm -f "$work/event"; rmdir "$work"' EXIT
trap 'exit 1' HUP INT TERM
snapshot PRE
if [ "$preflight" = 1 ]; then
 exec 7<&-
 printf 'PREFLIGHT\t%s\t%s\t%s\n' "$boot" "$key" "$seconds" >&2
 exit 0
fi
# Reader FD exists and the actual inhibitor has been checked before this marker.
printf 'READY\t%s\t%s\t%s\n' "$boot" "$key" "$seconds" >&2
deadline=$(( $(awk '{print int($1)}' /proc/uptime) + seconds ))
pressed=0 records=0
while :; do
 remaining=$((deadline - $(awk '{print int($1)}' /proc/uptime)))
 [ "$remaining" -gt 0 ] || fail 'monotonic event timeout'
 timeout -s TERM -k 1 "$remaining" dd bs=24 count=1 of="$work/event" <&7 2>/dev/null || fail 'event read timeout or error'
 [ "$(stat -c %s "$work/event")" = 24 ] || fail 'truncated input event'
 records=$((records + 1)); [ "$records" -le 4096 ] || fail 'event record limit'
 cat "$work/event"
 set -- $(od -An -j 16 -N 8 -t u2 "$work/event")
 [ "$#" = 4 ] || fail 'event decode error'
 [ "$1:$2" != 0:3 ] || fail 'SYN_DROPPED'
 [ "$1" = 1 ] || continue
 [ "$2" = "$code" ] && [ "$4" = 0 ] || fail 'wrong or signed key event'
 case $3:$pressed in
  1:0) pressed=1;;
  0:1) break;;
  *) fail 'unexpected key event sequence';;
 esac
done
snapshot POST
exec 7<&-
printf 'DONE\t%s\t%s\n' "$boot" "$key" >&2
