#!/bin/sh
set -eu

base=${1:?usage: build-persistent-root-standalone-initramfs.sh BASE OUTPUT}
output=${2:?missing output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
shutdown=$repo/initramfs/persistent-root-shutdown-standalone
expected_base=cf3f6dadfb7567da064b27ce341d2224328c8046e3bef870424dbe8ddf471827
epoch=1681862400

[ -f "$base" ] && [ ! -L "$base" ] &&
	[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ]
[ -x "$shutdown" ]
[ ! -e "$output" ]

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
root=$work/root
mkdir "$root"
gzip -dc "$base" | (cd "$root" && cpio -idm --quiet --no-absolute-filenames)
[ -x "$root/shutdown" ]

(cd "$root" && find . -type f ! -path ./shutdown -print0 | sort -z | xargs -0 sha256sum) >"$work/before"
install -m 0755 "$shutdown" "$root/shutdown"
(cd "$root" && find . -type f ! -path ./shutdown -print0 | sort -z | xargs -0 sha256sum) >"$work/after"
cmp "$work/before" "$work/after"

find "$root" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$root" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output.tmp"
mv -T "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
