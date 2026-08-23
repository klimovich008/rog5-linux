#!/bin/sh
set -eu

[ "$#" -eq 6 ] || {
	echo 'usage: build-local-image-stage-initramfs.sh BASE INIT INSTALL AUTHORIZED_KEY REBOOT_HELPER OUTPUT' >&2
	exit 1
}
base=$1
init=$2
installer=$3
authorized_key=$4
reboot_helper=$5
output=$6
expected_base=4326c052b568a04143befc43c84b177487ccb5b13a1762b22ed178fb1f32ba97
expected_key_sha256=04f39d5949c813450e201b7e579256b1afcd5c7fcea077d36ae445aa53519b61
expected_reboot_sha256=68d6a69e597e9fa86ee956ee9fadc15f4283e7dd2a6032b924449330bb3e4785
epoch=1681862400

fail() { echo "FAIL $*" >&2; exit 1; }
for input in "$base" "$init" "$installer" "$authorized_key" "$reboot_helper"; do
	[ -f "$input" ] && [ ! -L "$input" ] || fail "unsafe input: $input"
done
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || fail 'base hash changed'
[ "$(sha256sum "$authorized_key" | cut -d ' ' -f 1)" = "$expected_key_sha256" ] || fail 'authorized key changed'
[ "$(sha256sum "$reboot_helper" | cut -d ' ' -f 1)" = "$expected_reboot_sha256" ] || fail 'reboot helper changed'
[ ! -e "$output" ] && [ ! -L "$output" ] || fail 'output exists'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
gzip -dc "$base" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"
install -D -m 0755 "$installer" "$stage/usr/local/sbin/rog5-install-local-arch-image"
install -D -m 0755 "$reboot_helper" "$stage/usr/libexec/rog5-reboot-bootloader"
install -D -m 0600 "$authorized_key" "$stage/root/.ssh/authorized_keys"
sed -i 's/^root:[^:]*/root:!/' "$stage/etc/shadow"
grep -Fxq 'PermitRootLogin prohibit-password' "$stage/etc/ssh/sshd_config"
grep -Fxq 'PasswordAuthentication no' "$stage/etc/ssh/sshd_config"
grep -Fxq 'PubkeyAuthentication yes' "$stage/etc/ssh/sshd_config"
find "$stage" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output.tmp"
mv -T "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
echo 'PASS deterministic UFS-capable local-image staging initramfs'
