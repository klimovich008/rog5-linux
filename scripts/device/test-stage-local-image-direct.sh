#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
target=$repo/scripts/device/stage-local-image-direct.sh
streamer=$repo/scripts/host/stream-local-image-direct.py
generator=$repo/scripts/host/generate-local-image-direct-extents.py
map=$repo/configs/storage/local-image-direct-extents.tsv
builder=$repo/scripts/device/build-local-image-stage-initramfs.sh
fake=$repo/scripts/host/test-fixtures/local-image-direct-fake-target.py
candidate=$repo/configs/recovery-candidates/local-image-direct-v46.json
successor=$repo/configs/recovery-candidates/local-image-direct-v47.json
manifest=$repo/manifests/local-image-direct-v46-generation155.manifest
claim=$repo/scripts/host/consume-local-image-direct-v46-claim.py
successor_manifest=$repo/manifests/local-image-direct-v47-generation156.manifest
successor_claim=$repo/scripts/host/consume-local-image-direct-v47-claim.py
source=/home/deck/.local/state/rog5-local-image-v28-20260823-r1/arch-local-a.ext4
busybox_base=$repo/artifacts/local-image-write-benchmark-v45/initramfs.cpio.gz
[ -f "$busybox_base" ] ||
	busybox_base=$repo/artifacts/local-image-partial-inspect-v44/initramfs.cpio.gz

for path in "$target" "$streamer" "$generator" "$map" "$builder" "$fake" \
	"$candidate" "$manifest" "$claim"; do
	[ -f "$path" ] && [ ! -L "$path" ] || exit 1
done
[ -f "$successor" ] && [ ! -L "$successor" ]
for path in "$successor_manifest" "$successor_claim"; do
	[ -f "$path" ] && [ ! -L "$path" ]
done
sh -n "$target" "$builder"
python3 -m py_compile "$streamer" "$generator"
python3 -m py_compile "$fake"
python3 -m py_compile "$claim"
python3 -m py_compile "$successor_claim"
[ "$(sha256sum "$map" | cut -d ' ' -f 1)" = \
	e21b9453662d5f24536144e322ed0ef6bde7038efb44fdf1afcb80ee823ccd94 ]
for contract in \
	'extent_count=37' \
	'data_bytes=1850654720' \
	'image_sha256=533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153'; do
	grep -Fxq "$contract" "$map"
done
[ "$(awk -F '\t' 'NR > 8 { count++; bytes += $3 * 4096 } END { print count, bytes }' "$map")" = \
	"37 1850654720" ]
work=$(mktemp -d)
trap 'find "$work" -depth -delete' EXIT HUP INT TERM
if [ -f "$source" ]; then
	"$generator" "$source" --check "$map"
	"$streamer" "$source" -- python3 "$fake" "$work/state" "$map" >/dev/null
else
	echo 'SKIP direct extent regeneration: retained reviewed image is absent' >&2
fi
for contract in \
	'iflag=fullblock' \
	'oflag=direct conv=notrunc status=noxfer' \
	'timeout -k 5 180 sync -f "$partial"' \
	'timeout -k 5 180 e2fsck -fn "$partial"' \
	'mv -T "$partial" "$final"' \
	'relock || fail relock' \
	'printf b >/proc/sysrq-trigger'; do
	grep -Fq "$contract" "$target"
done
! grep -Fq 'find "$residual" -mindepth 1 -maxdepth 1 -printf' "$target"
grep -Fq 'case $inventory in' "$target"
grep -Fq "'') ;;" "$target"
grep -Fq 'DIRECT_EXTENT_MAP' "$builder"
grep -Fq 'rog5-local-image-direct-extents.tsv' "$builder"
python3 - "$candidate" <<'PY'
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "local-image-direct-v46"
assert record["status"] == "consumed"
assert record["authority"] == "none"
assert record["target_release"] == "7.1.4-g359318de534f"
artifact = record["artifacts"]["initramfs.cpio.gz"]
assert artifact["size"] == 23806105
assert artifact["sha256"] == \
    "732a107f835d882560b84e60d00caf9f3c6e10890d7e4456e7acf354d764cfc1"
PY
python3 - "$successor" <<'PY'
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "local-image-direct-v47"
assert record["status"] == "offline"
assert record["authority"] == "none"
artifact = record["artifacts"]["initramfs.cpio.gz"]
assert artifact["size"] == 23806146
assert artifact["sha256"] == \
    "d89983cd80e86dfc5f332e84482eae977ede5d1ff7880db49b6eabd4b06dc71f"
PY
grep -Fxq 'avb_generation=155' "$manifest"
grep -Fxq 'phone_flash=forbidden' "$manifest"
grep -Fq 'local-image-direct-v46-generation155-live-v1' "$claim"
grep -Fxq 'avb_generation=156' "$successor_manifest"
grep -Fxq 'phone_flash=forbidden' "$successor_manifest"
grep -Fq 'local-image-direct-v47-generation156-live-v1' "$successor_claim"
python3 - "$streamer" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")
start = source.index("def run(")
failure = source.index('fail(f"target command failed:', start)
preserve = source.rindex("sys.stdout.buffer.write(output)", start, failure)
assert preserve < failure
PY

root=$work/root
mkdir "$root"
gzip -dc "$busybox_base" |
	(cd "$root" && cpio -idm --quiet --no-absolute-filenames)
qemu=$(command -v qemu-aarch64-static || command -v qemu-aarch64 || true)
if [ -n "$qemu" ]; then
	truncate -s 8192 "$root/output"
	dd if=/dev/zero bs=4096 count=2 status=none |
		"$qemu" -L "$root" "$root/bin/busybox" dd of="$root/output" \
		bs=4096 count=2 iflag=fullblock oflag=direct conv=notrunc \
		status=noxfer 2>"$root/stats"
	[ "$(cat "$root/stats")" = "$(printf '2+0 records in\n2+0 records out')" ]
else
	echo 'SKIP sealed BusyBox direct-write dialect: qemu-user is unavailable' >&2
fi

echo 'PASS sparse Arch staging uses one canonical map and exact direct BusyBox writes'
