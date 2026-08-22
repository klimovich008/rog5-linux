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
	qemu-aarch64-static realpath rm script sed sgdisk sha256sum truncate umount \
	unshare; do
	command -v "$command" >/dev/null ||
		fail "missing ARM64 runtime test command: $command"
done

stage=$(mktemp -d)
cleanup() {
	umount "$stage/run/dirty-live" 2>/dev/null || true
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
guest /usr/sbin/dumpe2fs -h /run/fixtures/ext4.img 2>/dev/null |
	grep -Fq 'Filesystem state:'
guest /usr/sbin/resize2fs -P /run/fixtures/ext4.img |
	grep -Eq '^Estimated minimum size of the filesystem: [1-9][0-9]*$'

# A direct restart from a mounted fallback can leave a clean filesystem with
# journal replay pending. A read-only e2fsck deliberately skips that replay and
# returns zero, while resize2fs refuses the same image. Keep this discriminator
# so the target must classify the superblock before estimating a shrink size.
truncate -s 64M "$stage/run/fixtures/dirty-live.img"
mkfs.ext4 -q -F "$stage/run/fixtures/dirty-live.img"
mkdir -p "$stage/run/dirty-live"
mount -o loop "$stage/run/fixtures/dirty-live.img" "$stage/run/dirty-live"
printf '%s\n' pending-journal >"$stage/run/dirty-live/pending"
sync
cp --reflink=never "$stage/run/fixtures/dirty-live.img" \
	"$stage/run/fixtures/dirty-snapshot.img"
umount "$stage/run/dirty-live"
guest /usr/sbin/dumpe2fs -h /run/fixtures/dirty-snapshot.img 2>/dev/null |
	grep -Eq '^Filesystem features:.* needs_recovery( |$)'
guest /sbin/e2fsck -fn /run/fixtures/dirty-snapshot.img >/dev/null
if guest /usr/sbin/resize2fs -P /run/fixtures/dirty-snapshot.img \
	>"$stage/run/fixtures/dirty-resize.log" 2>&1; then
	fail 'resize2fs unexpectedly accepted journal-pending read-only input'
fi
grep -Fq "Please run 'e2fsck -f /run/fixtures/dirty-snapshot.img' first." \
	"$stage/run/fixtures/dirty-resize.log"

guest /sbin/mkfs.ext4 -V 2>&1 | grep -Fq 'mke2fs 1.47.4'
truncate -s 64M "$stage/run/fixtures/userdata-reset.img"
reset_uuid=0892bacf-3e02-41b0-84a4-5f05c2df7ce5
guest /sbin/mkfs.ext4 -q -F -b 4096 -L rog5-linux -U "$reset_uuid" -m 0 \
	-O ^casefold,^encrypt,^verity,^quota,^project \
	-E lazy_itable_init=0,lazy_journal_init=0 /run/fixtures/userdata-reset.img
guest /sbin/e2fsck -fn /run/fixtures/userdata-reset.img >/dev/null
reset_header=$(guest /usr/sbin/dumpe2fs -h /run/fixtures/userdata-reset.img 2>/dev/null)
printf '%s\n' "$reset_header" | grep -Fq "Filesystem UUID:          $reset_uuid"
printf '%s\n' "$reset_header" | grep -Fq 'Filesystem volume name:   rog5-linux'
printf '%s\n' "$reset_header" | grep -Fq 'Reserved block count:     0'
reset_features=$(printf '%s\n' "$reset_header" |
	sed -n 's/^Filesystem features:[[:space:]]*//p')
for forbidden in casefold encrypt verity quota project; do
	! printf '%s\n' "$reset_features" | grep -Eq "(^| )$forbidden( |$)" ||
		fail "sealed mkfs retained forbidden feature: $forbidden"
done
guest /usr/sbin/partprobe --help >/dev/null
script -qec "chroot $stage /usr/bin/qemu-aarch64-static /bin/stty -F /dev/tty raw -echo -echonl -opost clocal cread" \
	/dev/null >/dev/null

sha256sum "$archive"
echo 'PASS sealed ARM64 storage-tool closure executes in an initramfs-like chroot'
