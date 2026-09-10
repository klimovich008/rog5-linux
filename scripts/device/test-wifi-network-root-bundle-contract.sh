#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
stage_builder=$repo/scripts/device/build-wifi-kexec-stage-initramfs.sh
wrapper_builder=$repo/scripts/device/build-wifi-asus-kexec-stage.sh
verifier=$repo/scripts/device/verify-network-root-wifi-bundle.sh
comparer=$repo/scripts/device/compare-network-root-wifi-bundles.sh

for script in "$stage_builder" "$wrapper_builder" "$verifier" "$comparer"; do
	[ -x "$script" ] || {
		echo "FAIL missing executable Wi-Fi bundle tool: $script" >&2
		exit 1
	}
	sh -n "$script"
done

for contract in \
	eba1c3b862a47f75fbbcca8baed064baa5ebad37f4f138094a143eef7d062863 \
	349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf \
	0fb6d415597630508779263693803af40f35496adee17e82995b0189b2aa9c78 \
	4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac \
	a4edaee34dca66534cf886fd0daa6068273d4fd722b63960d517ef17699af43e \
	15acdcd6fad910f105047ef53de08b47cafadbbf94827e123931408d92310d89 \
	'opt/rog5-recovery/Image' \
	'opt/rog5-recovery/board.dtb' \
	'opt/rog5-recovery/initramfs.cpio.gz' \
	'BEGIN .*PRIVATE KEY' \
	"name '*.ko'" \
	'--owner=0:0' \
	'--reproducible'
do
	grep -Fq -- "$contract" "$stage_builder" || {
		echo "FAIL Wi-Fi kexec-stage builder omits: $contract" >&2
		exit 1
	}
done

for contract in \
	3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8 \
	54ea162415b31227ae50d98806d59179ac2b1acca53d71be1a3f036f9eb92069 \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f \
	'/root/build/rog5-kexec-stage-initramfs.cpio.gz' \
	'CONFIG_KEXEC=y' \
	'# CONFIG_KEXEC_FILE is not set' \
	'CONFIG_INITRAMFS_SOURCE="/root/build/rog5-kexec-stage-initramfs.cpio.gz"' \
	'CONFIG_INITRAMFS_COMPRESSION=".gz"' \
	'KBUILD_BUILD_TIMESTAMP' \
	'compile-only'
do
	grep -Fq -- "$contract" "$wrapper_builder" || {
		echo "FAIL Wi-Fi ASUS wrapper builder omits: $contract" >&2
		exit 1
	}
done

for contract in \
	'verify-network-root-bundle.sh' \
	'verify-mainline-wifi-build.sh' \
	'test-wifi-candidate-dtb.sh' \
	'CONFIG_SCSI_UFSHCD' \
	'/soc@0/pcie@1c00000' \
	'/soc@0/phy@1c06000' \
	'/soc@0/pcie@1c00000/pcie@0/wifi@0' \
	'qcom,wcn6855-pmu' \
	'pci17cb,1103' \
	'modules-7.1.4-network-root.tar.gz' \
	'rog5-wifi-root-overlay.tar.gz' \
	'Algorithm:' \
	'BEGIN .*PRIVATE KEY' \
	'offline validation only'
do
	grep -Fq -- "$contract" "$verifier" || {
		echo "FAIL Wi-Fi bundle verifier omits: $contract" >&2
		exit 1
	}
done

for artifact in \
	Image-5.4.210-network-root-stage \
	config-5.4.210-network-root-stage \
	build-meta-5.4.210-network-root-stage.txt \
	Image-7.1.4-network-root \
	Image.gz-7.1.4-network-root \
	config-7.1.4-network-root \
	modules-7.1.4-network-root.tar.gz \
	build-meta-7.1.4-network-root.txt \
	sm8350-asus-rog-phone5-recovery.dtb \
	rog5-network-root-initramfs.cpio.gz \
	rog5-network-root-kexec-stage-initramfs.cpio.gz \
	boot-5.4.210-network-root-stage.raw.img \
	boot-5.4.210-network-root-stage.avb.img \
	rog5-wifi-root-overlay.tar.gz \
	SHA256SUMS
do
	grep -Fq "$artifact" "$comparer" || {
		echo "FAIL Wi-Fi bundle comparer omits: $artifact" >&2
		exit 1
	}
done

if grep -Eq \
	'curl|wget|git[[:space:]]+(clone|fetch|pull)|(^|[;&|[:space:]])(fastboot|adb|ssh|scp|nmcli|hostapd|wpa_supplicant)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$stage_builder" "$wrapper_builder" "$verifier" "$comparer"
then
	echo 'FAIL Wi-Fi bundle tools use network, phone, radio, or storage control' >&2
	exit 1
fi

if [ -n "${BASE_STAGE:-}" ] || [ -n "${WIFI_IMAGE:-}" ] ||
	[ -n "${WIFI_DTB:-}" ]
then
	[ -s "${BASE_STAGE:-}" ]
	[ -s "${WIFI_IMAGE:-}" ]
	[ -s "${WIFI_DTB:-}" ]
	stage=$(mktemp -d)
	trap 'rm -rf "$stage"' EXIT INT TERM
	"$stage_builder" "$BASE_STAGE" "$WIFI_IMAGE" "$WIFI_DTB" \
		"$stage/one.cpio.gz" >/dev/null
	"$stage_builder" "$BASE_STAGE" "$WIFI_IMAGE" "$WIFI_DTB" \
		"$stage/two.cpio.gz" >/dev/null
	cmp "$stage/one.cpio.gz" "$stage/two.cpio.gz"
fi

echo 'PASS Wi-Fi network-root package is input-pinned, deterministic, credential-free, storage-disabled, and offline-only'
