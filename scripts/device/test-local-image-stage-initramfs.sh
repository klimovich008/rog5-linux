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
globfix=$repo/configs/recovery-candidates/local-image-stage-globfix-v38.json
globfix_manifest=$repo/manifests/local-image-stage-globfix-v38-generation147.manifest
rworder=$repo/configs/recovery-candidates/local-image-stage-rworder-v39.json
rworder_manifest=$repo/manifests/local-image-stage-rworder-v39-generation148.manifest
writekernel=$repo/configs/recovery-candidates/local-image-stage-writekernel-v40.json
writekernel_manifest=$repo/manifests/local-image-stage-writekernel-v40-generation149.manifest
claim=$repo/scripts/host/consume-local-image-stage-claim.py
successor_claim=$repo/scripts/host/consume-local-image-stage-writer-v2-claim.py
hotplug_claim=$repo/scripts/host/consume-local-image-stage-hotplug-v3-claim.py
usbmode_claim=$repo/scripts/host/consume-local-image-stage-usbmode-v5-claim.py
globfix_claim=$repo/scripts/host/consume-local-image-stage-globfix-v38-claim.py
rworder_claim=$repo/scripts/host/consume-local-image-stage-rworder-v39-claim.py
writekernel_claim=$repo/scripts/host/consume-local-image-stage-writekernel-v40-claim.py

for path in "$init" "$installer" "$builder" "$candidate" "$successor" \
	"$successor_manifest" "$hotplug" "$hotplug_manifest" "$claim" \
	"$successor_claim" "$hotplug_claim" "$usbmode" "$usbmode_manifest" \
	"$usbmode_claim" "$globfix" "$globfix_manifest" "$globfix_claim" \
	"$rworder" "$rworder_manifest" "$rworder_claim" "$writekernel" \
	"$writekernel_manifest" "$writekernel_claim"; do
	[ -f "$path" ] && [ ! -L "$path" ] || exit 1
done
! grep -Fq '$watchdog_sys/timeout' "$init"
sh -n "$init" "$installer" "$builder"
python3 -m py_compile "$claim"
python3 -m py_compile "$successor_claim"
python3 -m py_compile "$hotplug_claim"
python3 -m py_compile "$usbmode_claim"
python3 -m py_compile "$globfix_claim"
python3 -m py_compile "$rworder_claim"
python3 -m py_compile "$writekernel_claim"
grep -Fq 'consume-exact-boot-claim.py' "$claim"
grep -Fq 'consumer.CLAIMS[PROFILE] = EXPECTED' "$claim"
grep -Fq 'consumer.consume(PROFILE)' "$claim"
grep -Fq 'consumer["consume"](PROFILE)' "$globfix_claim"
grep -Fq 'consumer["consume"](PROFILE)' "$rworder_claim"
grep -Fq 'consumer["consume"](PROFILE)' "$writekernel_claim"
! grep -Eq 'os[.](open|rename|replace|fsync)|shutil|subprocess' "$claim"

! grep -Fxq 'set -f' "$init" || {
	echo 'FAIL local-image stage disables the fixed sysfs globs it relies on' >&2
	exit 1
}
! grep -Fxq 'set -f' "$installer" || {
	echo 'FAIL local-image installer disables its fixed userdata and relock globs' >&2
	exit 1
}
for contract in \
	'expected_topology_count=117' \
	'"$sys_block/size")" = 408997568' \
	'expected_udc=a600000.usb' \
	'/sbin/rog5-load-persistent-power-usb' \
	'phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko ufs-qcom.ko' \
	'blockdev --setro "$device"' \
	'/run/rog5-userdata-device' \
	'if [ -e /etc/nologin ] || [ -L /etc/nologin ]; then' \
	'publish_stage runtime ENTER none' \
	'/usr/sbin/sshd -h /run/ssh_host_ed25519_key'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing staging contract: $contract" >&2
		exit 1
	}
done
for contract in \
	'arm_hardware_watchdog() {' \
	'/rog5-watchdog-modules/qcom-wdt.ko' \
	'compatible=qcom,kpss-wdt' \
	'/sbin/watchdog -F -T 30 -t 5 /dev/watchdog0' \
	'arm_hardware_watchdog || fail hardware-watchdog'; do
	grep -Fq "$contract" "$init" || exit 1
