#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/storage-layout-stage2-mainline-readonly-v1.json
initramfs=$repo/artifacts/storage-layout-stage2-mainline-readonly-v1/initramfs.cpio.gz

python3 - "$candidate" "$initramfs" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "storage-layout-stage2-mainline-readonly-v1"
assert record["bundle"] == record["candidate"] == record["target_id"]
assert record["status"] == "offline"
assert record["authority"] == "none"
assert record["profile"] == "persistent-root-ro-v1"
assert record["target_release"] == "7.1.4-gae717d919f87"
artifact = record["artifacts"]["initramfs.cpio.gz"]
path = Path(sys.argv[2])
assert path.stat().st_size == artifact["size"] == 24007505
assert hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == \
    artifact["sha256"] == \
    "a060e1c0e13516fa58a41b203bb5014965a335096cbc257dee91883bcc8224ba"
PY

grep -Fqx 'expected_physical_count=117' "$repo/initramfs/persistent-root-init"
grep -Fq '"$sys_block/size")" = 408997568' "$repo/initramfs/persistent-root-init"
grep -Fqx 'expected_physical_count=117' "$repo/initramfs/persistent-root-attest"
grep -Fq '=== Stage-2 partitions ===' \
	"$repo/scripts/host/run-persistent-root-storage-live-cycle.py"
grep -Fq 'qcom-battmgr-bat/temp' \
	"$repo/scripts/host/run-persistent-root-storage-live-cycle.py"
gzip -t "$initramfs"
grep -Fq 'unbooted Generation 191 mainline Stage-2 read-only preflight; RAM-only, never flash' \
	"$repo/manifests/artifacts.tsv"

echo 'PASS mainline Stage-2 read-only target reuses proven charging/UFS bytes with current geometry'
