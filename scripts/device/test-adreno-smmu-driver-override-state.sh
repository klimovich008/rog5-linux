#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
checker=$repo/scripts/device/check-adreno-smmu-driver-override-state.sh

[ -x "$checker" ] || {
	echo 'FAIL missing executable Adreno SMMU driver-override checker' >&2
	exit 1
}
sh -n "$checker"

for contract in \
	'usage: check-adreno-smmu-driver-override-state.sh DRIVER_OVERRIDE' \
	'[ "$byte_count" -eq 7 ]' \
	'[ "$value" = '\''(null)'\'' ]' \
	'unset-null-representation'
do
	grep -Fq "$contract" "$checker" || {
		echo "FAIL driver-override checker omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'fastboot|adb|ssh|scp|insmod|rmmod|modprobe|drivers_probe|driver_override.*>|>.*driver_override|tee.*driver_override|[[:space:]]mount[[:space:]]|[[:space:]]dd[[:space:]]' \
	"$checker"
then
	echo 'FAIL driver-override checker contains a control or write path' >&2
	exit 1
fi

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
attribute=$stage/driver_override

printf '(null)\n' >"$attribute"
[ "$("$checker" "$attribute")" = unset-null-representation ] || {
	echo 'FAIL exact kernel NULL representation was not accepted' >&2
	exit 1
}

reject() {
	description=$1
	shift
	"$@" >"$attribute"
	if "$checker" "$attribute" >/dev/null 2>&1; then
		echo "FAIL driver-override checker accepted $description" >&2
		exit 1
	fi
}

reject 'an empty file' sh -c ':'
reject 'an empty line' printf '\n'
reject 'a missing newline' printf '(null)'
reject 'an extra newline' printf '(null)\n\n'
reject 'a literal driver name' printf 'arm-smmu\n'
reject 'a lookalike value' printf ' (null)\n'

ln -s "$attribute" "$stage/linked"
if "$checker" "$stage/linked" >/dev/null 2>&1; then
	echo 'FAIL driver-override checker accepted a symlink' >&2
	exit 1
fi

echo 'PASS exact seven-byte kernel NULL representation is the only accepted unset driver override'
