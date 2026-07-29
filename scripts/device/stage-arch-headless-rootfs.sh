#!/bin/bash
set -euo pipefail
trap 'echo "FAIL headless stage line=$LINENO command=$BASH_COMMAND" >&2' ERR

repo=${REPO:-/workspace/repo}
modules=${MODULES_ARCHIVE:-/input/modules.tar.gz}
authorized_key=${AUTHORIZED_KEY:-/input/authorized_key}
packages_file=$repo/packaging/arch/headless-packages.txt
: "${ROOTFS_SHA256:?missing ROOTFS_SHA256}"
: "${MODULES_SHA256:?missing MODULES_SHA256}"
: "${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE}"
: "${PROJECT_COMMIT:?missing PROJECT_COMMIT}"

[[ $(sha256sum "$modules" | cut -d' ' -f1) == "$MODULES_SHA256" ]]
[[ -r $packages_file ]]
[[ $(awk 'NF { count++ } END { print count+0 }' "$authorized_key") == 1 ]]
grep -Eq '^ssh-(ed25519|rsa|ecdsa-[^ ]+) [A-Za-z0-9+/=]+([[:space:]].*)?$' \
	"$authorized_key"
if grep -q 'BEGIN .*PRIVATE KEY' "$authorized_key"; then
	echo 'FAIL authorized-key input contains private-key material' >&2
	exit 1
fi
mapfile -t packages < <(
	sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' "$packages_file"
)
((${#packages[@]} > 0))

pacman-conf SigLevel | grep -qx PackageRequired
pacman-conf SigLevel | grep -qx PackageTrustedOnly
pacman-key --init
pacman-key --populate archlinuxarm
pacman-key --list-keys 68B3537F39A313B3E574D06777193F152BDBE6A6 \
	>/dev/null
pacman -Sy --noconfirm --disable-sandbox
if pacman -Q linux-aarch64 >/dev/null 2>&1; then
	pacman -Rns --noconfirm linux-aarch64
fi
pacman -Syu --needed --noconfirm --disable-sandbox "${packages[@]}"
ssh-keygen -l -f "$authorized_key" >/dev/null

tar --keep-directory-symlink -xzf "$modules" -C /
[[ -d "/lib/modules/$TARGET_KERNEL_RELEASE" ]]
depmod -a "$TARGET_KERNEL_RELEASE"

if getent passwd alarm >/dev/null; then
	userdel -r alarm
fi
getent group alarm >/dev/null && groupdel alarm

install -d -m0700 /root/.ssh
install -m0600 "$authorized_key" /root/.ssh/authorized_keys
install -Dm0644 "$repo/packaging/arch/10-rog5-sshd.conf" \
	/etc/ssh/sshd_config.d/10-rog5-server.conf
install -Dm0644 "$repo/packaging/arch/rog5-server-inhibit.service" \
	/etc/systemd/system/rog5-server-inhibit.service

usermod -L root
rm -f /etc/ssh/ssh_host_* /var/lib/dbus/machine-id
: >/etc/machine-id

install -d -m0755 /etc/systemd/logind.conf.d
cat >/etc/systemd/logind.conf.d/10-rog5-server.conf <<'EOF'
[Login]
HandlePowerKey=ignore
HandlePowerKeyLongPress=poweroff
HandleSuspendKey=ignore
HandleHibernateKey=ignore
EOF

systemctl disable systemd-networkd.service systemd-networkd.socket \
	systemd-networkd-wait-online.service
systemctl enable sshd.service rog5-server-inhibit.service
systemctl set-default multi-user.target

install -d -m0755 /etc/rog5
install -m0644 "$packages_file" /etc/rog5/packages.requested.txt
: >/etc/rog5/xattr-probe
setfattr -n user.rog5 -v preserved /etc/rog5/xattr-probe
cat >/etc/rog5/build <<EOF
profile=headless-ssh-v1
project_commit=$PROJECT_COMMIT
rootfs_sha256=$ROOTFS_SHA256
modules_sha256=$MODULES_SHA256
kernel_release=$TARGET_KERNEL_RELEASE
EOF
pacman -Q | LC_ALL=C sort >/etc/rog5/packages.txt
if [[ -r /etc/fstab ]]; then
	if awk '$1 !~ /^#/ && ($1 ~ /^\/dev\// ||
		$1 ~ /^(UUID|PARTUUID)=/) { found=1 }
		END { exit !found }' /etc/fstab; then
		echo 'FAIL headless root contains a physical fstab entry' >&2
		exit 1
	fi
fi
gpgconf --homedir /etc/pacman.d/gnupg --kill all || true
find /etc/pacman.d/gnupg -type s -delete

TARGET_KERNEL_RELEASE=$TARGET_KERNEL_RELEASE \
	/bin/bash "$repo/scripts/device/verify-staged-arch-headless-rootfs.sh"
