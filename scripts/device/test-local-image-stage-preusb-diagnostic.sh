#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-preusb-diagnostic-init
candidate=$repo/configs/recovery-candidates/local-image-stage-preusb-v4.json
manifest=$repo/manifests/local-image-stage-preusb-v4-generation113.manifest
claim=$repo/scripts/host/consume-local-image-stage-preusb-v4-claim.py

sh -n "$init"
python3 -m py_compile "$claim"
for contract in \
	'expected_release=@EXPECTED_KERNEL_RELEASE@' \
	'expected_bundle=@EXPECTED_BUNDLE@' \
	'echo /sbin/mdev >/proc/sys/kernel/hotplug 2>/dev/null || :' \
	'log kernel-release' \
	'sleep 5' \
	'log command-line' \
	'sleep 15' \
	'log preusb-checks-pass' \
	'sleep 25' \
	'sleep 60' \
	'"$reboot_helper" || true'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing pre-USB diagnostic contract: $contract" >&2
		exit 1
	}
done

for forbidden in \
	'/sys/class/block' '/dev/sd' 'blockdev' 'mount -t ext4' 'ssh' \
	'usb_gadget' 'insmod' 'modprobe' 'kexec'; do
	! grep -Fq "$forbidden" "$init" || {
		echo "FAIL pre-USB diagnostic contains forbidden surface: $forbidden" >&2
		exit 1
	}
done

python3 - "$candidate" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

candidate = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert candidate["candidate"] == "local-image-stage-preusb-v4"
assert candidate["status"] == "consumed"
assert candidate["authority"] == "none"
repo = Path(sys.argv[1]).resolve().parents[2]
for artifact in candidate["artifacts"].values():
    path = repo / artifact["path"]
    assert path.stat().st_size == artifact["size"]
    with path.open("rb") as source:
        assert hashlib.file_digest(source, "sha256").hexdigest() == artifact["sha256"]
PY
grep -Fqx 'avb_generation=113' "$manifest"
grep -Fqx 'diagnostic=preusb-fixed-delay-5-release-15-cmdline-25-pass' "$manifest"
grep -Fqx 'storage_policy=none' "$manifest"
grep -Fqx 'phone_flash=forbidden' "$manifest"

echo 'PASS pre-USB diagnostic distinguishes release, cmdline, and success without USB or storage'
