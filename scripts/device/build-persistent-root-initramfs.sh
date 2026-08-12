#!/bin/sh
set -eu

base=${1:?usage: build-persistent-root-initramfs.sh BASE VERIFIER OUTPUT}
verifier=${2:?missing persistent-root verifier}
output=${3:?missing output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-root-init
attest=$repo/initramfs/persistent-root-attest
shutdown=$repo/initramfs/persistent-root-shutdown
expected_base=819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5
expected_verifier=bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58
epoch=1681862400

for path in "$init" "$attest" "$shutdown"; do
	[ -x "$path" ] || {
		echo "FAIL missing executable P2 initramfs source: $path" >&2
		exit 1
	}
done
[ -r "$base" ] && [ -x "$verifier" ] || {
	echo 'FAIL missing P2 initramfs binary input' >&2
	exit 1
}
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || {
	echo 'FAIL accepted discovery initramfs hash changed' >&2
	exit 1
}
[ "$(sha256sum "$verifier" | cut -d ' ' -f 1)" = \
	"$expected_verifier" ] || {
	echo 'FAIL persistent-root verifier hash changed' >&2
	exit 1
}

readelf -h "$verifier" | grep -q 'Machine:.*AArch64'
! readelf -d "$verifier" | grep -q '(NEEDED)'
! readelf -l "$verifier" | grep -q 'Requesting program interpreter'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
gzip -dc "$base" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
[ -x "$stage/sbin/persistent-root-verify" ] &&
	[ "$(sha256sum "$stage/sbin/persistent-root-verify" | cut -d ' ' -f 1)" = \
		"$expected_verifier" ] &&
	cmp "$stage/sbin/persistent-root-verify" "$verifier" || {
	echo 'FAIL base and selected persistent-root verifier differ' >&2
	exit 1
}
install -m 0755 "$init" "$stage/init"
install -m 0755 "$shutdown" "$stage/shutdown"
install -D -m 0755 "$attest" \
	"$stage/usr/local/sbin/rog5-p2-attest"
install -m 0755 "$verifier" \
	"$stage/usr/local/sbin/persistent-root-verify"

rm -f "$stage"/etc/ssh/ssh_host_* "$stage/etc/machine-id" \
	"$stage/var/lib/dbus/machine-id" "$stage/root/.ssh/authorized_keys"
[ ! -e "$stage/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit)" ]
grep -qx 'PasswordAuthentication no' "$stage/etc/ssh/sshd_config"
grep -qx 'PermitRootLogin prohibit-password' "$stage/etc/ssh/sshd_config"
! find "$stage" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .

find "$stage" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output.tmp"
mv -T -- "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
echo 'PASS deterministic credential-free P2 read-only persistent-root initramfs'
