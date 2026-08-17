#!/bin/sh

# Resolve one partition by immutable GPT identity without trusting changing sdX
# names or Android by-name links. The caller separately requires a block node.
rog5_resolve_exact_partition() {
	[ "$#" -eq 5 ] || return 2
	sys_block=$1
	dev_root=$2
	expected_partname=$3
	expected_start=$4
	expected_size=$5
	match_count=0
	invalid=0
	candidate=

	for entry in "$sys_block"/*; do
		[ -d "$entry" ] || continue
		[ -r "$entry/uevent" ] || continue
		partname=$(sed -n 's/^PARTNAME=//p' "$entry/uevent")
		[ "$partname" = "$expected_partname" ] || continue
		match_count=$((match_count + 1))
		devname=$(sed -n 's/^DEVNAME=//p' "$entry/uevent")
		devtype=$(sed -n 's/^DEVTYPE=//p' "$entry/uevent")
		node=${entry##*/}
		case $devname in
			''|*[!A-Za-z0-9._-]*) invalid=1; continue ;;
		esac
		if [ "$devtype" != partition ] || [ "$devname" != "$node" ] ||
			[ ! -r "$entry/start" ] || [ ! -r "$entry/size" ] ||
			[ "$(tr -d '\r\n' <"$entry/start")" != "$expected_start" ] ||
			[ "$(tr -d '\r\n' <"$entry/size")" != "$expected_size" ] ||
			[ ! -e "$dev_root/$devname" ]; then
			invalid=1
			continue
		fi
		candidate=$dev_root/$devname
	done

	[ "$match_count" -eq 1 ] && [ "$invalid" -eq 0 ] &&
		[ -n "$candidate" ] || return 1
	printf '%s\n' "$candidate"
}
