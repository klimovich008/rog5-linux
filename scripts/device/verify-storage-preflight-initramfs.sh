#!/bin/sh
set -eu

archive=${1:?usage: verify-storage-preflight-initramfs.sh ARCHIVE INIT}
init=${2:?missing recovery init}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in cmp cpio find grep gzip mktemp readelf rm stat; do
	command -v "$command" >/dev/null ||
		fail "missing storage-preflight verifier command: $command"
done
for input in "$archive" "$init"; do
	[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
		fail 'unsafe storage-preflight verifier input'
done

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
gzip -dc "$archive" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
cmp "$stage/init" "$init" || fail 'storage-preflight init identity changed'
[ -f "$stage/etc/rog5/recovery-mode" ] &&
	[ ! -L "$stage/etc/rog5/recovery-mode" ] &&
	[ "$(stat -c %a "$stage/etc/rog5/recovery-mode")" = 444 ] &&
	[ "$(cat "$stage/etc/rog5/recovery-mode")" = storage-preflight-v2 ] ||
	fail 'storage-preflight mode identity is invalid'

for absent in \
	usr/libexec/rog5-recovery-control \
	usr/libexec/rog5-bundle-fetch \
	usr/libexec/rog5-bundle-verify \
	usr/sbin/kexec \
	etc/rog5/recovery-bundle-ed25519.pub \
	root/.ssh/authorized_keys \
	usr/sbin/sshd; do
	[ ! -e "$stage/$absent" ] && [ ! -L "$stage/$absent" ] ||
		fail "storage-preflight archive retains forbidden path: $absent"
done
for path in usr/bin/sgdisk lib/ld-musl-aarch64.so.1 \
	usr/lib/libuuid.so.1 usr/lib/libpopt.so.0 usr/lib/libstdc++.so.6 \
	usr/lib/libgcc_s.so.1 sbin/e2fsck usr/sbin/dumpe2fs \
	usr/sbin/resize2fs sbin/mkfs.ext4; do
	[ -e "$stage/$path" ] || fail "storage-preflight archive lacks $path"
done
[ -L "$stage/usr/sbin/partprobe" ] &&
	[ "$(readlink "$stage/usr/sbin/partprobe")" = /bin/busybox ] ||
	fail 'storage-preflight archive lacks the fixed BusyBox partprobe applet link'
[ -L "$stage/bin/stty" ] &&
	[ "$(readlink "$stage/bin/stty")" = /bin/busybox ] ||
	fail 'storage-preflight archive lacks the fixed BusyBox stty applet link'
readelf -h "$stage/usr/bin/sgdisk" | grep -q 'Machine:.*AArch64' ||
	fail 'storage-preflight sgdisk is not AArch64'

for contract in \
	'/usr/bin/sgdisk -v "$disk"' \
	'/sbin/e2fsck -fn "$userdata"' \
	'/usr/sbin/dumpe2fs -h "$userdata"' \
	'/usr/sbin/resize2fs -P "$userdata"' \
	'filesystem_requires_recovery' \
	'needs_recovery|orphan_present' \
	'/sbin/mkfs.ext4 -V' \
	'/usr/sbin/partprobe --help' \
	'stty -F /dev/ttyGS0 raw -echo -echonl -opost clocal cread' \
	'exec 3>/dev/ttyGS0' \
	'cat "$report" >&3' \
	'ROG5_STORAGE_PREFLIGHT_V2 status=RUNNING' \
	'ROG5_STORAGE_PREFLIGHT_V2 status=FAIL' \
	'ROG5_STORAGE_PREFLIGHT_V2 status=PASS' \
	'all_read_only=1 block_mounts=0'; do
	grep -Fq "$contract" "$stage/init" ||
		fail "storage-preflight archive lacks read-only contract: $contract"
done
if grep -Eq 'sgdisk[[:space:]].*--(delete|new|zap)|blockdev[[:space:]]+--setrw|resize2fs[[:space:]]+"\$userdata"([[:space:]]|$)|mkfs\.ext4[[:space:]]+"\$' "$stage/init"; then
	fail 'storage-preflight archive contains a storage mutation command'
fi
[ -z "$(find "$stage" -type f -perm /6000 -print -quit)" ] ||
	fail 'set-ID file exists in storage-preflight archive'

trap - EXIT HUP INT TERM
rm -rf -- "$stage"
echo 'PASS read-only storage-preflight initramfs contract'
