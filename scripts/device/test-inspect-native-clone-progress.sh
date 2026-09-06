#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
target=$repo/scripts/device/inspect-native-clone-progress.sh
archive=${1:-$repo/artifacts/storage-layout-stage2-direct-extent20-seg3a-v1/initramfs.cpio.gz}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ -x "$target" ] && [ ! -L "$target" ] ||
	fail 'missing read-only native-clone progress observer'
sh -n "$target"

for contract in \
	'probe_offset_blocks=1464081' \
	'probe_block_count=27204' \
	'probe_chunk_blocks=1024' \
	'24:arch_root_a)' \
	'[ "$count" -eq 117 ]' \
	'blockdev --getro' \
	'ro,noload,nodev,nosuid,noexec,noatime' \
	'iflag=skip_bytes,count_bytes,fullblock' \
	'ROG5_NATIVE_PROGRESS_V1 stage=source status=BEGIN' \
	'ROG5_NATIVE_PROGRESS_V1 stage=source status=PASS' \
	'ROG5_NATIVE_PROGRESS_V1 stage=target status=BEGIN' \
	'ROG5_NATIVE_PROGRESS_V1 stage=target status=MATCH' \
	'ROG5_NATIVE_PROGRESS_V1 stage=target status=MISMATCH' \
	'ROG5_NATIVE_PROGRESS_V1 stage=terminal status=PASS' \
	'"$reboot_helper" >/dev/null 2>&1 &' \
	'printf b >/proc/sysrq-trigger'; do
	grep -Fq "$contract" "$target" ||
		fail "missing observer contract: $contract"
done

if grep -Eq \
	'blockdev --setrw|mount .*-o rw|e2fsck|resize2fs|tune2fs|e2image|mkfs|sgdisk|fastboot|of="\$arch_root"|of="\$userdata"|of="\$disk"' \
	"$target"; then
	fail 'read-only observer contains a storage write or unbounded reset primitive'
fi

python3 - "$target" <<'PY'
from pathlib import Path
import re
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")

def value(name: str) -> int:
    match = re.search(rf"^{name}=([0-9]+)$", source, re.MULTILINE)
    assert match is not None, name
    return int(match.group(1))

assert value("probe_offset_blocks") == 1_464_081
assert value("probe_block_count") == 27_204
assert value("probe_chunk_blocks") == 1_024
assert value("probe_offset_blocks") + value("probe_block_count") == 1_491_285
assert source.count('dd if="$input"') == 1
assert source.count('read_range "$source_image"') == 1
assert source.count('read_range "$arch_root"') == 1
assert 'status=noxfer' in source
assert 'sha256sum "$source_chunk"' in source
assert 'sha256sum "$target_chunk"' in source
assert 'cmp "$source_chunk" "$target_chunk"' in source
assert 'verify_read_only' in source
assert 'verify_mount_count 0' in source

remaining = value("probe_block_count")
offset = value("probe_offset_blocks")
chunks = []
while remaining:
    blocks = min(remaining, value("probe_chunk_blocks"))
    chunks.append((offset, blocks))
    offset += blocks
    remaining -= blocks
assert len(chunks) == 27
assert chunks[0] == (1_464_081, 1_024)
assert chunks[-1] == (1_490_705, 580)
assert sum(blocks for _, blocks in chunks) == 27_204
assert chunks[-1][0] + chunks[-1][1] == 1_491_285
PY

for command in cpio gzip mktemp sha256sum; do
	command -v "$command" >/dev/null || fail "missing test command: $command"
done
[ -f "$archive" ] && [ ! -L "$archive" ] || fail 'missing exact sealed initramfs'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
gzip -dc "$archive" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
busybox=$stage/bin/busybox
[ -x "$busybox" ] && [ -e "$stage/lib/ld-musl-aarch64.so.1" ] ||
	fail 'sealed target BusyBox runtime is incomplete'
for applet in cmp dd sha256sum; do
	find "$stage" -type l -lname /bin/busybox -name "$applet" | grep -q . ||
		fail "sealed target lacks BusyBox applet: $applet"
done

if ! command -v qemu-aarch64-static >/dev/null; then
	echo 'SKIP sealed BusyBox runtime dialect: qemu-user is unavailable'
	echo 'PASS native-clone progress observer is read-only, exact-range, bounded, and sealed-BusyBox inventoried'
	exit 0
fi

source_fixture=$stage/run/source.fixture
copy_fixture=$stage/run/copy.fixture
mkdir -p "$stage/run"
dd if=/dev/zero of="$source_fixture" bs=1048576 count=2 status=none
printf ROG5 | dd of="$source_fixture" bs=1 seek=4096 conv=notrunc status=none
qemu-aarch64-static -L "$stage" "$busybox" dd \
	if="$source_fixture" of="$copy_fixture" ibs=1048576 obs=1048576 \
	skip=4096 count=1048576 iflag=skip_bytes,count_bytes,fullblock \
	conv=notrunc status=noxfer 2>/dev/null
[ "$(stat -c %s "$copy_fixture")" -eq 1048576 ] ||
	fail 'exact BusyBox byte-count dialect changed'
[ "$(dd if="$source_fixture" bs=1 skip=4096 count=1048576 status=none |
	sha256sum | cut -d ' ' -f 1)" = \
	"$(sha256sum "$copy_fixture" | cut -d ' ' -f 1)" ] ||
	fail 'exact BusyBox byte-offset output changed'
qemu-aarch64-static -L "$stage" "$busybox" cmp \
	"$copy_fixture" "$copy_fixture" >/dev/null

echo 'PASS native-clone progress observer is read-only, exact-range, bounded, and sealed-BusyBox tested'
