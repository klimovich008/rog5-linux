#!/bin/sh
# Offline test of rog5-charge-policy decisions against a fake power-supply,
# Type-C and thermal sysfs. The fake charge_behaviour reads back like the
# kernel's ("[auto] inhibit-charge force-discharge") after each write.
set -eu
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
b=$t/bat u=$t/usb
export ROG5_CHG_BAT=$b ROG5_CHG_USB=$u ROG5_CHG_PARTNER=$t/port0-partner ROG5_CHG_ZONES=$t/zones \
	ROG5_CHG_CONF=$t/charge-policy ROG5_CHG_STATE=$t/state ROG5_CHG_KMSG=$t/log
mkdir -p $b $u $t/zones/thermal_zone36
echo 0 >$b/charge_control_start_threshold; echo 100 >$b/charge_control_end_threshold
echo '[auto] inhibit-charge force-discharge' >$b/charge_behaviour
bat() { echo "$1" >$b/capacity; echo "$2" >$b/temp; echo "$3" >$b/current_now; echo "${4:-Charging}" >$b/status; }
bat 90 300 0
echo 1 >$u/online
z=$t/zones/thermal_zone36; echo skin-thermal >$z/type
echo critical >$z/trip_point_0_type; echo 65000 >$z/trip_point_0_temp
echo passive >$z/trip_point_1_type; echo passive >$z/trip_point_2_type
perf() { if [ "$1" = on ]; then echo 57000 >$z/trip_point_1_temp; echo 56000 >$z/trip_point_2_temp
	else echo 46000 >$z/trip_point_1_temp; echo 42000 >$z/trip_point_2_temp; fi; }
perf off

