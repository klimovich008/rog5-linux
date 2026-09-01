#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
base=$repo/artifacts/display-60hz-v1/sm8350-asus-rog-phone5-wifi-base.dtb
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-display-60hz.dtso
builder=$repo/scripts/device/build-display-60hz-candidate-dtb.sh
verifier=$repo/scripts/device/verify-display-60hz-dtb-delta.py
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

"$builder" "$base" "$overlay" "$work/first.dtb" >/dev/null
"$builder" "$base" "$overlay" "$work/second.dtb" >/dev/null
cmp "$work/first.dtb" "$work/second.dtb"
"$verifier" "$base" "$work/first.dtb" >/dev/null

cp "$work/first.dtb" "$work/usb-mutant.dtb"
fdtput -t s "$work/usb-mutant.dtb" /soc@0/usb@a8f8800 status okay
if "$verifier" "$base" "$work/usb-mutant.dtb" >/dev/null 2>&1; then
	echo 'FAIL display verifier accepted unrelated USB enablement' >&2
	exit 1
fi

cp "$work/first.dtb" "$work/gpio-mutant.dtb"
panel=/soc@0/display-subsystem@ae00000/dsi@ae94000/panel@0
set -- $(fdtget -t x "$work/gpio-mutant.dtb" "$panel" iris-wakeup-gpios)
fdtput -t x "$work/gpio-mutant.dtb" "$panel" iris-wakeup-gpios "$1" 5d 0
if "$verifier" "$base" "$work/gpio-mutant.dtb" >/dev/null 2>&1; then
	echo 'FAIL display verifier accepted wrong Iris wakeup GPIO' >&2
	exit 1
fi

cp "$work/first.dtb" "$work/mode-mutant.dtb"
fdtput -t s "$work/mode-mutant.dtb" "$panel" compatible asus,other-panel
if "$verifier" "$base" "$work/mode-mutant.dtb" >/dev/null 2>&1; then
	echo 'FAIL display verifier accepted wrong panel identity' >&2
	exit 1
fi

echo 'PASS 60 Hz display DTB is deterministic and rejects unrelated, GPIO, and panel mutations'
