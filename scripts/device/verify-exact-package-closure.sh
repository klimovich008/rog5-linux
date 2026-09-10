#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$#" -eq 2 ] ||
	fail 'usage: verify-exact-package-closure.sh EXPECTED ACTUAL'
expected=$1
actual=$2

for command in awk cmp sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing package-closure command: $command"
done
for inventory in "$expected" "$actual"; do
	[ -f "$inventory" ] && [ ! -L "$inventory" ] && [ -r "$inventory" ] ||
		fail "package inventory is absent, linked, or unreadable: $inventory"
done

validate_inventory() {
	LC_ALL=C awk '
		BEGIN { count=0; previous="" }
		index($0, "\r") != 0 || NF != 2 ||
		$1 !~ /^[a-z0-9@._+:-]+$/ || $2 !~ /^[!-~]+$/ {
			exit 1
		}
		previous != "" && previous >= $0 { exit 1 }
		{
			previous=$0
			count++
		}
		END {
			if (count == 0) exit 1
			print count
		}
	' "$1"
}

expected_count=$(validate_inventory "$expected") ||
	fail 'expected package closure is malformed, duplicate, or unsorted'
actual_count=$(validate_inventory "$actual") ||
	fail 'actual package closure is malformed, duplicate, or unsorted'
[ "$actual_count" = "$expected_count" ] ||
	fail 'exact package closure count differs'
cmp -s "$expected" "$actual" ||
	fail 'exact package closure differs'

digest=$(sha256sum "$expected" | awk '{ print $1 }')
printf 'PASS exact package closure count=%s sha256=%s\n' \
	"$expected_count" "$digest"
