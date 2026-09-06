#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
builder=$repo/scripts/device/build-qcom-wdt-candidate-dtb.sh
base=$repo/artifacts/local-image-stage-v1/board.dtb

sh -n "$builder"
for contract in \
	'expected_base=4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8' \
	'target-path = "/soc@0"' \
	'watchdog@17c10000' \
	'compatible = "qcom,kpss-wdt"' \
	'reg = <0x0 0x17c10000 0x0 0x1000>' \
	'clocks = <&sleep_clk>' \
	'timeout-sec = <30>'; do
	grep -Fq "$contract" "$builder" || exit 1
done

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
"$builder" "$base" "$work/a.dtb" >/dev/null
"$builder" "$base" "$work/b.dtb" >/dev/null
cmp "$work/a.dtb" "$work/b.dtb"
[ "$(fdtget "$work/a.dtb" /soc@0/watchdog@17c10000 compatible)" = qcom,kpss-wdt ]
[ "$(fdtget -tx "$work/a.dtb" /soc@0/watchdog@17c10000 reg)" = '0 17c10000 0 1000' ]
[ "$(fdtget "$work/a.dtb" /soc@0/watchdog@17c10000 timeout-sec)" = 30 ]
[ "$(fdtget "$work/a.dtb" /clocks/sleep-clk clock-frequency)" = 32764 ]

echo 'PASS APSS watchdog DTB is stock-address-grounded, deterministic, and exact'
