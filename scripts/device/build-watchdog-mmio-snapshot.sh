#!/bin/sh
set -eu

source_file=${1:?usage: build-watchdog-mmio-snapshot.sh SOURCE OUTPUT}
output=${2:?missing output}
expected_source_size=2133
expected_source_sha256=d224297d7e8db2766a175e7ec7154c617ace82128f4f7888b880fecc1c8d20e2
expected_output_size=67520
expected_output_sha256=e253cddbfaf4cf67e22764583c730a66ef00ae34aa77fc565d284e06ba70e89c
epoch=1681862400

fail() { echo "FAIL $*" >&2; exit 1; }

[ "$(uname -m)" = aarch64 ] || fail 'watchdog MMIO helper requires AArch64'
[ -f "$source_file" ] && [ ! -L "$source_file" ] || fail 'unsafe helper source'
[ ! -e "$output" ] && [ ! -L "$output" ] || fail 'helper output exists'
[ "$(stat -c %s "$source_file")" = "$expected_source_size" ] ||
	fail 'helper source size changed'
[ "$(sha256sum "$source_file" | cut -d ' ' -f 1)" = "$expected_source_sha256" ] ||
	fail 'helper source hash changed'

output_directory=$(dirname -- "$output")
output_name=$(basename -- "$output")
[ -d "$output_directory" ] && [ ! -L "$output_directory" ] ||
	fail 'unsafe helper output parent'

export LC_ALL=C SOURCE_DATE_EPOCH=$epoch TZ=UTC
umask 077
temporary_directory=$(mktemp -d "$output_directory/.${output_name}.tmp.XXXXXX")
temporary=$temporary_directory/output
trap 'rm -f -- "$temporary"; rmdir -- "$temporary_directory" 2>/dev/null || :' EXIT HUP INT TERM

cc -std=c11 -O2 -static -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$source_file" -o "$temporary"

file "$temporary" |
	grep -q 'ELF 64-bit LSB pie executable, ARM aarch64.*static-pie linked' ||
	fail 'helper is not static PIE AArch64'
if readelf -l "$temporary" | grep -q INTERP; then
	fail 'helper has a dynamic interpreter'
fi
[ "$(stat -c %s "$temporary")" = "$expected_output_size" ] ||
	fail 'helper output size changed'
[ "$(sha256sum "$temporary" | cut -d ' ' -f 1)" = "$expected_output_sha256" ] ||
	fail 'helper output hash changed'
strings "$temporary" | grep -Fqx /dev/mem || fail 'helper fixed device changed'
if strings "$temporary" | grep -qE '/dev/(block|disk)|fastboot|adb|/bin/(ba)?sh'; then
	fail 'helper exposes a storage, boot, or shell surface'
fi

chmod 0755 "$temporary"
mv -T -- "$temporary" "$output"
rmdir -- "$temporary_directory"
trap - EXIT HUP INT TERM
sha256sum "$source_file" "$output"
echo 'PASS reproducible read-only watchdog MMIO snapshot helper'
