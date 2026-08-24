#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-init
installer=$repo/scripts/device/install-local-arch-image.sh
builder=$repo/scripts/device/build-local-image-stage-initramfs.sh
candidate=$repo/configs/recovery-candidates/local-image-stage-v1.json
successor=$repo/configs/recovery-candidates/local-image-stage-writer-v2.json
successor_manifest=$repo/manifests/local-image-stage-writer-v2-generation111.manifest
hotplug=$repo/configs/recovery-candidates/local-image-stage-hotplug-v3.json
hotplug_manifest=$repo/manifests/local-image-stage-hotplug-v3-generation112.manifest
usbmode=$repo/configs/recovery-candidates/local-image-stage-usbmode-v5.json
usbmode_manifest=$repo/manifests/local-image-stage-usbmode-v5-generation114.manifest
claim=$repo/scripts/host/consume-local-image-stage-claim.py
successor_claim=$repo/scripts/host/consume-local-image-stage-writer-v2-claim.py
hotplug_claim=$repo/scripts/host/consume-local-image-stage-hotplug-v3-claim.py
usbmode_claim=$repo/scripts/host/consume-local-image-stage-usbmode-v5-claim.py

for path in "$init" "$installer" "$builder" "$candidate" "$successor" \
	"$successor_manifest" "$hotplug" "$hotplug_manifest" "$claim" \
	"$successor_claim" "$hotplug_claim" "$usbmode" "$usbmode_manifest" \
	"$usbmode_claim"; do
	[ -f "$path" ] && [ ! -L "$path" ] || exit 1
done
sh -n "$init" "$installer" "$builder"
python3 -m py_compile "$claim"
python3 -m py_compile "$successor_claim"
python3 -m py_compile "$hotplug_claim"
python3 -m py_compile "$usbmode_claim"
grep -Fq 'consume-exact-boot-claim.py' "$claim"
grep -Fq 'consumer.CLAIMS[PROFILE] = EXPECTED' "$claim"
grep -Fq 'consumer.consume(PROFILE)' "$claim"
! grep -Eq 'os[.](open|rename|replace|fsync)|shutil|subprocess' "$claim"

