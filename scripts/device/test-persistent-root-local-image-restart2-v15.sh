#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/persistent-root-local-image-restart2-v15.json
v14=$repo/configs/recovery-candidates/persistent-root-local-image-any-prior-v14.json
initramfs=$repo/artifacts/persistent-root-local-image-restart2-v15/initramfs.cpio.gz
runner=$repo/scripts/host/run-persistent-root-storage-live-cycle.py

python3 - "$candidate" "$v14" <<'PY'
import json
from pathlib import Path
import sys

current = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
previous = json.loads(Path(sys.argv[2]).read_text(encoding="ascii"))
assert current["candidate"] == "persistent-root-local-image-restart2-v15"
assert current["status"] == "consumed"
assert current["artifacts"]["Image"] == previous["artifacts"]["Image"]
assert current["artifacts"]["board.dtb"] == previous["artifacts"]["board.dtb"]
assert current["artifacts"]["initramfs.cpio.gz"]["sha256"] == "7895daaa285f3fd067dabd5a1dd34eaf23d02cc743af4e33d9175bab54da80dd"
PY

if [ -f "$initramfs" ]; then
	[ "$(stat -c %s "$initramfs")" = 23810989 ]
	[ "$(sha256sum "$initramfs" | cut -d ' ' -f 1)" = \
		7895daaa285f3fd067dabd5a1dd34eaf23d02cc743af4e33d9175bab54da80dd ]
	stage=$(mktemp -d)
	trap 'find "$stage" -depth -delete' EXIT HUP INT TERM
	gzip -dc "$initramfs" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
	grep -Fxq 'expected_probe_boot_id=any-prior' "$stage/init"
	grep -Fq 'read-only:any-prior) ;;' "$stage/init"
	[ "$(sha256sum "$stage/usr/libexec/rog5-reboot-bootloader" | cut -d ' ' -f 1)" = \
		68d6a69e597e9fa86ee956ee9fadc15f4283e7dd2a6032b924449330bb3e4785 ]
	python3 - "$stage/init" "$stage/shutdown" <<'PY'
from pathlib import Path
import sys
for name in sys.argv[1:]:
    source = Path(name).read_text(encoding="ascii")
    assert source.index('"$reboot_helper" || true') < source.index("printf b >/proc/sysrq-trigger")
PY
fi
! grep -Fq 'persistent-root-local-image-restart2-v15-generation108-live-v1' "$runner"
grep -Fq 'wait_for_target_host_key(cycle, anchor, target_known_hosts)' "$runner"

echo 'PASS consumed V15 retains exact any-prior and restart2-first evidence'
