#!/bin/sh
set -eu

[ "$#" -eq 1 ] || {
	echo 'usage: build-persistent-root-power-usb-dtb.sh OUTPUT' >&2
	exit 1
}

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
. "$repo/scripts/host/generated-power-usb-active.sh"
base_relative=$(PYTHONPATH="$repo/scripts/host" python3 -c \
	'from generated_power_usb_active import ARTIFACTS; print(ARTIFACTS["board.dtb"]["path"])')
base=$repo/$base_relative
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-ufs-discovery.dtso
builder=$repo/scripts/device/build-ufs-discovery-candidate-dtb.sh
verifier=$repo/scripts/device/verify-persistent-root-power-usb-dtb.sh
output=$1

[ -f "$base" ] && [ ! -L "$base" ] &&
	[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$POWER_USB_EXPECTED_DTB_SHA256" ] || {
	echo 'FAIL canonical active power/USB DTB identity changed' >&2
	exit 1
}
case $output in /*) ;; *) echo 'FAIL output must be absolute' >&2; exit 1 ;; esac
parent=$(dirname -- "$output")
[ -d "$parent" ] && [ ! -L "$parent" ] || {
	echo 'FAIL output parent is absent or linked' >&2
	exit 1
}
[ ! -e "$output" ] && [ ! -L "$output" ] || {
	echo 'FAIL output already exists' >&2
	exit 1
}

stage=$(mktemp -d "$parent/.rog5-composed-dtb.XXXXXX")
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
"$builder" "$base" "$overlay" "$stage/board.dtb" >/dev/null
"$verifier" "$stage/board.dtb" >/dev/null
ln "$stage/board.dtb" "$output" || {
	echo 'FAIL output appeared during composed DTB build' >&2
	exit 1
}

printf 'sha256=%s\n' "$(sha256sum "$output" | cut -d ' ' -f 1)"
echo 'PASS canonical power/USB DTB composed with the read-only UFS overlay'
