#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-udc-inventory-init
candidate=$repo/configs/recovery-candidates/local-image-stage-udc-v7.json
manifest=$repo/manifests/local-image-stage-udc-v7-generation116.manifest
claim=$repo/scripts/host/consume-local-image-stage-udc-v7-claim.py
stable_candidate=$repo/configs/recovery-candidates/local-image-stage-udc-stable-v8.json
stable_manifest=$repo/manifests/local-image-stage-udc-stable-v8-generation117.manifest
stable_claim=$repo/scripts/host/consume-local-image-stage-udc-stable-v8-claim.py

sh -n "$init"
python3 -m py_compile "$claim"
python3 -m py_compile "$stable_claim"
for contract in \
	'expected_release=@EXPECTED_KERNEL_RELEASE@' \
	'expected_bundle=@EXPECTED_BUNDLE@' \
	'[ -e "/sys/class/udc/$expected_udc" ] || delayed_return 5' \
	'sleep 5' \
	'[ "$extra_count" -ne 0 ] || delayed_return 10' \
	'[ "$extra_count" -eq 1 ] || delayed_return 70' \
	'a800000.usb) delayed_return 15' \
	'a600000.dwc3) delayed_return 20' \
	'a800000.dwc3) delayed_return 25' \
	'ci_hdrc.*) delayed_return 30' \
	'musb*|*.musb) delayed_return 35' \
	'dwc2*|*.dwc2) delayed_return 40' \
	'dummy_udc.*) delayed_return 45' \
	'*.usb) delayed_return 50' \
	'*.dwc3) delayed_return 55' \
	'*) delayed_return 60' \
	'sleep 120'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing UDC inventory contract: $contract" >&2
		exit 1
	}
done
for forbidden in usb_gadget '/sys/class/block' '/dev/sd' blockdev ext4 ssh kexec insmod modprobe; do
	! grep -Fq "$forbidden" "$init" || {
		echo "FAIL UDC inventory contains forbidden surface: $forbidden" >&2
		exit 1
	}
done
python3 - "$candidate" <<'PY'
import hashlib, json, sys
from pathlib import Path
c = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert c["candidate"] == "local-image-stage-udc-v7"
assert c["status"] == "consumed" and c["authority"] == "none"
repo = Path(sys.argv[1]).resolve().parents[2]
for a in c["artifacts"].values():
    p = repo / a["path"]
    assert p.stat().st_size == a["size"]
    with p.open("rb") as f:
        assert hashlib.file_digest(f, "sha256").hexdigest() == a["sha256"]
PY
grep -Fqx 'avb_generation=116' "$manifest"
grep -Fqx 'diagnostic=one-extra-udc-basename-pattern-timing' "$manifest"
grep -Fqx 'storage_policy=none' "$manifest"
grep -Fqx 'phone_flash=forbidden' "$manifest"
python3 - "$candidate" "$stable_candidate" <<'PY'
import json, sys
from pathlib import Path
previous = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
current = json.loads(Path(sys.argv[2]).read_text(encoding="ascii"))
assert previous["status"] == "consumed"
assert current["candidate"] == "local-image-stage-udc-stable-v8"
assert current["status"] == "consumed" and current["authority"] == "none"
assert current["artifacts"]["Image"]["sha256"] == previous["artifacts"]["Image"]["sha256"]
assert current["artifacts"]["board.dtb"]["sha256"] == previous["artifacts"]["board.dtb"]["sha256"]
assert current["artifacts"]["initramfs.cpio.gz"]["sha256"] == "3cf4d974f21170ab143bf34f4e10b190d69a0743951f90e870d16713d826ecb9"
PY
grep -Fqx 'avb_generation=117' "$stable_manifest"
grep -Fqx 'diagnostic=five-second-stabilized-one-extra-udc-basename' "$stable_manifest"
grep -Fqx 'phone_flash=forbidden' "$stable_manifest"
echo 'PASS UDC inventory classifies one extra basename without binding or storage'
