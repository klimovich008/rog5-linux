#!/bin/sh
set -eu

base_rootfs=${1:?usage: build-wifi-root-overlay.sh BASE_ROOTFS OLD_MODULES WIFI_MODULES OUTPUT}
old_modules=${2:?missing accepted network-root modules}
wifi_modules=${3:?missing Wi-Fi modules}
output=${4:?missing output archive}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
blacklist=$repo/packaging/arch/20-rog5-wifi-probe-blacklist.conf
unmanaged=$repo/packaging/arch/20-rog5-wifi-unmanaged.conf
probe=$repo/scripts/device/probe-network-root-wifi.sh
base_rootfs_sha=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7
old_modules_sha=5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9
wifi_modules_sha=e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d
release=7.1.4-g7a5cef0db479
epoch=1681862400

for tool in bsdtar comm cut find gzip install mkdir mv readlink sed \
	sha256sum sort tar; do
	command -v "$tool" >/dev/null
done
for input in "$base_rootfs" "$old_modules" "$wifi_modules" "$blacklist" \
	"$unmanaged" "$probe"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] || {
		echo "FAIL missing or linked Wi-Fi overlay input: $input" >&2
		exit 1
	}
done
[ -x "$probe" ]
[ "$(sha256sum "$base_rootfs" | cut -d ' ' -f 1)" = "$base_rootfs_sha" ]
[ "$(sha256sum "$old_modules" | cut -d ' ' -f 1)" = "$old_modules_sha" ]
[ "$(sha256sum "$wifi_modules" | cut -d ' ' -f 1)" = "$wifi_modules_sha" ]
gzip -t "$base_rootfs"
gzip -t "$old_modules"
gzip -t "$wifi_modules"

output_real=$(readlink -m -- "$output")
for input in "$base_rootfs" "$old_modules" "$wifi_modules" "$blacklist" \
	"$unmanaged" "$probe"; do
	[ "$output_real" != "$(readlink -f -- "$input")" ] || {
		echo 'FAIL Wi-Fi root-overlay output aliases an input' >&2
		exit 1
	}
done
[ ! -e "$output_real" ] || {
	echo "FAIL refusing existing Wi-Fi root overlay: $output_real" >&2
	exit 1
}

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
old_listing=$stage/old-modules.list
new_listing=$stage/new-modules.list
tar -tzf "$old_modules" | LC_ALL=C sort >"$old_listing"
tar -tzf "$wifi_modules" | LC_ALL=C sort >"$new_listing"
[ -z "$(comm -23 "$old_listing" "$new_listing")" ] || {
	echo 'FAIL Wi-Fi module tree removes an accepted path' >&2
	exit 1
}
[ "$(comm -13 "$old_listing" "$new_listing")" = \
	"lib/modules/$release/kernel/drivers/phy/qualcomm/phy-qcom-qmp-pcie.ko" ] ||
	{
		echo 'FAIL Wi-Fi module tree path delta is not exactly the QMP PCIe PHY' >&2
		exit 1
	}

base_listing=$stage/base-rootfs.list
bsdtar -tzf "$base_rootfs" >"$base_listing"
if grep -Eq \
	'^[.]/etc/NetworkManager/system-connections/.+|^[.]/etc/wireguard/wg0[.]conf$|^[.]/etc/ssh/ssh_host_' \
	"$base_listing"
then
	echo 'FAIL accepted predecessor root embeds first-boot or network credentials' >&2
	exit 1
fi

base_firmware=$stage/base-firmware
mkdir -p "$base_firmware"
bsdtar -xzf "$base_rootfs" -C "$base_firmware" -- \
	./usr/lib/firmware/ath11k/WCN6855/hw2.0/amss.bin \
	./usr/lib/firmware/ath11k/WCN6855/hw2.0/board-2.bin \
	./usr/lib/firmware/ath11k/WCN6855/hw2.0/m3.bin \
	./usr/lib/firmware/ath11k/WCN6855/hw2.0/regdb.bin \
	./usr/lib/firmware/regulatory.db \
	./usr/lib/firmware/regulatory.db.p7s
