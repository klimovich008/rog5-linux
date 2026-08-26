#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/storage-layout-stage2-mainline-readonly-v1.json
successor=$repo/configs/recovery-candidates/storage-layout-stage2-mainline-readonly-v2.json
initramfs=$repo/artifacts/storage-layout-stage2-mainline-readonly-v1/initramfs.cpio.gz

python3 - "$candidate" "$initramfs" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "storage-layout-stage2-mainline-readonly-v1"
assert record["bundle"] == record["candidate"] == record["target_id"]
assert record["status"] == "consumed"
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
python3 - "$successor" <<'PY'
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "storage-layout-stage2-mainline-readonly-v2"
assert record["bundle"] == record["candidate"] == record["target_id"]
assert record["status"] == "offline" and record["authority"] == "none"
assert record["artifacts"]["initramfs.cpio.gz"]["sha256"] == \
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
[ "$(sha256sum "$repo/artifacts/recovery-init-generation163/recovery-init" | cut -d ' ' -f 1)" = \
	e81ed4d2bfa88d2b8ab818025653faa5b7511e5dfe7f4fb69c9184bb1691a442 ]
[ "$(sha256sum "$repo/artifacts/recovery-init-generation163/verify-stable-recovery-initramfs.sh" | cut -d ' ' -f 1)" = \
	3c72a1d8072b4b222aea6950482c31a292e34f3296deefe18987d2d02facfd07 ]
grep -Fq 'consumed Generation 191 pre-ACM recovery mismatch' \
	"$repo/manifests/artifacts.tsv"
grep -Fq 'unbooted Generation 192 mainline Stage-2 read-only preflight' \
	"$repo/manifests/artifacts.tsv"

echo 'PASS mainline Stage-2 read-only target reuses proven charging/UFS bytes with current geometry'
