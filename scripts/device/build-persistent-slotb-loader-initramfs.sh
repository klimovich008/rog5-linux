#!/bin/sh
set -eu

base=${1:?usage: build-persistent-slotb-loader-initramfs.sh BASE OUTPUT}
output=${2:?missing output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-slotb-loader-init
reboot_source=$repo/tools/reboot_bootloader/rog5-reboot-bootloader.c
trial_helper=$repo/$(cat "$repo/configs/persistent-trial-helper.path")
expected_base=d2f46588b46b615eae907ef98e2108fbcc06efc330ffa40136f6e89bdc39ddbc
expected_trial_helper=$(cut -d ' ' -f 1 "$(dirname "$trial_helper")/SHA256SUMS")
epoch=1681862400

[ -f "$base" ] && [ ! -L "$base" ] &&
	[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ]
[ -x "$init" ] && [ -f "$reboot_source" ] && [ ! -L "$reboot_source" ]
[ -f "$trial_helper" ] && [ ! -L "$trial_helper" ] &&
	[ -x "$trial_helper" ] &&
	[ "$(sha256sum "$trial_helper" | cut -d ' ' -f 1)" = \
	"$expected_trial_helper" ]
[ ! -e "$output" ]

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
root=$work/root
mkdir "$root"
gzip -dc "$base" | (cd "$root" && cpio -idm --quiet --no-absolute-filenames)
[ "$(sha256sum "$root/usr/libexec/rog5-bundle-verify" | cut -d ' ' -f 1)" = c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb ]
[ "$(sha256sum "$root/usr/sbin/kexec" | cut -d ' ' -f 1)" = 5e5d0a78b3f0bcf3921ff060f4dce5011cbac24b5e12fedeb8ca03ea5b40d015 ]
[ "$(sha256sum "$root/etc/rog5/recovery-bundle-ed25519.pub" | cut -d ' ' -f 1)" = cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]

install -m 0755 "$init" "$root/init"
install -d -m 0755 "$root/usr/libexec"
install -m 0755 "$trial_helper" \
	"$root/usr/libexec/rog5-persistent-trial-state"
clang --target=aarch64-linux-gnu -fuse-ld=lld -nostdlib -static \
	-fno-builtin -Wall -Wextra -Werror -fno-pic -fno-pie \
	-fno-stack-protector -Wl,-e,_start -Wl,--build-id=none \
	-Wl,-z,noexecstack -o "$root/usr/libexec/rog5-reboot-bootloader" \
	"$reboot_source"
readelf -h "$root/usr/libexec/rog5-reboot-bootloader" | grep -q 'Machine:.*AArch64'

find "$root" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$root" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output.tmp"
mv -T "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
