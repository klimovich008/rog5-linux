#!/bin/sh
set -eu

archive=${1:?usage: verify-storage-preflight-arm64-runtime.sh ARCHIVE}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$(id -u)" -eq 0 ] || fail 'ARM64 runtime closure test requires root'
[ -f "$archive" ] && [ -r "$archive" ] && [ ! -L "$archive" ] ||
	fail 'unsafe storage-preflight archive'
archive=$(realpath -e "$archive")
script=$(realpath -e "$0")
case ${ROG5_STORAGE_RUNTIME_NAMESPACE:-0} in
	0)
	exec unshare --mount --propagation private env \
		ROG5_STORAGE_RUNTIME_NAMESPACE=1 "$script" "$archive"
	;;
	1) ;;
	*) fail 'invalid ARM64 runtime namespace state' ;;
esac
for command in chroot cpio cp env find grep gzip mkfs.ext4 mktemp mount \
	qemu-aarch64-static realpath rm sgdisk sha256sum truncate umount unshare; do
	command -v "$command" >/dev/null ||
		fail "missing ARM64 runtime test command: $command"
done

stage=$(mktemp -d)
cleanup() {
	umount "$stage/proc" 2>/dev/null || true
	umount "$stage/dev" 2>/dev/null || true
	rm -rf -- "$stage"
}
trap cleanup EXIT HUP INT TERM
gzip -dc "$archive" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
mount --bind /dev "$stage/dev"
mount -t proc proc "$stage/proc"
install -m 0755 "$(command -v qemu-aarch64-static)" \
	"$stage/usr/bin/qemu-aarch64-static"
mkdir -p "$stage/run/fixtures"
truncate -s 64M "$stage/run/fixtures/disk.img"
sgdisk --clear --new=1:2048:0 --typecode=1:8300 \
	"$stage/run/fixtures/disk.img" >/dev/null
truncate -s 64M "$stage/run/fixtures/ext4.img"
mkfs.ext4 -q -F "$stage/run/fixtures/ext4.img"

guest() {
	chroot "$stage" /usr/bin/qemu-aarch64-static "$@"
}

guest /usr/bin/sgdisk --version | grep -Fq 'GPT fdisk (sgdisk) version 1.0.10'
guest /usr/bin/sgdisk -v /run/fixtures/disk.img |
	grep -Fq 'No problems found.'
guest /sbin/e2fsck -fn /run/fixtures/ext4.img >/dev/null
guest /usr/sbin/resize2fs -P /run/fixtures/ext4.img |
	grep -Eq '^Estimated minimum size of the filesystem: [1-9][0-9]*$'
guest /usr/sbin/dumpe2fs -h /run/fixtures/ext4.img 2>/dev/null |
	grep -Fq 'Filesystem state:'
guest /sbin/mkfs.ext4 -V 2>&1 | grep -Fq 'mke2fs 1.47.4'
guest /usr/sbin/partprobe --help >/dev/null

sha256sum "$archive"
echo 'PASS sealed ARM64 storage-tool closure executes in an initramfs-like chroot'
