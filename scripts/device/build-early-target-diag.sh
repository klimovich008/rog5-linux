#!/bin/sh
set -eu

source_file=${1:?usage: build-early-target-diag.sh SOURCE OUTPUT}
output=${2:?missing output}
epoch=1681862400
expected_source_size=22039
expected_source_sha256=a7a5f81343240d5dc8aa2a14b060009b401949d6162fc7ef8fb47635d3aaef85
expected_output_size=67288
expected_output_sha256=437747043b5d606d82e00c37b8a3e45f54a96cdb9c5c22780bb285ab10650a9d

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$(uname -m)" = aarch64 ] ||
	fail 'early-target reporter must be built natively for AArch64'
[ -f "$source_file" ] && [ -r "$source_file" ] &&
	[ ! -L "$source_file" ] ||
	fail 'missing regular early-target reporter source'
for command in cc file readelf sha256sum stat strings; do
	command -v "$command" >/dev/null ||
		fail "missing early-target reporter build command: $command"
done
[ "$(cc -dumpfullversion)" = 15.2.0 ] ||
	fail 'unexpected early-target reporter compiler'
[ "$(stat -c %s "$source_file")" = "$expected_source_size" ] ||
	fail 'early-target reporter source size is not sealed'
[ "$(sha256sum "$source_file" | cut -d ' ' -f 1)" = \
	"$expected_source_sha256" ] ||
	fail 'early-target reporter source hash is not sealed'

output_directory=$(dirname -- "$output")
output_name=$(basename -- "$output")
[ -d "$output_directory" ] && [ ! -L "$output_directory" ] ||
	fail 'early-target reporter output parent is absent or linked'
[ ! -e "$output" ] && [ ! -L "$output" ] ||
	fail 'early-target reporter output already exists'

export LC_ALL=C
export SOURCE_DATE_EPOCH=$epoch
export TZ=UTC
umask 077
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
	grep -q 'ELF 64-bit LSB pie executable, ARM aarch64.*static-pie linked' ||
	fail 'early-target reporter is not static PIE AArch64'
readelf -h "$temporary" | grep -q 'Machine:.*AArch64' ||
	fail 'early-target reporter ELF machine changed'
if readelf -l "$temporary" | grep -q 'INTERP'; then
	fail 'early-target reporter has a dynamic interpreter'
fi
readelf -l "$temporary" | grep -q 'GNU_RELRO' ||
	fail 'early-target reporter lacks RELRO'
if readelf -W -l "$temporary" |
	awk '$1 == "GNU_STACK" && $0 ~ /RWE/ { found=1 } END { exit !found }'
then
	fail 'early-target reporter has an executable stack'
fi
[ "$(stat -c %s "$temporary")" = "$expected_output_size" ] ||
	fail 'early-target reporter output size is not sealed'
[ "$(sha256sum "$temporary" | cut -d ' ' -f 1)" = \
	"$expected_output_sha256" ] ||
	fail 'early-target reporter output hash is not sealed'
for marker in \
	'/dev/ttyGS0' \
		'rog5-early-target-diag-v1' \
		'nfs-mount-returned' \
		'route-failed' \
		'host-port-timeout' \
		'charging-probe-complete' \
		'watchdog-pretimeout' \
	'cannot require diagnostic peer credentials'; do
	strings "$temporary" | grep -Fqx "$marker" ||
		fail "early-target reporter lacks marker: $marker"
done
if strings "$temporary" | grep -qE \
	'ROG5_DIAG_TEST_|/bin/(ba)?sh|/dev/(block|disk)|(^|/)(fastboot|adb)( |$)'
then
	fail 'production reporter contains a test, shell, storage, or boot interface'
fi

chmod 0755 "$temporary"
mv -T -- "$temporary" "$output"
rmdir -- "$temporary_directory"
trap - EXIT HUP INT TERM

printf 'compiler=%s\n' "$(cc --version | sed -n '1p')"
printf 'source_date_epoch=%s\n' "$SOURCE_DATE_EPOCH"
sha256sum "$source_file" "$output"
echo 'PASS hardened static-PIE AArch64 early-target reporter build'
