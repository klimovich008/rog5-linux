#!/bin/bash
set -euo pipefail

repo=${REPO:-/workspace/repo}
modules=${MODULES_ARCHIVE:-/input/modules.tar.gz}
authorized_key=${AUTHORIZED_KEY:-/input/authorized_key}
: "${ROOTFS_SHA256:?missing ROOTFS_SHA256}"
: "${MODULES_SHA256:?missing MODULES_SHA256}"
: "${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE}"
: "${PROJECT_COMMIT:?missing PROJECT_COMMIT}"

[[ $(sha256sum "$modules" | cut -d' ' -f1) == "$MODULES_SHA256" ]]
[[ $(awk 'NF { count++ } END { print count+0 }' "$authorized_key") == 1 ]]
grep -Eq '^ssh-(ed25519|rsa|ecdsa-[^ ]+) [A-Za-z0-9+/=]+([[:space:]].*)?$' "$authorized_key"

pacman-conf SigLevel | grep -qx PackageRequired
pacman-conf SigLevel | grep -qx PackageTrustedOnly
pacman-key --init
pacman-key --populate archlinuxarm
pacman-key --list-keys 68B3537F39A313B3E574D06777193F152BDBE6A6 >/dev/null
pacman -Sy --noconfirm --disable-sandbox
if pacman -Q linux-aarch64 >/dev/null 2>&1; then
	pacman -Rns --noconfirm linux-aarch64
fi
pacman -Syu --needed --noconfirm --disable-sandbox \
	dnsmasq hostapd iw networkmanager openssh nftables upower wireguard-tools

tar -xzf "$modules" -C /
[[ -d "/lib/modules/$TARGET_KERNEL_RELEASE" ]]
depmod -a "$TARGET_KERNEL_RELEASE"

install -Dm0755 "$repo/scripts/device/vpn-hotspot.sh" /usr/local/sbin/rog5-vpn-hotspot.sh
install -Dm0644 "$repo/packaging/arch/rog5-vpn-hotspot.service" /etc/systemd/system/rog5-vpn-hotspot.service
install -d -m0700 /root/.ssh
install -m0600 "$authorized_key" /root/.ssh/authorized_keys
install -d -m0755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/10-rog5-server.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
EOF

usermod -L root
if getent passwd alarm >/dev/null; then
	usermod -L -s /usr/bin/nologin alarm
fi
rm -f /etc/ssh/ssh_host_* /var/lib/dbus/machine-id
: > /etc/machine-id
install -d -m0755 /etc/systemd/system/multi-user.target.wants
ln -sfn /usr/lib/systemd/system/sshd.service \
	/etc/systemd/system/multi-user.target.wants/sshd.service

install -d -m0755 /etc/rog5
cat > /etc/rog5/build <<EOF
project_commit=$PROJECT_COMMIT
rootfs_sha256=$ROOTFS_SHA256
modules_sha256=$MODULES_SHA256
kernel_release=$TARGET_KERNEL_RELEASE
EOF
pacman -Q | LC_ALL=C sort > /etc/rog5/packages.txt

TARGET_KERNEL_RELEASE=$TARGET_KERNEL_RELEASE \
	/bin/bash "$repo/scripts/device/verify-staged-arch-rootfs.sh"
