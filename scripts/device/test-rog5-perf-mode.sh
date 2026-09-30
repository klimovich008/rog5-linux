#!/bin/sh
# Offline test of rog5-perf-mode against a fake thermal sysfs.
set -eu
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ROG5_PERF_MODE_ZONES=$t ROG5_PERF_MODE_STATE=$t/state/perf-mode ROG5_PERF_MODE_LOCK=$t/lock
mkdir -p $t/thermal_zone3 $t/thermal_zone36
echo cpu4-top-thermal >$t/thermal_zone3/type
z=$t/thermal_zone36; echo skin-thermal >$z/type; echo 40100 >$z/temp
echo critical >$z/trip_point_0_type; echo 65000 >$z/trip_point_0_temp
echo passive >$z/trip_point_1_type; echo 46000 >$z/trip_point_1_temp
echo passive >$z/trip_point_2_type; echo 42000 >$z/trip_point_2_temp
m=$z/trip_point_
check() { got="$(cat ${m}0_temp) $(cat ${m}1_temp) $(cat ${m}2_temp)"; [ "$got" = "$1" ] || { echo "FAIL $2: $got"; exit 1; }; }
"$here/rog5-perf-mode" status | grep -q 'mode: normal' || { echo 'FAIL status normal'; exit 1; }
"$here/rog5-perf-mode" performance >/dev/null; check '65000 57000 56000' 'performance'
[ "$(cat $t/state/perf-mode)" = performance ] || { echo 'FAIL saved'; exit 1; }
"$here/rog5-perf-mode" status | grep -q 'mode: performance' || { echo 'FAIL status perf'; exit 1; }
"$here/rog5-perf-mode" normal >/dev/null; check '65000 46000 42000' 'normal'
echo performance >$t/state/perf-mode; "$here/rog5-perf-mode" apply >/dev/null; check '65000 57000 56000' 'apply'
# auto: performance only with external power and a connected DP connector
export ROG5_PERF_MODE_SUPPLIES=$t/ps ROG5_PERF_MODE_DRM=$t/drm
mkdir -p $t/ps/usb $t/ps/bat $t/drm/card0-DP-1
echo USB >$t/ps/usb/type; echo 0 >$t/ps/usb/online; echo Battery >$t/ps/bat/type
echo disconnected >$t/drm/card0-DP-1/status
"$here/rog5-perf-mode" auto >/dev/null; check '65000 46000 42000' 'auto battery'
echo 1 >$t/ps/usb/online; "$here/rog5-perf-mode" apply >/dev/null; check '65000 46000 42000' 'auto ac without display'
echo connected >$t/drm/card0-DP-1/status; "$here/rog5-perf-mode" apply >/dev/null; check '65000 57000 56000' 'auto desktop on ac'
"$here/rog5-perf-mode" status | grep -q 'auto picks performance' || { echo 'FAIL status auto'; exit 1; }
echo 0 >$t/ps/usb/online; "$here/rog5-perf-mode" apply >/dev/null; check '65000 46000 42000' 'auto unplugged'
"$here/rog5-perf-mode" normal >/dev/null
if "$here/rog5-perf-mode" turbo 2>/dev/null; then echo 'FAIL unknown mode accepted'; exit 1; fi
# concurrent changes never leave the trips crossed
for i in 1 2 3 4 5 6 7 8; do "$here/rog5-perf-mode" performance >/dev/null & "$here/rog5-perf-mode" normal >/dev/null & done; wait
case "$(cat ${m}1_temp) $(cat ${m}2_temp)" in '46000 42000'|'57000 56000') ;; *) echo "FAIL crossed trips: $(cat ${m}1_temp) $(cat ${m}2_temp)"; exit 1 ;; esac
echo PASS rog5-perf-mode
