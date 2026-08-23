#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/persistent-root-power-usb-v9.json
initramfs=$repo/artifacts/persistent-root-power-usb-v9/initramfs.cpio.gz
claim=$repo/scripts/host/consume-persistent-root-power-usb-v9-claim.py

python3 - "$candidate" <<'PY'
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "persistent-root-power-usb-v9"
assert record["status"] == "consumed"
assert record["profile"] == "persistent-root-ro-v1"
assert record["target_release"] == "7.1.4-gae717d919f87"
assert record["artifacts"]["Image"]["sha256"] == "a4648dd425616adff2dfb07590be4f85d17d5305e1f72830eb85e668490046d6"
assert record["artifacts"]["board.dtb"]["sha256"] == "4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8"
assert record["artifacts"]["initramfs.cpio.gz"]["sha256"] == "4326c052b568a04143befc43c84b177487ccb5b13a1762b22ed178fb1f32ba97"
PY

if [ -f "$initramfs" ]; then
	[ "$(stat -c %s "$initramfs")" = 23810495 ]
	[ "$(sha256sum "$initramfs" | cut -d ' ' -f 1)" = \
		4326c052b568a04143befc43c84b177487ccb5b13a1762b22ed178fb1f32ba97 ]
	gzip -t "$initramfs"
fi
python3 -m py_compile "$claim"
grep -Fq 'consume-exact-boot-claim.py' "$claim"
grep -Fq 'consumer.consume(PROFILE)' "$claim"

echo 'PASS V9 reuses the live-proven charging/UFS/local-root target under a fresh one-use identity'
