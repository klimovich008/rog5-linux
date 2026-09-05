#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
target=$repo/scripts/device/inspect-native-arch-root.sh
candidate=$repo/configs/recovery-candidates/storage-layout-stage2-native-postmortem-v1.json
artifact=$repo/artifacts/storage-layout-stage2-native-postmortem-v1/initramfs.cpio.gz
manifest=$repo/manifests/storage-layout-stage2-native-postmortem-v1-generation195.manifest
watchdog_candidate=$repo/configs/recovery-candidates/storage-layout-stage2-watchdog-probe-v1.json
watchdog_artifact=$repo/artifacts/storage-layout-stage2-watchdog-probe-v1/initramfs.cpio.gz
watchdog_manifest=$repo/manifests/storage-layout-stage2-watchdog-probe-v1-generation198.manifest

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
	'verify_boot_critical_root "$target_mount"' \
	'tree=BOOT_CRITICAL_PASS' \
	'tree=BOOT_CRITICAL_MISMATCH' \
	'ROG5_NATIVE_TREE_V1 item=%s status=%s metadata=%s sha256=%s' \
	'verify_exact_regular seal' \
	'verify_exact_link init' \
	'verify_exact_regular systemd' \
	'verify_exact_regular sshd' \
	'verify_exact_regular ssh-keygen' \
	'verify_exact_regular authorized-keys' \
	'verify_exact_regular ssh-policy' \
	'dad2b1339d6b9178f83ef96791e5c020604e16ec7921e6eaf89d3b38eec478d0' \
	'6a88a601266f5775291e394106e97fa0c1c38ac10a1715c56156cda7e8812932' \
	'ROG5_NATIVE_POSTMORTEM_V1 stage=terminal status=PASS'; do
	grep -Fq "$contract" "$target" || {
		echo "FAIL missing native-root postmortem contract: $contract" >&2
		exit 1
	}
done
[ "$(grep -Fc 'verify_exact_regular ' "$target")" -eq 6 ]
[ "$(grep -Fc 'verify_exact_link ' "$target")" -eq 1 ]
! grep -Eq 'blockdev --setrw|mount .*-o rw|e2fsck|resize2fs|tune2fs|e2image|mkfs|sgdisk|fastboot|sha256sum "\$arch_root"' "$target"

python3 - "$candidate" "$artifact" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "storage-layout-stage2-native-postmortem-v1"
assert record["candidate"] == record["bundle"] == record["target_id"]
assert record["status"] == "consumed" and record["authority"] == "none"
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

python3 - "$watchdog_candidate" "$watchdog_artifact" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "storage-layout-stage2-watchdog-probe-v1"
assert record["candidate"] == record["bundle"] == record["target_id"]
assert record["status"] == "offline" and record["authority"] == "none"
item = record["artifacts"]["initramfs.cpio.gz"]
path = Path(sys.argv[2])
assert path.stat().st_size == item["size"] == 23910865
assert hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == \
    item["sha256"] == \
    "52303ff9187c571c8c572d7ef3e2296a9c5e6670d6205a702baf335e4378fb72"
PY
grep -Fqx 'avb_generation=198' "$watchdog_manifest"
grep -Fqx 'storage_policy=read-only-watchdog-discriminator' "$watchdog_manifest"

echo 'PASS native-root postmortem is exact-geometry, read-only, boot-critical, and disposition-complete'
