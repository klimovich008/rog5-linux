#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
target=$repo/scripts/device/clone-local-image-to-arch-root.sh
builder=$repo/scripts/device/build-local-image-stage-initramfs.sh
candidate=$repo/configs/recovery-candidates/storage-layout-stage2-mainline-clone-v1.json
artifact=$repo/artifacts/storage-layout-stage2-mainline-clone-v1/initramfs.cpio.gz
successor=$repo/configs/recovery-candidates/storage-layout-stage2-mainline-clone-v2.json
successor_initramfs=$repo/artifacts/storage-layout-stage2-mainline-clone-v2/initramfs.cpio.gz
successor_dtb=$repo/artifacts/storage-layout-stage2-mainline-clone-v2/board.dtb
successor_manifest=$repo/manifests/storage-layout-stage2-mainline-clone-v2-generation196.manifest
current=$repo/configs/recovery-candidates/storage-layout-stage2-mainline-clone-v3.json
current_initramfs=$repo/artifacts/storage-layout-stage2-mainline-clone-v3/initramfs.cpio.gz
current_manifest=$repo/manifests/storage-layout-stage2-mainline-clone-v3-generation197.manifest

sh -n "$target"
for contract in \
	'e2image -ra -p "$source_image" "$arch_root"' \
	'24:arch_root_a)' \
	'67108824' \
	'verify_lock_state 2' \
	'target_uuid=8b03827a-cc2d-4408-8558-e9b61195f96b' \
	'target_blocks=8388603' \
	'[ "$count" -eq 117 ]' \
	'"$verifier" "$target_mount"' \
	'losetup -r "$source_loop" "$source_image"' \
	'"$verifier" "$source_verify_mount" "$native_seal"' \
	'verify_mount_count 2' \
	'format=rog5-hardware-watchdog-v1' \
	'timeout_seconds=30' \
	'kill -0 "$hardware_watchdog_pid"' \
	'ROG5_NATIVE_CLONE_V1 stage=terminal status=PASS'; do
	grep -Fq "$contract" "$target" || {
		echo "FAIL missing native-clone contract: $contract" >&2
		exit 1
	}
done
! grep -Fq 'sha256sum "$source_image"' "$target"
! grep -Eq 'sgdisk|mkfs|fastboot|/dev/sd[a-z]24' "$target"
grep -Fq 'native_seal=${NATIVE_SEAL:-}' "$builder"
grep -Fq 'ln -s /proc/mounts "$stage/etc/mtab"' "$builder"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
source=$work/source.ext4
clone=$work/clone.ext4
truncate -s 64M "$source"
mkfs.ext4 -q -F -b 4096 -L ROG5_TEST "$source"
printf 'allocated-block-clone\n' >"$work/payload"
debugfs -w -R "write $work/payload /payload" "$source" >/dev/null 2>&1
dd if=/dev/urandom of="$clone" bs=1M count=64 status=none
e2image -ra -p "$source" "$clone" >/dev/null 2>&1
e2fsck -fn "$clone" >/dev/null 2>&1
[ "$(debugfs -R 'cat /payload' "$clone" 2>/dev/null)" = allocated-block-clone ]

python3 - "$candidate" "$artifact" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "storage-layout-stage2-mainline-clone-v1"
assert record["candidate"] == record["bundle"] == record["target_id"]
assert record["status"] == "consumed" and record["authority"] == "none"
assert record["target_release"] == "7.1.4-g359318de534f"
item = record["artifacts"]["initramfs.cpio.gz"]
path = Path(sys.argv[2])
assert path.stat().st_size == item["size"] == 23804636
assert hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == \
    item["sha256"] == \
    "a4d096eae3909c61fe0ea3eefb70b09e58e74e481c0b695024709c2ede3d9e99"
PY

python3 - "$successor" "$successor_initramfs" "$successor_dtb" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "storage-layout-stage2-mainline-clone-v2"
assert record["candidate"] == record["bundle"] == record["target_id"]
assert record["status"] == "consumed" and record["authority"] == "none"
expected = {
    "initramfs.cpio.gz": (
        Path(sys.argv[2]),
        23912736,
        "7d530c37d9ede1febd3aa2854bb8b7abffee24d5071fb426df35f12abba2854d",
    ),
    "board.dtb": (
        Path(sys.argv[3]),
        103226,
        "9d1bcd7f2dbbdfb0dfe48124de4a0763712c3375465d72987f18bb316435427e",
    ),
}
for name, (path, size, digest) in expected.items():
    item = record["artifacts"][name]
    assert path.stat().st_size == item["size"] == size
    assert hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == \
        item["sha256"] == digest
PY
grep -Fqx 'avb_generation=196' "$successor_manifest"
grep -Fqx 'watchdog=qcom-kpss-30s-ping5s' "$successor_manifest"

python3 - "$current" "$current_initramfs" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "storage-layout-stage2-mainline-clone-v3"
assert record["candidate"] == record["bundle"] == record["target_id"]
assert record["status"] == "offline" and record["authority"] == "none"
item = record["artifacts"]["initramfs.cpio.gz"]
path = Path(sys.argv[2])
assert path.stat().st_size == item["size"] == 23912989
assert hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == \
    item["sha256"] == \
    "721f45d2dc97958470ae496afe6b2383ec93642e0a5823031a716b1dcbf5a0eb"
PY
grep -Fqx 'avb_generation=197' "$current_manifest"
grep -Fqx 'watchdog=qcom-kpss-30s-ping5s-no-sysfs-dependency' "$current_manifest"

echo 'PASS p24 clone is exact-scope, allocated-block, power/thermal-gated, sealed, and hostile-destination tested'
