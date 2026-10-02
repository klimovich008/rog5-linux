#!/bin/sh
# Offline test of rog5-sleep-policy --once decisions with a fake sysfs.
set -eu
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ROG5_SLEEP_WIFI_PS=0 ROG5_SLEEP_MODE=suspend ROG5_SLEEP_USB=$t/usb ROG5_SLEEP_DPMS=$t/dpms ROG5_SLEEP_STAY=$t/stay ROG5_SLEEP_USB_DEVICES=$t/usbdev ROG5_SLEEP_SSH_BLOCKS=0 ROG5_SLEEP_KMSG=/dev/null ROG5_SLEEP_EXT_DISPLAYS=$t/dp \
	ROG5_SLEEP_SUPPLIES=$t/supply ROG5_SLEEP_CHG_BEHAVIOUR=$t/chg ROG5_SLEEP_TYPEC=$t/typec ROG5_SLEEP_ASOUND=$t/asound \
	ROG5_SLEEP_INHIBITORS_CMD="cat $t/inhibitors"
echo 'a(ssssuu) 0' >$t/inhibitors
check() { got=$("$here/rog5-sleep-policy" --once); [ "$got" = "$1" ] || { echo "FAIL expected $1 got $got ($2)"; exit 1; }; }
echo 1 >$t/usb; echo Off >$t/dpms; check usb-power 'plugged in, screen off'
echo 0 >$t/usb; echo On >$t/dpms; check screen-on 'battery, screen on'
echo Off >$t/dpms; check sleep-eligible 'battery, screen off'

# External power beyond qcom-battmgr-usb/online.
mkdir -p $t/supply/qcom-battmgr-bat $t/supply/ucsi-source-psy-pmic_glink.ucsi.01 $t/typec/port0
echo Battery >$t/supply/qcom-battmgr-bat/type; echo 1 >$t/supply/qcom-battmgr-bat/online
echo USB >$t/supply/ucsi-source-psy-pmic_glink.ucsi.01/type; echo 0 >$t/supply/ucsi-source-psy-pmic_glink.ucsi.01/online
check sleep-eligible 'battery online=1 is not external power; UCSI offline'
echo 1 >$t/supply/ucsi-source-psy-pmic_glink.ucsi.01/online
check external-power:ucsi-source-psy-pmic_glink.ucsi.01 'UCSI: the partner sources VBUS'
echo 0 >$t/supply/ucsi-source-psy-pmic_glink.ucsi.01/online
echo '[auto] inhibit-charge force-discharge' >$t/chg; check sleep-eligible 'charge_behaviour auto'
echo 'auto inhibit-charge [force-discharge]' >$t/chg
check sleep-eligible 'force-discharge left over, no Type-C partner: on battery'
mkdir -p $t/typec/port0-partner $t/typec/port1 $t/typec/port1-partner
echo '[source] sink' >$t/typec/port0/power_role; echo '[source] sink' >$t/typec/port1/power_role
check sleep-eligible 'force-discharge left over, partners that the phone powers (disk): on battery'
echo 'source [sink]' >$t/typec/port0/power_role
check usb-power-suspended 'force-discharge with the charger attached (battmgr-usb online 0)'
echo 'auto [inhibit-charge] force-discharge' >$t/chg; check usb-power-suspended 'inhibit-charge with a partner'
rm -r $t/typec/port0-partner $t/typec/port1-partner $t/chg

# Audio playback: any ALSA playback substream running or draining.
mkdir -p $t/asound/card0/pcm0p/sub0 $t/asound/card0/pcm1c/sub0 $t/asound/card1/pcm3p/sub0
echo closed >$t/asound/card0/pcm0p/sub0/status
printf 'state: RUNNING\nowner_pid   : 1\n' >$t/asound/card0/pcm1c/sub0/status
check sleep-eligible 'capture running, playback closed'
printf 'state: PREPARED\n' >$t/asound/card1/pcm3p/sub0/status; check sleep-eligible 'playback prepared, not running'
printf 'state: RUNNING\nowner_pid   : 812\n' >$t/asound/card1/pcm3p/sub0/status; check audio-playback 'playback running (USB card)'
printf 'state: DRAINING\n' >$t/asound/card1/pcm3p/sub0/status; check audio-playback 'playback draining'
rm -r $t/asound

