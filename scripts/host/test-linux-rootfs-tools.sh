#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
fetch=$repo/scripts/host/get-arch-rootfs.sh
stage=$repo/scripts/host/stage-arch-rootfs.sh
agent_test=$repo/scripts/device/test-agent-isolation.sh
metrics_test=$repo/scripts/device/test-collect-baseline.sh
hotspot_wireguard_contract=$repo/scripts/device/test-vpn-hotspot-wireguard-contract.sh
successor_export_test=$repo/scripts/host/test-arch-successor-export.sh
successor_target_test=$repo/scripts/device/test-run-network-root-arch-successor-v1-gate.sh
successor_runner_test=$repo/scripts/host/test-run-arch-successor-v1-live-gate.sh
successor_v2_test=$repo/scripts/device/test-arch-successor-v2-packaging-contract.sh
successor_v2_export_test=$repo/scripts/host/test-arch-successor-v2-export.sh
successor_v2_nfs_test=$repo/scripts/host/test-serve-arch-successor-v2-live-window.sh
successor_v2_target_test=$repo/scripts/device/test-run-network-root-arch-successor-v2-gate.sh
successor_v2_runner_test=$repo/scripts/host/test-run-arch-successor-v2-live-gate.sh
successor_v3_test=$repo/scripts/device/test-arch-successor-v3-power-button-contract.sh

for script in "$fetch" "$stage" "$agent_test" "$metrics_test" \
	"$hotspot_wireguard_contract" \
	"$successor_export_test" "$successor_target_test" \
	"$successor_runner_test" "$successor_v2_test" \
	"$successor_v2_export_test" "$successor_v2_nfs_test" \
	"$successor_v2_target_test" "$successor_v2_runner_test" \
	"$successor_v3_test"; do
	[ -x "$script" ] || {
		echo "FAIL missing executable Linux host tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done
"$agent_test" >/dev/null
"$metrics_test" >/dev/null
"$hotspot_wireguard_contract" >/dev/null
"$successor_export_test" >/dev/null
"$successor_target_test" >/dev/null
"$successor_runner_test" >/dev/null
"$successor_v2_test" >/dev/null
"$successor_v2_export_test" >/dev/null
"$successor_v2_nfs_test" >/dev/null
"$successor_v2_target_test" >/dev/null
"$successor_v2_runner_test" >/dev/null
"$successor_v3_test" >/dev/null

grep -Fq 'verify-arch-rootfs.sh' "$fetch"
grep -Fq '91e6b11698f8df66042d56aaa56fbe9c9263847d' "$fetch"
grep -Fq '68B3537F39A313B3E574D06777193F152BDBE6A6' \
	"$repo/scripts/device/verify-arch-rootfs.sh"

grep -Fq 'verify-staged-arch-rootfs-v2.sh' "$stage"
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
