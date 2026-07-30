#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
stage=$repo/scripts/device/stage-arch-headless-core-rootfs.sh
verify=$repo/scripts/device/verify-staged-arch-headless-core-rootfs.sh
base_verify=$repo/scripts/device/verify-staged-arch-headless-rootfs.sh
host=$repo/scripts/host/stage-arch-rootfs.sh
runner=$repo/scripts/device/run-arch-rootfs-stage.sh
binary=$repo/artifacts/headless-indicator-v1/rog5-key-indicatord
unit=$repo/packaging/arch/rog5-key-indicator.service
modules_conf=$repo/packaging/arch/rog5-status-led.modules.conf
manifest=$repo/manifests/artifacts.tsv
expected_hash=3792745382a390ebeef37a081e532884aae07bbcd73fd9f0da1c94e67bdabbc8

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in awk file readelf sha256sum stat strings; do
	command -v "$command" >/dev/null ||
		fail "missing headless-core contract command: $command"
done
for path in "$stage" "$verify" "$base_verify" "$host"; do
	[ -f "$path" ] && [ ! -L "$path" ] && [ -x "$path" ] ||
		fail "missing executable headless-core source: $path"
	bash -n "$path"
done
[ -f "$runner" ] && [ ! -L "$runner" ] ||
	fail 'missing regular headless-core chroot runner'
bash -n "$runner"
for path in "$binary" "$unit" "$modules_conf" "$manifest"; do
	[ -f "$path" ] && [ ! -L "$path" ] ||
		fail "missing regular headless-core input: $path"
done
[ -x "$binary" ] || fail 'headless-core indicator is not executable'
[ "$(stat -c %s "$binary")" = 67520 ]
[ "$(sha256sum "$binary" | cut -d' ' -f1)" = "$expected_hash" ]
file "$binary" |
	grep -q 'ELF 64-bit LSB pie executable, ARM aarch64.*static-pie linked'
readelf -h "$binary" | grep -q 'Machine:.*AArch64'
if readelf -l "$binary" | grep -q INTERP; then
	fail 'headless-core indicator has a dynamic interpreter'
fi
if strings "$binary" | grep -q -- '--fixture'; then
	fail 'headless-core production binary contains fixture support'
fi

awk -F '\t' -v hash="$expected_hash" '
	$1 == "artifacts/headless-indicator-v1/rog5-key-indicatord" {
		count++
		if ($2 != 67520 || $3 != hash || $5 != "yes")
			exit 1
	}
	END { exit count != 1 }
' "$manifest" || fail 'headless-core artifact manifest entry is not exact'

grep -Fq 'headless-v2)' "$host"
grep -Fq 'scripts/device/stage-arch-headless-core-rootfs.sh)' "$runner"
grep -Fq 'stage-arch-headless-core-rootfs.sh' "$host"
grep -Fq 'verify-staged-arch-headless-core-rootfs.sh' "$host"
grep -Fq 'indicator_required=1' "$host"
grep -Fq 'INDICATOR_SHA256=$indicator_hash' "$host"
grep -Fq 'target=/stage/input/rog5-key-indicatord,readonly' "$host"
grep -Fq 'artifacts/headless-indicator-v1/rog5-key-indicatord' "$host"
grep -Fq '/usr/local/libexec/rog5-key-indicatord' "$stage" "$verify"
grep -Fq 'systemctl enable rog5-key-indicator.service' "$stage"
grep -Fq 'ExecStopPost=/usr/local/libexec/rog5-key-indicatord --off' "$unit"
grep -Fq 'ProtectKernelTunables=yes' "$unit"
if grep -q '^ConditionPathExists=' "$unit"; then
	fail 'headless-core indicator can silently skip before LPG probe'
fi
grep -Fq 'profile=headless-core-v2' "$stage" "$verify"
grep -Fq 'EXPECTED_HEADLESS_PROFILE:-headless-ssh-v1' "$base_verify"
grep -Fq 'find "/lib/modules/$TARGET_KERNEL_RELEASE"' "$verify"
grep -Fq "python python3 startplasma-wayland" "$verify"

if grep -Eqi \
	'chromium|greetd|krdp|kwin|mesa|nodejs|npm|pipewire|plasma|ttyd|vulkan|wireguard|wpa_supplicant' \
	"$stage" "$repo/packaging/arch/headless-packages.txt"; then
	fail 'headless-core stage enables a deferred UI or agent package'
fi
if grep -Eq \
	'fastboot|adb|/dev/(sd|mmcblk|nvme)|mkfs|fsck|mount[[:space:]].*(userdata|data)' \
	"$stage" "$verify" "$unit"; then
	fail 'headless-core root contains a phone boot or storage action'
fi

echo 'PASS successor headless-core root adds only the sealed native key indicator'