# logind inhibitors (busctl ListInhibitors reply): only block-mode "sleep"
# from someone other than rog5-server keeps the phone awake.
printf '%s\n' 'a(ssssuu) 3 "sleep:handle-power-key" "rog5-server" "keep-server-workloads-running" "block" 0 612 "shutdown:sleep" "NetworkManager" "NetworkManager needs to turn off networks" "delay" 0 555 "handle-power-key:handle-suspend-key" "phosh" "Phosh handling \"power\" keys" "block" 1000 900' >$t/inhibitors
check sleep-eligible 'server inhibitor, delay and handle-* inhibitors only'
printf '%s\n' 'a(ssssuu) 2 "sleep:handle-power-key" "rog5-server" "keep-server-workloads-running" "block" 0 612 "shutdown:sleep" "backup job" "nightly \"rsync\" run" "block" 0 4242' >$t/inhibitors
check sleep-inhibitor:backup_job 'block sleep inhibitor from a detached job'
ROG5_SLEEP_INHIBIT_IGNORE='rog5-server,backup' check sleep-inhibitor:backup_job 'ignore list matches whole names'
ROG5_SLEEP_INHIBIT_IGNORE='rog5-server,backup job' check sleep-eligible 'ignored by name'
ROG5_SLEEP_INHIBIT_IGNORE='' ROG5_SLEEP_INHIBITORS_CMD="cat $t/inhibitors" check sleep-inhibitor:rog5-server 'empty ignore list'
printf '%s\n' 'a(ssssuu) 1 "idle" "user session inhibited" "x" "block" 1000 1' >$t/inhibitors
check sleep-eligible 'idle inhibitor does not block suspend'
printf '%s\n' 'a(ssssuu) 1 "sleep" "user session inhibited" "Playing music" "block-weak" 1000 1' >$t/inhibitors
check 'sleep-inhibitor:user_session_inhibited' 'gnome-session block-weak inhibitor'
printf '%s\n' 'a(ssssuu) 0' >$t/inhibitors; check sleep-eligible 'no inhibitors'
printf '%s\n' 'Call failed: Connection timed out' >$t/inhibitors; check inhibitors-unknown 'unparsable reply'
rm $t/inhibitors
ROG5_SLEEP_INHIBITORS_CMD=false check inhibitors-unknown 'logind unreachable: a held inhibitor may be missed, stay awake'
printf '%s\n' 'a(ssssuu) 0' >$t/inhibitors
: >$t/stay; check stay-awake-file 'stay-awake file'
rm $t/stay; mkdir -p $t/usbdev/usb3 $t/usbdev/3-0:1.0; check sleep-eligible 'root hubs only'
mkdir $t/usbdev/3-1 $t/usbdev/3-1.1; check sleep-eligible 'hub and drive, default: hubs survive suspend (0105)'
ROG5_SLEEP_USB_DEVICE_BLOCKS=1 check usb-device 'hub and drive, USB devices block sleep'
mkdir $t/dp; echo enabled >$t/dp/enabled; echo On >$t/dp/dpms; check external-display 'desktop mode: panel off, DP lit'
echo Off >$t/dp/dpms; check sleep-eligible 'desktop mode: DP blanked'
rm -r $t/dp
rm -r $t/usbdev; rm $t/dpms; check screen-on 'no dpms file: never sleep blind'

