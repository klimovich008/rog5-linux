#!/bin/sh
set -eu

source_file=${1:?usage: build-recovery-bundle-verifier.sh SOURCE OUTPUT}
output=${2:?missing output}
epoch=1681862400

[ "$(uname -m)" = aarch64 ] || {
	echo 'FAIL recovery bundle verifier must be built natively for AArch64' >&2
	exit 1
}
[ -f "$source_file" ] && [ -r "$source_file" ] &&
	[ ! -L "$source_file" ] || {
	echo 'FAIL missing regular recovery bundle verifier source' >&2
	exit 1
}
for command in cc file openssl readelf sha256sum strings; do
	command -v "$command" >/dev/null || {
		echo "FAIL missing verifier build command: $command" >&2
		exit 1
	}
done
[ "$(cc -dumpfullversion)" = 15.2.0 ] || {
	echo 'FAIL unexpected recovery bundle verifier compiler' >&2
	exit 1
}
[ "$(openssl version)" = 'OpenSSL 3.5.7 9 Jun 2026 (Library: OpenSSL 3.5.7 9 Jun 2026)' ] || {
	echo 'FAIL unexpected recovery bundle verifier OpenSSL' >&2
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
	"$source_file" -o "$temporary" -lcrypto -lz

file "$temporary" |
	grep -q 'ELF 64-bit LSB pie executable, ARM aarch64.*static-pie linked'
readelf -h "$temporary" | grep -q 'Machine:.*AArch64'
if readelf -l "$temporary" | grep -q 'INTERP'; then
	echo 'FAIL recovery bundle verifier has a dynamic interpreter' >&2
	exit 1
fi
readelf -l "$temporary" | grep -q 'GNU_RELRO'
if readelf -W -l "$temporary" |
	awk '$1 == "GNU_STACK" && $0 ~ /RWE/ { found=1 } END { exit !found }'
then
	echo 'FAIL recovery bundle verifier has an executable stack' >&2
	exit 1
fi
strings "$temporary" | grep -qx '/run/rog5-bundles'
strings "$temporary" |
	grep -qx '/etc/rog5/recovery-bundle-ed25519.pub'
strings "$temporary" | grep -qx 'ED25519'
if strings "$temporary" | grep -q -- '--bundle-root'; then
	echo 'FAIL production verifier contains bundle-root override' >&2
	exit 1
fi
if strings "$temporary" | grep -q -- '--trust-key'; then
	echo 'FAIL production verifier contains trust-key override' >&2
	exit 1
fi
if strings "$temporary" | grep -q 'ROG5_BUNDLE_TEST'; then
	echo 'FAIL production verifier contains a test interface' >&2
	exit 1
fi

chmod 0755 "$temporary"
mv -T -- "$temporary" "$output"
rmdir -- "$temporary_directory"
trap - EXIT HUP INT TERM

printf 'compiler=%s\n' "$(cc --version | sed -n '1p')"
printf 'openssl=%s\n' "$(openssl version)"
printf 'source_date_epoch=%s\n' "$SOURCE_DATE_EPOCH"
sha256sum "$source_file" "$output"
echo 'PASS hardened static-PIE AArch64 recovery bundle verifier build'
