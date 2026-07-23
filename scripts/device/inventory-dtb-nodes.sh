#!/bin/sh
set -eu

dtb=${1:?usage: inventory-dtb-nodes.sh DTB}
[ -s "$dtb" ] || { echo 'FAIL missing DTB' >&2; exit 1; }

walk() {
	local parent children child path
	parent=$1
	children=$(fdtget -l "$dtb" "$parent" 2>/dev/null || true)
	for child in $children; do
		case $parent in /) path=/$child ;; *) path=$parent/$child ;; esac
		case $child in
			reserved-memory|memory@*|*ufs*|*usb*|*qupv3*|*uart*|*serial*) printf '%s\n' "$path" ;;
		esac
		walk "$path"
	done
}

walk /
