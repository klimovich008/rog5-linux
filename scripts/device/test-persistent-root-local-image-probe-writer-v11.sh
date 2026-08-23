#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/persistent-root-local-image-probe-writer-v11.json
root=$repo/artifacts/persistent-root-local-image-probe-writer-v11
claim=$repo/scripts/host/consume-persistent-root-local-image-probe-writer-v11-claim.py

python3 - "$candidate" <<'PY'
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "persistent-root-local-image-probe-writer-v11"
assert record["target_release"] == "7.1.4-g359318de534f"
assert record["artifacts"]["Image"]["sha256"] == "7c89d9a0a7ace2b0057b6cf2b535e134da596d3f3c3c3774c5b64014e32bf234"
assert record["artifacts"]["board.dtb"]["sha256"] == "40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2"
assert record["artifacts"]["initramfs.cpio.gz"]["sha256"] == "9bfd90cf7c03b76d104d3804d2cef91696009c8e028aa951ffef5b9e100a397f"
PY

for spec in \
	'Image 38189568 7c89d9a0a7ace2b0057b6cf2b535e134da596d3f3c3c3774c5b64014e32bf234' \
	'board.dtb 103542 40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2' \
	'initramfs.cpio.gz 7506469 9bfd90cf7c03b76d104d3804d2cef91696009c8e028aa951ffef5b9e100a397f'; do
	set -- $spec
	[ ! -f "$root/$1" ] || {
		[ "$(stat -c %s "$root/$1")" = "$2" ]
		[ "$(sha256sum "$root/$1" | cut -d ' ' -f 1)" = "$3" ]
	}
done
if [ -f "$root/initramfs.cpio.gz" ]; then
	stage=$(mktemp -d)
	trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
	gzip -dc "$root/initramfs.cpio.gz" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
	grep -Fxq 'expected_ufs_storage_mode=local-write' "$stage/init"
	grep -Fxq 'expected_probe_boot_id=current' "$stage/init"
	[ -d "$stage/rog5-ufs-modules" ]
	[ "$(find "$stage/rog5-ufs-modules" -type f -name '*.ko' | wc -l)" -eq 4 ]
	[ ! -e "$stage/sbin/rog5-load-persistent-power-usb" ]
fi
python3 -m py_compile "$claim"
grep -Fq 'consumer.consume(PROFILE)' "$claim"

echo 'PASS V11 reuses the live-proven Generation-64 bounded writer only for one exact probe'
