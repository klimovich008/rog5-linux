#!/bin/bash
set -euo pipefail

repo=${REPO:-/workspace/repo}

/bin/bash "$repo/scripts/device/stage-arch-rootfs.sh"
install -Dm0755 "$repo/scripts/device/power-buttond.py" \
	/usr/local/libexec/rog5-power-buttond
install -Dm0755 "$repo/scripts/device/status-screen.sh" \
	/usr/local/libexec/rog5-status-screen
install -Dm0644 "$repo/packaging/arch/rog5-power-button.service" \
	/etc/systemd/system/rog5-power-button.service
install -Dm0644 "$repo/packaging/arch/rog5-status-screen.service" \
	/etc/systemd/system/rog5-status-screen.service
systemctl enable rog5-status-screen.service rog5-power-button.service

TARGET_KERNEL_RELEASE=${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE} \
	/bin/bash "$repo/scripts/device/verify-staged-arch-rootfs-v3.sh"