# Loop: the suspend command returns before the kernel suspends (like
# systemctl). The daemon must wait for suspend_stats to move before it reads
# the wake IRQ or suspends again.
mkdir $t/stats; echo 0 >$t/stats/success; echo 0 >$t/stats/fail
echo 999 >$t/wake; echo Off >$t/dpms
cat >$t/fake-suspend <<EOS
#!/bin/sh
echo call >>$t/calls
( sleep 2; echo \$((\$(cat $t/stats/success) + 1)) >$t/stats/success.new; mv $t/stats/success.new $t/stats/success ) &
EOS
chmod +x $t/fake-suspend
ROG5_SLEEP_IDLE=1 ROG5_SLEEP_AWAKE=1 ROG5_SLEEP_POLL=1 ROG5_SLEEP_STATE=$t/state \
ROG5_SLEEP_MEM_SLEEP=$t/mem_sleep ROG5_SLEEP_STATS=$t/stats ROG5_SLEEP_WAKE_IRQ=$t/wake \
ROG5_SLEEP_SUSPEND_CMD=$t/fake-suspend "$here/rog5-sleep-policy" & pid=$!
sleep 9; kill $pid; wait $pid 2>/dev/null || true; sleep 2
calls=$(wc -l <$t/calls); ok=$(cat $t/stats/success)
[ "$calls" -ge 2 ] || { echo "FAIL loop suspended $calls times"; exit 1; }
[ "$calls" -le "$ok" ] || [ "$calls" -eq $((ok + 1)) ] || { echo "FAIL $calls suspend calls for $ok kernel suspends"; exit 1; }
[ "$calls" -le 3 ] || { echo "FAIL did not wait for the kernel: $calls calls in 9 s"; exit 1; }

