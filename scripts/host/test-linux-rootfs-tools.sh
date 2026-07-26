#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
fetch=$repo/scripts/host/get-arch-rootfs.sh
stage=$repo/scripts/host/stage-arch-rootfs.sh
agent_test=$repo/scripts/device/test-agent-isolation.sh

for script in "$fetch" "$stage" "$agent_test"; do
	[ -x "$script" ] || {
		echo "FAIL missing executable Linux host tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done
"$agent_test" >/dev/null

grep -Fq 'verify-arch-rootfs.sh' "$fetch"
grep -Fq '91e6b11698f8df66042d56aaa56fbe9c9263847d' "$fetch"
grep -Fq '68B3537F39A313B3E574D06777193F152BDBE6A6' \
	"$repo/scripts/device/verify-arch-rootfs.sh"

grep -Fq 'verify-staged-arch-rootfs.sh' "$stage"
grep -Fq 'modules-7.1.4-network-root.tar.gz' "$stage"
grep -Fq 'bsdtar --acls --xattrs --fflags' "$stage"
grep -Fq '10-rog5-sshd.conf' "$repo/scripts/device/stage-arch-rootfs.sh"
grep -Fqx 'HostKey /etc/ssh/ssh_host_ed25519_key' \
	"$repo/packaging/arch/10-rog5-sshd.conf"
grep -Fq 'unmanaged-devices=interface-name:usb0' \
	"$repo/packaging/arch/10-rog5-usb-unmanaged.conf"

if grep -Eq -- '--privileged|--network[= ]host' "$fetch" "$stage"; then
	echo 'FAIL Linux rootfs tools request broad container privileges' >&2
	exit 1
fi
if grep -Eq '(^|[[:space:]])fastboot[[:space:]]+flash|(^|[[:space:]])dd[[:space:]].*of=/dev/' \
	"$fetch" "$stage"; then
	echo 'FAIL Linux rootfs tools contain a phone-storage write command' >&2
	exit 1
fi

echo 'PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes'