# Emulate the kernel's sysfs read-back of charge_behaviour.
run() {
	out=$("$here/rog5-charge-policy" "$@") || true
	cur=$(cat $b/charge_behaviour)
	case $cur in *'['*) ;; *)
		printf '%s\n' "auto inhibit-charge force-discharge" | sed "s/\(^\| \)$cur\( \|$\)/\1[$cur]\2/" >$b/charge_behaviour ;;
	esac
	printf '%s' "$out"
}
sel() { sed 's/.*\[\(.*\)\].*/\1/' $b/charge_behaviour; }
check() { # expected-decision expected-sysfs description [args]
	want=$1 want_fs=$2 what=$3; shift 3
	[ $# -gt 0 ] || set -- --once
	got=$(run "$@" | tail -n 1)
	fs="$(sel) $(cat $b/charge_control_start_threshold) $(cat $b/charge_control_end_threshold)"
	[ "$got" = "$want" ] || { echo "FAIL $what: decision '$got', expected '$want'"; cat $t/log 2>/dev/null; exit 1; }
	[ "$fs" = "$want_fs" ] || { echo "FAIL $what: sysfs '$fs', expected '$want_fs'"; exit 1; }
}

# Defaults (no config): limit 70-80, auto.
check 'auto 70 80 limit' 'auto 70 80' 'default limit window'
# Unchanged values are not rewritten (a threshold write clears the kernel's hold).
before=$(stat -c %y $b/charge_control_end_threshold $b/charge_control_start_threshold $b/charge_behaviour)
sleep 1.1
check 'auto 70 80 limit' 'auto 70 80' 'steady state'
[ "$before" = "$(stat -c %y $b/charge_control_end_threshold $b/charge_control_start_threshold $b/charge_behaviour)" ] ||
	{ echo 'FAIL steady state rewrote sysfs'; exit 1; }

# Performance mode on external power: bypass; not when low; not on battery.
perf on
check 'inhibit-charge 70 80 performance' 'inhibit-charge 70 80' 'performance mode bypass'
bat 20 300 0
check 'auto 70 80 performance-but-low' 'auto 70 80' 'performance but below bypass_min'
bat 90 300 0
echo 0 >$u/online
check 'auto 70 80 battery' 'auto 70 80' 'unplugged'
echo 1 >$u/online

# The adapter can't carry the load: discharging in bypass -> auto, backoff.
printf 'discharge_s=0\nbackoff_s=3600\n' >$t/charge-policy
check 'inhibit-charge 70 80 performance' 'inhibit-charge 70 80' 'bypass again'
bat 90 300 -450000
check 'auto 70 80 performance-backoff' 'auto 70 80' 'discharging in bypass'
bat 90 300 0
check 'auto 70 80 performance-backoff' 'auto 70 80' 'still in backoff'
printf 'discharge_s=0\nbackoff_s=0\n' >$t/charge-policy
check 'inhibit-charge 70 80 performance' 'inhibit-charge 70 80' 'backoff over'
# a short dip below discharge_ma for less than discharge_s keeps bypass
printf 'discharge_s=600\n' >$t/charge-policy
bat 90 300 -450000
check 'inhibit-charge 70 80 performance' 'inhibit-charge 70 80' 'short discharge tolerated'
bat 90 300 -100000
check 'inhibit-charge 70 80 performance' 'inhibit-charge 70 80' 'small discharge ignored'
[ ! -e $t/state/low ] || { echo 'FAIL low timer not reset'; exit 1; }
perf off; bat 90 300 0; rm $t/charge-policy
check 'auto 70 80 limit' 'auto 70 80' 'performance off'

# Battery temperature bypass with hysteresis.
bat 90 400 0
check 'inhibit-charge 70 80 battery-hot' 'inhibit-charge 70 80' 'hot'
bat 90 380 0
check 'inhibit-charge 70 80 battery-hot' 'inhibit-charge 70 80' 'still warm (hysteresis)'
bat 90 369 0
check 'auto 70 80 limit' 'auto 70 80' 'cooled down'
printf 'bypass_temp=0\n' >$t/charge-policy; bat 90 450 0
check 'auto 70 80 limit' 'auto 70 80' 'temperature bypass disabled'

# Modes.
printf 'mode=bypass\n' >$t/charge-policy; bat 90 300 0
check 'inhibit-charge 0 100 bypass-mode' 'inhibit-charge 0 100' 'bypass mode'
printf 'mode = full  # comment\n' >$t/charge-policy
check 'auto 0 100 full' 'auto 0 100' 'full mode'
printf 'mode=off\nbypass_perf=1\n' >$t/charge-policy; perf on
check 'auto 0 100 off' 'auto 0 100' 'off ignores performance'
perf off
printf 'mode=limit\nstart=85\nend=90\n' >$t/charge-policy
check 'auto 85 90 limit' 'auto 85 90' 'custom window'
printf 'mode=turbo\nend=abc\n' >$t/charge-policy
check 'auto 0 100 off' 'auto 0 100' 'unknown mode -> off'
grep -q "unknown mode 'turbo'" $t/log && grep -q "ignoring end='abc'" $t/log || { echo 'FAIL bad config not logged'; exit 1; }
printf 'end=5\nstart=90\n' >$t/charge-policy
check 'auto 75 80 limit' 'auto 75 80' 'out-of-range end and start >= end'
rm $t/charge-policy

# Full-charge override: until Full, then back to the limit.
bat 90 300 500000
check 'auto 0 100 full' 'auto 0 100' 'full override' full
check 'auto 0 100 full' 'auto 0 100' 'full override persists'
bat 100 300 0 Full
check 'auto 70 80 limit' 'auto 70 80' 'full reached -> limit'
[ ! -e $t/state/full ] || { echo 'FAIL override not cleared'; exit 1; }
# ... or until unplugged
bat 90 300 500000
check 'auto 0 100 full' 'auto 0 100' 'full override 2' full
echo 0 >$u/online
check 'auto 70 80 battery' 'auto 70 80' 'unplugged during full ends the override'
echo 1 >$u/online
check 'auto 70 80 limit' 'auto 70 80' 'replug after full -> limit'
# ... or cancelled
check 'auto 0 100 full' 'auto 0 100' 'full override 3' full
check 'auto 70 80 limit' 'auto 70 80' 'cancel-full' cancel-full
# An explicit full charge beats the performance bypass (perf_on_power=always
# made a 50 % battery stay at 50 % for the whole override); heat still wins.
bat 50 300 0; perf on
check 'auto 0 100 full' 'auto 0 100' 'full override charges in performance mode' full
bat 50 410 0
check 'inhibit-charge 0 100 battery-hot' 'inhibit-charge 0 100' 'full override, hot battery bypasses'
bat 50 300 0
check 'auto 0 100 full' 'auto 0 100' 'full override, cooled'
check 'inhibit-charge 70 80 performance' 'inhibit-charge 70 80' 'cancel-full in performance mode' cancel-full
check 'inhibit-charge 70 80 performance' 'inhibit-charge 70 80' 'cancelled full -> performance bypass again'
printf 'mode=full\n' >$t/charge-policy
check 'auto 0 100 full' 'auto 0 100' 'full mode charges in performance mode'
perf off; bat 90 300 0; rm -f $t/charge-policy $t/state/hot
check 'auto 70 80 limit' 'auto 70 80' 'back to the default window'

# Drain (opt-in): force-discharge from >= end+3 down to end, never below 50.
printf 'drain=1\n' >$t/charge-policy
bat 82 300 0
check 'auto 70 80 limit' 'auto 70 80' 'drain: within 3 % of end'
bat 95 300 0
check 'force-discharge 70 80 drain' 'force-discharge 70 80' 'drain starts'
echo 0 >$u/online; mkdir $t/port0-partner
check 'force-discharge 70 80 drain' 'force-discharge 70 80' 'drain: USB input suspended, partner present'
bat 80 300 -300000
check 'auto 70 80 limit' 'auto 70 80' 'drain done at end'
echo 1 >$u/online; bat 95 300 0
check 'force-discharge 70 80 drain' 'force-discharge 70 80' 'drain again'
echo 0 >$u/online; rmdir $t/port0-partner
check 'auto 70 80 battery' 'auto 70 80' 'drain: charger removed'
echo 1 >$u/online
printf 'drain=1\nstart=30\nend=40\n' >$t/charge-policy; bat 52 300 0
check 'force-discharge 30 40 drain' 'force-discharge 30 40' 'drain floor 50'
bat 50 300 0
check 'auto 30 40 limit' 'auto 30 40' 'drain stops at 50'
printf 'drain=1\n' >$t/charge-policy; bat 95 300 0; perf on
check 'inhibit-charge 70 80 performance' 'inhibit-charge 70 80' 'no drain in performance mode'
perf off
check 'force-discharge 70 80 drain' 'force-discharge 70 80' 'drain before heat'
bat 95 420 0
check 'inhibit-charge 70 80 battery-hot' 'inhibit-charge 70 80' 'heat hands a drain over to bypass'
bat 95 300 0
check 'force-discharge 70 80 drain' 'force-discharge 70 80' 'drain after cooling'
# a stale drain flag never drains below the floor
bat 10 300 0; : >$t/state/draining
check 'auto 70 80 limit' 'auto 70 80' 'stale drain flag at 10 %'
[ ! -e $t/state/draining ] || { echo 'FAIL stale drain flag kept'; exit 1; }
bat 90 300 0; rm $t/charge-policy
check 'auto 70 80 limit' 'auto 70 80' 'drain off by default'

# Leading zeros are valid settings; completing an override honours mode=off.
printf 'full_hours=08\nend=080\nstart=070\n' >$t/charge-policy
check 'auto 70 80 limit' 'auto 70 80' 'leading zeros'
printf 'mode=off\n' >$t/charge-policy
check 'auto 0 100 full' 'auto 0 100' 'full override in mode off' full
bat 100 300 0 Full; perf on
check 'auto 0 100 off' 'auto 0 100' 'full done -> off, even in performance mode'
perf off; bat 90 300 0; rm $t/charge-policy
check 'auto 70 80 limit' 'auto 70 80' 'defaults again'

# Command-line changes edit the config and apply at once.
printf '# kept comment\nbypass_temp=45\n' >$t/charge-policy
check 'auto 55 60 limit' 'auto 55 60' 'limit command' limit 60
grep -q '^# kept comment' $t/charge-policy && grep -q '^bypass_temp=45' $t/charge-policy || { echo 'FAIL setconf lost lines'; exit 1; }
check 'auto 50 60 limit' 'auto 50 60' 'limit command with start' limit 60 50
check 'inhibit-charge 0 100 bypass-mode' 'inhibit-charge 0 100' 'mode command' mode bypass
[ "$(grep -c '^mode=' $t/charge-policy)" = 1 ] || { echo 'FAIL duplicate mode lines'; exit 1; }
for bad in 'limit 10' 'limit 80 90' 'limit x' 'mode turbo'; do
	# shellcheck disable=SC2086
	if "$here/rog5-charge-policy" $bad 2>/dev/null; then echo "FAIL accepted: $bad"; exit 1; fi
done
rm $t/charge-policy
check 'auto 70 80 limit' 'auto 70 80' 'back to defaults'

# Errors: unreadable battery -> auto, no limit; no kernel interface -> nothing.
rm $b/capacity
check 'auto 0 100 error' 'auto 0 100' 'battery unreadable'
grep -q 'falling back to auto' $t/log || { echo 'FAIL fallback not logged'; exit 1; }
bat 90 300 0
check 'auto 70 80 limit' 'auto 70 80' 'battery readable again'
echo nonsense >$b/temp
check 'auto 0 100 error' 'auto 0 100' 'garbage temperature'
perf on
for bad in 'temp:' 'temp:--' 'temp:3-0' 'current_now:' 'current_now:-'; do
	bat 90 300 0; echo "${bad#*:}" >$b/${bad%%:*}
	check 'auto 0 100 error' 'auto 0 100' "unusable $bad in performance mode"
done
rm $b/current_now
check 'auto 0 100 error' 'auto 0 100' 'current_now missing in performance mode'
perf off
bat 90 300 0
perf on
check 'inhibit-charge 70 80 performance' 'inhibit-charge 70 80' 'bypass before stop'
perf off
run stop >/dev/null
[ "$(sel) $(cat $b/charge_control_start_threshold) $(cat $b/charge_control_end_threshold)" = 'auto 0 100' ] || { echo 'FAIL stop'; exit 1; }
run status | grep -q '^mode: limit' || { echo 'FAIL status'; exit 1; }
mv $b/charge_behaviour $t/cb
if "$here/rog5-charge-policy" --once >/dev/null; then echo 'FAIL no interface accepted'; exit 1; fi
mv $t/cb $b/charge_behaviour
if "$here/rog5-charge-policy" bogus 2>/dev/null; then echo 'FAIL unknown command accepted'; exit 1; fi

# The loop: applies the config and keeps running.
rm -rf $t/state
ROG5_CHG_POLL=1 "$here/rog5-charge-policy" & pid=$!
sleep 2
kill $pid; wait $pid 2>/dev/null || true
[ "$(cat $b/charge_control_end_threshold)" = 80 ] || { echo 'FAIL loop did not apply the limit'; exit 1; }
echo PASS rog5-charge-policy
