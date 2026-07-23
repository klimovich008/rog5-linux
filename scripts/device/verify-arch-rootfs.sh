#!/bin/sh
set -eu

rootfs=${1:?usage: verify-arch-rootfs.sh ROOTFS SIGNATURE KEYRING}
signature=${2:?usage: verify-arch-rootfs.sh ROOTFS SIGNATURE KEYRING}
keyring=${3:?usage: verify-arch-rootfs.sh ROOTFS SIGNATURE KEYRING}
expected=${ARCH_ROOTFS_SIGNING_FINGERPRINT:-68B3537F39A313B3E574D06777193F152BDBE6A6}
listing=$(mktemp)
binary_keyring=$(mktemp)
trap 'rm -f "$listing" "$binary_keyring"' EXIT INT TERM

[ "${#expected}" -eq 40 ] || {
	echo 'FAIL signing fingerprint must be exactly 40 uppercase hexadecimal characters' >&2
	exit 2
}
case $expected in
	*[!0-9A-F]*)
		echo 'FAIL signing fingerprint must be exactly 40 uppercase hexadecimal characters' >&2
		exit 2
		;;
esac

[ -s "$rootfs" ] || { echo 'FAIL missing rootfs archive' >&2; exit 1; }
[ -s "$signature" ] || { echo 'FAIL missing rootfs signature' >&2; exit 1; }
[ -s "$keyring" ] || { echo 'FAIL missing Arch Linux ARM keyring' >&2; exit 1; }

gpg --batch --dearmor < "$keyring" > "$binary_keyring"
status=$(gpgv --status-fd 1 --keyring "$binary_keyring" "$signature" "$rootfs" 2>/dev/null) || {
	echo 'FAIL rootfs signature verification' >&2
	exit 1
}
printf '%s\n' "$status" | grep -q "^\[GNUPG:\] VALIDSIG $expected " || {
	echo 'FAIL rootfs signature used an unexpected key' >&2
	exit 1
}

tar -tzf "$rootfs" > "$listing"
if awk '/^\// || /(^|\/)\.\.($|\/)/ { found=1 } END { exit !found }' "$listing"; then
	echo 'FAIL unsafe path in rootfs archive' >&2
	exit 1
fi
for required in ./etc/os-release ./etc/shadow ./usr/bin/bash ./usr/bin/pacman; do
	grep -qx "$required" "$listing" || { echo "FAIL rootfs missing $required" >&2; exit 1; }
done

sha256sum "$rootfs"
echo "PASS signed Arch Linux ARM rootfs fingerprint=$expected"
