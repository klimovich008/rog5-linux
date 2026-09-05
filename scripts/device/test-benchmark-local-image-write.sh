#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
benchmark=$repo/scripts/device/benchmark-local-image-write.sh
base=$repo/artifacts/local-image-write-benchmark-v45/initramfs.cpio.gz
candidate=$repo/configs/recovery-candidates/local-image-write-benchmark-v45.json
manifest=$repo/manifests/local-image-write-benchmark-v45-generation154.manifest
claim=$repo/scripts/host/consume-local-image-write-benchmark-v45-claim.py

[ -f "$benchmark" ] && [ ! -L "$benchmark" ]
for path in "$candidate" "$manifest" "$claim"; do
	[ -f "$path" ] && [ ! -L "$path" ]
done
[ ! -e "$base" ] || { [ -f "$base" ] && [ ! -L "$base" ]; }
sh -n "$benchmark"
python3 -m py_compile "$claim"
for contract in \
	'expected_partial_size=17179869184' \
	'[ "$partial_size" -ge 0 ] && [ "$partial_size" -le "$expected_partial_size" ]' \
	'test_size=33554432' \
	'blockdev --setrw "$userdata_disk"' \
	'blockdev --setrw "$userdata"' \
	'oflag=direct conv=fsync' \
	'timeout -k 5 180 dd' \
	"'direct_seconds=%e'" \
	"'buffered_seconds=%e'" \
	'sync -f "$benchmark"' \
	'ufs_error_lines=%s' \
	'temperature_decic=%s'; do
	grep -Fq "$contract" "$benchmark" || {
		echo "FAIL missing write-benchmark contract: $contract" >&2
		exit 1
	}
done
! grep -Fq '[ "$partial_size" -gt 0 ]' "$benchmark"

python3 - "$benchmark" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text()
emergency = source.index('emergency_bootloader() {')
helper = source.index('"$reboot_helper" >/dev/null 2>&1 &', emergency)
sysrq = source.index('printf b >/proc/sysrq-trigger', helper)
assert helper < sysrq
failure = source.index('fail() {')
failure_end = source.index('\n}\n', failure)
assert 'sync' not in source[failure:failure_end]
direct = source.index('of="$benchmark/direct.bin"')
buffered = source.index('of="$benchmark/buffered.bin"')
assert direct < buffered
PY

python3 - "$candidate" "$base" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "local-image-write-benchmark-v45"
assert record["status"] == "consumed"
assert record["authority"] == "none"
assert record["target_release"] == "7.1.4-g359318de534f"
artifact = record["artifacts"]["initramfs.cpio.gz"]
assert artifact["size"] == 23805026
assert artifact["sha256"] == \
    "d017b3d1bbf6b7c9974d7aba1083c3332a7aeec5611eaf00c0445e8d06f82259"
path = Path(sys.argv[2])
if path.exists():
    assert path.stat().st_size == artifact["size"]
    assert hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == \
        artifact["sha256"]
PY
grep -Fxq 'avb_generation=154' "$manifest"
grep -Fxq 'phone_flash=forbidden' "$manifest"
grep -Fq 'local-image-write-benchmark-v45-generation154-live-v1' "$claim"
if [ -f "$base" ]; then
	root=$(mktemp -d)
	trap 'find "$root" -depth -delete' EXIT HUP INT TERM
	gzip -dc "$base" | (cd "$root" && cpio -idm --quiet --no-absolute-filenames)
	qemu=$(command -v qemu-aarch64-static || command -v qemu-aarch64 || true)
	if [ -n "$qemu" ]; then
		"$qemu" -L "$root" "$root/bin/busybox" dd if=/dev/zero \
			of="$root/direct.bin" bs=1048576 count=4 oflag=direct conv=fsync status=none
		"$qemu" -L "$root" "$root/bin/busybox" dd if=/dev/zero \
			of="$root/buffered.bin" bs=1048576 count=4 conv=fsync status=none
		[ "$(stat -c %s "$root/direct.bin")" -eq 4194304 ]
		[ "$(stat -c %s "$root/buffered.bin")" -eq 4194304 ]
	else
		echo 'SKIP sealed AArch64 BusyBox direct-I/O execution: qemu-user is unavailable' >&2
	fi
else
	echo 'SKIP retained Generation 154 initramfs checks: ignored artifact is absent' >&2
fi

echo 'PASS local-image write benchmark is bounded, direct-first, and sync-independent on emergency fallback'
