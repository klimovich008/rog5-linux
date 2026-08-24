#!/bin/sh
set -eu

[ "$#" -eq 6 ] || {
	echo 'usage: build-local-image-stage-initramfs.sh BASE INIT INSTALL AUTHORIZED_KEY REBOOT_HELPER OUTPUT' >&2
	exit 1
}
base=$1
init=$2
installer=$3
authorized_key=$4
reboot_helper=$5
output=$6
expected_base=4326c052b568a04143befc43c84b177487ccb5b13a1762b22ed178fb1f32ba97
expected_key_sha256=04f39d5949c813450e201b7e579256b1afcd5c7fcea077d36ae445aa53519b61
expected_reboot_sha256=68d6a69e597e9fa86ee956ee9fadc15f4283e7dd2a6032b924449330bb3e4785
expected_release=${EXPECTED_RELEASE:-7.1.4-gae717d919f87}
expected_bundle=${EXPECTED_BUNDLE:-local-image-stage-v1}
ufs_modules=${UFS_MODULES:-}
power_modules_root=${POWER_MODULES_ROOT:-}
epoch=1681862400

fail() { echo "FAIL $*" >&2; exit 1; }
for input in "$base" "$init" "$installer" "$authorized_key" "$reboot_helper"; do
	[ -f "$input" ] && [ ! -L "$input" ] || fail "unsafe input: $input"
done
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || fail 'base hash changed'
[ "$(sha256sum "$authorized_key" | cut -d ' ' -f 1)" = "$expected_key_sha256" ] || fail 'authorized key changed'
[ "$(sha256sum "$reboot_helper" | cut -d ' ' -f 1)" = "$expected_reboot_sha256" ] || fail 'reboot helper changed'
[ ! -e "$output" ] && [ ! -L "$output" ] || fail 'output exists'
printf '%s\n' "$expected_release" | grep -Eq '^7[.]1[.]4-g[0-9a-f]{12}$' ||
	fail 'invalid expected kernel release'
printf '%s\n' "$expected_bundle" | grep -Eq '^[a-z0-9][a-z0-9-]{0,63}$' ||
	fail 'invalid expected bundle'
case "$ufs_modules:$power_modules_root" in
	:) ;;
	:*|*:) fail 'UFS_MODULES and POWER_MODULES_ROOT must be supplied together' ;;
esac

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
gzip -dc "$base" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"
[ "$(grep -Fc '@EXPECTED_BUNDLE@' "$stage/init")" -eq 1 ] ||
	fail 'init bundle placeholder changed'
sed -i "s/@EXPECTED_BUNDLE@/$expected_bundle/" "$stage/init"
grep -Fqx "expected_bundle=$expected_bundle" "$stage/init" ||
	fail 'init bundle substitution failed'
[ "$(grep -Fc '@EXPECTED_KERNEL_RELEASE@' "$stage/init")" -eq 1 ] ||
	fail 'init release placeholder changed'
sed -i "s/@EXPECTED_KERNEL_RELEASE@/$expected_release/" "$stage/init"
grep -Fqx "expected_release=$expected_release" "$stage/init" ||
	fail 'init release substitution failed'
if [ -n "$ufs_modules" ]; then
	[ -d "$ufs_modules" ] && [ ! -L "$ufs_modules" ] &&
		[ -d "$power_modules_root/lib/modules/$expected_release/kernel" ] &&
		[ ! -L "$power_modules_root" ] || fail 'unsafe module input'
	rm -rf -- "$stage/rog5-ufs-modules" "$stage/rog5-power-usb-modules"
	install -d -m 0755 "$stage/rog5-ufs-modules" "$stage/rog5-power-usb-modules"
	set -- phy-qcom-qmp-ufs.ko ufs-qcom.ko ufshcd-core.ko ufshcd-pltfrm.ko
	[ "$(find "$ufs_modules" -mindepth 1 -maxdepth 1 -type f -name '*.ko' | wc -l)" -eq "$#" ] ||
		fail 'UFS module inventory changed'
	for module in "$@"; do
		[ "$(modinfo -F vermagic "$ufs_modules/$module" | awk '{print $1}')" = "$expected_release" ] ||
			fail "UFS module ABI changed: $module"
		install -m 0644 "$ufs_modules/$module" "$stage/rog5-ufs-modules/$module"
	done
	module_root=$power_modules_root/lib/modules/$expected_release/kernel
	[ "$(find "$module_root" -type f -name '*.ko' | wc -l)" -eq 15 ] ||
		fail 'power/USB module inventory changed'
	find "$module_root" -type f -name '*.ko' -print | while IFS= read -r module; do
		[ "$(modinfo -F vermagic "$module" | awk '{print $1}')" = "$expected_release" ] ||
			fail "power/USB module ABI changed: $module"
		install -m 0644 "$module" "$stage/rog5-power-usb-modules/${module##*/}"
	done
	[ "$(find "$stage/rog5-power-usb-modules" -type f -name '*.ko' | wc -l)" -eq 15 ] ||
		fail 'power/USB module names collide'
fi
for module in "$stage/rog5-ufs-modules"/*.ko \
	"$stage/rog5-power-usb-modules"/*.ko; do
	[ -f "$module" ] && [ ! -L "$module" ] ||
		fail 'packaged module inventory is incomplete'
	[ "$(modinfo -F vermagic "$module" | awk '{print $1}')" = "$expected_release" ] ||
		fail "packaged module ABI changed: ${module##*/}"
done
install -D -m 0755 "$installer" "$stage/usr/local/sbin/rog5-install-local-arch-image"
install -D -m 0755 "$reboot_helper" "$stage/usr/libexec/rog5-reboot-bootloader"
install -D -m 0600 "$authorized_key" "$stage/root/.ssh/authorized_keys"
sed -i 's/^root:[^:]*/root:!/' "$stage/etc/shadow"
grep -Fxq 'PermitRootLogin prohibit-password' "$stage/etc/ssh/sshd_config"
grep -Fxq 'PasswordAuthentication no' "$stage/etc/ssh/sshd_config"
grep -Fxq 'PubkeyAuthentication yes' "$stage/etc/ssh/sshd_config"
find "$stage" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output.tmp"
mv -T "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
echo 'PASS deterministic UFS-capable local-image staging initramfs'
