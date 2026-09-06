#!/bin/sh
set -eu

source_file=${1:?usage: build-key-indicatord.sh SOURCE OUTPUT}
output=${2:?missing output}
epoch=1681862400
expected_source_size=20530
expected_source_sha256=3d597f919d71a76f2aef0ae2aa269e219ffe7c0bdca0e9b73481d52dff686939
expected_output_size=67520
expected_output_sha256=3792745382a390ebeef37a081e532884aae07bbcd73fd9f0da1c94e67bdabbc8

[ "$(uname -m)" = aarch64 ] || {
	echo 'FAIL key indicator must be built natively for AArch64' >&2
	exit 1
}
[ -f "$source_file" ] && [ -r "$source_file" ] &&
	[ ! -L "$source_file" ] || {
	echo 'FAIL missing regular key-indicator source' >&2
	exit 1
}
for command in cc file readelf sha256sum stat strings; do
	command -v "$command" >/dev/null || {
		echo "FAIL missing key-indicator build command: $command" >&2
		exit 1
	}
done
[ "$(stat -c %s "$source_file")" = "$expected_source_size" ] || {
	echo 'FAIL key-indicator source size is not sealed' >&2
	exit 1
}
[ "$(sha256sum "$source_file" | cut -d' ' -f1)" = \
	"$expected_source_sha256" ] || {
	echo 'FAIL key-indicator source hash is not sealed' >&2
	exit 1
}
[ "$(cc -dumpfullversion)" = 15.2.0 ] || {
	echo 'FAIL unexpected key-indicator compiler' >&2
	exit 1
}

export SOURCE_DATE_EPOCH=$epoch
umask 077
output_directory=$(dirname "$output")
output_name=$(basename "$output")
mkdir -p "$output_directory"
[ ! -e "$output" ] && [ ! -L "$output" ] || {
	echo "FAIL refusing existing key-indicator output: $output" >&2
	exit 1
}
temporary_directory=$(mktemp -d \
	"$output_directory/.${output_name}.tmp.XXXXXX")
temporary=$temporary_directory/output
cleanup() {
	rm -f -- "$temporary"
	rmdir -- "$temporary_directory" 2>/dev/null || :
}
trap cleanup EXIT HUP INT TERM

cc -std=c11 -O2 -static -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$source_file" -o "$temporary"

file "$temporary" |
	grep -q 'ELF 64-bit LSB pie executable, ARM aarch64.*static-pie linked'
readelf -h "$temporary" | grep -q 'Machine:.*AArch64'
if readelf -l "$temporary" | grep -q 'INTERP'; then
	echo 'FAIL key indicator has a dynamic interpreter' >&2
	exit 1
fi
readelf -l "$temporary" | grep -q 'GNU_RELRO'
readelf -W -l "$temporary" | grep -q 'GNU_STACK'
if readelf -W -l "$temporary" |
	awk '$1 == "GNU_STACK" && $0 ~ /RWE/ { found=1 } END { exit !found }'
then
	echo 'FAIL key indicator has an executable stack' >&2
	exit 1
fi
[ "$(stat -c %s "$temporary")" = "$expected_output_size" ] || {
	echo 'FAIL key-indicator output size is not sealed' >&2
	exit 1
}
[ "$(sha256sum "$temporary" | cut -d' ' -f1)" = \
	"$expected_output_sha256" ] || {
	echo 'FAIL key-indicator output hash is not sealed' >&2
	exit 1
}
for marker in \
	'/sys/class/input' \
	'/dev/input' \
	'pmic_pwrkey' \
	'/sys/class/leds/green:status' \
	'/soc@0/spmi@c440000/pmic@2/pwm/led@2' \
	'qcom-spmi-lpg' \
	'format=rog5-buttons-indicator-runtime-v1'
do
	strings "$temporary" | grep -Fqx "$marker"
done
if strings "$temporary" | grep -qE \
	'ROG5_INDICATOR_TESTING|--fixture|/bin/(ba)?sh|/dev/(block|disk)|(^|/)(fastboot|adb|reboot|poweroff)( |$)'
then
	echo 'FAIL production key indicator contains a test, shell, storage, or boot interface' >&2
	exit 1
fi

chmod 0755 "$temporary"
mv -- "$temporary" "$output"
rmdir -- "$temporary_directory"
trap - EXIT HUP INT TERM

printf 'compiler=%s\n' "$(cc --version | sed -n '1p')"
printf 'source_date_epoch=%s\n' "$SOURCE_DATE_EPOCH"
sha256sum "$source_file" "$output"
echo 'PASS hardened static-PIE AArch64 key indicator build'
