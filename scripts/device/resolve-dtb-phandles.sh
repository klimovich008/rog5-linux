#!/bin/sh
set -eu

dtb=${1:?usage: resolve-dtb-phandles.sh DTB HEX_PHANDLE...}
shift
[ "$#" -gt 0 ] || { echo 'FAIL no phandles requested' >&2; exit 2; }

walk() {
	local parent children child path value target
	parent=$1
	shift
	value=$(fdtget -t x "$dtb" "$parent" phandle 2>/dev/null || true)
	for target in "$@"; do
		[ "$value" = "$target" ] && printf '%s=%s\n' "$target" "$parent"
	done
	children=$(fdtget -l "$dtb" "$parent" 2>/dev/null || true)
	for child in $children; do
		case $parent in /) path=/$child ;; *) path=$parent/$child ;; esac
		walk "$path" "$@"
	done
}

walk / "$@"
