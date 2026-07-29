#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

base=${1:?usage: build-buttons-indicator-candidate-dtb.sh BASE OVERLAY OUTPUT}
overlay=${2:?missing buttons and indicator overlay}
output=${3:?missing output}
script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
verifier=$script_dir/verify-buttons-indicator-dtb-delta.py

for input in "$base" "$overlay" "$verifier"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "input is not a readable ordinary file: $input"
done
[ -x "$verifier" ] || fail "DTB verifier is not executable: $verifier"
for command in dtc fdtoverlay fdtget sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing DTB build command: $command"
done
if [ -L "$output" ] || [ -d "$output" ]; then
	fail "output is a link or directory: $output"
fi
if [ -e "$output" ] && [ ! -f "$output" ]; then
	fail "existing output is not an ordinary file: $output"
fi

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

dtc -q -@ -I dts -O dtb -o "$stage/buttons-indicator.dtbo" "$overlay"
output_parent=$(dirname "$output")
mkdir -p "$output_parent"
publish_stage=$(mktemp -d "$output_parent/.rog5-buttons-indicator-dtb.XXXXXX")
candidate=$publish_stage/candidate.dtb
fdtoverlay -i "$base" -o "$candidate" "$stage/buttons-indicator.dtbo"
dtc -q -I dtb -O dts -o /dev/null "$candidate"
"$verifier" "$base" "$candidate"

[ "$(fdtget -t s "$candidate" \
	/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey status)" = okay ]
[ "$(fdtget -t s "$candidate" \
	/soc@0/spmi@c440000/pmic@0/pon@1300/resin status)" = okay ]
[ "$(fdtget -t x "$candidate" \
	/soc@0/spmi@c440000/pmic@0/pon@1300/resin linux,code)" = 72 ]
[ "$(fdtget -t s "$candidate" /gpio-keys/key-volume-up label)" = volume_up ]
[ "$(fdtget -t x "$candidate" /gpio-keys/key-volume-up linux,code)" = 73 ]
[ "$(fdtget -t s "$candidate" \
	/soc@0/spmi@c440000/pmic@2/pwm/led@2 default-state)" = off ]

mv "$candidate" "$output"
rm -rf "$publish_stage"
publish_stage=
sha256sum "$output"
echo 'PASS isolated buttons and green-indicator candidate DTB'
