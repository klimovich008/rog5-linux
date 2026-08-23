#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/persistent-root-local-image-any-prior-v12.json
initramfs=$repo/artifacts/persistent-root-local-image-any-prior-v12/initramfs.cpio.gz
claim=$repo/scripts/host/consume-persistent-root-local-image-any-prior-v12-claim.py

python3 - "$candidate" <<'PY'
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "persistent-root-local-image-any-prior-v12"
assert record["status"] == "consumed"
assert record["target_release"] == "7.1.4-gae717d919f87"
assert record["artifacts"]["initramfs.cpio.gz"]["sha256"] == "eb93a9c7cf86ed5c50f5099ea8fc40e034f844070cc4b7499295125855f51d20"
PY

if [ -f "$initramfs" ]; then
	[ "$(stat -c %s "$initramfs")" = 23810540 ]
	[ "$(sha256sum "$initramfs" | cut -d ' ' -f 1)" = \
		eb93a9c7cf86ed5c50f5099ea8fc40e034f844070cc4b7499295125855f51d20 ]
	stage=$(mktemp -d)
	trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
	gzip -dc "$initramfs" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
	grep -Fxq 'expected_ufs_storage_mode=read-only' "$stage/init"
	grep -Fxq 'expected_probe_boot_id=any-prior' "$stage/init"
	grep -Fxq 'expected_probe_boot_id=any-prior' "$stage/usr/local/sbin/rog5-p2-attest"
	grep -Fq '[ "$probe_boot_id" != "$target_boot_id" ]' "$stage/init"
	grep -Fq '[ "$probe_boot_id" != "$current_boot_id" ]' "$stage/usr/local/sbin/rog5-p2-attest"
fi
python3 -m py_compile "$claim"
grep -Fq 'consumer.consume(PROFILE)' "$claim"

echo 'PASS V12 reads one canonical prior-writer probe and keeps the current charging/UFS stack read-only'
