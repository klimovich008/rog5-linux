#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

base=${1:?usage: build-headless-display-isolation-candidate-dtb.sh BASE OVERLAY OUTPUT}
overlay=${2:?missing headless display-isolation overlay}
output=${3:?missing output}
script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
verifier=$script_dir/verify-headless-display-isolation-dtb-delta.py

for input in "$base" "$overlay" "$verifier"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "input is not a readable ordinary file: $input"
done
[ -x "$verifier" ] || fail "DTB verifier is not executable: $verifier"
for command in dtc fdtoverlay python3 sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing DTB build command: $command"
done
if [ -L "$output" ] || [ -d "$output" ]; then
	fail "output is a link or directory: $output"
fi
[ ! -e "$output" ] || fail "output already exists: $output"

stage=$(mktemp -d)
publish_stage=
cleanup() {
	rm -rf "$stage"
	if [ -n "$publish_stage" ]; then
		rm -rf "$publish_stage"
	fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

dtc -q -@ -I dts -O dtb -o "$stage/headless-display-isolation.dtbo" \
	"$overlay"
output_parent=$(dirname "$output")
mkdir -p "$output_parent"
publish_stage=$(mktemp -d \
	"$output_parent/.rog5-headless-display-isolation-dtb.XXXXXX")
candidate=$publish_stage/candidate.dtb
fdtoverlay -i "$base" -o "$candidate" \
	"$stage/headless-display-isolation.dtbo"
dtc -q -I dtb -O dts -o /dev/null "$candidate"
"$verifier" "$base" "$candidate" >/dev/null

if ! ln "$candidate" "$output" 2>/dev/null; then
	fail "cannot publish output without replacement: $output"
fi
rm "$candidate"
rm -rf "$publish_stage"
publish_stage=
sha256sum "$output"
echo 'PASS isolated headless display-provider candidate DTB'
