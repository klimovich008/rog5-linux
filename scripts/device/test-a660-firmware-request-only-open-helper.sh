#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
source_file=$repo/tools/diagnostics/a660-firmware-request-only-open.c
source_verifier=$repo/scripts/device/verify-a660-firmware-request-only-open-source.sh
source_test=$repo/scripts/device/test-a660-firmware-request-only-open-source.sh
builder=$repo/scripts/device/build-a660-firmware-request-only-open-helper.sh
binary_verifier=$repo/scripts/device/verify-a660-firmware-request-only-open-helper.sh

for input in "$source_verifier" "$source_test" "$builder" "$binary_verifier"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 open-helper tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done
[ -f "$source_file" ] && [ ! -L "$source_file" ] || {
	echo 'FAIL missing A660 open-helper source' >&2
	exit 1
}

for contract in \
	68f7dbb0669b2b386fba2434c58aeb039917ba1ca229479c53a1d729f124f3ef \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	ffb57737611ecea9a5f7d17ab74bc2b37c3d80f792e763061e902016785fff59 \
	'/root/build/a660-firmware-request-only-open' \
	'--target=aarch64-linux-gnu' \
	'-nostdlib -static' \
	'--build-id=none' \
	'--no-dynamic-linker' \
	'/dev/dri/renderD128' \
	'OPEN_ERRNO=117' \
	'SYS_OPENAT = 56' \
	'EUCLEAN = 117' \
	'exactly one openat invocation' \
	'There are no relocations in this file.'
do
	if ! grep -Fq -- "$contract" "$source_file" "$source_verifier" \
		"$source_test" "$builder" "$binary_verifier"
	then
		echo "FAIL A660 open-helper contract omits: $contract" >&2
		exit 1
	fi
done

"$source_test"

if [ -n "${HELPER_BUILD_A:-}" ] || [ -n "${HELPER_BUILD_B:-}" ]; then
	[ -n "${HELPER_BUILD_A:-}" ] && [ -n "${HELPER_BUILD_B:-}" ]
	[ "$(stat -Lc '%d:%i' "$HELPER_BUILD_A")" != \
		"$(stat -Lc '%d:%i' "$HELPER_BUILD_B")" ] || {
		echo 'FAIL helper build directories must be distinct' >&2
		exit 1
	}
	"$binary_verifier" "$HELPER_BUILD_A"
	"$binary_verifier" "$HELPER_BUILD_B"
	cmp "$HELPER_BUILD_A/rog5-a660-firmware-request-only-open" \
		"$HELPER_BUILD_B/rog5-a660-firmware-request-only-open"
	cmp "$HELPER_BUILD_A/build-meta.txt" "$HELPER_BUILD_B/build-meta.txt"
	echo 'PASS two isolated A660 one-open helper builds are byte-identical'
fi

if grep -Eq \
	'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|/dev/(block|mapper|mmc|sd)' \
	"$source_file" "$source_verifier" "$source_test" "$builder" \
	"$binary_verifier"
then
	echo 'FAIL A660 open-helper path contains phone-storage access' >&2
	exit 1
fi

echo 'PASS A660 open helper is source-mutation-tested, static, exact-node, one-open, reproducible, and storage-blind'