done
grep -Fq "sed -i 's/^root:[^:]*/root:x/'" "$builder"
grep -Fq "grep -Fxq 'root:x:0:0:99999:7:::'" "$builder"
grep -Fq 'expected_release=@EXPECTED_KERNEL_RELEASE@' "$init"
grep -Fq 'expected_bundle=@EXPECTED_BUNDLE@' "$init"
grep -Fq 'echo /sbin/mdev >/proc/sys/kernel/hotplug || :' "$init"
grep -Fq 'usb_mode=/sys/bus/platform/devices/a600000.ssusb/mode' "$init"
grep -Fq '[ ! -e "$usb_mode" ] || echo peripheral >"$usb_mode" || fail usb-mode' "$init"
if grep -Fq 'udc_state() {' "$init"; then
	echo 'FAIL post-bind UDC class inventory is a transient false invariant' >&2
	exit 1
fi
grep -Fq 'if echo "$expected_udc" >"$gadget/UDC"; then' "$init"
grep -Fq 'bound_udc=1' "$init"
grep -Fq 'if [ -e "/sys/class/udc/$expected_udc" ]; then' "$init"
grep -Fq '[ ! -e "/sys/class/udc/$expected_udc" ] ||' "$init"
grep -Fq '[ -z "$(cat "$gadget/UDC")" ] || fail udc-identity' "$init"
grep -Fq 'while [ "$attempt" -lt 2500 ]; do' "$init"
grep -Fq 'sleep 0.01' "$init"
grep -Fq '[ "$bound_udc" -eq 1 ] || fail udc-identity' "$init"
grep -Fq '[ "$(cat "$gadget/UDC")" = "$expected_udc" ] || fail udc-identity' "$init"
grep -Fq '[ "$count" -eq "$expected_topology_count" ] || fail "ufs-count-$count"' "$init"
for contract in \
	'classify_zero_ufs() {' \
	'ufs_dt=/sys/firmware/devicetree/base/soc@0/ufshc@1d84000' \
	'fail ufs-dt-missing' \
	'fail ufs-dt-status-missing' \
	'dd if="$ufs_dt/status" bs=1 count=4' \
	'fail ufs-dt-disabled' \
	'fail ufs-dt-status-invalid' \
	'for candidate in /sys/bus/platform/devices/*; do' \
	'[ "$(readlink -f "$candidate/of_node")" = "$ufs_dt" ] || continue' \
	'fail "ufs-dt-okay-platform-$platform_count"' \
	'fail ufs-platform-unbound' \
	'fail "ufs-bound-host-$host_count"' \
	'fail "ufs-host-$host_count-block-0"'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing zero-UFS classifier contract: $contract" >&2
		exit 1
	}
done
if grep -Fq '$(udc_state)' "$init"; then
	echo 'FAIL target still evaluates the transient post-bind UDC class' >&2
	exit 1
fi
for contract in \
	"'format=rog5-persistent-root-stage-v2'" \
	'publish_stage power-usb ENTER none' \
	'publish_stage power-usb FAIL "$power_detail"' \
	'publish_stage power-usb PASS ready' \
	'power_detail=${power_result#power-usb-}' \
	'sleep 10'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing early power/USB stage contract: $contract" >&2
		exit 1
	}
done
python3 - "$init" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text()
carrier = source.index('fail ncm-carrier')
enter = source.index('publish_stage power-usb ENTER none')
reporter = source.index('start_stage_reporter', enter)
loader = source.index('/sbin/rog5-load-persistent-power-usb', reporter)
assert carrier < enter < reporter < loader
PY
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
	'packaged module ABI changed:' \
	'modinfo -F vermagic'; do
	grep -Fq "$contract" "$builder" || {
		echo "FAIL missing staging rebuild contract: $contract" >&2
		exit 1
	}
done
grep -Fq 'watchdog_module=${WATCHDOG_MODULE:-}' "$builder"
grep -Fq 'watchdog module identity changed' "$builder"
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
python3 - "$installer" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text()
failure = source.index("printf 'state=FAIL")
reboot = source.index('return_bootloader', failure)
assert failure < reboot
disk_rw = source.index('blockdev --setrw "$userdata_disk"')
partition_rw = source.index('blockdev --setrw "$userdata"')
assert disk_rw < partition_rw
PY

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

python3 - "$globfix" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

candidate = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert candidate["candidate"] == "local-image-stage-globfix-v38"
assert candidate["status"] == "consumed"
assert candidate["authority"] == "none"
assert candidate["artifacts"]["Image"]["sha256"] == \
    "1a1958fe72201a3cb1fa7bdfc203ab5132cd236c5e4f95cdd13cc825bdf9ce22"
assert candidate["artifacts"]["board.dtb"]["sha256"] == \
    "4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8"
