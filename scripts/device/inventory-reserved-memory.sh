#!/bin/sh
set -eu

dtb=${1:?usage: inventory-reserved-memory.sh DTB}
[ -s "$dtb" ] || { echo 'FAIL missing DTB' >&2; exit 1; }

for child in $(fdtget -l "$dtb" /reserved-memory); do
	node=/reserved-memory/$child
	printf '%s' "$child"
	if fdtget "$dtb" "$node" reg >/dev/null 2>&1; then
		printf ' reg='
		fdtget -t x "$dtb" "$node" reg | tr ' ' ',' | tr -d '\n'
	else
		printf ' dynamic'
	fi
	fdtget "$dtb" "$node" no-map >/dev/null 2>&1 && printf ' no-map' || true
	printf '\n'
done
