#!/bin/sh
set -eu

archive=${1:?usage: verify-storage-layout-stage2-arm64-runtime.sh ARCHIVE}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$(id -u)" -eq 0 ] || fail 'Stage-2 ARM64 runtime test requires root'
[ -f "$archive" ] && [ -r "$archive" ] && [ ! -L "$archive" ] ||
	fail 'unsafe Stage-2 archive'
archive=$(realpath -e "$archive")
script=$(realpath -e "$0")
repo=$(CDPATH='' cd -- "$(dirname "$script")/../.." && pwd -P)
root_tool=$repo/scripts/device/persistent-root-tool.py
case ${ROG5_STAGE2_RUNTIME_NAMESPACE:-0} in
	0)
		exec unshare --mount --propagation private env \
			ROG5_STAGE2_RUNTIME_NAMESPACE=1 "$script" "$archive"
		;;
	1) ;;
	*) fail 'invalid Stage-2 runtime namespace state' ;;
esac
for command in chroot cpio env gzip install mkfs.ext4 mktemp mount \
	qemu-aarch64-static realpath sha256sum truncate umount unshare; do
	command -v "$command" >/dev/null ||
		fail "missing Stage-2 runtime test command: $command"
done
[ -x "$root_tool" ] || fail 'persistent-root sealing oracle is absent'

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
mkdir -p "$stage/run/fixtures/tree"

guest() {
	chroot "$stage" /usr/bin/qemu-aarch64-static "$@"
}

guest /usr/sbin/tune2fs -V 2>&1 | grep -Fq 'tune2fs 1.47.4'
if guest /usr/libexec/rog5-persistent-root-verify \
	>/run/rog5-stage2-verifier-usage.log 2>&1; then
	fail 'persistent-root verifier accepted no arguments'
fi
grep -Fq 'usage:' /run/rog5-stage2-verifier-usage.log

printf '%s\n' native-root-fixture >"$stage/run/fixtures/tree/content"
: >"$stage/run/fixtures/tree/.rog5-persistent-seal"
touch -d @1681862400 "$stage/run/fixtures/tree" \
	"$stage/run/fixtures/tree/content"
tree_report=$("$root_tool" seal "$stage/run/fixtures/tree")
{
	printf '%s\n' \
		'seal_format=rog5-persistent-root-v1' \
		'generation=arch-a' \
		'source_archive_size=1' \
		'source_archive_sha256=0000000000000000000000000000000000000000000000000000000000000000' \
		'promotion_state=UNBOOTED'
	printf '%s\n' "$tree_report"
} >"$stage/run/fixtures/native.seal"
chmod 0444 "$stage/run/fixtures/native.seal"
printf '%s\n' stale-provenance >"$stage/run/fixtures/tree/.rog5-persistent-seal"
chmod 0444 "$stage/run/fixtures/tree/.rog5-persistent-seal"
cp "$stage/run/fixtures/native.seal" \
	"$stage/run/fixtures/tree/.rog5-persistent-seal.next"
chmod 0444 "$stage/run/fixtures/tree/.rog5-persistent-seal.next"
mv -f "$stage/run/fixtures/tree/.rog5-persistent-seal.next" \
	"$stage/run/fixtures/tree/.rog5-persistent-seal"
touch -d @1681862400 "$stage/run/fixtures/tree"
seal_hash=$(sha256sum "$stage/run/fixtures/native.seal" |
	awk '{print $1}')
guest /usr/libexec/rog5-persistent-root-verify \
	/run/fixtures/tree /run/fixtures/tree/.rog5-persistent-seal "$seal_hash" |
	grep -Fq 'PASS persistent root matches anchored seal'

truncate -s 64M "$stage/run/fixtures/source.ext4"
mkfs.ext4 -q -F -b 4096 -m 1 -L ROG5_ARCH_A \
	-U 598a876b-a8db-4859-a01a-1b864b0a87f4 \
	"$stage/run/fixtures/source.ext4"
truncate -s 128M "$stage/run/fixtures/target.ext4"
guest /bin/dd if=/run/fixtures/source.ext4 of=/run/fixtures/target.ext4 \
	bs=1048576 count=64 conv=fsync,notrunc >/dev/null 2>&1
source_hash=$(sha256sum "$stage/run/fixtures/source.ext4" | awk '{print $1}')
target_hash=$(guest /bin/dd if=/run/fixtures/target.ext4 bs=1048576 count=64 \
	2>/dev/null | sha256sum | awk '{print $1}')
[ "$target_hash" = "$source_hash" ] || fail 'fixture clone prefix changed'
guest /usr/sbin/tune2fs -U 11111111-2222-4333-8444-555555555555 \
	/run/fixtures/target.ext4 >/dev/null 2>&1
if guest /sbin/e2fsck -f -p /run/fixtures/target.ext4 >/dev/null 2>&1; then
	:
else
	status=$?
	[ "$status" -eq 1 ] || fail 'fixture pre-grow e2fsck failed'
fi
guest /usr/sbin/resize2fs /run/fixtures/target.ext4 >/dev/null
if guest /sbin/e2fsck -f -p /run/fixtures/target.ext4 >/dev/null 2>&1; then
	:
else
	status=$?
	[ "$status" -eq 1 ] || fail 'fixture post-grow e2fsck failed'
fi
guest /usr/sbin/dumpe2fs -h /run/fixtures/target.ext4 2>/dev/null |
	grep -Fq 'Filesystem UUID:          11111111-2222-4333-8444-555555555555'
guest /usr/sbin/dumpe2fs -h /run/fixtures/target.ext4 2>/dev/null |
	grep -Fq 'Block count:              32768'

sha256sum "$archive"
echo 'PASS sealed Stage-2 AArch64 verifier, clone, UUID, e2fsck, and grow closure'
