#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-persistent-root-entry-asus-kexec-stage.sh

[ -x "$builder" ] || {
	echo 'FAIL missing executable P2 entry ASUS wrapper builder' >&2
	exit 1
}
sh -n "$builder"

for contract in \
	'3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8' \
	'54ea162415b31227ae50d98806d59179ac2b1acca53d71be1a3f036f9eb92069' \
	'df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f' \
	'3360abb8b47cdc5ffd5be59664b979fad186611442bd8224ced225084a4ecc73' \
	'/root/build/rog5-kexec-stage-initramfs.cpio.gz' \
	'CONFIG_KEXEC=y' \
	'# CONFIG_KEXEC_FILE is not set' \
	'CONFIG_INITRAMFS_SOURCE="/root/build/rog5-kexec-stage-initramfs.cpio.gz"' \
	'CONFIG_INITRAMFS_COMPRESSION=".gz"' \
	'CONFIG_LOCALVERSION="-qgki-perf-kexec-stage-builtin-recovery"' \
	'KBUILD_BUILD_TIMESTAMP=' \
	'DISABLE_WRAPPER=1' \
	'ASUS_BUILD_PROJECT=ZS673KS' \
	'olddefconfig' \
	'-j "$jobs" Image' \
	'image.count(initramfs) != 1'; do
	grep -Fq -- "$contract" "$builder" || {
		echo "FAIL P2 entry wrapper builder omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'curl|wget|git[[:space:]]+(clone|pull|fetch)|fastboot|adb|ssh|scp|rsync|mount[[:space:]]|sudo' \
	"$builder"; then
	echo 'FAIL P2 entry wrapper builder has network or device control' >&2
	exit 1
fi

echo 'PASS P2 early-entry ASUS wrapper build contract is pinned, offline, one-embed, and reproducible'
