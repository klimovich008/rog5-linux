#!/bin/sh
set -eu

source_file=${1:?usage: build-recovery-control.sh SOURCE OUTPUT}
output=${2:?missing output}
epoch=1681862400

[ "$(uname -m)" = aarch64 ] || {
	echo 'FAIL recovery responder must be built natively for AArch64' >&2
	exit 1
}
[ -f "$source_file" ] && [ -r "$source_file" ] &&
	[ ! -L "$source_file" ] || {
	echo 'FAIL missing regular recovery responder source' >&2
	exit 1
}
for command in cc file readelf sha256sum strings; do
	command -v "$command" >/dev/null || {
		echo "FAIL missing responder build command: $command" >&2
		exit 1
	}
done
[ "$(cc -dumpfullversion)" = 15.2.0 ] || {
	echo 'FAIL unexpected recovery responder compiler' >&2
	exit 1
}

export SOURCE_DATE_EPOCH=$epoch
umask 077
output_directory=$(dirname "$output")
output_name=$(basename "$output")
mkdir -p "$output_directory"
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
	echo 'FAIL recovery responder has a dynamic interpreter' >&2
	exit 1
fi
readelf -l "$temporary" | grep -q 'GNU_RELRO'
if readelf -W -l "$temporary" |
	awk '$1 == "GNU_STACK" && $0 ~ /RWE/ { found=1 } END { exit !found }'
then
	echo 'FAIL recovery responder has an executable stack' >&2
	exit 1
fi
strings "$temporary" | grep -qx '/usr/sbin/kexec'
strings "$temporary" |
	grep -qx '/usr/libexec/rog5-bundle-fetch'
strings "$temporary" |
	grep -qx '/usr/libexec/rog5-bundle-verify'
strings "$temporary" | grep -qx -- '--handoff-fd3'
strings "$temporary" | grep -qx '/proc/self/fd/%d'
strings "$temporary" | grep -qx 'usb0'
strings "$temporary" | grep -qx '169.254.77.1'
strings "$temporary" | grep -qx '169.254.77.2'
if strings "$temporary" | grep -q 'ROG5_TEST_'; then
	echo 'FAIL production responder contains a test interface' >&2
	exit 1
fi
if strings "$temporary" | grep -q '/bin/sh'; then
	echo 'FAIL production responder contains a shell path' >&2
	exit 1
fi
if strings "$temporary" | grep -q 'kexec -e'; then
	echo 'FAIL production responder contains shell-style kexec text' >&2
	exit 1
fi

chmod 0755 "$temporary"
mv -T -- "$temporary" "$output"
rmdir -- "$temporary_directory"
trap - EXIT HUP INT TERM

printf 'compiler=%s\n' "$(cc --version | sed -n '1p')"
printf 'source_date_epoch=%s\n' "$SOURCE_DATE_EPOCH"
sha256sum "$source_file" "$output"
echo 'PASS hardened static-PIE AArch64 recovery responder build'
