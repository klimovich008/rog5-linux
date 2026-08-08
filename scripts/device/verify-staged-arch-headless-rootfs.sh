#!/bin/bash
set -euo pipefail
trap 'echo "FAIL headless verify line=$LINENO command=$BASH_COMMAND" >&2' ERR

repo=/workspace/repo
packages_file=$repo/packaging/arch/headless-packages.txt
package_closure=$repo/packaging/arch/headless-package-closure.txt
package_closure_verifier=$repo/scripts/device/verify-exact-package-closure.sh
: "${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE}"
expected_profile=${EXPECTED_HEADLESS_PROFILE:-headless-ssh-v1}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

case $expected_profile in
	headless-ssh-v1)
		expected_build_lines=5
		sshd_policy=$repo/packaging/arch/10-rog5-sshd.conf
		;;
	headless-core-v2)
		expected_build_lines=7
		sshd_policy=$repo/packaging/arch/10-rog5-sshd.conf
		;;
	headless-ssh-v2)
		expected_build_lines=6
		sshd_policy=$repo/packaging/arch/10-rog5-sshd-v2.conf
		;;
	*) fail "unsupported expected headless profile: $expected_profile" ;;
esac

[[ $(uname -m) == aarch64 ]]
cmp /etc/rog5/packages.requested.txt "$packages_file"
while read -r package; do
	[[ -n $package ]] || continue
	case $package in \#*) continue ;; esac
	pacman -Q "$package" >/dev/null
done </etc/rog5/packages.requested.txt
actual_packages=$(mktemp /run/rog5-headless-packages.XXXXXX)
cleanup_packages() {
	rm -f -- "$actual_packages"
}
trap cleanup_packages EXIT
LC_ALL=C pacman -Q | LC_ALL=C sort >"$actual_packages"
bash "$package_closure_verifier" "$package_closure" \
	/etc/rog5/packages.txt
bash "$package_closure_verifier" "$package_closure" "$actual_packages"
rm -f -- "$actual_packages"
trap - EXIT
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

[[ -d /root/.ssh && ! -L /root/.ssh ]]
[[ $(stat -c %U:%G:%a /root/.ssh) == root:root:700 ]]
[[ $(stat -c %U:%G:%a:%h /root/.ssh/authorized_keys) == \
	root:root:600:1 ]]
if [[ $expected_profile == headless-ssh-v2 ]]; then
	[[ $(awk 'END { print NR+0 }' /root/.ssh/authorized_keys) == 1 ]]
	grep -Eq '^ssh-ed25519 [A-Za-z0-9+/]{68}$' \
		/root/.ssh/authorized_keys
	authorized_key_fingerprint=$(
		ssh-keygen -E sha256 -lf /root/.ssh/authorized_keys |
			awk 'NR == 1 { print $2 }'
	)
	[[ $authorized_key_fingerprint =~ ^SHA256:[A-Za-z0-9+/]{43}$ ]]
	grep -Fqx \
		"authorized_key_fingerprint=$authorized_key_fingerprint" \
		/etc/rog5/build
else
	grep -Eq '^ssh-(ed25519|rsa|ecdsa-[^ ]+) ' \
		/root/.ssh/authorized_keys
	[[ $(awk 'NF { count++ } END { print count+0 }' \
		/root/.ssh/authorized_keys) == 1 ]]
fi
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

cmp /etc/ssh/sshd_config.d/10-rog5-server.conf "$sshd_policy"
ssh-keygen -q -t ed25519 -N '' -f /run/rog5-sshd-verify-key
sed 's|^HostKey .*|HostKey /run/rog5-sshd-verify-key|' \
	"$sshd_policy" \
	>/run/rog5-sshd-verify.conf
sshd -T -C user=root,host=localhost,addr=127.0.0.1 \
	-f /run/rog5-sshd-verify.conf >/run/rog5-sshd-effective.conf
grep -Fixq 'passwordauthentication no' /run/rog5-sshd-effective.conf
grep -Fixq 'kbdinteractiveauthentication no' \
	/run/rog5-sshd-effective.conf
grep -Eqi '^permitrootlogin (without-password|prohibit-password)$' \
	/run/rog5-sshd-effective.conf
grep -Fixq 'pubkeyauthentication yes' /run/rog5-sshd-effective.conf
if [[ $expected_profile == headless-ssh-v2 ]]; then
	grep -Fixq 'authorizedkeysfile /root/.ssh/authorized_keys' \
		/run/rog5-sshd-effective.conf
fi
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
[[ $(awk 'END { print NR+0 }' /etc/rog5/build) == \
	"$expected_build_lines" ]]
[[ $(getfattr --only-values -n user.rog5 /etc/rog5/xattr-probe \
	2>/dev/null) == preserved ]]
[[ -d /etc/pacman.d/gnupg && ! -L /etc/pacman.d/gnupg ]]
[[ $(stat -c %U:%G:%a /etc/pacman.d/gnupg) == root:root:755 ]]
[[ -z $(find /etc/pacman.d/gnupg -mindepth 1 -print -quit) ]] ||
	fail 'headless root retained generated Pacman trust or signing state'
[[ -f /var/log/pacman.log && ! -L /var/log/pacman.log ]]
[[ $(stat -c %U:%G:%a:%s /var/log/pacman.log) == root:root:644:0 ]]
if [[ -e /var/cache/ldconfig || -L /var/cache/ldconfig ]]; then
	[[ -d /var/cache/ldconfig && ! -L /var/cache/ldconfig ]]
fi
[[ ! -e /var/cache/ldconfig/aux-cache &&
	! -L /var/cache/ldconfig/aux-cache ]]
if [[ -r /etc/fstab ]]; then
	if awk '$1 !~ /^#/ && ($1 ~ /^\/dev\// ||
		$1 ~ /^(UUID|PARTUUID)=/) { found=1 }
		END { exit !found }' /etc/fstab; then
		fail 'headless root contains a physical fstab entry'
	fi
fi

echo "PASS staged minimal SSH-only Arch rootfs kernel=$TARGET_KERNEL_RELEASE"