artifact = Path(sys.argv[1]).resolve().parents[2] / \
    candidate["artifacts"]["initramfs.cpio.gz"]["path"]
assert artifact.stat().st_size == 23804816
assert hashlib.file_digest(artifact.open("rb"), "sha256").hexdigest() == \
    "bc9770b48f516db4b91b5955e127208ff8a04bd0c3799a429437e8d0b5b01d4b"
PY
grep -Fxq 'avb_generation=147' "$globfix_manifest"
grep -Fxq 'delta=remove-installer-noglob-and-report-failure-before-reboot' \
	"$globfix_manifest"
grep -Fxq 'phone_flash=forbidden' "$globfix_manifest"

python3 - "$rworder" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

candidate = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert candidate["candidate"] == "local-image-stage-rworder-v39"
assert candidate["status"] == "consumed"
assert candidate["authority"] == "none"
artifact = Path(sys.argv[1]).resolve().parents[2] / \
    candidate["artifacts"]["initramfs.cpio.gz"]["path"]
assert artifact.stat().st_size == 23804943
assert hashlib.file_digest(artifact.open("rb"), "sha256").hexdigest() == \
    "efdd2a131fcc38cefc660df3f74552f4191604785bfe55ffa38ab02a71206d12"
PY
grep -Fxq 'avb_generation=148' "$rworder_manifest"
grep -Fxq 'delta=set-parent-disk-rw-before-partition-with-exact-readbacks' \
	"$rworder_manifest"
grep -Fxq 'phone_flash=forbidden' "$rworder_manifest"

python3 - "$writekernel" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

candidate = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
assert candidate["candidate"] == "local-image-stage-writekernel-v40"
assert candidate["status"] == "consumed"
assert candidate["authority"] == "none"
assert candidate["target_release"] == "7.1.4-g359318de534f"
assert candidate["artifacts"]["Image"]["sha256"] == \
    "a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e"
artifact = Path(sys.argv[1]).resolve().parents[2] / \
    candidate["artifacts"]["initramfs.cpio.gz"]["path"]
assert artifact.stat().st_size == 23804743
assert hashlib.file_digest(artifact.open("rb"), "sha256").hexdigest() == \
    "6ed0954e7f01fe5fd437a05872783824b5c975fa9d38d0e561b02fe80871fac8"
PY
grep -Fxq 'avb_generation=149' "$writekernel_manifest"
grep -Fxq 'delta=compose-clean-twin-bounded-write-kernel-with-corrected-stager' \
	"$writekernel_manifest"
grep -Fxq 'phone_flash=forbidden' "$writekernel_manifest"
retained_write_twins=0
for retained in \
	/home/deck/.local/state/rog5-local-image-stage-write-kernel-a-20260823-r1 \
	/home/deck/.local/state/rog5-local-image-stage-write-kernel-b-20260823-r1; do
	[ -d "$retained" ] || continue
	retained_write_twins=$((retained_write_twins + 1))
	grep -Fxq 'CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y' "$retained/.config"
	grep -Fxq 'CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=y' "$retained/.config"
	grep -Fxq 'CONFIG_NVMEM_SPMI_SDAM=y' "$retained/.config"
	grep -Fxq 'CONFIG_NVMEM_REBOOT_MODE=y' "$retained/.config"
	[ "$(sha256sum "$retained/arch/arm64/boot/Image" | cut -d ' ' -f 1)" = \
		a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e ]
	[ "$(find "$retained/deferred-ufs-modules" -type f -name '*.ko' | wc -l)" -eq 4 ]
	[ "$(find "$retained/power-usb-modules" -type f -name '*.ko' | wc -l)" -eq 15 ]
done
[ "$retained_write_twins" -eq 0 ] || [ "$retained_write_twins" -eq 2 ]

busybox_root=$(mktemp -d)
trap 'find "$busybox_root" -depth -delete' EXIT HUP INT TERM
gzip -dc "$repo/artifacts/local-image-stage-hotplug-v3/initramfs.cpio.gz" |
	(cd "$busybox_root" && cpio -idm --quiet --no-absolute-filenames)
qemu=$(command -v qemu-aarch64-static || command -v qemu-aarch64 || true)
if [ -n "$qemu" ]; then
	mkdir "$busybox_root/glob-fixture"
	touch "$busybox_root/glob-fixture/lost+found"
	"$qemu" -L "$busybox_root" "$busybox_root/bin/busybox" sh -c \
		'set -eu; mountpoint=$1; set -- "$mountpoint"/*; [ "$#" -eq 1 ] && [ "${1##*/}" = lost+found ]' \
		sh "$busybox_root/glob-fixture"
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
