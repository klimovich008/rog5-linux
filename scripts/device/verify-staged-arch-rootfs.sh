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
	nmcli node npm nft pip sshd startplasma-wayland systemd-analyze \
	systemd-inhibit tmux ttyd vulkaninfo wg; do
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
cmp /etc/ssh/sshd_config.d/10-rog5-server.conf \
	/workspace/repo/packaging/arch/10-rog5-sshd.conf
[[ $(systemctl is-enabled NetworkManager.service) == enabled ]]
[[ $(systemctl is-enabled NetworkManager-wait-online.service) == enabled ]]
grep -qx 'unmanaged-devices=interface-name:usb0' \
	/etc/NetworkManager/conf.d/10-rog5-usb-unmanaged.conf
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
grep -qx 'command = "/usr/bin/agreety --cmd /usr/bin/startplasma-wayland"' /etc/greetd/config.toml
grep -qx 'user = "greeter"' /etc/greetd/config.toml
! grep -q '^\[initial_session\]' /etc/greetd/config.toml
grep -qx 'HandlePowerKey=ignore' /etc/systemd/logind.conf.d/10-rog5-server.conf
[[ -z $(find /etc/NetworkManager/system-connections -type f -print -quit) ]]
grep -qx 'ExecStart=/usr/bin/krdpserver --address 127.0.0.1' \
	/home/rog5/.config/systemd/user/app-org.kde.krdpserver.service.d/10-rog5-loopback.conf
[[ ! -e /home/rog5/.config/krdpserverrc ]]
[[ ! -e /home/rog5/.local/share/kwalletd ]]
agent_passwd=$(getent passwd rog5-agent)
IFS=: read -r agent_name agent_password agent_uid agent_gid _ \
	agent_home agent_shell \
	<<<"$agent_passwd"
[[ $agent_name == rog5-agent ]]
[[ $agent_password == x ]]
((agent_uid > 0 && agent_uid != 1000))
((agent_gid > 0 && agent_gid != 1000))
[[ $agent_home == /var/lib/rog5-agent ]]
[[ $agent_shell == /usr/bin/nologin ]]
awk -F: '$1 == "rog5-agent" { exit substr($2,1,1) != "!" }' /etc/shadow
[[ $(id -nG rog5-agent) == rog5-agent ]]
[[ $(stat -c %U:%G:%a /var/lib/rog5-agent) == rog5-agent:rog5-agent:700 ]]
[[ $(stat -c %U:%G:%a /var/lib/rog5-agent/private) == rog5-agent:rog5-agent:700 ]]
[[ ! -e /var/lib/rog5-agent/.ssh ]]
[[ -z $(find /var/lib/rog5-agent -mindepth 1 \
	! -path /var/lib/rog5-agent/private -print -quit) ]]
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
cmp /etc/systemd/system/rog5-chromium-headless.service \
	/workspace/repo/packaging/arch/rog5-chromium-headless.service
grep -qx 'User=rog5-agent' \
	/etc/systemd/system/rog5-chromium-headless.service
grep -qx 'Group=rog5-agent' \
	/etc/systemd/system/rog5-chromium-headless.service
grep -qx 'NoNewPrivileges=yes' \
	/etc/systemd/system/rog5-chromium-headless.service
grep -qx 'PrivateDevices=yes' \
	/etc/systemd/system/rog5-chromium-headless.service
grep -qx 'ProtectHome=yes' \
	/etc/systemd/system/rog5-chromium-headless.service
grep -qx 'ProtectSystem=strict' \
	/etc/systemd/system/rog5-chromium-headless.service
grep -qx 'ReadWritePaths=/var/lib/rog5-agent' \
	/etc/systemd/system/rog5-chromium-headless.service
systemd-analyze verify \
	/etc/systemd/system/rog5-chromium-headless.service >/dev/null
sh /workspace/repo/scripts/device/verify-a660-firmware.sh /usr/lib/firmware
[[ -r /usr/lib/firmware/regulatory.db ]]
[[ ! -e /etc/wireguard/wg0.conf ]]
[[ ! -s /etc/machine-id ]]
if [[ -r /etc/fstab ]]; then
	! awk '$1 !~ /^#/ && ($1 ~ /^\/dev\// || $1 ~ /^(UUID|PARTUUID)=/) {
		exit 1
	}' /etc/fstab
fi
[[ -z $(find /etc/pacman.d/gnupg -type s -print -quit) ]]
[[ $(getfattr --only-values -n user.rog5 /etc/rog5/xattr-probe 2>/dev/null) == preserved ]]

echo "PASS staged Arch rootfs kernel=$TARGET_KERNEL_RELEASE"
