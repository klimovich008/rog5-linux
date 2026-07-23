#!/bin/sh
set -eu

base=${1:?usage: build-recovery-initramfs.sh BASE_INITRAMFS INIT OUTPUT}
init=${2:?missing recovery init}
output=${3:?missing output}
expected_base=100e33ea4bc7e2d568450418bba3617f24394e8bb122a39fd5db334555d3bdca
epoch=1681862400

[ -r "$base" ] && [ -x "$init" ] || { echo 'FAIL missing initramfs input' >&2; exit 1; }
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || {
	echo 'FAIL base initramfs hash mismatch' >&2
	exit 1
}

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
gzip -dc "$base" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"
rm -f "$stage"/etc/ssh/ssh_host_* "$stage/etc/machine-id" "$stage/var/lib/dbus/machine-id"

[ -s "$stage/root/.ssh/authorized_keys" ]
! grep -q 'BEGIN .*PRIVATE KEY' "$stage/root/.ssh/authorized_keys"
grep -qx 'PasswordAuthentication no' "$stage/etc/ssh/sshd_config"
grep -qx 'PermitRootLogin prohibit-password' "$stage/etc/ssh/sshd_config"

find "$stage" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$stage" && find . -mindepth 1 -print0 | sort -z | \
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) | gzip -n >"$output.tmp"
mv "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
echo 'PASS deterministic recovery initramfs with SSH, NCM, ACM, and rollback timer'
