#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
executor=$repo/scripts/device/storage-layout-stage2

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in awk chmod dumpe2fs mkfs.ext4 mktemp sed truncate; do
	command -v "$command" >/dev/null ||
		fail "missing Stage-2 fixture command: $command"
done
[ -x "$executor" ] || fail 'Stage-2 executor is absent'

work=$(mktemp -d)
cleanup() {
	rm -rf -- "$work"
}
trap cleanup EXIT HUP INT TERM
functions=$work/functions.sh
awk '/^if ! exec 3<>/{ exit } { print }' "$executor" >"$functions"
chmod 0600 "$functions"
fixture=$work/exact.ext4
uuid=598a876b-a8db-4859-a01a-1b864b0a87f4
truncate -s 64M "$fixture"
mkfs.ext4 -q -F -b 4096 -m 1 -L ROG5_ARCH_A -U "$uuid" "$fixture"

(
	. "$functions"
	verify_ext4 "$fixture" "$uuid" 16384 ROG5_ARCH_A "$work/exact.log"
) || fail 'exact clean ext4 fixture was rejected'
(
	. "$functions"
	verify_ext4 "$fixture" 00000000-0000-0000-0000-000000000000 \
		16384 ROG5_ARCH_A "$work/wrong-uuid.log"
) && fail 'wrong filesystem UUID was accepted'
(
	. "$functions"
	verify_ext4 "$fixture" "$uuid" 16383 ROG5_ARCH_A "$work/wrong-blocks.log"
) && fail 'wrong filesystem block count was accepted'
(
	. "$functions"
	verify_ext4 "$fixture" "$uuid" 16384 rog5-linux "$work/wrong-label.log"
) && fail 'wrong filesystem label was accepted'

echo 'PASS Stage-2 ext4 parser accepts only the exact clean UUID, label, and geometry'
