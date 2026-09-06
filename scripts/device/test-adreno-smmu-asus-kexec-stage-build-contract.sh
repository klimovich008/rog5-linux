#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-adreno-smmu-asus-kexec-stage.sh
compare=$repo/scripts/device/compare-asus-kexec-stage-builds.sh

[ -x "$builder" ] || {
	echo 'FAIL missing executable Adreno SMMU ASUS wrapper builder' >&2
	exit 1
}
[ -x "$compare" ]
sh -n "$builder" "$compare"

for contract in \
	3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8 \
	54ea162415b31227ae50d98806d59179ac2b1acca53d71be1a3f036f9eb92069 \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f \
	85f764dd206afd3a2b652c7119eb266f62d687a02b1c32a5d303a51d012157b4 \
	'/root/build/rog5-kexec-stage-initramfs.cpio.gz' \
	'CONFIG_KEXEC=y' \
	'# CONFIG_KEXEC_FILE is not set' \
	'CONFIG_INITRAMFS_SOURCE="/root/build/rog5-kexec-stage-initramfs.cpio.gz"' \
	'CONFIG_INITRAMFS_COMPRESSION=".gz"' \
	'CONFIG_LOCALVERSION="-qgki-perf-kexec-stage-builtin-recovery"' \
	'KBUILD_BUILD_USER=rog5-linux' \
	'KBUILD_BUILD_HOST=rog5-builder' \
	'Wed Apr 19 00:00:00 UTC 2023' \
	'ASUS_BUILD_PROJECT=ZS673KS' \
	'Linux version 5.4.210' \
	'compile-only'
do
	grep -Fq "$contract" "$builder" || {
		echo "FAIL ASUS wrapper builder omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'curl|wget|git[[:space:]]+(clone|fetch|pull)|fastboot|adb|/dev/(block|disk)|[[:space:]]mount[[:space:]]|[[:space:]]dd[[:space:]]' \
	"$builder"
then
	echo 'FAIL ASUS wrapper builder contains network or device-control logic' >&2
	exit 1
fi

echo 'PASS Adreno SMMU ASUS wrapper build contract is pinned, offline, and reproducible'
