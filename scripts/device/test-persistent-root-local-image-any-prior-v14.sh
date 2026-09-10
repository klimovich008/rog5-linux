#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/persistent-root-local-image-any-prior-v14.json
v13=$repo/configs/recovery-candidates/persistent-root-local-image-any-prior-v13.json
initramfs=$repo/artifacts/persistent-root-local-image-any-prior-v14/initramfs.cpio.gz

python3 - "$candidate" "$v13" <<'PY'
import json
from pathlib import Path
import sys

current = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
previous = json.loads(Path(sys.argv[2]).read_text(encoding="ascii"))
assert current["candidate"] == "persistent-root-local-image-any-prior-v14"
assert current["status"] == "offline"
assert previous["status"] == "consumed"
assert current["artifacts"]["Image"] == previous["artifacts"]["Image"]
assert current["artifacts"]["board.dtb"] == previous["artifacts"]["board.dtb"]
assert current["artifacts"]["initramfs.cpio.gz"]["sha256"] == "d5261ca13bf4a484f4c7c1d62adac8e9ed01441377e159bc6879f1eb984ec222"
PY

if [ -f "$initramfs" ]; then
	[ "$(stat -c %s "$initramfs")" = 23810475 ]
	[ "$(sha256sum "$initramfs" | cut -d ' ' -f 1)" = \
		d5261ca13bf4a484f4c7c1d62adac8e9ed01441377e159bc6879f1eb984ec222 ]
	stage=$(mktemp -d)
	trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
	gzip -dc "$initramfs" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
	grep -Fxq 'expected_probe_boot_id=any-prior' "$stage/init"
	grep -Fq 'read-only:any-prior) ;;' "$stage/init"
fi
echo 'PASS unbooted V14 retains the early any-prior fix as immutable evidence'
