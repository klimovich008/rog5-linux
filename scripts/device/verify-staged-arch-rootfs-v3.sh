#!/bin/bash
set -euo pipefail

repo=/workspace/repo
v2_verifier=$repo/scripts/device/verify-staged-arch-rootfs-v2.sh
button=$repo/scripts/device/power-buttond.py
button_test=$repo/scripts/device/test-power-buttond.sh
button_unit=$repo/packaging/arch/rog5-power-button.service
status=$repo/scripts/device/status-screen.sh
status_test=$repo/scripts/device/test-status-screen.sh
status_unit=$repo/packaging/arch/rog5-status-screen.service

[[ $(sha256sum "$v2_verifier" | cut -d ' ' -f 1) == \
	5137868d14400815e99ee642d78ccd125196ce811238120836c59cce92abe44e ]]
TARGET_KERNEL_RELEASE=${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE} \
	/bin/bash "$v2_verifier" >/dev/null

cmp /usr/local/libexec/rog5-power-buttond "$button"
cmp /etc/systemd/system/rog5-power-button.service "$button_unit"
cmp /usr/local/libexec/rog5-status-screen "$status"
cmp /etc/systemd/system/rog5-status-screen.service "$status_unit"
[[ $(stat -c %a /usr/local/libexec/rog5-power-buttond) == 755 ]]
[[ $(stat -c %a /etc/systemd/system/rog5-power-button.service) == 644 ]]
[[ $(stat -c %a /usr/local/libexec/rog5-status-screen) == 755 ]]
[[ $(stat -c %a /etc/systemd/system/rog5-status-screen.service) == 644 ]]
[[ $(systemctl is-enabled rog5-status-screen.service) == enabled ]]
[[ $(systemctl is-enabled rog5-power-button.service) == enabled ]]
TARGET=/usr/local/libexec/rog5-power-buttond \
	UNIT=/etc/systemd/system/rog5-power-button.service \
	"$button_test" >/dev/null
TARGET=/usr/local/libexec/rog5-status-screen \
	UNIT=/etc/systemd/system/rog5-status-screen.service \
	"$status_test" >/dev/null
systemd-analyze verify \
	/etc/systemd/system/rog5-power-button.service \
	/etc/systemd/system/rog5-status-screen.service >/dev/null

echo "PASS staged Arch successor v3 rootfs kernel=$TARGET_KERNEL_RELEASE power-button=status-screen-toggle"
