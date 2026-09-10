#!/bin/sh
set -eu

dtb=${1:?usage: verify-power-usb-active-dtb.sh BOARD_DTB}

[ -f "$dtb" ] && [ ! -L "$dtb" ] && [ -s "$dtb" ] || {
	echo 'FAIL active power/USB DTB is missing or unsafe' >&2
	exit 1
}

check_reg() {
	node=$1
	expected=$2
	actual=$(fdtget -t x "$dtb" "$node" reg 2>/dev/null) || {
		echo "FAIL active power/USB DTB lacks $node" >&2
		exit 1
	}
	[ "$actual" = "$expected" ] || {
		echo "FAIL active power/USB DTB has wrong $node geometry" >&2
		exit 1
	}
}

low=/reserved-memory/memory@cbc00000
memshare=/reserved-memory/memory@d8000000
high=/reserved-memory/memory@edc00000

check_reg "$low" '0 cbc00000 0 4400000'
check_reg "$memshare" '0 d8000000 0 800000'
check_reg "$high" '0 edc00000 0 12000000'
! fdtget "$dtb" "$low" no-map >/dev/null 2>&1 || {
	echo 'FAIL low stock-owned RAM span must remain mapped' >&2
	exit 1
}
fdtget "$dtb" "$memshare" no-map >/dev/null 2>&1 || {
	echo 'FAIL stock memshare RAM span must be no-map' >&2
	exit 1
}
! fdtget "$dtb" "$high" no-map >/dev/null 2>&1 || {
	echo 'FAIL high stock-owned RAM span must remain mapped' >&2
	exit 1
}

echo 'PASS active power/USB DTB preserves the live-proven PAS allocation exclusions'
