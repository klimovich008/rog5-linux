#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
probe=$repo/scripts/device/inspect-local-image-partial.sh
base=$repo/artifacts/local-image-partial-inspect-v44/initramfs.cpio.gz
candidate=$repo/configs/recovery-candidates/local-image-partial-inspect-v44.json
manifest=$repo/manifests/local-image-partial-inspect-v44-generation153.manifest
claim=$repo/scripts/host/consume-local-image-partial-inspect-v44-claim.py
for path in "$probe" "$base" "$candidate" "$manifest" "$claim"; do
	[ -f "$path" ] && [ ! -L "$path" ]
done
sh -n "$probe"
python3 -m py_compile "$claim"
for contract in \
	'ro,noload,nodev,nosuid,noexec,noatime' \
	"'format=rog5-local-image-partial-inspection-v1'" \
	"partial_type=symlink" \
	"partial_type=regular" \
	"partial_type=other" \
	"partial_type=absent" \
	"partial_blocks_512=" \
	'"$reboot_helper" >/dev/null 2>&1 &' \
	'printf b >/proc/sysrq-trigger'; do
	grep -Fq "$contract" "$probe" || exit 1
done
! grep -Eq 'blockdev --setrw|mount -t ext4 -o rw|sync|rm |rmdir|truncate|fallocate|dd ' "$probe"
python3 - "$probe" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text()
helper = source.index('"$reboot_helper" >/dev/null 2>&1 &')
sysrq = source.index('printf b >/proc/sysrq-trigger', helper)
mount = source.index('mount -t ext4 -o ro,noload')
stat = source.index("metadata=$(stat -c '%u:%g:%a:%h:%s:%b'", mount)
assert helper < sysrq
assert mount < stat
PY
root=$(mktemp -d)
trap 'find "$root" -depth -delete' EXIT HUP INT TERM
gzip -dc "$base" | (cd "$root" && cpio -idm --quiet --no-absolute-filenames)
cmp "$probe" "$root/usr/local/sbin/rog5-install-local-arch-image"
python3 - "$candidate" "$base" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "local-image-partial-inspect-v44"
assert record["status"] == "offline"
assert record["authority"] == "none"
path = Path(sys.argv[2])
artifact = record["artifacts"]["initramfs.cpio.gz"]
assert path.stat().st_size == artifact["size"] == 23804046
assert hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == \
    artifact["sha256"] == \
    "952e2f8d39bb9e691e622456a233531d286c948852434bac76e8dfddf5ec458e"
PY
grep -Fxq 'avb_generation=153' "$manifest"
grep -Fxq 'phone_flash=forbidden' "$manifest"
grep -Fq 'local-image-partial-inspect-v44-generation153-live-v1' "$claim"
echo 'PASS partial-image inspection is read-only, exact-field, bounded, and sync-independent'
