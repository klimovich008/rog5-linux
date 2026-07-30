#!/bin/bash
set -euo pipefail
trap 'echo "FAIL headless verify line=$LINENO command=$BASH_COMMAND" >&2' ERR

repo=/workspace/repo
packages_file=$repo/packaging/arch/headless-packages.txt
: "${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE}"
expected_profile=${EXPECTED_HEADLESS_PROFILE:-headless-ssh-v1}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $(uname -m) == aarch64 ]]
cmp /etc/rog5/packages.requested.txt "$packages_file"
while read -r package; do
	[[ -n $package ]] || continue
	case $package in \#*) continue ;; esac
	pacman -Q "$package" >/dev/null
done </etc/rog5/packages.requested.txt
if pacman -Q linux-aarch64 >/dev/null 2>&1; then
	fail 'headless root retained the distribution kernel'
fi
if pacman -Qq | grep -Eq '^linux-firmware($|-)'; then
	fail 'headless root retained the distribution firmware bundle'
fi
for package in chromium dnsmasq greetd krdp kwin mesa networkmanager nodejs \
	npm pipewire plasma-desktop ttyd vulkan-freedreno vulkan-tools \
	wireguard-tools wpa_supplicant; do
	if pacman -Q "$package" >/dev/null 2>&1; then
		fail "headless root retained deferred package: $package"
	fi
done

[[ -d "/lib/modules/$TARGET_KERNEL_RELEASE" ]]
[[ -s "/lib/modules/$TARGET_KERNEL_RELEASE/modules.dep" ]]
[[ $(find /lib/modules -mindepth 1 -maxdepth 1 -type d | wc -l) == 1 ]]
for command in depmod ip ss sshd systemd-analyze systemd-inhibit; do
	command -v "$command" >/dev/null
done
for command in chromium greetd krdpserver kwin_wayland nmcli node npm \
	startplasma-wayland ttyd vulkaninfo wg; do
	if command -v "$command" >/dev/null; then
		fail "headless root retained deferred command: $command"
	fi
done

[[ $(stat -c %U:%G:%a /root/.ssh/authorized_keys) == root:root:600 ]]
grep -Eq '^ssh-(ed25519|rsa|ecdsa-[^ ]+) ' \
	/root/.ssh/authorized_keys
[[ $(awk 'NF { count++ } END { print count+0 }' \
	/root/.ssh/authorized_keys) == 1 ]]
ssh-keygen -l -f /root/.ssh/authorized_keys >/dev/null
if grep -q 'BEGIN .*PRIVATE KEY' /root/.ssh/authorized_keys; then
	fail 'authorized key contains private-key material'
fi
awk -F: '$1 == "root" { exit substr($2,1,1) != "!" }' /etc/shadow
for account in alarm rog5 rog5-agent; do
	if getent passwd "$account" >/dev/null; then
		fail "headless root retained interactive account: $account"
	fi
done
if awk -F: '$3 >= 1000 && $3 < 65534 { found=1 }
	END { exit !found }' /etc/passwd; then
	fail 'headless root retained a regular user account'
fi

cmp /etc/ssh/sshd_config.d/10-rog5-server.conf \
	"$repo/packaging/arch/10-rog5-sshd.conf"
ssh-keygen -q -t ed25519 -N '' -f /run/rog5-sshd-verify-key
sed 's|^HostKey .*|HostKey /run/rog5-sshd-verify-key|' \
	/etc/ssh/sshd_config.d/10-rog5-server.conf \
	>/run/rog5-sshd-verify.conf
sshd -T -C user=root,host=localhost,addr=127.0.0.1 \
	-f /run/rog5-sshd-verify.conf >/run/rog5-sshd-effective.conf
grep -Fixq 'passwordauthentication no' /run/rog5-sshd-effective.conf
grep -Fixq 'kbdinteractiveauthentication no' \
	/run/rog5-sshd-effective.conf
grep -Eqi '^permitrootlogin (without-password|prohibit-password)$' \
	/run/rog5-sshd-effective.conf
grep -Fixq 'pubkeyauthentication yes' /run/rog5-sshd-effective.conf
rm -f /run/rog5-sshd-verify-key /run/rog5-sshd-verify-key.pub \
	/run/rog5-sshd-verify.conf /run/rog5-sshd-effective.conf
grep -Fqx 'HostKey /etc/ssh/ssh_host_ed25519_key' \
	/etc/ssh/sshd_config.d/10-rog5-server.conf
[[ -z $(find /etc/ssh -maxdepth 1 -type f -name 'ssh_host_*' \
	-print -quit) ]]
[[ ! -s /etc/machine-id ]]
[[ ! -e /var/lib/dbus/machine-id ]]

[[ $(systemctl is-enabled sshd.service) == enabled ]]
[[ $(systemctl is-enabled rog5-server-inhibit.service) == enabled ]]
for unit in systemd-networkd.service systemd-networkd.socket \
	systemd-networkd-wait-online.service greetd.service \
	NetworkManager.service; do
	[[ $(systemctl is-enabled "$unit" 2>/dev/null || true) != enabled ]]
done
[[ $(readlink /etc/systemd/system/default.target) == \
	/usr/lib/systemd/system/multi-user.target ]]
cmp /etc/systemd/system/rog5-server-inhibit.service \
	"$repo/packaging/arch/rog5-server-inhibit.service"
systemd-analyze verify \
	/etc/systemd/system/rog5-server-inhibit.service >/dev/null
grep -qx 'HandlePowerKey=ignore' \
	/etc/systemd/logind.conf.d/10-rog5-server.conf

for firmware in /usr/lib/firmware/qcom/a660_sqe.fw \
	/usr/lib/firmware/qcom/a660_gmu.bin \
	/usr/lib/firmware/qcom/sm8350/a660_zap.mbn; do
	[[ ! -e $firmware ]]
done
grep -Fqx "profile=$expected_profile" /etc/rog5/build
[[ $(getfattr --only-values -n user.rog5 /etc/rog5/xattr-probe \
	2>/dev/null) == preserved ]]
[[ -d /etc/pacman.d/gnupg && ! -L /etc/pacman.d/gnupg ]]
[[ $(stat -c %U:%G:%a /etc/pacman.d/gnupg) == root:root:755 ]]
[[ -z $(find /etc/pacman.d/gnupg -mindepth 1 -print -quit) ]] ||
	fail 'headless root retained generated Pacman trust or signing state'
if [[ -r /etc/fstab ]]; then
	if awk '$1 !~ /^#/ && ($1 ~ /^\/dev\// ||
		$1 ~ /^(UUID|PARTUUID)=/) { found=1 }
		END { exit !found }' /etc/fstab; then
		fail 'headless root contains a physical fstab entry'
	fi
fi

echo "PASS staged minimal SSH-only Arch rootfs kernel=$TARGET_KERNEL_RELEASE"
