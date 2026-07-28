#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-root-entry-init
builder=$repo/scripts/device/build-persistent-root-entry-initramfs.sh
base=$repo/artifacts/ufs-discovery-v2/rog5-ufs-discovery-initramfs.cpio.gz

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in cp cpio gzip grep mktemp sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing entry-initramfs test command: $command"
done
for source in "$init" "$builder"; do
	[ -x "$source" ] ||
		fail "missing executable entry-initramfs source: $source"
	sh -n "$source"
done
[ -s "$base" ] || fail 'missing accepted UFS initramfs base'

for contract in \
	'entry_timeout=120' \
	'rog5.p2_entry_diag=1' \
	'release_file=/proc/sys/kernel/osrelease' \
	'IFS= read -r running_kernel_release <"$release_file"' \
	'block_backed_mounts=' \
	'/run/rog5-p2-entry' \
	'status=PASS' \
	'mode=early-entry' \
	'kernel=7.1.4-gcfd385a1c754' \
	'persistent_tokens=1' \
	'discovery_tokens=1' \
	'entry_tokens=1' \
	'watchdog_seconds=120' \
	'PASS P2 early-entry oracle init=entered storage=untouched watchdog=armed' \
	'ROG5 P2 entry oracle' \
	'/dev/ttyGS0'; do
	grep -Fq "$contract" "$init" ||
		fail "entry init omits contract: $contract"
done

if grep -Eq \
	'/dev/(sd|mmcblk|nvme)|mount[[:space:]].*(ext[234]|f2fs|btrfs)|blockdev|fsck|mkfs|/rog5/|authorized_keys|dropbear|sshd|fastboot|adb' \
	"$init"; then
	fail 'entry init contains a block-storage, credential, or host-control path'
fi

watchdog_line=$(grep -n '^arm_entry_watchdog$' "$init" | cut -d: -f1)
release_line=$(grep -n \
	'IFS= read -r running_kernel_release <"$release_file"' "$init" |
	cut -d: -f1)
marker_line=$(grep -n '^write_entry_marker$' "$init" | cut -d: -f1)
usb_line=$(grep -n '^if configure_entry_usb; then$' "$init" | cut -d: -f1)
[ "$watchdog_line" -lt "$release_line" ]
[ "$release_line" -lt "$marker_line" ]
[ "$marker_line" -lt "$usb_line" ]

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
"$builder" "$base" "$stage/a.cpio.gz" >/dev/null
"$builder" "$base" "$stage/b.cpio.gz" >/dev/null
cmp "$stage/a.cpio.gz" "$stage/b.cpio.gz"
if "$builder" "$base" "$stage/a.cpio.gz" >/dev/null 2>&1; then
	fail 'entry builder overwrote an existing output'
fi
if "$builder" "$base" "$base" >/dev/null 2>&1; then
	fail 'entry builder accepted its immutable input as output'
fi
cp "$base" "$stage/mutant.cpio.gz"
printf x >>"$stage/mutant.cpio.gz"
if "$builder" "$stage/mutant.cpio.gz" \
	"$stage/mutant-output.cpio.gz" >/dev/null 2>&1; then
	fail 'entry builder accepted a changed base hash'
fi
mkdir "$stage/root"
gzip -dc "$stage/a.cpio.gz" |
	(cd "$stage/root" && cpio -idm --quiet --no-absolute-filenames)
cmp "$stage/root/init" "$init"
[ -x "$stage/root/init" ]
[ ! -e "$stage/root/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/root/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit)" ]
! find "$stage/root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .

echo 'PASS deterministic credential-free P2 early-entry initramfs is RAM-only, marker-first, and reset-bounded'