# Wi-Fi power save: off at once for a client, on again only after the hold;
# a burst of short SSH connections must not toggle it each time. Fake iw/ip/ss.
b=$t/bin; mkdir -p $b $t/ps-state
cat >$b/iw <<EOS
#!/bin/sh
case "\$*" in "dev") echo "phy#0"; echo "	Interface wlan0" ;; *"set power_save"*) echo "\$5" >>$t/ps ;; esac
EOS
cat >$b/ip <<'EOS'
#!/bin/sh
echo "1: x inet 192.0.2.10/24 brd 192.0.2.255 scope global x"
EOS
cat >$b/ss <<EOS
#!/bin/sh
case "\$*" in
*-Htln*) echo "LISTEN 0 128 0.0.0.0:22 0.0.0.0:*" ;;
*established*) [ -e $t/client ] && echo "0 0 192.0.2.10:22 192.0.2.99:50000" ;;
esac
exit 0
EOS
chmod +x $b/*
rm -f $t/stay; echo 0 >$t/usb; echo Off >$t/dpms
PATH=$b:$PATH ROG5_SLEEP_WIFI_PS=1 ROG5_SLEEP_WIFI_PS_HOLD=3 ROG5_SLEEP_MODE=reachable ROG5_SLEEP_POLL=1 \
ROG5_SLEEP_STATE=$t/ps-state ROG5_SLEEP_MEM_SLEEP=$t/mem_sleep "$here/rog5-sleep-policy" & pid=$!
sleep 5; [ "$(cat $t/ps 2>/dev/null)" = on ] || { kill $pid; echo "FAIL power save not on after the hold"; exit 1; }
for i in 1 2 3; do : >$t/client; sleep 1.2; rm -f $t/client; sleep 1.2; done
sleep 5; kill $pid; wait $pid 2>/dev/null || true
[ "$(tr '\n' ' ' <$t/ps)" = "on off on " ] || { echo "FAIL power save toggles: $(tr '\n' ' ' <$t/ps)"; exit 1; }

# Wi-Fi power save is cached only once applied: no interface yet (boot before
# the driver) and a failed `iw` are retried; a recreated interface (new
# ifindex) gets the state again.
cat >$b/iw <<EOS
#!/bin/sh
case "\$*" in
"dev") [ -e $t/ps-iface ] && { echo "phy#0"; echo "	Interface wlan0"; echo "		ifindex \$(cat $t/ps-iface)"; } ;;
*"set power_save"*) [ -e $t/ps-fail ] && exit 1; echo "\$5" >>$t/ps2 ;;
esac
exit 0
EOS
chmod +x $b/iw
rm -rf $t/ps-state $t/ps2 $t/ps-iface; mkdir -p $t/ps-state; : >$t/ps-fail
rm -f $t/kmsg
PATH=$b:$PATH ROG5_SLEEP_WIFI_PS=1 ROG5_SLEEP_WIFI_PS_HOLD=0 ROG5_SLEEP_MODE=reachable ROG5_SLEEP_POLL=1 ROG5_SLEEP_KMSG=$t/kmsg \
ROG5_SLEEP_STATE=$t/ps-state ROG5_SLEEP_MEM_SLEEP=$t/mem_sleep "$here/rog5-sleep-policy" & pid=$!
sleep 2.5; [ ! -e $t/ps2 ] || { kill $pid; echo "FAIL power save set without an interface"; exit 1; }
echo 3 >$t/ps-iface
sleep 2.5; [ ! -e $t/ps2 ] || { kill $pid; echo "FAIL power save recorded although iw failed"; exit 1; }
rm -f $t/ps-fail
sleep 2.5; [ "$(tr '\n' ' ' <$t/ps2 2>/dev/null)" = "on " ] || { kill $pid; echo "FAIL power save not retried: $(cat $t/ps2 2>/dev/null)"; exit 1; }
sleep 2; [ "$(tr '\n' ' ' <$t/ps2)" = "on " ] || { kill $pid; echo "FAIL power save rewritten without a change: $(tr '\n' ' ' <$t/ps2)"; exit 1; }
echo 4 >$t/ps-iface
sleep 2.5; kill $pid; wait $pid 2>/dev/null || true
[ "$(tr '\n' ' ' <$t/ps2)" = "on on " ] || { echo "FAIL recreated interface not set again: $(tr '\n' ' ' <$t/ps2)"; exit 1; }
[ "$(grep -c 'could not set wifi power save' $t/kmsg)" = 1 ] || { echo "FAIL power-save failure logged $(grep -c 'could not set wifi power save' $t/kmsg) times (want once)"; exit 1; }

# A partial update (wlan0 took "on", wlan1 failed) drops the cache, so the
# way back to "off" is applied to both, not skipped as unchanged.
cat >$b/iw <<EOS
#!/bin/sh
case "\$*" in
"dev") echo "phy#0"; echo "	Interface wlan0"; echo "		ifindex 3"; echo "phy#1"; echo "	Interface wlan1"; echo "		ifindex 4" ;;
*"set power_save"*) [ "\$2" = wlan1 ] && [ "\$5" = on ] && [ -e $t/ps-fail1 ] && exit 1; echo "\$2 \$5" >>$t/ps3 ;;
esac
exit 0
EOS
chmod +x $b/iw
rm -rf $t/ps-state $t/ps3; mkdir -p $t/ps-state; : >$t/client; : >$t/ps-fail1
PATH=$b:$PATH ROG5_SLEEP_WIFI_PS=1 ROG5_SLEEP_WIFI_PS_HOLD=0 ROG5_SLEEP_MODE=reachable ROG5_SLEEP_POLL=1 ROG5_SLEEP_KMSG=/dev/null \
ROG5_SLEEP_STATE=$t/ps-state ROG5_SLEEP_MEM_SLEEP=$t/mem_sleep "$here/rog5-sleep-policy" & pid=$!
sleep 2.5; rm -f $t/client
sleep 2.5; : >$t/client
sleep 2.5; kill $pid; wait $pid 2>/dev/null || true
# (the failed "on" is retried every poll until the client returns)
tr '\n' ' ' <$t/ps3 | grep -Eqx 'wlan0 off wlan1 off (wlan0 on )+wlan0 off wlan1 off ' ||
	{ echo "FAIL partial power-save update: $(tr '\n' ' ' <$t/ps3)"; exit 1; }
# A killed loop leaves its current `sleep $ROG5_SLEEP_POLL` (1 s) behind;
# let it end so the runner sees no background descendants.
sleep 2
echo PASS rog5-sleep-policy
