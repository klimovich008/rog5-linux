#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-wifi-bundle.sh

[ -x "$verifier" ] || {
	echo "FAIL missing Wi-Fi bundle verifier: $verifier" >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	'EXPECTED_NETWORK_ROOT_LOADER_SHA256' \
	'CONFIG_SCSI_UFSHCD' \
	'verify-mainline-wifi-build.sh' \
	'test-wifi-candidate-dtb.sh' \
	'verify-wifi-root-overlay.sh' \
	'rog5-network-root-kexec-stage-initramfs.cpio.gz' \
	'Algorithm:' \
	'BEGIN .*PRIVATE KEY' \
	'offline validation only'
do
	grep -Fq -- "$contract" "$verifier" || {
		echo "FAIL Wi-Fi bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'curl|wget|git[[:space:]]+(clone|fetch|pull)|(^|[;&|[:space:]])(fastboot|adb|ssh|scp|nmcli|hostapd|wpa_supplicant)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL Wi-Fi bundle verifier uses network, phone, radio, or storage control' >&2
	exit 1
fi

inputs=${ARTIFACT_DIR:+yes}${MKBOOTIMG_DIR:+yes}${AVBTOOL:+yes}
inputs=${inputs}${BASE_ARTIFACT_DIR:+yes}${WIFI_BUILD:+yes}
inputs=${inputs}${WIFI_DTB:+yes}${BASE_ROOTFS:+yes}
if [ -z "$inputs" ]; then
	echo 'PASS Wi-Fi bundle verifier is offline-only and mutation-testable'
	exit 0
fi

: "${ARTIFACT_DIR:?missing candidate artifact directory}"
: "${MKBOOTIMG_DIR:?missing mkbootimg directory}"
: "${AVBTOOL:?missing avbtool}"
: "${BASE_ARTIFACT_DIR:?missing accepted v8 artifact directory}"
: "${WIFI_BUILD:?missing accepted WCN6855 build directory}"
: "${WIFI_DTB:?missing accepted WCN6855 DTB}"
: "${BASE_ROOTFS:?missing accepted Arch successor v3 root}"

artifact_dir=$ARTIFACT_DIR
mkbootimg_dir=$MKBOOTIMG_DIR
avbtool=$AVBTOOL
base_artifact_dir=$BASE_ARTIFACT_DIR
wifi_build=$WIFI_BUILD
wifi_dtb=$WIFI_DTB
base_rootfs=$BASE_ROOTFS
expected_sums=${EXPECTED_SHA256:-$artifact_dir/SHA256SUMS}
base_sums=${BASE_SHA256:-$base_artifact_dir/SHA256SUMS}
unset ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL BASE_ARTIFACT_DIR
unset WIFI_BUILD WIFI_DTB BASE_ROOTFS EXPECTED_SHA256 BASE_SHA256
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

verify() {
	dir=$1
	"$verifier" "$dir" "$mkbootimg_dir" "$avbtool" \
		"$dir/SHA256SUMS" "$base_artifact_dir" "$base_sums" \
		"$wifi_build" "$wifi_dtb" "$base_rootfs"
}

refresh_manifest_entry() {
	dir=$1
	file=$2
	sum=$(sha256sum "$dir/$file" | cut -d ' ' -f 1)
	awk -v file="$file" -v sum="$sum" \
		'$2 == file { $1 = sum } { print }' \
		"$dir/SHA256SUMS" >"$dir/SHA256SUMS.new"
	mv "$dir/SHA256SUMS.new" "$dir/SHA256SUMS"
}

expect_rejection() {
	label=$1
	file=$2
	case_dir=$stage/$label
	mkdir -p "$case_dir"
	cp -a --reflink=always "$artifact_dir/." "$case_dir/"
	printf X >>"$case_dir/$file"
	refresh_manifest_entry "$case_dir" "$file"
	if verify "$case_dir" >"$stage/$label.log" 2>&1; then
		echo "FAIL verifier accepted mutated $file" >&2
		exit 1
	fi
}

cmp "$expected_sums" "$artifact_dir/SHA256SUMS"
verify "$artifact_dir" >/dev/null
expect_rejection dtb sm8350-asus-rog-phone5-recovery.dtb
expect_rejection overlay rog5-wifi-root-overlay.tar.gz
expect_rejection raw-boot boot-5.4.210-network-root-stage.raw.img

echo 'PASS valid Wi-Fi bundle accepted; DTB, overlay, and raw-boot mutations rejected after manifest refresh'