for contract in \
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
grep -Fq 'expected_release=@EXPECTED_KERNEL_RELEASE@' "$init"
grep -Fq 'expected_bundle=@EXPECTED_BUNDLE@' "$init"
grep -Fq 'echo /sbin/mdev >/proc/sys/kernel/hotplug || :' "$init"
grep -Fq 'usb_mode=/sys/bus/platform/devices/a600000.ssusb/mode' "$init"
grep -Fq '[ ! -e "$usb_mode" ] || echo peripheral >"$usb_mode" || fail usb-mode' "$init"
grep -Fq 'stable_udc=0' "$init"
grep -Fq '[ "$stable_udc" -eq 50 ] || fail udc-identity' "$init"
grep -Fq '*) fail udc-identity ;;' "$init"
! grep -Fq 'acm.usb0' "$init"
python3 - "$init" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text()
initial_scan = source.index('\nmdev -s\n')
link = source.index('ln -s "$gadget/functions/ncm.usb0"')
ufs = source.index('for module in phy-qcom-qmp-ufs.ko')
assert initial_scan < link
assert 'mdev -s' not in source[link:ufs]
PY
for contract in \
	'expected_release=${EXPECTED_RELEASE:-7.1.4-gae717d919f87}' \
	'expected_bundle=${EXPECTED_BUNDLE:-local-image-stage-v1}' \
	'UFS_MODULES and POWER_MODULES_ROOT must be supplied together' \
	'power/USB module inventory changed' \
	'modinfo -F vermagic'; do
	grep -Fq "$contract" "$builder" || {
		echo "FAIL missing staging rebuild contract: $contract" >&2
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
	'cat "$status"' \
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

python3 - "$successor" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

candidate = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert candidate["candidate"] == "local-image-stage-writer-v2"
assert candidate["status"] == "consumed"
assert candidate["authority"] == "none"
assert candidate["target_release"] == "7.1.4-g359318de534f"
repo = Path(sys.argv[1]).resolve().parents[2]
for artifact in candidate["artifacts"].values():
    path = repo / artifact["path"]
    assert path.stat().st_size == artifact["size"]
    assert hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == artifact["sha256"]
PY
grep -Fqx 'avb_generation=111' "$successor_manifest"
grep -Fqx 'phone_flash=forbidden' "$successor_manifest"

python3 - "$successor" "$hotplug" <<'PY'
import json
from pathlib import Path
import sys

previous = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
current = json.loads(Path(sys.argv[2]).read_text(encoding="ascii"))
assert previous["status"] == "consumed"
assert current["status"] == "consumed"
assert current["authority"] == "none"
assert current["candidate"] == "local-image-stage-hotplug-v3"
assert current["artifacts"]["Image"] == {
    **previous["artifacts"]["Image"],
    "path": "artifacts/local-image-stage-hotplug-v3/Image",
}
assert current["artifacts"]["board.dtb"] == {
    **previous["artifacts"]["board.dtb"],
    "path": "artifacts/local-image-stage-hotplug-v3/board.dtb",
}
assert current["artifacts"]["initramfs.cpio.gz"]["sha256"] == \
    "0cb40afda8d0068f9c504dde10b155dc71f74b85bc4612e89d368f97b05c8701"
PY
grep -Fqx 'avb_generation=112' "$hotplug_manifest"
grep -Fqx 'delta=guard-absent-optional-kernel-hotplug-sysctl-only' \
	"$hotplug_manifest"
grep -Fqx 'phone_flash=forbidden' "$hotplug_manifest"

python3 - "$hotplug" "$usbmode" <<'PY'
import json
from pathlib import Path
import sys

previous = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
current = json.loads(Path(sys.argv[2]).read_text(encoding="ascii"))
assert previous["status"] == "consumed"
assert current["status"] == "consumed"
assert current["authority"] == "none"
assert current["candidate"] == "local-image-stage-usbmode-v5"
assert current["artifacts"]["Image"]["sha256"] == previous["artifacts"]["Image"]["sha256"]
assert current["artifacts"]["board.dtb"]["sha256"] == previous["artifacts"]["board.dtb"]["sha256"]
assert current["artifacts"]["initramfs.cpio.gz"]["sha256"] == \
    "5cf22d30cc3d2cae98c700b749ebdeb3c0f74376b7246ea57cf004f17cfc8e55"
PY
grep -Fqx 'avb_generation=114' "$usbmode_manifest"
grep -Fqx 'delta=add-mature-a600000-peripheral-mode-transition-only' \
	"$usbmode_manifest"
grep -Fqx 'phone_flash=forbidden' "$usbmode_manifest"

busybox_root=$(mktemp -d)
trap 'find "$busybox_root" -depth -delete' EXIT HUP INT TERM
gzip -dc "$repo/artifacts/local-image-stage-hotplug-v3/initramfs.cpio.gz" |
	(cd "$busybox_root" && cpio -idm --quiet --no-absolute-filenames)
qemu=$(command -v qemu-aarch64-static || command -v qemu-aarch64 || true)
if [ -n "$qemu" ]; then
	if "$qemu" -L "$busybox_root" "$busybox_root/bin/busybox" sh -c \
		'set -e; echo /sbin/mdev >/proc/sys/kernel/definitely-absent; echo SURVIVED' \
		>"$busybox_root/unguarded.out" 2>/dev/null; then
		echo 'FAIL unguarded missing hotplug sysctl unexpectedly survived' >&2
		exit 1
	fi
	[ ! -s "$busybox_root/unguarded.out" ]
	"$qemu" -L "$busybox_root" "$busybox_root/bin/busybox" sh -c \
		'set -e; echo /sbin/mdev >/proc/sys/kernel/definitely-absent || :; echo SURVIVED' \
		>"$busybox_root/guarded.out" 2>/dev/null
	grep -Fqx SURVIVED "$busybox_root/guarded.out"
else
	echo 'SKIP sealed AArch64 BusyBox execution: qemu-user is unavailable' >&2
fi

echo 'PASS local-image staging uses the UFS-capable composition and one bounded image path'
