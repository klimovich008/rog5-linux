#!/bin/bash
set -euo pipefail
trap 'echo "FAIL stage line=$LINENO command=$BASH_COMMAND" >&2' ERR

repo=${REPO:-/workspace/repo}
modules=${MODULES_ARCHIVE:-/input/modules.tar.gz}
firmware=${FIRMWARE_ROOT:-/input/firmware}
authorized_key=${AUTHORIZED_KEY:-/input/authorized_key}
packages_file=$repo/packaging/arch/packages.txt
: "${ROOTFS_SHA256:?missing ROOTFS_SHA256}"
: "${MODULES_SHA256:?missing MODULES_SHA256}"
: "${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE}"
: "${PROJECT_COMMIT:?missing PROJECT_COMMIT}"

[[ $(sha256sum "$modules" | cut -d' ' -f1) == "$MODULES_SHA256" ]]
[[ -r $packages_file ]]
[[ $(awk 'NF { count++ } END { print count+0 }' "$authorized_key") == 1 ]]
grep -Eq '^ssh-(ed25519|rsa|ecdsa-[^ ]+) [A-Za-z0-9+/=]+([[:space:]].*)?$' "$authorized_key"
mapfile -t packages < <(sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' "$packages_file")
((${#packages[@]} > 0))

pacman-conf SigLevel | grep -qx PackageRequired
pacman-conf SigLevel | grep -qx PackageTrustedOnly
pacman-key --init
pacman-key --populate archlinuxarm
pacman-key --list-keys 68B3537F39A313B3E574D06777193F152BDBE6A6 >/dev/null
pacman -Sy --noconfirm --disable-sandbox
if pacman -Q linux-aarch64 >/dev/null 2>&1; then
	pacman -Rns --noconfirm linux-aarch64
fi
pacman -Syu --needed --noconfirm --disable-sandbox "${packages[@]}"

tar --keep-directory-symlink -xzf "$modules" -C /
[[ -d "/lib/modules/$TARGET_KERNEL_RELEASE" ]]
depmod -a "$TARGET_KERNEL_RELEASE"
sh "$repo/scripts/device/verify-a660-firmware.sh" "$firmware"
install -Dm0644 "$firmware/qcom/a660_sqe.fw" /usr/lib/firmware/qcom/a660_sqe.fw
install -Dm0644 "$firmware/qcom/a660_gmu.bin" /usr/lib/firmware/qcom/a660_gmu.bin
install -Dm0644 "$firmware/qcom/sm8350/a660_zap.mbn" \
	/usr/lib/firmware/qcom/sm8350/a660_zap.mbn

install -Dm0755 "$repo/scripts/device/display-profile.sh" /usr/local/bin/rog5-display-profile.sh
install -Dm0755 "$repo/scripts/device/power-profile.sh" /usr/local/bin/rog5-power-profile.sh
install -Dm0755 "$repo/scripts/device/screen-toggle.sh" /usr/local/bin/rog5-screen-toggle.sh
install -Dm0755 "$repo/scripts/device/collect-baseline.sh" \
	/usr/local/bin/rog5-collect-baseline.sh
install -Dm0755 "$repo/scripts/device/vpn-hotspot.sh" /usr/local/sbin/rog5-vpn-hotspot.sh
install -Dm0644 "$repo/packaging/arch/rog5-vpn-hotspot.service" /etc/systemd/system/rog5-vpn-hotspot.service
install -Dm0644 "$repo/packaging/arch/rog5-chromium-headless.service" \
	/etc/systemd/system/rog5-chromium-headless.service
install -Dm0644 "$repo/packaging/arch/rog5-server-inhibit.service" \
	/etc/systemd/system/rog5-server-inhibit.service
install -Dm0644 "$repo/packaging/arch/rog5-ttyd.service" /etc/systemd/system/rog5-ttyd.service
install -Dm0644 "$repo/packaging/arch/10-rog5-usb-unmanaged.conf" \
	/etc/NetworkManager/conf.d/10-rog5-usb-unmanaged.conf

if getent passwd alarm >/dev/null; then
	usermod -l rog5 alarm
	getent group alarm >/dev/null && groupmod -n rog5 alarm
	usermod -d /home/rog5 -m rog5
elif ! getent passwd rog5 >/dev/null; then
	useradd -m -s /bin/bash rog5
fi
usermod -L -s /bin/bash rog5
for group in input render video; do
	getent group "$group" >/dev/null && usermod -aG "$group" rog5
done

getent passwd rog5-agent >/dev/null && {
	echo 'FAIL reserved rog5-agent account already exists' >&2
	exit 1
}
useradd --system --user-group \
	--home-dir /var/lib/rog5-agent --no-create-home \
	--shell /usr/bin/nologin rog5-agent
usermod -L rog5-agent
install -d -o rog5-agent -g rog5-agent -m0700 \
	/var/lib/rog5-agent /var/lib/rog5-agent/private

install -d -m0700 /root/.ssh
install -m0600 "$authorized_key" /root/.ssh/authorized_keys
install -d -o rog5 -g rog5 -m0700 /home/rog5/.ssh
install -o rog5 -g rog5 -m0600 "$authorized_key" /home/rog5/.ssh/authorized_keys
install -d -o rog5 -g rog5 -m0755 /home/rog5/.config \
	/home/rog5/.config/systemd /home/rog5/.config/systemd/user \
	/home/rog5/.config/systemd/user/app-org.kde.krdpserver.service.d
install -o rog5 -g rog5 -m0644 "$repo/packaging/arch/krdp-loopback.conf" \
	/home/rog5/.config/systemd/user/app-org.kde.krdpserver.service.d/10-rog5-loopback.conf
install -Dm0644 "$repo/packaging/arch/10-rog5-sshd.conf" \
	/etc/ssh/sshd_config.d/10-rog5-server.conf

usermod -L root
rm -f /etc/ssh/ssh_host_* /var/lib/dbus/machine-id
: > /etc/machine-id

install -d -m0755 /etc/greetd
cat > /etc/greetd/config.toml <<'EOF'
[terminal]
vt = 1

[default_session]
command = "/usr/bin/agreety --cmd /usr/bin/startplasma-wayland"
user = "greeter"
EOF

install -d -m0755 /etc/systemd/logind.conf.d
cat > /etc/systemd/logind.conf.d/10-rog5-server.conf <<'EOF'
[Login]
HandlePowerKey=ignore
HandlePowerKeyLongPress=poweroff
HandleSuspendKey=ignore
HandleHibernateKey=ignore
EOF

systemctl disable systemd-networkd.service systemd-networkd.socket \
	systemd-networkd-wait-online.service
systemctl enable NetworkManager.service NetworkManager-wait-online.service \
	sshd.service greetd.service rog5-server-inhibit.service
systemctl set-default multi-user.target

install -d -m0755 /etc/rog5
install -m0644 "$packages_file" /etc/rog5/packages.requested.txt
: > /etc/rog5/xattr-probe
setfattr -n user.rog5 -v preserved /etc/rog5/xattr-probe
cat > /etc/rog5/build <<EOF
project_commit=$PROJECT_COMMIT
rootfs_sha256=$ROOTFS_SHA256
modules_sha256=$MODULES_SHA256
kernel_release=$TARGET_KERNEL_RELEASE
EOF
pacman -Q | LC_ALL=C sort > /etc/rog5/packages.txt
if [[ -r /etc/fstab ]]; then
	! awk '$1 !~ /^#/ && ($1 ~ /^\/dev\// || $1 ~ /^(UUID|PARTUUID)=/) {
		exit 1
	}' /etc/fstab
fi
gpgconf --homedir /etc/pacman.d/gnupg --kill all || true
find /etc/pacman.d/gnupg -type s -delete

TARGET_KERNEL_RELEASE=$TARGET_KERNEL_RELEASE \
	/bin/bash "$repo/scripts/device/verify-staged-arch-rootfs.sh"
