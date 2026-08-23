#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-init
installer=$repo/scripts/device/install-local-arch-image.sh
builder=$repo/scripts/device/build-local-image-stage-initramfs.sh
candidate=$repo/configs/recovery-candidates/local-image-stage-v1.json

for path in "$init" "$installer" "$builder" "$candidate"; do
	[ -f "$path" ] && [ ! -L "$path" ] || exit 1
done
sh -n "$init" "$installer" "$builder"

for contract in \
	'expected_release=7.1.4-gae717d919f87' \
	'expected_physical_count=116' \
	'expected_udc=a600000.usb' \
	'/sbin/rog5-load-persistent-power-usb' \
	'phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko ufs-qcom.ko' \
	'blockdev --setro "$device"' \
	'/run/rog5-userdata-device' \
	'/usr/sbin/sshd -h /run/ssh_host_ed25519_key'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing staging contract: $contract" >&2
		exit 1
	}
done
! grep -Fq 'verify_no_phone_storage' "$init"
! grep -Fq 'mount_network_root' "$init"

for contract in \
	'expected_input_sha256=41f75ab6c9c74e3f511fcac4a85b1c4da93695bc56bf85ab954a42f70d83ba88' \
	'expected_image_sha256=533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153' \
	'blockdev --setrw "$userdata"' \
	'blockdev --setrw "$userdata_disk"' \
	'gzip -dc "$input" >"$partial"' \
	'e2fsck -fn "$partial"' \
	'mv -T "$partial" "$final"' \
	'relock || fail relock'; do
	grep -Fq "$contract" "$installer" || {
		echo "FAIL missing bounded installer contract: $contract" >&2
		exit 1
	}
done

python3 - "$candidate" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

candidate = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert candidate["profile"] == "persistent-root-ro-v1"
assert candidate["target_release"] == "7.1.4-gae717d919f87"
expected = {
    "Image": (38191616, "a4648dd425616adff2dfb07590be4f85d17d5305e1f72830eb85e668490046d6"),
    "board.dtb": (103098, "4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8"),
    "initramfs.cpio.gz": (23805707, "968e2ce5573f539bd329827babe184627bc26ae0bcd94386cc7d04a7edba4fda"),
}
repo = Path(sys.argv[1]).resolve().parents[2]
for name, (size, digest) in expected.items():
    path = repo / candidate["artifacts"][name]["path"]
    if not path.exists():
        continue
    assert path.stat().st_size == size
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
PY

echo 'PASS local-image staging uses the UFS-capable composition and one bounded image path'
