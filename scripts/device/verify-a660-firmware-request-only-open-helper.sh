#!/bin/sh
set -eu

build_dir=${1:?usage: verify-a660-firmware-request-only-open-helper.sh BUILD_DIR}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
source_file=$repo/tools/diagnostics/a660-firmware-request-only-open.c
source_verifier=$repo/scripts/device/verify-a660-firmware-request-only-open-source.sh
binary=$build_dir/rog5-a660-firmware-request-only-open
meta=$build_dir/build-meta.txt
expected_source=68f7dbb0669b2b386fba2434c58aeb039917ba1ca229479c53a1d729f124f3ef
expected_binary=d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae
expected_meta=ffb57737611ecea9a5f7d17ab74bc2b37c3d80f792e763061e902016785fff59

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$2
	label=$3
	[ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] ||
		fail "$label is missing, linked, or unreadable"
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ] ||
		fail "$label hash mismatch"
}

for command in awk cut file grep readelf sha256sum stat strings; do
	command -v "$command" >/dev/null ||
		fail "missing verification command: $command"
done
[ -x "$source_verifier" ] || fail 'missing source verifier'
"$source_verifier" "$source_file" >/dev/null

check_hash "$binary" "$expected_binary" 'open-helper binary'
check_hash "$meta" "$expected_meta" 'open-helper metadata'
[ "$(stat -c '%a:%s' "$binary")" = 755:896 ] ||
	fail 'open-helper binary mode or size changed'
[ "$(stat -c '%a:%s' "$meta")" = 644:253 ] ||
	fail 'open-helper metadata mode or size changed'

for identity in \
	'format=rog5-a660-firmware-request-only-open-v1' \
	"source_sha256=$expected_source" \
	'compiler=Ubuntu clang version 18.1.3 (1ubuntu1)' \
	"binary_sha256=$expected_binary"
do
	grep -Fqx "$identity" "$meta" ||
		fail "open-helper metadata omits: $identity"
done

file "$binary" |
	grep -Fq \
	'ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, stripped' ||
	fail 'open-helper binary identity changed'
header=$(readelf -h "$binary")
printf '%s\n' "$header" |
	grep -Eq 'Type:[[:space:]]+EXEC \(Executable file\)' ||
	fail 'open-helper is not an executable ELF'
printf '%s\n' "$header" | grep -Eq 'Machine:[[:space:]]+AArch64' ||
	fail 'open-helper architecture changed'
printf '%s\n' "$header" |
	grep -Eq 'Entry point address:[[:space:]]+0x21015c' ||
	fail 'open-helper entry point changed'

program_headers=$(readelf -lW "$binary")
if printf '%s\n' "$program_headers" |
	grep -Eq '(^|[[:space:]])(INTERP|DYNAMIC)([[:space:]]|$)'
then
	fail 'open-helper gained an interpreter or dynamic segment'
fi
printf '%s\n' "$program_headers" |
	grep -Eq 'GNU_STACK[[:space:]].*RW[[:space:]]' ||
	fail 'open-helper stack is not read/write'
if printf '%s\n' "$program_headers" |
	grep -Eq 'GNU_STACK[[:space:]].*RWE'
then
	fail 'open-helper stack is executable'
fi
readelf -rW "$binary" | grep -Fq 'There are no relocations in this file.' ||
	fail 'open-helper gained relocations'

[ "$(strings -a "$binary" | grep -Fxc '/dev/dri/renderD128')" -eq 1 ] ||
	fail 'open-helper render-node string is not exact'
[ "$(strings -a "$binary" | grep -Fxc 'OPEN_ERRNO=117')" -eq 1 ] ||
	fail 'open-helper expected-result string is not exact'
[ "$(strings -a "$binary" | grep -Fxc 'OPEN_ERRNO=unexpected')" -eq 1 ] ||
	fail 'open-helper failure-result string is not exact'
if strings -a "$binary" |
	grep -Eq 'a660_(sqe[.]fw|gmu[.]bin|zap[.]mbn)|/dev/(block|mapper|mmc|sd)'
then
	fail 'open-helper embeds firmware or storage paths'
fi

echo 'PASS exact 896-byte static AArch64 helper performs the source-locked one-open EUCLEAN check'
