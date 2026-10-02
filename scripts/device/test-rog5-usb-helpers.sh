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
# systemctl list-jobs: the queued jobs of the test ("jobs-fail": no bus).
if [ "$c" = systemctl ] && [ "\$1" = list-jobs ]; then
	[ -e "$t/jobs-fail" ] && exit 1
	cat "$t/jobs" 2>/dev/null
fi
exit 0
EOS
done
# dmesg: the kernel log of the test (pmic_glink_altmode notifications).
cat >"$t/bin/dmesg" <<EOS
#!/bin/sh
cat "$t/dmesg" 2>/dev/null
EOS
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
# "flip-host" (or "flip-at" N): UCSI switches the port to host during the
# first (Nth) 1 s wait.
if [ "\$1" = 1 ] && [ -e "$t/flip-at" ]; then
	n=\$((\$(cat "$t/flip-at") - 1)); echo \$n >"$t/flip-at"
	[ \$n = 0 ] && { rm "$t/flip-at"; : >"$t/flip-host"; }
fi
if [ "\$1" = 1 ] && [ -e "$t/flip-host" ]; then
	rm "$t/flip-host"
	echo host >"$t/sys/class/usb_role/a600000.usb-role-switch/role"
	echo '[host] device' >"$t/sys/class/typec/port0/data_role"
fi
# "lit-at" N: the compositor's first modeset lights the DP connector at the
# Nth 1 s wait.
if [ "\$1" = 1 ] && [ -e "$t/lit-at" ]; then
	n=\$((\$(cat "$t/lit-at") - 1)); echo \$n >"$t/lit-at"
	[ \$n = 0 ] && { rm "$t/lit-at"; mkdir -p "$t/sys/class/drm/card1-DP-1"; echo connected >"$t/sys/class/drm/card1-DP-1/status"; }
fi
# "hub-after-hpd": the monitor's hub enumerates on its own after HPD.
[ "\$1" = 2 ] && [ -e "$t/hub-after-hpd" ] && mkdir -p "$t/sys/bus/platform/devices/a600000.usb/xhci-hcd.1.auto/usb3/3-1"
# The Type-C data_role file plays the kernel: a raw "device" write is the
# UCSI request ("kick-result": the role afterwards, default rejected;
# "kick-dp": the ADSP enters DP), a raw "host" the swap back.
dr=$t/sys/class/typec/port0/data_role
case \$(cat "\$dr" 2>/dev/null) in
device)
	echo kick >>"$t/calls"
	if [ -e "$t/kick-result" ]; then cp "$t/kick-result" "\$dr"; else echo '[host] device' >"\$dr"; fi
	[ -e "$t/kick-dp" ] && { mkdir -p "$t/sys/class/drm/card1-DP-1"; echo connected >"$t/sys/class/drm/card1-DP-1/status"; }
	[ -e "$t/kick-suspend" ] && { : >"$t/run/rog5-usb-suspending"; : >"$t/sleeping"; } ;;
host)
	echo swap-back >>"$t/calls"; echo '[host] device' >"\$dr" ;;
esac
# "event-during": a udev event (pending marker) arrives while the run waits.
if [ -e "$t/event-during" ]; then
	rm "$t/event-during"
	: >"$t/run/rog5-usb-reconnect.pending"
	[ -e "$t/event-suspend" ] && { : >"$t/run/rog5-usb-suspending"; : >"$t/sleeping"; }
