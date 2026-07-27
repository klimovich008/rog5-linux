#!/bin/bash
set -euo pipefail

repo=/workspace/repo
v1_verifier=$repo/scripts/device/verify-staged-arch-rootfs.sh
transition_test=$repo/scripts/device/test-vpn-hotspot-transition-v2.sh

[[ $(sha256sum "$v1_verifier" | cut -d ' ' -f 1) == \
	e8ab452b1994ffbffe0a0e1db32e3b2f66866d813e8f32b03713fb4f2545e87f ]]
TARGET_KERNEL_RELEASE=${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE} \
	/bin/bash "$v1_verifier" >/dev/null

cmp /usr/local/sbin/rog5-vpn-hotspot.sh \
	/workspace/repo/scripts/device/vpn-hotspot-v2.sh
cmp /etc/systemd/system/rog5-vpn-hotspot.service \
	/workspace/repo/packaging/arch/rog5-vpn-hotspot-v2.service
sh "$transition_test" >/dev/null

echo "PASS staged Arch successor v2 rootfs kernel=$TARGET_KERNEL_RELEASE hotspot=fail-closed-transition-v2"
