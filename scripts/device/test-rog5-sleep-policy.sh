#!/bin/sh
# Offline test of rog5-sleep-policy --once decisions with a fake sysfs.
set -eu
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ROG5_SLEEP_WIFI_PS=0 ROG5_SLEEP_MODE=suspend ROG5_SLEEP_USB=$t/usb ROG5_SLEEP_DPMS=$t/dpms ROG5_SLEEP_STAY=$t/stay ROG5_SLEEP_USB_DEVICES=$t/usbdev ROG5_SLEEP_SSH_BLOCKS=0 ROG5_SLEEP_KMSG=/dev/null
check() { got=$("$here/rog5-sleep-policy" --once); [ "$got" = "$1" ] || { echo "FAIL expected $1 got $got ($2)"; exit 1; }; }
echo 1 >$t/usb; echo Off >$t/dpms; check usb-power 'plugged in, screen off'
echo 0 >$t/usb; echo On >$t/dpms; check screen-on 'battery, screen on'
echo Off >$t/dpms; check sleep-eligible 'battery, screen off'
: >$t/stay; check stay-awake-file 'stay-awake file'
rm $t/stay; mkdir -p $t/usbdev/usb3 $t/usbdev/3-0:1.0; check sleep-eligible 'root hubs only'
mkdir $t/usbdev/3-1 $t/usbdev/3-1.1; check sleep-eligible 'hub and drive, default: hubs survive suspend (0105)'
ROG5_SLEEP_USB_DEVICE_BLOCKS=1 check usb-device 'hub and drive, USB devices block sleep'
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
echo PASS rog5-sleep-policy
