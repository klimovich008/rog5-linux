#!/bin/sh
# Offline test of the rog5-usb-reconnect / rog5-usb-sleep suspend interlock
# with a fake sysfs and stub commands (never touches the real /sys or /run).
set -eu
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
fail() { echo "FAIL $*"; [ -f "$t/kmsg" ] && sed 's/^/  kmsg: /' "$t/kmsg"; [ -f "$t/calls" ] && sed 's/^/  call: /' "$t/calls"; exit 1; }

mkdir -p "$t/bin"
# Stubs: every call is recorded; behaviour switches through files in $t.
for c in systemctl systemd-run ip; do
	cat >"$t/bin/$c" <<EOS
#!/bin/sh
echo "$c \$*" >>"$t/calls"
[ "$c" = systemd-run ] && [ -e "$t/systemd-run-fails" ] && exit 1
exit 0
EOS
done
cat >"$t/bin/pgrep" <<EOS
#!/bin/sh
[ -e "$t/sleeping" ]
EOS
# sleep returns at once; "sleep 7" is the settle, where a test can change the role.
cat >"$t/bin/sleep" <<EOS
#!/bin/sh
echo "sleep \$*" >>"$t/calls"
[ "\$1" = 7 ] && [ -e "$t/settle-role" ] && cp "$t/settle-role" "$t/sys/class/usb_role/a600000.usb-role-switch/role"
[ "\$1" = 7 ] && [ -e "$t/settle-typec" ] && cp "$t/settle-typec" "$t/sys/class/typec/port0/data_role"
[ "\$1" = 7 ] && [ -e "$t/settle-unplug" ] && rmdir "$t/sys/class/typec/port0-partner"
exit 0
EOS
chmod +x "$t/bin"/*
export PATH="$t/bin:$PATH" ROG5_USB_SYS=$t/sys ROG5_USB_RUN=$t/run ROG5_USB_KMSG=$t/kmsg
export ROG5_USB_HOST_SETTLE=7 ROG5_USB_HOST_WAIT=1 ROG5_USB_HOST_RETRY_S=35 ROG5_USB_SLEEP_SETTLE=0

reset() {
	rm -rf "$t/sys" "$t/run" "$t/kmsg" "$t/calls" "$t/sleeping" "$t/settle-role" "$t/settle-typec" "$t/settle-unplug" "$t/systemd-run-fails"
	mkdir -p "$t/run" "$t/sys/class/usb_role/a600000.usb-role-switch" "$t/sys/class/typec/port0" \
		"$t/sys/bus/platform/drivers/dwc3" "$t/sys/bus/platform/devices/a600000.usb/power" \
		"$t/sys/bus/platform/devices/a600000.usb/driver" "$t/sys/bus/platform/drivers/xhci-hcd"
	echo host >"$t/sys/class/usb_role/a600000.usb-role-switch/role"
	echo '[host] device' >"$t/sys/class/typec/port0/data_role"
	mkdir -p "$t/sys/class/typec/port0-partner"
	: >"$t/sys/bus/platform/drivers/dwc3/bind"; : >"$t/sys/bus/platform/drivers/dwc3/unbind"
	: >"$t/kmsg"; : >"$t/calls"
}
role() { cat "$t/sys/class/usb_role/a600000.usb-role-switch/role"; }
reconnect() { "$here/rog5-usb-reconnect" || true; }

# 1 A suspend in progress (marker + systemd-sleep alive): no controller
# access, and the skipped run is recorded for "post".
reset; : >"$t/run/rog5-usb-suspending"; : >"$t/sleeping"
reconnect
[ ! -s "$t/sys/bus/platform/drivers/dwc3/unbind" ] || fail 'unbound during a suspend'
[ -e "$t/run/rog5-usb-reconnect.skipped" ] || fail 'skipped run not recorded'
grep -q 'suspend in progress' "$t/kmsg" || fail 'no suspend log'

# 2 A stale marker (no systemd-sleep) is removed and ignored.
reset; : >"$t/run/rog5-usb-suspending"; mkdir -p "$t/sys/bus/platform/devices/a600000.usb/xhci-hcd.1.auto/usb1/1-1"
reconnect
[ ! -e "$t/run/rog5-usb-suspending" ] || fail 'stale marker kept'
grep -q 'stale suspend marker' "$t/kmsg" || fail 'stale marker not logged'
[ ! -s "$t/sys/bus/platform/drivers/dwc3/unbind" ] || fail 're-init although a device is enumerated'

# 3 Unplug during the settle: UCSI sets "none"; the helper must not force
# host mode, clears its retry count and schedules a fresh look.
reset; echo 2 >"$t/run/rog5-usb-reconnect.retries"; echo none >"$t/settle-role"
reconnect
grep -q a600000.usb "$t/sys/bus/platform/drivers/dwc3/unbind" || fail 'no re-init'
[ "$(role)" = none ] || fail "role forced to $(role) after an unplug in the settle"
[ ! -e "$t/run/rog5-usb-reconnect.retries" ] || fail 'retry count kept after the role change'
grep -q 'systemd-run.*--collect.*--on-active=2 ' "$t/calls" || fail 'no fresh run scheduled'

# 3b Unplug during the settle, UCSI keeps "[host]" but the partner is gone:
# no host either.
reset; echo device >"$t/settle-role"; : >"$t/settle-unplug"
reconnect
[ "$(role)" = device ] || fail "role $(role) after an unplug that kept the data role"
grep -q 'no longer a USB device' "$t/kmsg" || fail 'partner loss not logged'

# 4 A PC during the settle: UCSI sets "device" and the Type-C data role is
# device: stay in device mode.
reset; echo device >"$t/settle-role"; echo 'host [device]' >"$t/settle-typec"
reconnect
[ "$(role)" = device ] || fail "role $(role) with a PC attached"
grep -q 'no longer a USB device' "$t/kmsg" || fail 'PC case not logged'

# 5 Settle survives: back to host; nothing enumerates; the retry is
# scheduled with a unique, collected unit and counted only if scheduled.
reset
reconnect
[ "$(role)" = host ] || fail "role $(role) after the settle"
[ "$(cat "$t/run/rog5-usb-reconnect.retries")" = 1 ] || fail 'retry not counted'
grep -q 'systemd-run.*--collect.*RemainAfterElapse=no.*--on-active=35 --unit=rog5-usb-reconnect-retry-[0-9]*-[0-9]* ' "$t/calls" || fail 'retry unit'
[ "$(cat "$t/sys/bus/platform/devices/a600000.usb/power/control")" = auto ] || fail 'runtime PM not restored'

# 6 Scheduling fails: the count is not advanced and the failure is logged.
reset; : >"$t/systemd-run-fails"
reconnect
[ ! -e "$t/run/rog5-usb-reconnect.retries" ] || fail 'retry counted although not scheduled'
grep -q 'FAIL could not schedule' "$t/kmsg" || fail 'scheduling failure not logged'

# 7 Lock busy during a suspend: the dropped event is recorded.
reset; : >"$t/run/rog5-usb-suspending"
flock "$t/run/rog5-usb-reconnect.lock" sh -c "\"$here/rog5-usb-reconnect\"" || true
[ -e "$t/run/rog5-usb-reconnect.skipped" ] || fail 'busy lock during suspend not recorded'

# 8 A bind failure after the unbind: the EXIT trap tries to bind again.
reset; rm "$t/sys/bus/platform/drivers/dwc3/bind"; mkdir "$t/sys/bus/platform/drivers/dwc3/bind"
rmdir "$t/sys/bus/platform/devices/a600000.usb/driver"
reconnect 2>/dev/null
grep -q 'FAIL bind' "$t/kmsg" && grep -q 'FAIL could not bind a600000.usb again' "$t/kmsg" || fail 'no rebind attempt on exit'

# 9 Sleep hook "pre": waits for a reconnect run holding the lock, marks the
# suspend; "post" clears the marker and starts a skipped run.
reset
( flock "$t/run/rog5-usb-reconnect.lock" /bin/sleep 2 ) & holder=$!
/bin/sleep 0.3
start=$(date +%s)
"$here/rog5-usb-sleep" pre
[ $(( $(date +%s) - start )) -ge 1 ] || fail 'pre did not wait for the lock'
wait $holder
[ -e "$t/run/rog5-usb-suspending" ] || fail 'no suspend marker'
: >"$t/run/rog5-usb-reconnect.skipped"
"$here/rog5-usb-sleep" post
[ ! -e "$t/run/rog5-usb-suspending" ] || fail 'marker left after post'
grep -q 'systemctl --no-block start rog5-usb-reconnect.service' "$t/calls" || fail 'skipped run not started'
: >"$t/calls"; "$here/rog5-usb-sleep" pre; "$here/rog5-usb-sleep" post
! grep -q 'start rog5-usb-reconnect' "$t/calls" || fail 'reconnect started without a skipped run'

# 10 "pre" with a run that does not finish: stopped, controller bound again.
reset; rmdir "$t/sys/bus/platform/devices/a600000.usb/driver"
( flock "$t/run/rog5-usb-reconnect.lock" /bin/sleep 3 ) & holder=$!
/bin/sleep 0.3
ROG5_USB_SLEEP_LOCK_WAIT=1 "$here/rog5-usb-sleep" pre || true
grep -q 'systemctl kill --signal=TERM rog5-usb-reconnect.service' "$t/calls" || fail 'stuck run not stopped'
grep -q a600000.usb "$t/sys/bus/platform/drivers/dwc3/bind" || fail 'controller not bound again'
[ -e "$t/run/rog5-usb-reconnect.skipped" ] || fail 'stopped run not marked for replay'
wait $holder

# 11 A run that holds on past the kill: no unlocked recovery.
reset; rmdir "$t/sys/bus/platform/devices/a600000.usb/driver"
( flock "$t/run/rog5-usb-reconnect.lock" /bin/sleep 14 ) & holder=$!
/bin/sleep 0.3
ROG5_USB_SLEEP_LOCK_WAIT=1 "$here/rog5-usb-sleep" pre || true
grep -q 'FAIL reconnect lock still held' "$t/kmsg" || fail 'held lock not reported'
! grep -q a600000.usb "$t/sys/bus/platform/drivers/dwc3/bind" || fail 'bound without the lock'
kill $holder 2>/dev/null; wait $holder 2>/dev/null || true

# 12 rog5-usb-bottom status in stage B: Type-C port, 5 V and the RT1715
# ALERT interrupt count summed over the CPUs; "on" is refused.
reset
b=$t/sys/devices/platform/soc@0/a8f8800.usb/a800000.usb/xhci-hcd.2.auto
mkdir -p "$b/usb1" "$t/dt/soc@0/geniqup@ac0000/i2c@a94000/typec@4e" "$t/sys/class/typec/port1" \
	"$t/sys/devices/a94000.i2c/i2c-2/2-004e" "$t/sys/class/regulator/regulator.40" "$t/proc"
ln -s "$t/sys/devices/a94000.i2c/i2c-2/2-004e" "$t/sys/class/typec/port1/device"
echo '[source]' >"$t/sys/class/typec/port1/power_role"; echo '[host]' >"$t/sys/class/typec/port1/data_role"
echo btm_vbus >"$t/sys/class/regulator/regulator.40/name"; echo disabled >"$t/sys/class/regulator/regulator.40/state"
printf '%s\n' '           CPU0       CPU1' \
	' 188:        161          0  msmgpio  23 Edge      4-0038' \
	' 195:          3          2  msmgpio 118 Level     2-004e' >"$t/proc/interrupts"
out=$(ROG5_USB_DT=$t/dt ROG5_USB_PROC=$t/proc "$here/rog5-usb-bottom" status)
echo "$out" | grep -qx 'typec=port1 power_role=\[source\] data_role=\[host\] partner=none' || fail "stage-B typec line: $out"
echo "$out" | grep -qx '5V=disabled' || fail "stage-B 5V line: $out"
echo "$out" | grep -qx 'alert_irqs=5' || fail "stage-B alert count: $out"
: >"$t/proc/interrupts"
ROG5_USB_DT=$t/dt ROG5_USB_PROC=$t/proc "$here/rog5-usb-bottom" status | grep -qx 'alert_irqs=missing' || fail 'no missing ALERT interrupt report'
! ROG5_USB_DT=$t/dt "$here/rog5-usb-bottom" on 2>/dev/null || fail 'stage B accepted "on"'

echo PASS rog5-usb-reconnect / rog5-usb-sleep / rog5-usb-bottom
