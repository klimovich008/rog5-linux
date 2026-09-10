#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

attribute=${1:?usage: check-adreno-smmu-driver-override-state.sh DRIVER_OVERRIDE}
[ "$#" -eq 1 ] || fail 'expected one driver_override path'

for command in cat wc; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done

[ -r "$attribute" ] && [ ! -L "$attribute" ] ||
	fail 'driver_override is not a readable unlinked attribute'
byte_count=$(wc -c <"$attribute")
[ "$byte_count" -eq 7 ] ||
	fail 'driver_override is not the exact seven-byte unset representation'
value=$(cat "$attribute")
[ "$value" = '(null)' ] ||
	fail 'driver_override is not the exact kernel NULL representation'

echo 'unset-null-representation'
