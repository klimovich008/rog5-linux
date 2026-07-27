#!/bin/sh
set -eu

source_file=${1:?usage: build-persistent-root-verifier.sh SOURCE OUTPUT}
output=${2:?missing output}
epoch=1681862400

[ "$(uname -m)" = aarch64 ] || {
	echo 'FAIL persistent-root verifier must be built natively for AArch64' >&2
	exit 1
}
[ -r "$source_file" ] && [ ! -L "$source_file" ] || {
	echo 'FAIL missing regular persistent-root verifier source' >&2
	exit 1
}
for command in cc file readelf sha256sum; do
	command -v "$command" >/dev/null || {
		echo "FAIL missing verifier build command: $command" >&2
		exit 1
	}
done
[ "$(cc -dumpfullversion)" = 15.2.0 ] || {
	echo 'FAIL unexpected persistent-root verifier compiler' >&2
	exit 1
}

export SOURCE_DATE_EPOCH=$epoch
umask 077
mkdir -p "$(dirname "$output")"
temporary=$output.tmp
trap 'rm -f -- "$temporary"' EXIT HUP INT TERM

cc -std=c11 -O2 -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$source_file" -o "$temporary"

file "$temporary" | grep -q 'ELF 64-bit LSB pie executable, ARM aarch64'
readelf -l "$temporary" |
	grep -Fq '[Requesting program interpreter: /lib/ld-musl-aarch64.so.1]'
[ "$(readelf -d "$temporary" |
	sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')" = \
	libc.musl-aarch64.so.1 ]
readelf -d "$temporary" | grep -Fq 'BIND_NOW'
readelf -l "$temporary" | grep -q 'GNU_RELRO'
if readelf -W -l "$temporary" |
	awk '$1 == "GNU_STACK" && $0 ~ /RWE/ { found=1 } END { exit !found }'
then
	echo 'FAIL persistent-root verifier has an executable stack' >&2
	exit 1
fi

chmod 0755 "$temporary"
mv -T -- "$temporary" "$output"
trap - EXIT HUP INT TERM

printf 'compiler=%s\n' "$(cc --version | sed -n '1p')"
printf 'source_date_epoch=%s\n' "$SOURCE_DATE_EPOCH"
sha256sum "$source_file" "$output"
echo 'PASS hardened AArch64 persistent-root verifier build'
