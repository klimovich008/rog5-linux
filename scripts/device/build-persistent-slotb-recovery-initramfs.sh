#!/bin/sh
set -eu

base=${1:?usage: build-persistent-slotb-recovery-initramfs.sh BASE INIT EXECUTOR OUTPUT}
init=${2:?missing recovery init}
executor=${3:?missing local loader executor}
output=${4:?missing output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
reboot_source=$repo/tools/reboot_bootloader/rog5-reboot-bootloader.c
expected_base=d2f46588b46b615eae907ef98e2108fbcc06efc330ffa40136f6e89bdc39ddbc
epoch=1681862400

fail() { echo "FAIL $*" >&2; exit 1; }

for command in chmod clang cmp cpio cut dirname find grep gzip install \
	mkdir mktemp mv readelf rm sha256sum sort stat touch; do
	command -v "$command" >/dev/null || fail "missing local-loader build command: $command"
done
for input in "$base" "$init" "$executor" "$reboot_source"; do
	[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
		fail "unsafe local-loader input: $(basename "$input")"
done
[ -x "$init" ] && [ -x "$executor" ] || fail 'init and executor must be executable'
[ ! -e "$output" ] && [ ! -L "$output" ] || fail 'local-loader output already exists'
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] ||
	fail 'unexpected live-proven recovery archive'

stage=$(mktemp -d)
output_directory=$(dirname "$output")
mkdir -p "$output_directory"
temporary=$(mktemp "$output_directory/.loader-recovery.tmp.XXXXXX")
cleanup() {
	rm -rf -- "$stage"
	rm -f -- "$temporary"
}
trap cleanup EXIT HUP INT TERM

gzip -dc "$base" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"
[ "$(sha256sum "$stage/usr/libexec/rog5-bundle-verify" | cut -d ' ' -f 1)" = \
	c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb ] ||
	fail 'bundle verifier identity changed'
[ "$(sha256sum "$stage/usr/sbin/kexec" | cut -d ' ' -f 1)" = \
	5e5d0a78b3f0bcf3921ff060f4dce5011cbac24b5e12fedeb8ca03ea5b40d015 ] ||
	fail 'kexec identity changed'
[ "$(sha256sum "$stage/etc/rog5/recovery-bundle-ed25519.pub" | cut -d ' ' -f 1)" = \
	cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ] ||
	fail 'local bundle trust key changed'

rm -f -- "$stage/usr/libexec/rog5-recovery-control" \
	"$stage/usr/libexec/rog5-bundle-fetch"
chmod 0644 "$stage/etc/rog5/recovery-mode"
printf '%s\n' persistent-slotb-loader-v1 >"$stage/etc/rog5/recovery-mode"
chmod 0444 "$stage/etc/rog5/recovery-mode"
install -m 0755 "$executor" "$stage/usr/libexec/rog5-persistent-slotb-local-loader"

clang --target=aarch64-linux-gnu -fuse-ld=lld -nostdlib -static \
	-fno-builtin -Wall -Wextra -Werror -fno-pic -fno-pie \
	-fno-stack-protector -Wl,-e,_start -Wl,--build-id=none \
	-Wl,-z,noexecstack -o "$stage/usr/libexec/rog5-reboot-bootloader" \
	"$reboot_source"
readelf -h "$stage/usr/libexec/rog5-reboot-bootloader" |
	grep -q 'Machine:.*AArch64' || fail 'reboot helper is not AArch64'

cmp "$stage/init" "$init"
cmp "$stage/usr/libexec/rog5-persistent-slotb-local-loader" "$executor"
[ "$(cat "$stage/etc/rog5/recovery-mode")" = persistent-slotb-loader-v1 ]
[ ! -e "$stage/usr/libexec/rog5-recovery-control" ]
[ ! -e "$stage/usr/libexec/rog5-bundle-fetch" ]
[ -x "$stage/usr/libexec/rog5-bundle-verify" ]
[ -x "$stage/usr/sbin/kexec" ]

find "$stage" -exec touch -h -d "@$epoch" {} +
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$temporary"
gzip -t "$temporary"
mv -T -- "$temporary" "$output"
trap - EXIT HUP INT TERM
rm -rf -- "$stage"

sha256sum "$init" "$executor" "$output"
echo 'PASS deterministic canonical-recovery local signed-bundle loader initramfs'
