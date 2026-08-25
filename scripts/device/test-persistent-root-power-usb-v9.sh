#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/persistent-root-power-usb-v9.json
initramfs=$repo/artifacts/persistent-root-power-usb-v9/initramfs.cpio.gz
claim=$repo/scripts/host/consume-persistent-root-power-usb-v9-claim.py
successor=$repo/configs/recovery-candidates/persistent-root-local-v51.json
successor_initramfs=$repo/artifacts/persistent-root-local-v51/initramfs.cpio.gz
successor_manifest=$repo/manifests/persistent-root-local-v51-generation160.manifest
successor_claim=$repo/scripts/host/consume-persistent-root-local-v51-claim.py

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
python3 -m py_compile "$successor_claim"
grep -Fq 'consume-exact-boot-claim.py' "$claim"
grep -Fq 'consumer.consume(PROFILE)' "$claim"
python3 - "$successor" "$successor_initramfs" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

record = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert record["candidate"] == "persistent-root-local-v51"
assert record["status"] == "offline"
assert record["authority"] == "none"
assert record["target_release"] == "7.1.4-gae717d919f87"
artifact = record["artifacts"]["initramfs.cpio.gz"]
assert artifact["size"] == 24006947
assert artifact["sha256"] == \
    "d2810bc803e262ea0628913d9db18d5615dead8f4b84e2e72ddfa0773d536c81"
path = Path(sys.argv[2])
if path.exists():
    assert path.stat().st_size == artifact["size"]
    assert hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == \
        artifact["sha256"]
PY
grep -Fxq 'avb_generation=160' "$successor_manifest"
grep -Fxq 'probe_policy=staged-seal-absent' "$successor_manifest"
grep -Fxq 'sdam_module_sha256=31ca158c428ce41b03b56ebf6af9c4c73664a0b87823c71803f2777e22e044df' "$successor_manifest"
grep -Fxq 'reboot_mode_module_sha256=6fff7c58aea3759d84652b9188e000ac3816517c5fdbb2958b556083afc92db3' "$successor_manifest"
grep -Fq 'persistent-root-local-v51-generation160-live-v1' "$successor_claim"

echo 'PASS V9 reuses the live-proven charging/UFS/local-root target under a fresh one-use identity'
