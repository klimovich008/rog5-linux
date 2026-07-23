#!/bin/bash
set -euo pipefail
trap 'echo "FAIL verify line=$LINENO command=$BASH_COMMAND" >&2' ERR

: "${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE}"

[[ $(uname -m) == aarch64 ]]
for package in attr dnsmasq hostapd iw networkmanager openssh nftables upower wireguard-tools; do
	pacman -Q "$package" >/dev/null
done
! pacman -Q linux-aarch64 >/dev/null 2>&1
[[ -d "/lib/modules/$TARGET_KERNEL_RELEASE" ]]
[[ -s "/lib/modules/$TARGET_KERNEL_RELEASE/modules.dep" ]]
[[ $(find /lib/modules -mindepth 1 -maxdepth 1 -type d | wc -l) == 1 ]]

for command in hostapd dnsmasq nmcli nft sshd wg; do
	command -v "$command" >/dev/null
done
[[ $(stat -c %a /root/.ssh/authorized_keys) == 600 ]]
grep -Eq '^ssh-(ed25519|rsa|ecdsa-[^ ]+) ' /root/.ssh/authorized_keys
! grep -q 'BEGIN .*PRIVATE KEY' /root/.ssh/authorized_keys
awk -F: '$1 == "root" { exit substr($2,1,1) != "!" }' /etc/shadow
grep -qx 'PasswordAuthentication no' /etc/ssh/sshd_config.d/10-rog5-server.conf
grep -qx 'PermitRootLogin prohibit-password' /etc/ssh/sshd_config.d/10-rog5-server.conf
[[ $(readlink /etc/systemd/system/multi-user.target.wants/sshd.service) == /usr/lib/systemd/system/sshd.service ]]
[[ -x /usr/local/sbin/rog5-vpn-hotspot.sh ]]
[[ -r /etc/systemd/system/rog5-vpn-hotspot.service ]]
[[ ! -e /etc/wireguard/wg0.conf ]]
[[ ! -s /etc/machine-id ]]
[[ $(getfattr --only-values -n user.rog5 /etc/rog5/xattr-probe 2>/dev/null) == preserved ]]

echo "PASS staged Arch rootfs kernel=$TARGET_KERNEL_RELEASE"
