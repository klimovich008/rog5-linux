#!/bin/sh
set -eu

base=${1:?usage: build-persistent-root-entry-initramfs.sh BASE OUTPUT}
output=${2:?missing output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-root-entry-init
expected_base=df1d0cdb95513d7ef6d772a3a6165d37b3b226682d92e30a2143409341bbefb1
epoch=1681862400

[ -x "$init" ] || {
	echo "FAIL missing executable P2 entry init: $init" >&2
	exit 1
}
[ -r "$base" ] || {
	echo "FAIL missing accepted discovery initramfs: $base" >&2
	exit 1
}
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || {
	echo 'FAIL accepted discovery initramfs hash changed' >&2
	exit 1
}

base_dir=$(CDPATH='' cd -- "$(dirname "$base")" && pwd)
base_path=$base_dir/$(basename "$base")
mkdir -p "$(dirname "$output")"
output_dir=$(CDPATH='' cd -- "$(dirname "$output")" && pwd)
output_path=$output_dir/$(basename "$output")
[ "$base_path" != "$output_path" ] || {
	echo 'FAIL output aliases accepted discovery initramfs' >&2
	exit 1
}
[ ! -e "$output_path" ] || {
	echo "FAIL refusing existing P2 entry output: $output_path" >&2
	exit 1
}

stage=$(mktemp -d)
temporary_output=$(mktemp "$output_dir/.rog5-p2-entry.XXXXXX")
trap 'rm -rf -- "$stage"; rm -f -- "$temporary_output"' \
	EXIT HUP INT TERM

gzip -dc "$base" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"

rm -f "$stage"/etc/ssh/ssh_host_* "$stage/etc/machine-id" \
	"$stage/var/lib/dbus/machine-id" \
	"$stage/root/.ssh/authorized_keys"
[ ! -e "$stage/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit)" ]
! find "$stage" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .

find "$stage" -exec touch -h -d "@$epoch" {} +
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$temporary_output"
gzip -t "$temporary_output"
chmod 0644 "$temporary_output"
mv -T -- "$temporary_output" "$output_path"
sha256sum "$output_path"
echo 'PASS deterministic credential-free RAM-only P2 entry initramfs'
