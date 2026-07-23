#!/bin/bash
set -euo pipefail
trap 'echo "FAIL verify line=$LINENO command=$BASH_COMMAND" >&2' ERR

: "${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE}"

[[ $(uname -m) == aarch64 ]]
cmp /etc/rog5/packages.requested.txt /workspace/repo/packaging/arch/packages.txt
while read -r package; do
	[[ -n $package ]] || continue
	case $package in \#*) continue ;; esac
	pacman -Q "$package" >/dev/null
done < /etc/rog5/packages.requested.txt
! pacman -Q linux-aarch64 >/dev/null 2>&1
[[ -d "/lib/modules/$TARGET_KERNEL_RELEASE" ]]
[[ -s "/lib/modules/$TARGET_KERNEL_RELEASE/modules.dep" ]]
[[ $(find /lib/modules -mindepth 1 -maxdepth 1 -type d | wc -l) == 1 ]]

for command in chromium dnsmasq eglinfo git krdpserver kscreen-doctor kwin_wayland \
	nmcli node npm nft pip sshd startplasma-wayland systemd-inhibit tmux ttyd \
	vulkaninfo wg; do
	command -v "$command" >/dev/null
done
[[ $(stat -c %a /root/.ssh/authorized_keys) == 600 ]]
grep -Eq '^ssh-(ed25519|rsa|ecdsa-[^ ]+) ' /root/.ssh/authorized_keys
! grep -q 'BEGIN .*PRIVATE KEY' /root/.ssh/authorized_keys
[[ $(id -u rog5) == 1000 ]]
! getent passwd alarm >/dev/null
for group in input render video; do
	id -nG rog5 | tr ' ' '\n' | grep -qx "$group"
done
[[ $(stat -c %U:%G /home/rog5/.ssh/authorized_keys) == rog5:rog5 ]]
[[ $(stat -c %a /home/rog5/.ssh/authorized_keys) == 600 ]]
cmp /root/.ssh/authorized_keys /home/rog5/.ssh/authorized_keys
awk -F: '$1 == "root" { exit substr($2,1,1) != "!" }' /etc/shadow
awk -F: '$1 == "rog5" { exit substr($2,1,1) != "!" }' /etc/shadow
grep -qx 'PasswordAuthentication no' /etc/ssh/sshd_config.d/10-rog5-server.conf
grep -qx 'PermitRootLogin prohibit-password' /etc/ssh/sshd_config.d/10-rog5-server.conf
[[ $(systemctl is-enabled NetworkManager.service) == enabled ]]
[[ $(systemctl is-enabled NetworkManager-wait-online.service) == enabled ]]
for unit in systemd-networkd.service systemd-networkd.socket systemd-networkd-wait-online.service; do
	[[ $(systemctl is-enabled "$unit" 2>/dev/null || true) != enabled ]]
done
[[ -z $(find /etc/systemd/system -type l -lname '*systemd-networkd*' -print -quit) ]]
for unit in greetd.service rog5-server-inhibit.service sshd.service; do
	[[ $(systemctl is-enabled "$unit") == enabled ]]
done
[[ $(systemctl is-enabled rog5-chromium-headless.service 2>/dev/null || true) == disabled ]]
[[ $(systemctl is-enabled rog5-ttyd.service 2>/dev/null || true) == disabled ]]
[[ $(systemctl is-enabled rog5-vpn-hotspot.service 2>/dev/null || true) == disabled ]]
[[ $(readlink /etc/systemd/system/default.target) == /usr/lib/systemd/system/multi-user.target ]]
grep -qx 'command = "/usr/bin/startplasma-wayland"' /etc/greetd/config.toml
! grep -q '^\[initial_session\]' /etc/greetd/config.toml
grep -qx 'HandlePowerKey=ignore' /etc/systemd/logind.conf.d/10-rog5-server.conf
[[ -z $(find /etc/NetworkManager/system-connections -type f -print -quit) ]]
grep -qx 'ExecStart=/usr/bin/krdpserver --address 127.0.0.1' \
	/home/rog5/.config/systemd/user/app-org.kde.krdpserver.service.d/10-rog5-loopback.conf
[[ ! -e /home/rog5/.config/krdpserverrc ]]
[[ ! -e /home/rog5/.local/share/kwalletd ]]
for file in /usr/local/bin/rog5-display-profile.sh /usr/local/bin/rog5-power-profile.sh \
	/usr/local/bin/rog5-screen-toggle.sh /usr/local/sbin/rog5-vpn-hotspot.sh; do
	[[ -x $file ]]
done
[[ -r /etc/systemd/system/rog5-vpn-hotspot.service ]]
[[ -r /etc/systemd/system/rog5-chromium-headless.service ]]
[[ -r /etc/systemd/system/rog5-server-inhibit.service ]]
[[ -r /etc/systemd/system/rog5-ttyd.service ]]
grep -qx 'ExecStart=/usr/bin/systemd-inhibit --what=sleep:handle-power-key --who=rog5-server --why=keep-server-workloads-running --mode=block /usr/bin/sleep infinity' \
	/etc/systemd/system/rog5-server-inhibit.service
sh /workspace/repo/scripts/device/verify-a660-firmware.sh /usr/lib/firmware
[[ -r /usr/lib/firmware/regulatory.db ]]
[[ ! -e /etc/wireguard/wg0.conf ]]
[[ ! -s /etc/machine-id ]]
[[ -z $(find /etc/pacman.d/gnupg -type s -print -quit) ]]
[[ $(getfattr --only-values -n user.rog5 /etc/rog5/xattr-probe 2>/dev/null) == preserved ]]

echo "PASS staged Arch rootfs kernel=$TARGET_KERNEL_RELEASE"