fi
exit 0
EOS
chmod +x "$t/bin"/*
export PATH="$t/bin:$PATH" ROG5_USB_SYS=$t/sys ROG5_USB_RUN=$t/run ROG5_USB_KMSG=$t/kmsg
export ROG5_USB_HOST_SETTLE=7 ROG5_USB_HOST_WAIT=1 ROG5_USB_HOST_RETRY_S=35 ROG5_USB_SLEEP_SETTLE=0 ROG5_USB_DP_WAIT=3 ROG5_USB_DP_LIT_WAIT=6

reset() {
	rm -rf "$t/sys" "$t/run" "$t/kmsg" "$t/calls" "$t/sleeping" "$t/settle-role" "$t/settle-typec" "$t/settle-unplug" "$t/systemd-run-fails" \
		"$t/flip-host" "$t/flip-at" "$t/event-during" "$t/event-suspend" "$t/kick-result" "$t/kick-dp" \
		"$t/kick-suspend" "$t/hub-after-hpd" "$t/dmesg" "$t/lit-at" "$t/jobs" "$t/jobs-fail"
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

# 2b The admission ran (marker) and the suspend job is queued, but
# systemd-sleep has not started yet: the marker is live.
reset; : >"$t/run/rog5-usb-suspending"; printf '%s\n' '4711 systemd-suspend.service start waiting' '4710 suspend.target start waiting' >"$t/jobs"
reconnect
[ -e "$t/run/rog5-usb-suspending" ] || fail 'marker of a queued suspend removed'
[ -e "$t/run/rog5-usb-reconnect.skipped" ] || fail 'run skipped for a queued suspend not recorded'
[ ! -s "$t/sys/bus/platform/drivers/dwc3/unbind" ] || fail 'unbound while a suspend was queued'
# ... another job does not keep a marker alive (hybrid sleep and
# suspend-then-hibernate are disabled by sleep.conf.d/50-rog5.conf)
reset; : >"$t/run/rog5-usb-suspending"; echo '12 systemd-suspend-then-hibernate.service start waiting' >"$t/jobs"; mkdir -p "$t/sys/bus/platform/devices/a600000.usb/xhci-hcd.1.auto/usb1/1-1"
reconnect
[ ! -e "$t/run/rog5-usb-suspending" ] || fail 'marker kept for an unrelated job'
# ... and an unreadable job list counts as a live suspend
reset; : >"$t/run/rog5-usb-suspending"; : >"$t/jobs-fail"
reconnect
[ -e "$t/run/rog5-usb-suspending" ] || fail 'marker removed although the job list was unreadable'
[ ! -s "$t/sys/bus/platform/drivers/dwc3/unbind" ] || fail 'unbound with an unreadable job list'

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
grep -q 'systemd-run.*--collect.*RemainAfterElapse=no.*--on-active=35 --unit=rog5-usb-reconnect-retry-[0-9]*-[0-9]*-[0-9]* ' "$t/calls" || fail 'retry unit'
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

# 11b Admission (rog5-usb-suspend-admit.service): lock free -> admitted,
# marker set, an old skipped record dropped, no controller access, no kill.
reset; : >"$t/run/rog5-usb-reconnect.skipped"
"$here/rog5-usb-sleep" admit || fail 'admission refused with a free lock'
[ -e "$t/run/rog5-usb-suspending" ] || fail 'admission did not mark the suspend'
[ ! -e "$t/run/rog5-usb-reconnect.skipped" ] || fail 'old skipped record kept by the admission'
! grep -q 'systemctl kill' "$t/calls" || fail 'admission stopped a reconnect run'
# ... then pre/post as before: post clears the marker
"$here/rog5-usb-sleep" pre; "$here/rog5-usb-sleep" post
[ ! -e "$t/run/rog5-usb-suspending" ] || fail 'marker left after admit/pre/post'

# 11b2 A run that read the job list before the suspend was queued removes
# the admission's marker as stale while admit waits: admit restores it under
# the lock before it admits the suspend.
reset
( flock "$t/run/rog5-usb-reconnect.lock" sh -c "/bin/sleep 0.6; rm -f '$t/run/rog5-usb-suspending'; /bin/sleep 0.5" ) & holder=$!
/bin/sleep 0.3
ROG5_USB_SLEEP_LOCK_WAIT=5 "$here/rog5-usb-sleep" admit || fail 'admission refused after a stale-marker race'
wait $holder
[ -e "$t/run/rog5-usb-suspending" ] || fail 'admission succeeded without its marker'

# 11c Admission waits for a run that finishes within the wait.
reset
( flock "$t/run/rog5-usb-reconnect.lock" /bin/sleep 2 ) & holder=$!
/bin/sleep 0.3
start=$(date +%s)
ROG5_USB_SLEEP_LOCK_WAIT=5 "$here/rog5-usb-sleep" admit || fail 'admission refused although the run finished in time'
[ $(( $(date +%s) - start )) -ge 1 ] || fail 'admission did not wait for the lock'
wait $holder

# 11d Admission with a run that keeps the lock: refused (non-zero, so
# systemd-suspend.service fails its dependency), marker removed, the run is
# neither killed nor its controller touched, a skipped event is replayed.
reset; rmdir "$t/sys/bus/platform/devices/a600000.usb/driver"
( flock "$t/run/rog5-usb-reconnect.lock" /bin/sleep 3 ) & holder=$!
/bin/sleep 0.3
if ROG5_USB_SLEEP_LOCK_WAIT=1 "$here/rog5-usb-sleep" admit; then fail 'admission granted with the lock held'; fi
[ ! -e "$t/run/rog5-usb-suspending" ] || fail 'marker left after a refused admission'
grep -q 'FAIL rog5-usb-reconnect still running after 1s; refusing suspend' "$t/kmsg" || fail 'refusal not logged'
! grep -q 'systemctl kill' "$t/calls" || fail 'refused admission killed the reconnect run'
[ ! -s "$t/sys/bus/platform/drivers/dwc3/bind" ] && [ ! -s "$t/sys/bus/platform/drivers/dwc3/unbind" ] || fail 'refused admission touched dwc3'
wait $holder
reset
( flock "$t/run/rog5-usb-reconnect.lock" sh -c "/bin/sleep 0.6; : >'$t/run/rog5-usb-reconnect.skipped'; /bin/sleep 2.4" ) & holder=$!
/bin/sleep 0.3
ROG5_USB_SLEEP_LOCK_WAIT=1 "$here/rog5-usb-sleep" admit && fail 'admission granted with the lock held (skipped case)'
grep -q 'systemctl --no-block start rog5-usb-reconnect.service' "$t/calls" || fail 'skipped event not replayed after a refused admission'
[ ! -e "$t/run/rog5-usb-reconnect.skipped" ] || fail 'skipped record kept after its replay'
wait $holder

# 11e Units: the suspend job requires and follows the admission, which runs
# the installed hook, reruns every time and cleans the marker on failure.
units=$here/../../configs/systemd
dropin=$units/systemd-suspend.service.d/50-rog5-usb.conf
grep -qx 'Requires=rog5-usb-suspend-admit.service' "$dropin" && grep -qx 'After=rog5-usb-suspend-admit.service' "$dropin" || fail 'suspend drop-in'
admit_unit=$units/rog5-usb-suspend-admit.service
grep -qx 'ExecStart=/usr/lib/systemd/system-sleep/rog5-usb-sleep admit' "$admit_unit" || fail 'admission ExecStart'
grep -qx 'Type=oneshot' "$admit_unit" && ! grep -q "^RemainAfterExit" "$admit_unit" || fail 'admission must rerun on every suspend'
grep -qF "\"\$\$SERVICE_RESULT\" = success ] || rm -f /run/rog5-usb-suspending" "$admit_unit" || fail 'admission cleanup'
sleepconf=$units/sleep.conf.d/50-rog5.conf
for k in AllowHibernation=no AllowSuspendThenHibernate=no AllowHybridSleep=no MemorySleepMode=s2idle; do
	grep -qx "$k" "$sleepconf" || fail "sleep.conf.d: no $k"
done
manifest=$here/../../configs/rootfs/userspace.tsv
for row in 'scripts/device/rog5-usb-sleep	/usr/lib/systemd/system-sleep/rog5-usb-sleep' \
	'configs/systemd/rog5-usb-suspend-admit.service	/etc/systemd/system/rog5-usb-suspend-admit.service' \
	'configs/systemd/systemd-suspend.service.d/50-rog5-usb.conf	/etc/systemd/system/systemd-suspend.service.d/50-rog5-usb.conf' \
	'configs/systemd/sleep.conf.d/50-rog5.conf	/etc/systemd/sleep.conf.d/50-rog5.conf'; do
	grep -qF "$row" "$manifest" || fail "not installed: $row"
done

# 12a The 19:00 monitor (2026-09-30): the supply reports SDP first, the
# run waits for the gadget, UCSI switches the port to host a second later
# (that role event is merged into the running job). The run itself must
# follow the switch and re-initialise in host mode.
reset
unbind=$t/sys/bus/platform/drivers/dwc3/unbind
echo device >"$t/sys/class/usb_role/a600000.usb-role-switch/role"
echo 'host [device]' >"$t/sys/class/typec/port0/data_role"
mkdir -p "$t/sys/class/power_supply/qcom-battmgr-usb" "$t/sys/class/udc/a600000.usb"
echo 1 >"$t/sys/class/power_supply/qcom-battmgr-usb/online"
echo 'Unknown [SDP] DCP CDP' >"$t/sys/class/power_supply/qcom-battmgr-usb/usb_type"
echo default >"$t/sys/class/udc/a600000.usb/state"
: >"$t/flip-host"
reconnect
grep -q 'port mode changed while waiting' "$t/kmsg" || fail 'mode change not followed'
grep -q 'host mode, nothing enumerated' "$t/kmsg" || fail 'no host-mode re-init after the switch'
grep -q a600000.usb "$unbind" || fail 'controller not re-initialised'
[ "$(role)" = host ] || fail "role $(role) after the host-mode re-init"
! grep -q 'gadget still' "$t/kmsg" || fail 'gadget re-init in host mode'

# 12b An event during a run is replayed once after it; one before the run
# is covered by the run itself.
reset; cut -d. -f1 /proc/uptime >"$t/run/rog5-usb-reconnect.host"; : >"$t/event-during"
reconnect
[ ! -s "$unbind" ] || fail 'rate limit ignored'
[ ! -e "$t/run/rog5-usb-reconnect.pending" ] || fail 'pending marker kept'
grep -q 'systemd-run.*--on-active=2 ' "$t/calls" || fail 'event during the run not replayed'
reset; cut -d. -f1 /proc/uptime >"$t/run/rog5-usb-reconnect.host"; : >"$t/run/rog5-usb-reconnect.pending"
reconnect
[ ! -e "$t/run/rog5-usb-reconnect.pending" ] || fail 'pending marker kept (event before the run)'
! grep -q systemd-run "$t/calls" || fail 'replayed an event the run already covered'
# ... but during a suspend "post" replays it instead.
reset; cut -d. -f1 /proc/uptime >"$t/run/rog5-usb-reconnect.host"; : >"$t/event-during"; : >"$t/event-suspend"
reconnect
! grep -q systemd-run "$t/calls" || fail 'replay scheduled during a suspend'
[ -e "$t/run/rog5-usb-reconnect.skipped" ] || fail 'event during a suspend not handed to post'

# 12c Retries used up: give up (recording the DP state); later events
# without a new DP sink leave the controller alone; a DP sink that
# connected since arms one more cycle; giving up with DP connected stays.
reset; echo 3 >"$t/run/rog5-usb-reconnect.retries"
reconnect
grep -q 'giving up' "$t/kmsg" || fail 'no give-up log'
[ "$(cat "$t/run/rog5-usb-reconnect.gaveup")" = nodp ] || fail 'give-up state'
[ ! -e "$t/run/rog5-usb-reconnect.retries" ] || fail 'retry count kept after giving up'
rm -f "$t/run/rog5-usb-reconnect.host"; : >"$unbind"
reconnect
[ ! -s "$unbind" ] || fail 're-init on an empty port after giving up'
mkdir -p "$t/sys/class/drm/card1-DP-1"; echo connected >"$t/sys/class/drm/card1-DP-1/status"
rm -f "$t/run/rog5-usb-reconnect.host"
reconnect
grep -q 'DP sink connected since the last attempt' "$t/kmsg" || fail 'DP connect did not re-arm'
grep -q a600000.usb "$unbind" || fail 'no re-init after a DP sink connected'
[ "$(cat "$t/run/rog5-usb-reconnect.retries")" = 1 ] || fail 'new cycle not counted from 1'
[ ! -e "$t/run/rog5-usb-reconnect.gaveup" ] || fail 'give-up marker kept after re-arming'
echo dp >"$t/run/rog5-usb-reconnect.gaveup"; rm -f "$t/run/rog5-usb-reconnect.retries" "$t/run/rog5-usb-reconnect.host"; : >"$unbind"
reconnect
[ ! -s "$unbind" ] || fail 're-init although DP was already connected when giving up'

# 12d A DP sink connecting inside the 30 s rate limit after giving up gets a
# run scheduled for when the limit has passed.
reset; echo nodp >"$t/run/rog5-usb-reconnect.gaveup"
mkdir -p "$t/sys/class/drm/card1-DP-1"; echo connected >"$t/sys/class/drm/card1-DP-1/status"
cut -d. -f1 /proc/uptime >"$t/run/rog5-usb-reconnect.host"
reconnect
[ ! -s "$unbind" ] || fail 'rate limit ignored after DP connect'
grep -q 'systemd-run.*--on-active=3[01] ' "$t/calls" || fail 'no run after the rate limit'

# 12e A device that enumerates, or leaving host mode, clears the give-up.
reset; echo nodp >"$t/run/rog5-usb-reconnect.gaveup"; mkdir -p "$t/sys/bus/platform/devices/a600000.usb/xhci-hcd.1.auto/usb3/3-1"
reconnect
[ ! -e "$t/run/rog5-usb-reconnect.gaveup" ] || fail 'give-up kept with a device enumerated'
reset; echo nodp >"$t/run/rog5-usb-reconnect.gaveup"; echo none >"$t/sys/class/usb_role/a600000.usb-role-switch/role"; rm -r "$t/sys/class/typec/port0-partner"
reconnect
[ ! -e "$t/run/rog5-usb-reconnect.gaveup" ] || fail 'give-up kept after leaving host mode'

# 12f Replays in a row are bounded: after $max_replays the chain stops
# (and the count is cleared); a run without an event clears the count.
reset; cut -d. -f1 /proc/uptime >"$t/run/rog5-usb-reconnect.host"; echo 3 >"$t/run/rog5-usb-reconnect.replays"; : >"$t/event-during"
reconnect
! grep -q systemd-run "$t/calls" || fail 'replay chain not bounded'
grep -q 'not replaying after 3 replays' "$t/kmsg" || fail 'bounded replay not logged'
[ ! -e "$t/run/rog5-usb-reconnect.replays" ] || fail 'replay count kept after stopping the chain'
reset; cut -d. -f1 /proc/uptime >"$t/run/rog5-usb-reconnect.host"; echo 1 >"$t/run/rog5-usb-reconnect.replays"; : >"$t/event-during"
reconnect
[ "$(cat "$t/run/rog5-usb-reconnect.replays")" = 2 ] || fail 'replay not counted'
reconnect
[ ! -e "$t/run/rog5-usb-reconnect.replays" ] || fail 'replay count kept by a run without events'

# 12g udev: supply and DRM hotplug (DP HPD) events set the pending marker
# before starting a run; role events (caused by the re-init itself) don't.
rules=$here/../../configs/udev/90-rog5-usb-reconnect.rules
for k in power_supply drm typec; do
	grep "SUBSYSTEM==\"$k\"" "$rules" | grep -q 'touch /run/rog5-usb-reconnect.pending", RUN+="/usr/bin/systemctl --no-block start rog5-usb-reconnect.service"' ||
		fail "no pending marker before the start on $k events"
done
grep -q 'SUBSYSTEM=="drm", KERNEL=="card\[0-9\]\*", ACTION=="change", ENV{HOTPLUG}=="1"' "$rules" || fail 'no DRM hotplug trigger'
grep 'SUBSYSTEM=="usb_role"' "$rules" | grep -q 'start rog5-usb-reconnect.service' || fail 'no role trigger'
grep -q 'SUBSYSTEM=="typec", KERNEL=="port0-partner", ACTION=="add"' "$rules" || fail 'no partner-attach (boot) trigger'
! grep 'SUBSYSTEM=="usb_role"' "$rules" | grep -q pending || fail 'role events replayed (self-inflicted by the re-init)'

# 12h Retry and EXIT replay in one run: distinct timer units.
reset; : >"$t/event-during"
reconnect
[ "$(grep -c 'systemd-run' "$t/calls")" = 2 ] || fail 'retry and replay not both scheduled'
[ "$(grep -o -- '--unit=[^ ]*' "$t/calls" | sort -u | wc -l)" = 2 ] || fail 'timer unit names collide'

# 12i A DP disconnect seen inside the rate limit is recorded, so that the
# next connect re-arms.
reset; echo dp >"$t/run/rog5-usb-reconnect.gaveup"; cut -d. -f1 /proc/uptime >"$t/run/rog5-usb-reconnect.host"
reconnect
[ "$(cat "$t/run/rog5-usb-reconnect.gaveup")" = nodp ] || fail 'DP disconnect not recorded while rate-limited'

# 12j Gadget re-init, then UCSI switches to host while waiting for the
# gadget: follow it into host mode.
reset
echo device >"$t/sys/class/usb_role/a600000.usb-role-switch/role"
echo 'host [device]' >"$t/sys/class/typec/port0/data_role"
mkdir -p "$t/sys/class/power_supply/qcom-battmgr-usb" "$t/sys/class/udc/a600000.usb"
echo 1 >"$t/sys/class/power_supply/qcom-battmgr-usb/online"
echo 'Unknown [SDP] DCP CDP' >"$t/sys/class/power_supply/qcom-battmgr-usb/usb_type"
echo default >"$t/sys/class/udc/a600000.usb/state"
mkdir -p "$t/sys/kernel/config/usb_gadget/rog5-persistent-root"; echo a600000.usb >"$t/sys/kernel/config/usb_gadget/rog5-persistent-root/UDC"
echo 9 >"$t/flip-at"
reconnect
grep -q 'gadget still default' "$t/kmsg" || fail 'no gadget re-init first'
grep -q 'port mode changed while waiting' "$t/kmsg" || fail 'host switch after the gadget re-init not followed'
grep -q 'host mode, nothing enumerated' "$t/kmsg" || fail 'no host-mode pass after the gadget re-init'

# 13 DP discovery kick (boot race, r206): host port, PD partner powering
# the phone, no DP sink and nothing enumerated after the DP wait: one
# "device" data-role request, DP comes up, then the usual re-init.
kick_setup() {
	reset
	echo yes >"$t/sys/class/typec/port0-partner/supports_usb_power_delivery"
	echo 'source [sink]' >"$t/sys/class/typec/port0/power_role"
}
kick_setup; : >"$t/kick-dp"
reconnect
[ "$(grep -c '^kick' "$t/calls")" = 1 ] || fail 'no single DP kick'
grep -q 'kick 1/2' "$t/kmsg" && grep -q 'DP sink up' "$t/kmsg" || fail 'kick not logged'
grep -q a600000.usb "$unbind" || fail 'no re-init after the kick'
[ "$(cat "$t/run/rog5-usb-reconnect.kicks")" = 1 ] || fail 'kick not counted'
! grep -q swap-back "$t/calls" || fail 'swapped back after a rejected request'
# budget used up: no more kicks, the re-init still runs
kick_setup; echo 2 >"$t/run/rog5-usb-reconnect.kicks"
reconnect
! grep -q '^kick' "$t/calls" || fail 'kick beyond the budget'
grep -q a600000.usb "$unbind" || fail 'no re-init without a kick'
# a partner that accepts the swap is switched back to host
kick_setup; echo 'host [device]' >"$t/kick-result"
reconnect
grep -q swap-back "$t/calls" && grep -q 'switching back to host' "$t/kmsg" || fail 'accepted swap not reverted'
grep -q 'no DP sink 3s after the kick' "$t/kmsg" || fail 'missing DP after the kick not logged'
# no kick: phone is the source, DP already up, or a suspend starts
kick_setup; echo '[source] sink' >"$t/sys/class/typec/port0/power_role"
reconnect
! grep -q '^kick' "$t/calls" || fail 'kick with the phone as the source'
kick_setup; mkdir -p "$t/sys/class/drm/card1-DP-1"; echo connected >"$t/sys/class/drm/card1-DP-1/status"
reconnect
! grep -q '^kick' "$t/calls" || fail 'kick with DP up'
kick_setup; : >"$t/event-during"; : >"$t/event-suspend"
reconnect
! grep -q '^kick' "$t/calls" || fail 'kick during a suspend'
[ ! -s "$unbind" ] || fail 're-init during a suspend'
# a suspend that begins during the kick's waits: no re-init
kick_setup; : >"$t/kick-dp"; : >"$t/kick-suspend"
reconnect
grep -q '^kick' "$t/calls" || fail 'no kick before the suspend'
[ ! -s "$unbind" ] || fail 're-init after a suspend began during the kick'
# a hub that enumerates on its own after HPD is left alone
kick_setup; : >"$t/kick-dp"; : >"$t/hub-after-hpd"
reconnect
[ ! -s "$unbind" ] || fail 'working hub re-initialised after the kick'
# r207 boot: the ADSP entered DP alt mode (pin_assignment=3 hpd=1) before
# the compositor's first modeset lit the connector: no kick; wait for the
# connector, then the usual re-init.
an='pmic_glink_altmode.pmic_glink_altmode pmic_glink.altmode.0: DP port=0'
kick_setup
printf '[   25.31] %s pin_assignment=0 mux_ctrl=0 orientation=2 hpd=0 irq=0\n[   25.32] %s pin_assignment=3 mux_ctrl=2 orientation=0 hpd=1 irq=0\n' "$an" "$an" >"$t/dmesg"
echo 4 >"$t/lit-at"
reconnect
! grep -q '^kick' "$t/calls" || fail 'kick although the ADSP was in DP alt mode'
grep -q a600000.usb "$unbind" || fail 'no re-init once the connector lit'
! grep -q 'no kick' "$t/kmsg" || fail 'connector lit, but reported as missing'
# ... and when the connector does not light within the wait: still no kick
kick_setup
printf '[   25.32] %s pin_assignment=3 mux_ctrl=2 orientation=0 hpd=1 irq=0\n' "$an" >"$t/dmesg"
reconnect
! grep -q '^kick' "$t/calls" || fail 'kick although the ADSP was in DP alt mode (connector dark)'
grep -q 'DP alt mode entered (pin_assignment/hpd 3 1) but no DP connector after 6s; no kick' "$t/kmsg" || fail 'dark connector not logged'
grep -q a600000.usb "$unbind" || fail 'no re-init with a dark connector'
[ "$(grep -c 'sleep 1' "$t/calls")" -ge 5 ] || fail 'display stack not given the longer wait'
# 2026-10-01: an HDMI adapter (pin_assignment=4) with nothing on its HDMI
# (hpd=0): no kick and no display wait; the re-init follows as soon as
# for a partner the phone powers (same number of waits).
kick_setup; echo '[source] sink' >"$t/sys/class/typec/port0/power_role"
reconnect
base=$(grep -c 'sleep 1' "$t/calls")
kick_setup
printf '[   48.10] %s pin_assignment=4 mux_ctrl=3 orientation=1 hpd=0 irq=0\n' "$an" >"$t/dmesg"
reconnect
! grep -q '^kick' "$t/calls" || fail 'kick behind a sinkless DP adapter'
grep -q 'DP alt mode entered without a sink (pin_assignment/hpd 4 0); no kick, no display wait' "$t/kmsg" || fail 'sinkless adapter not logged'
grep -q a600000.usb "$unbind" || fail 'no re-init behind a sinkless DP adapter'
[ "$(grep -c 'sleep 1' "$t/calls")" = "$base" ] || fail "waited for a display behind a sinkless adapter ($(grep -c 'sleep 1' "$t/calls") vs $base waits)"
# r206 boot: only pin_assignment=0 (or DP left after an unplug): kick
kick_setup
printf '[   25.01] %s pin_assignment=3 mux_ctrl=2 orientation=0 hpd=1 irq=0\n[   26.00] %s pin_assignment=0 mux_ctrl=0 orientation=2 hpd=0 irq=0\n' "$an" "$an" >"$t/dmesg"
reconnect
[ "$(grep -c '^kick' "$t/calls")" = 1 ] || fail 'no kick without DP alt mode'
grep -q 'last notification: 0 0' "$t/kmsg" || fail 'last notification not logged'
# leaving host mode clears the budget
kick_setup; echo 2 >"$t/run/rog5-usb-reconnect.kicks"; echo none >"$t/sys/class/usb_role/a600000.usb-role-switch/role"; rm -r "$t/sys/class/typec/port0-partner"
reconnect
[ ! -e "$t/run/rog5-usb-reconnect.kicks" ] || fail 'kick budget kept after leaving host mode'

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
