#!/bin/sh
set -eu

fail() { echo "FAIL $*" >&2; exit 1; }
base=${1:?usage: build-display-60hz-candidate-dtb.sh BASE OVERLAY OUTPUT}
overlay=${2:?missing overlay}
output=${3:?missing output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-display-60hz-dtb-delta.py

for path in "$base" "$overlay" "$verifier"; do
	[ -f "$path" ] && [ ! -L "$path" ] && [ -r "$path" ] ||
		fail "unsafe input: $path"
done
for command in dtc fdtoverlay fdtget sha256sum; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
[ ! -L "$output" ] && [ ! -d "$output" ] || fail 'unsafe output'

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
dtc -q -@ -I dts -O dtb -o "$work/display.dtbo" "$overlay"
fdtoverlay -i "$base" -o "$work/candidate.dtb" "$work/display.dtbo"
dtc -q -I dtb -O dts -o /dev/null "$work/candidate.dtb"
"$verifier" "$base" "$work/candidate.dtb"

parent=$(dirname "$output")
mkdir -p "$parent"
stage=$(mktemp -d "$parent/.rog5-display-60hz.XXXXXX")
trap 'rm -rf -- "$work" "$stage"' EXIT HUP INT TERM
mv "$work/candidate.dtb" "$stage/candidate.dtb"
mv "$stage/candidate.dtb" "$output"
rmdir "$stage"
sha256sum "$output"
echo 'PASS deterministic 60 Hz AMS678/Iris-bypass candidate DTB'
