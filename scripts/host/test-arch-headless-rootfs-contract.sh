#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
packages=$repo/packaging/arch/headless-packages.txt
stage=$repo/scripts/device/stage-arch-headless-rootfs.sh
verify=$repo/scripts/device/verify-staged-arch-headless-rootfs.sh
runner=$repo/scripts/device/run-arch-rootfs-stage.sh
host=$repo/scripts/host/stage-arch-rootfs.sh
fixture=$repo/configs/ssh/rog5-headless-build-fixture.pub

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for path in "$stage" "$verify" "$host"; do
	if [ ! -f "$path" ] || [ -L "$path" ] || [ ! -x "$path" ]; then
		fail "missing executable headless-root source: $path"
	fi
	bash -n "$path"
done
if [ ! -f "$runner" ] || [ -L "$runner" ]; then
	fail 'missing headless-root chroot runner'
fi
bash -n "$runner"
if [ ! -f "$packages" ] || [ -L "$packages" ]; then
	fail 'missing headless package profile'
fi
if [ ! -f "$fixture" ] || [ -L "$fixture" ]; then
	fail 'missing public-only headless build fixture'
fi
ssh-keygen -l -f "$fixture" >/dev/null

requested=$(sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' \
	"$packages")
[ "$requested" = "attr
diffutils
openssh" ] || fail 'headless package inventory changed'

grep -Fq 'headless-v1)' "$host"
grep -Fq 'stage-arch-headless-rootfs.sh' "$host"
grep -Fq 'verify-staged-arch-headless-rootfs.sh' "$host"
grep -Fq "ARCH_DEVICE_STAGE=\$device_stage" "$host"
grep -Fq 'firmware_required=0' "$host"
grep -Fq "\"\${firmware_mount[@]}\"" "$host"
grep -Fq 'scripts/device/stage-arch-headless-rootfs.sh' "$runner"
grep -Fq 'systemctl enable sshd.service rog5-server-inhibit.service' "$stage"
grep -Fq 'systemctl set-default multi-user.target' "$stage"
grep -Fq 'systemd-networkd.service systemd-networkd.socket' "$stage"
grep -Fq 'rm -f /etc/ssh/ssh_host_* /var/lib/dbus/machine-id' "$stage"
grep -Fq 'profile=headless-ssh-v1' "$stage"
grep -Fq "ssh-keygen -l -f \"\$authorized_key\"" "$stage" "$host"
grep -Fq "linux-firmware(\$|-)" "$stage" "$verify"
grep -Fq 'sshd -T -C user=root,host=localhost,addr=127.0.0.1' "$verify"
grep -Fq 'PasswordAuthentication no' \
	"$repo/packaging/arch/10-rog5-sshd.conf"

if grep -Eqi \
	'chromium|greetd|krdp|kwin|mesa|nodejs|npm|pipewire|plasma|ttyd|vulkan|wireguard|wpa_supplicant|a660_(gmu|sqe)|a660_zap' \
	"$packages" "$stage"; then
	fail 'headless root enables a deferred package or GPU firmware'
fi
if grep -Eq \
	'fastboot|adb|/dev/(sd|mmcblk|nvme)|mkfs|fsck' \
	"$packages" "$stage" "$verify" "$runner" "$host"; then
	fail 'headless root contains a credential, phone action, or storage write'
fi

echo 'PASS minimal SSH-only Arch root contract'
