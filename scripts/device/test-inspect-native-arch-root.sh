#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
target=$repo/scripts/device/inspect-native-arch-root.sh
candidate=$repo/configs/recovery-candidates/storage-layout-stage2-native-postmortem-v1.json
artifact=$repo/artifacts/storage-layout-stage2-native-postmortem-v1/initramfs.cpio.gz
manifest=$repo/manifests/storage-layout-stage2-native-postmortem-v1-generation195.manifest

sh -n "$target"
for contract in \
	'24:arch_root_a)' \
	'[ "$count" -eq 117 ]' \
	'verify_mount_count 0' \
	'blockdev --getro' \
	'bs=1048576 count=4' \
	'bs=1 skip=1080 count=2' \
	'od -An -tx1 -v' \
	'disposition=non-ext4' \
	'disposition=source-clone' \
	'disposition=grown-target' \
	'disposition=partial-ext4' \
	'ro,noload,nodev,nosuid,noexec,noatime' \
	'"$verifier" "$target_mount" "$native_seal"' \
	'ROG5_NATIVE_POSTMORTEM_V1 stage=terminal status=PASS'; do
	grep -Fq "$contract" "$target" || {
		echo "FAIL missing native-root postmortem contract: $contract" >&2
		exit 1
	}
done
! grep -Eq 'blockdev --setrw|mount .*-o rw|e2fsck|resize2fs|tune2fs|e2image|mkfs|sgdisk|fastboot|sha256sum "\$arch_root"' "$target"

python3 - "$candidate" "$artifact" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "storage-layout-stage2-native-postmortem-v1"
assert record["candidate"] == record["bundle"] == record["target_id"]
assert record["status"] == "offline" and record["authority"] == "none"
assert record["target_release"] == "7.1.4-g359318de534f"
item = record["artifacts"]["initramfs.cpio.gz"]
path = Path(sys.argv[2])
assert path.stat().st_size == item["size"] == 23803943
assert hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == \
    item["sha256"] == \
    "5cf50f5b2cb2a68611e07c61241c1160a47b2e91d36bd3007de86ff3a382f879"
PY
grep -Fqx 'avb_generation=195' "$manifest"
grep -Fqx 'storage_policy=read-only-p24-disposition' "$manifest"
grep -Fqx 'inspection_bound=4MiB-prefix-plus-superblock-plus-known-tree' "$manifest"
grep -Fq 'build/storage-layout-stage2-native-postmortem-v1-generation195-20260826-r1/repack/stable-recovery-a.avb.img' \
	"$repo/manifests/temporary-boot-images.tsv"

echo 'PASS native-root postmortem is exact-geometry, read-only, bounded, and disposition-complete'
