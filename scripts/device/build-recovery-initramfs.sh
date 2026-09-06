#!/bin/sh
set -eu

base=${1:?usage: build-recovery-initramfs.sh BASE_INITRAMFS INIT OUTPUT [AUTHORIZED_KEY] [SHUTDOWN]}
init=${2:?missing recovery init}
output=${3:?missing output}
authorized_key=${4:-}
shutdown=${5:-}
expected_base=100e33ea4bc7e2d568450418bba3617f24394e8bb122a39fd5db334555d3bdca
epoch=1681862400

[ -r "$base" ] && [ -x "$init" ] || { echo 'FAIL missing initramfs input' >&2; exit 1; }
[ -z "$shutdown" ] || [ -x "$shutdown" ] || {
	echo 'FAIL shutdown must be executable' >&2
	exit 1
}
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || {
	echo 'FAIL base initramfs hash mismatch' >&2
	exit 1
}

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
gzip -dc "$base" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"
[ -z "$shutdown" ] ||
	install -m 0755 "$shutdown" "$stage/shutdown"
rm -f "$stage"/etc/ssh/ssh_host_* "$stage/etc/machine-id" \
	"$stage/var/lib/dbus/machine-id" "$stage/root/.ssh/authorized_keys"
if [ -n "$authorized_key" ]; then
	[ -r "$authorized_key" ] ||
		{ echo 'FAIL authorized key is not readable' >&2; exit 1; }
	grep -Eq '^(ssh-ed25519|ecdsa-sha2-nistp256|ssh-rsa) ' "$authorized_key" ||
		{ echo 'FAIL invalid authorized key format' >&2; exit 1; }
	awk 'NF { count++ } END { exit count != 1 }' "$authorized_key" ||
		{ echo 'FAIL expected exactly one authorized key' >&2; exit 1; }
	install -D -m 0600 "$authorized_key" "$stage/root/.ssh/authorized_keys"
	[ -s "$stage/root/.ssh/authorized_keys" ]
	! grep -q 'BEGIN .*PRIVATE KEY' "$stage/root/.ssh/authorized_keys"
else
	[ ! -e "$stage/root/.ssh/authorized_keys" ]
fi

grep -qx 'PasswordAuthentication no' "$stage/etc/ssh/sshd_config"
grep -qx 'PermitRootLogin prohibit-password' "$stage/etc/ssh/sshd_config"

find "$stage" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$stage" && find . -mindepth 1 -print0 | sort -z | \
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) | gzip -n >"$output.tmp"
mv "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
echo "PASS deterministic recovery initramfs with NCM, ACM, rollback, $([ -n "$shutdown" ] && echo exitrd || echo no-exitrd), and $([ -n "$authorized_key" ] && echo SSH || echo no credentials)"
