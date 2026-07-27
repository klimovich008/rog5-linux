#!/bin/sh
set -eu

base_rootfs=${1:?usage: verify-wifi-root-overlay.sh BASE_ROOTFS WIFI_MODULES OVERLAY}
wifi_modules=${2:?missing Wi-Fi modules}
overlay=${3:?missing Wi-Fi root overlay}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
blacklist=$repo/packaging/arch/20-rog5-wifi-probe-blacklist.conf
unmanaged=$repo/packaging/arch/20-rog5-wifi-unmanaged.conf
probe=$repo/scripts/device/probe-network-root-wifi.sh
base_rootfs_sha=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7
accepted_modules_sha=5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9
wifi_modules_sha=e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d
release=7.1.4-g7a5cef0db479
module_root=usr/lib/modules/7.1.4-g7a5cef0db479

for input in "$base_rootfs" "$wifi_modules" "$overlay" "$blacklist" \
	"$unmanaged" "$probe"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] || {
		echo "FAIL missing or linked Wi-Fi overlay verification input: $input" >&2
		exit 1
	}
done
[ "$(sha256sum "$wifi_modules" | cut -d ' ' -f 1)" = \
	"$wifi_modules_sha" ]
gzip -t "$wifi_modules"
gzip -t "$overlay"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
listing=$stage/overlay.list
tar -tzf "$overlay" >"$listing"
awk '
	/^\// { bad=1 }
	{
		path=$0
		sub(/^[.]\//, "", path)
		sub(/\/$/, "", path)
		count=split(path, part, "/")
		for (field=1; field <= count; field++)
			if (part[field] == "..") bad=1
	}
	END { exit bad ? 1 : 0 }
' "$listing" || {
	echo 'FAIL Wi-Fi root overlay contains an unsafe path' >&2
	exit 1
}
if awk '
	{
		path=$0
		sub(/^[.]\//, "", path)
		sub(/\/$/, "", path)
		if (path == "" ||
		    path ~ /^usr\/lib\/modules\// ||
		    path == "usr/lib/modules" ||
		    path == "usr" || path == "usr/lib" ||
		    path == "usr/local" || path == "usr/local/sbin" ||
		    path == "usr/local/sbin/rog5-wifi-enumeration-probe" ||
		    path == "etc" || path == "etc/modprobe.d" ||
		    path == "etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf" ||
		    path == "etc/NetworkManager" ||
		    path == "etc/NetworkManager/conf.d" ||
		    path == "etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf" ||
		    path == "etc/rog5" ||
		    path == "etc/rog5/wifi-enumeration-v1")
			next
		bad=1
	}
	END { exit bad ? 0 : 1 }
' "$listing"
then
	echo 'FAIL Wi-Fi root overlay contains a path outside its exact delta' >&2
	exit 1
fi
if grep -Eq \
	'(^|/)(root/[.]ssh|home/[^/]+/[.]ssh|etc/ssh/ssh_host_|NetworkManager/system-connections|wireguard/wg0[.]conf)(/|$)' \
	"$listing"
then
	echo 'FAIL Wi-Fi root overlay contains a credential path' >&2
	exit 1
fi

root=$stage/root
modules_stage=$stage/modules
mkdir -p "$root" "$modules_stage"
tar -xzf "$overlay" -C "$root"
tar -xzf "$wifi_modules" -C "$modules_stage"
diff --no-dereference -qr "$modules_stage/lib/modules/$release" \
	"$root/$module_root" >/dev/null || {
	echo 'FAIL Wi-Fi root overlay module tree differs from the accepted archive' >&2
	exit 1
}

cmp "$root/etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf" "$blacklist"
cmp "$root/etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf" \
	"$unmanaged"
cmp "$root/usr/local/sbin/rog5-wifi-enumeration-probe" "$probe"
check_archive_meta() {
	path=$1
	expected=$2
	actual=$(tar --numeric-owner -tvzf "$overlay" "./$path" |
		awk '{ print $1 " " $2 }')
	[ "$actual" = "$expected" ] || {
		echo "FAIL Wi-Fi root overlay metadata differs for $path" >&2
		exit 1
	}
}
check_archive_meta etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf \
	'-rw-r--r-- 0/0'
check_archive_meta etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf \
	'-rw-r--r-- 0/0'
check_archive_meta usr/local/sbin/rog5-wifi-enumeration-probe \
	'-rwxr-xr-x 0/0'

seal=$root/etc/rog5/wifi-enumeration-v1
check_archive_meta etc/rog5/wifi-enumeration-v1 '-r--r--r-- 0/0'
expected_seal=$stage/expected-seal
{
	printf 'generation=wifi-enumeration-v1\n'
	printf 'base_rootfs_sha256=%s\n' "$base_rootfs_sha"
	printf 'accepted_modules_sha256=%s\n' "$accepted_modules_sha"
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
} >"$expected_seal"
cmp "$expected_seal" "$seal" || {
	echo 'FAIL Wi-Fi root-overlay seal is not byte-exact' >&2
	exit 1
}

[ "$(sha256sum "$base_rootfs" | cut -d ' ' -f 1)" = "$base_rootfs_sha" ]
gzip -t "$base_rootfs"
check_base_firmware() {
	path=$1
	expected=$2
	[ "$(sha256sum "$base_firmware/$path" | cut -d ' ' -f 1)" = \
		"$expected" ]
}
base_firmware=$stage/base-firmware
mkdir -p "$base_firmware"
bsdtar -xzf "$base_rootfs" -C "$base_firmware" -- \
	./usr/lib/firmware/ath11k/WCN6855/hw2.0/amss.bin \
	./usr/lib/firmware/ath11k/WCN6855/hw2.0/board-2.bin \
	./usr/lib/firmware/ath11k/WCN6855/hw2.0/m3.bin \
	./usr/lib/firmware/ath11k/WCN6855/hw2.0/regdb.bin
check_base_firmware usr/lib/firmware/ath11k/WCN6855/hw2.0/amss.bin \
	e12b23ddc4b8d2d2a10a651a5d6fdcd00f60fcae884d2cf5dad17627211fcdfd
check_base_firmware usr/lib/firmware/ath11k/WCN6855/hw2.0/board-2.bin \
	9287fa8d14d915892666b03e9403135875d08371fd1438d2c6d9fe96ae71cf68
check_base_firmware usr/lib/firmware/ath11k/WCN6855/hw2.0/m3.bin \
	0c590881870d0e6e98fc7d393ce05690e09287933b1b535e935bf5d98b77713f
check_base_firmware usr/lib/firmware/ath11k/WCN6855/hw2.0/regdb.bin \
	e1b774b1feda4cab01f5a26089124059539fc31544ac34129dce45c8ff26d645

qmp=$root/$module_root/kernel/drivers/phy/qualcomm/phy-qcom-qmp-pcie.ko
pwrctrl=$root/$module_root/kernel/drivers/pci/pwrctrl/pci-pwrctrl-pwrseq.ko
pwrseq=$root/$module_root/kernel/drivers/power/sequencing/pwrseq-qcom-wcn.ko
ath11k_pci=$root/$module_root/kernel/drivers/net/wireless/ath/ath11k/ath11k_pci.ko
[ "$(modinfo -F name "$qmp")" = phy_qcom_qmp_pcie ]
modinfo -F alias "$pwrctrl" | grep -F 'of:N*T*Cpci17cb,1103' >/dev/null
modinfo -F alias "$pwrseq" | grep -F 'of:N*T*Cqcom,wcn6855-pmu' >/dev/null
modinfo -F alias "$ath11k_pci" |
	grep -F 'pci:v000017CBd00001103' >/dev/null

if find "$root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .
then
	echo 'FAIL Wi-Fi root overlay contains private-key material' >&2
	exit 1
fi
[ -z "$(find "$root/etc/NetworkManager/system-connections" -type f \
	-print -quit 2>/dev/null)" ]
[ ! -e "$root/etc/wireguard/wg0.conf" ]

echo 'PASS verified WCN6855 root overlay: exact module tree, inherited firmware, auto-probe lock, enumeration-only control, and no credentials'
