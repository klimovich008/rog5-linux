#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-configfs-beacon-init
candidate=$repo/configs/recovery-candidates/local-image-stage-configfs-v6.json
manifest=$repo/manifests/local-image-stage-configfs-v6-generation115.manifest
claim=$repo/scripts/host/consume-local-image-stage-configfs-v6-claim.py

sh -n "$init"
python3 -m py_compile "$claim"
for contract in \
	'expected_release=@EXPECTED_KERNEL_RELEASE@' \
	'expected_bundle=@EXPECTED_BUNDLE@' \
	'mount -t configfs configfs /sys/kernel/config || delayed_return 5' \
	'|| delayed_return 10' \
	'} || delayed_return 15' \
	'|| delayed_return 20' \
	'} || delayed_return 25' \
	'[ -e "/sys/class/udc/$expected_udc" ] || delayed_return 15' \
	'delayed_return 45' \
	'echo "$expected_udc" >"$gadget/UDC" || delayed_return 55' \
	'sleep 30' \
	'sleep 120'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing ConfigFS beacon contract: $contract" >&2
		exit 1
	}
done
for forbidden in '/sys/class/block' '/dev/sd' blockdev ext4 ssh kexec insmod modprobe; do
	! grep -Fq "$forbidden" "$init" || {
		echo "FAIL ConfigFS beacon contains forbidden surface: $forbidden" >&2
		exit 1
	}
done
python3 - "$candidate" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

candidate = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert candidate["candidate"] == "local-image-stage-configfs-v6"
assert candidate["status"] == "offline"
assert candidate["authority"] == "none"
repo = Path(sys.argv[1]).resolve().parents[2]
for artifact in candidate["artifacts"].values():
    path = repo / artifact["path"]
    assert path.stat().st_size == artifact["size"]
    with path.open("rb") as source:
        assert hashlib.file_digest(source, "sha256").hexdigest() == artifact["sha256"]
PY
grep -Fqx 'avb_generation=115' "$manifest"
grep -Fqx 'diagnostic=configfs-grouped-timing-and-target-usb-beacon' "$manifest"
grep -Fqx 'storage_policy=none' "$manifest"
grep -Fqx 'phone_flash=forbidden' "$manifest"
echo 'PASS ConfigFS beacon classifies every pre-bind group without storage'
