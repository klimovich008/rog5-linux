#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/persistent-root-power-usb-v10.json
initramfs=$repo/artifacts/persistent-root-power-usb-v10/initramfs.cpio.gz
claim=$repo/scripts/host/consume-persistent-root-power-usb-v10-claim.py

python3 - "$candidate" <<'PY'
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "persistent-root-power-usb-v10"
assert record["status"] == "consumed"
assert record["profile"] == "persistent-root-ro-v1"
assert record["artifacts"]["Image"]["sha256"] == "a4648dd425616adff2dfb07590be4f85d17d5305e1f72830eb85e668490046d6"
assert record["artifacts"]["board.dtb"]["sha256"] == "4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8"
assert record["artifacts"]["initramfs.cpio.gz"]["sha256"] == "3e3a377f54f6bb78f6e0e0d90ec27e8a4580700996d8c1fbaa414c62afe5c14f"
PY

if [ -f "$initramfs" ]; then
	[ "$(stat -c %s "$initramfs")" = 23810962 ]
	[ "$(sha256sum "$initramfs" | cut -d ' ' -f 1)" = \
		3e3a377f54f6bb78f6e0e0d90ec27e8a4580700996d8c1fbaa414c62afe5c14f ]
	stage=$(mktemp -d)
	trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
	gzip -dc "$initramfs" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
	grep -Fxq 'expected_ufs_storage_mode=local-write' "$stage/init"
	grep -Fxq 'expected_probe_boot_id=current' "$stage/init"
	grep -Fq 'blockdev --setrw "$userdata"' "$stage/init"
	grep -Fq 'blockdev --setrw "$userdata_disk"' "$stage/init"
	grep -Fq 'write_exact_local_image_probe' "$stage/init"
	grep -Fq 'close_exact_userdata_write_window' "$stage/init"
fi
python3 -m py_compile "$claim"
grep -Fq 'consume-exact-boot-claim.py' "$claim"
grep -Fq 'consumer.consume(PROFILE)' "$claim"

echo 'PASS V10 changes only the target to the bounded one-probe local-write mode'