check_base_firmware() {
	path=$1
	expected=$2
	[ "$(grep -Fxc "./$path" "$base_listing")" -eq 1 ]
	[ "$(sha256sum "$base_firmware/$path" | cut -d ' ' -f 1)" = \
		"$expected" ]
}
check_base_firmware usr/lib/firmware/ath11k/WCN6855/hw2.0/amss.bin \
	e12b23ddc4b8d2d2a10a651a5d6fdcd00f60fcae884d2cf5dad17627211fcdfd
check_base_firmware usr/lib/firmware/ath11k/WCN6855/hw2.0/board-2.bin \
	9287fa8d14d915892666b03e9403135875d08371fd1438d2c6d9fe96ae71cf68
check_base_firmware usr/lib/firmware/ath11k/WCN6855/hw2.0/m3.bin \
	0c590881870d0e6e98fc7d393ce05690e09287933b1b535e935bf5d98b77713f
check_base_firmware usr/lib/firmware/ath11k/WCN6855/hw2.0/regdb.bin \
	e1b774b1feda4cab01f5a26089124059539fc31544ac34129dce45c8ff26d645
check_base_firmware usr/lib/firmware/regulatory.db \
	2fb33ca0074db573e05ef7dd50bb45b63c0ff98b7e852e1105ebad536fae8e6b
check_base_firmware usr/lib/firmware/regulatory.db.p7s \
	c941c08f51c93e46722293b85631604c3740d86c3de0c75f79aef50d2e919179

modules_stage=$stage/modules
root=$stage/root
mkdir -p "$modules_stage" "$root/usr/lib" "$root/etc/modprobe.d" \
	"$root/etc/NetworkManager/conf.d" "$root/etc/rog5" \
	"$root/usr/local/sbin"
tar -xzf "$wifi_modules" -C "$modules_stage"
[ -d "$modules_stage/lib/modules/$release" ]
mv "$modules_stage/lib/modules" "$root/usr/lib/modules"
install -m 0644 "$blacklist" \
	"$root/etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf"
install -m 0644 "$unmanaged" \
	"$root/etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf"
install -m 0755 "$probe" \
	"$root/usr/local/sbin/rog5-wifi-enumeration-probe"

seal=$root/etc/rog5/wifi-enumeration-v1
{
	printf 'generation=wifi-enumeration-v1\n'
	printf 'base_rootfs_sha256=%s\n' "$base_rootfs_sha"
	printf 'accepted_modules_sha256=%s\n' "$old_modules_sha"
	printf 'wifi_modules_sha256=%s\n' "$wifi_modules_sha"
	printf 'kernel_release=%s\n' "$release"
	printf 'wifi_image_sha256=a4edaee34dca66534cf886fd0daa6068273d4fd722b63960d517ef17699af43e\n'
	printf 'wifi_dtb_sha256=15acdcd6fad910f105047ef53de08b47cafadbbf94827e123931408d92310d89\n'
	printf 'probe_sha256=%s\n' \
		"$(sha256sum "$probe" | cut -d ' ' -f 1)"
	printf 'blacklist_sha256=%s\n' \
		"$(sha256sum "$blacklist" | cut -d ' ' -f 1)"
	printf 'unmanaged_sha256=%s\n' \
		"$(sha256sum "$unmanaged" | cut -d ' ' -f 1)"
	printf 'firmware_policy=PREDECESSOR_PINNED_NO_CREDENTIALS\n'
	printf 'probe_scope=ENUMERATION_ONLY_NO_SCAN_NO_ASSOCIATION_NO_AP\n'
	printf 'promotion_state=UNBOOTED_HOLD\n'
} >"$seal"
chmod 0444 "$seal"

find "$root" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output_real")"
tar --sort=name --mtime="@$epoch" --owner=0 --group=0 --numeric-owner \
	-C "$root" -cf - . | gzip -n >"$output_real.tmp"
mv "$output_real.tmp" "$output_real"
gzip -t "$output_real"
sha256sum "$output_real"
echo 'PASS deterministic WCN6855 root overlay; exact module-tree successor, auto-probe locked, firmware inherited, credentials absent'
