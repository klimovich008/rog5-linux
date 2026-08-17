#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/build-direct-charging-rescue.sh
tools=$repo/artifacts/android-boot-tools-v1
reboot_source=$repo/tools/reboot_bootloader/rog5-reboot-bootloader.c
stage=$(mktemp -d)
trap 'find "$stage" -depth -delete' EXIT HUP INT TERM
mkdir -p "$stage/bundle" "$stage/bundle-root/sbin"

printf 'fixture-kernel\n' >"$stage/bundle/Image"
printf 'fixture-dtb\n' >"$stage/bundle/board.dtb"
cat >"$stage/bundle-root/init" <<'INIT'
#!/bin/sh
set -eu
fail() { while :; do sleep 3600; done; }
slot_suffix_tokens=$(grep -Fxc 'androidboot.slot_suffix=_b' /proc/cmdline || true)
[ "$slot_suffix_tokens" -eq 1 ] || fail 'expected unique active slot-B suffix'
(
	sleep 30
	echo b >/proc/sysrq-trigger
) &
while :; do sleep 3600; done
INIT
chmod 0755 "$stage/bundle-root/init"
(
	cd "$stage/bundle-root"
	find . -print0 | LC_ALL=C sort -z |
		cpio --null -o --quiet --format=newc --owner=0:0 --reproducible |
		gzip -n >"$stage/bundle/initramfs.cpio.gz"
)
printf '%s\n' \
	'console=ttyMSM0,115200n8 loop.max_part=7 androidboot.mode=charger androidboot.force_normal_boot=0 rdinit=/init panic=10 oops=panic loop.max_part=7 ignore_loglevel rog5.charging_rescue=1' \
	>"$stage/bundle/cmdline"
(cd "$stage/bundle" && \
	sha256sum Image board.dtb cmdline initramfs.cpio.gz >SHA256SUMS)

python3 "$tools/mkbootimg.py" \
	--header_version 3 \
	--os_version 11.0.0 \
	--os_patch_level 2023-04 \
	--kernel "$stage/bundle/Image" \
	--ramdisk "$stage/bundle/initramfs.cpio.gz" \
	--cmdline '' \
	--output "$stage/template.raw.img"
cp "$stage/template.raw.img" "$stage/template.img"
python3 "$tools/avbtool.py" add_hash_footer \
	--image "$stage/template.img" \
	--partition_name boot \
	--partition_size 100663296 \
	--algorithm NONE \
	--salt "$(sha256sum "$stage/template.raw.img" | awk '{print $1}')"

manifest_sha=$(sha256sum "$stage/bundle/SHA256SUMS" | awk '{print $1}')
template_sha=$(sha256sum "$stage/template.img" | awk '{print $1}')
"$builder" "$stage/bundle" "$stage/template.img" "$stage/a" \
	"$manifest_sha" "$template_sha" >/dev/null
"$builder" "$stage/bundle" "$stage/template.img" "$stage/b" \
	"$manifest_sha" "$template_sha" >/dev/null
diff -qr "$stage/a" "$stage/b" >/dev/null
(cd "$stage/a" && sha256sum -c SHA256SUMS >/dev/null)

mkdir "$stage/inspection"
python3 "$tools/unpack_bootimg.py" --boot_img "$stage/a/boot.img" \
	--out "$stage/inspection/unpacked" --format=mkbootimg --null \
	>"$stage/inspection/args.nul"
cmp "$stage/inspection/unpacked/kernel" "$stage/bundle/Image"
gzip -dc "$stage/bundle/initramfs.cpio.gz" >"$stage/source-initramfs.cpio"
gzip -dc "$stage/inspection/unpacked/ramdisk" >"$stage/direct-initramfs.cpio"
mkdir "$stage/direct-root"
(
	cd "$stage/direct-root"
	cpio -idm --quiet <"$stage/direct-initramfs.cpio"
)
grep -aFq 'androidboot.slot_suffix=_b' "$stage/source-initramfs.cpio"
grep -aFq 'expected unique active slot-B suffix' "$stage/source-initramfs.cpio"
grep -aFq 'echo b >/proc/sysrq-trigger' "$stage/source-initramfs.cpio"
grep -aFq 'androidboot.slot_suffix=_a' "$stage/direct-initramfs.cpio"
grep -aFq 'expected unique active slot-A suffix' "$stage/direct-initramfs.cpio"
! grep -aFq 'androidboot.slot_suffix=_b' "$stage/direct-initramfs.cpio"
! grep -aFq 'active slot-B suffix' "$stage/direct-initramfs.cpio"
! grep -aFq 'echo b >/proc/sysrq-trigger' "$stage/direct-initramfs.cpio"
grep -Fq '/sbin/rog5-reboot-bootloader || fail' "$stage/direct-root/init"
[[ -f $stage/direct-root/sbin/rog5-reboot-bootloader &&
	-x $stage/direct-root/sbin/rog5-reboot-bootloader ]]
[[ -f $reboot_source && ! -L $reboot_source ]]
for token in \
	'#define LINUX_REBOOT_MAGIC1 0xFEE1DEADUL' \
	'#define LINUX_REBOOT_MAGIC2 672274793UL' \
	'#define LINUX_REBOOT_CMD_RESTART2 0xA1B2C3D4UL' \
	'#define NR_REBOOT 142UL' \
	'static const char command[] = "bootloader"' \
	'exit_status(111)'; do
	grep -Fq "$token" "$reboot_source"
done
readelf -h "$stage/direct-root/sbin/rog5-reboot-bootloader" |
	grep -Fq 'Machine:                           AArch64'
! readelf -l "$stage/direct-root/sbin/rog5-reboot-bootloader" |
	grep -Eq 'INTERP|DYNAMIC'
tr '\000' '\n' <"$stage/inspection/args.nul" >"$stage/inspection/args.lines"
cmdline=$(awk '$0 == "--cmdline" {getline; print; exit}' \
	"$stage/inspection/args.lines")
[[ $cmdline == \
	'console=ttyMSM0,115200n8 androidboot.mode=charger androidboot.force_normal_boot=0 rdinit=/init panic=10 oops=panic loop.max_part=7 ignore_loglevel rog5.charging_rescue=1 rog5.charging_route=fastboot-direct-v3' ]]
[[ $(tr ' ' '\n' <<<"$cmdline" |
	grep -Fxc 'rog5.charging_route=fastboot-direct-v3') -eq 1 ]]
[[ $(tr ' ' '\n' <<<"$cmdline" | grep -Fxc ignore_loglevel) -eq 1 ]]
[[ $(tr ' ' '\n' <<<"$cmdline" | grep -Fxc loop.max_part=7) -eq 1 ]]
grep -Fqx 'candidate=official-ww33-charging-direct-v3' "$stage/a/candidate.txt"
grep -Fqx 'required_slot=a' "$stage/a/candidate.txt"
grep -Fqx 'initramfs_slot_contract=a' "$stage/a/candidate.txt"
grep -Fqx 'rollback_target=bootloader' "$stage/a/candidate.txt"
grep -Fqx 'operation=fastboot-boot-only' "$stage/a/candidate.txt"
grep -Fqx 'persistent_phone_writes=none-requested' "$stage/a/candidate.txt"

if "$builder" "$stage/bundle" "$stage/template.img" "$stage/a" \
	"$manifest_sha" "$template_sha" >/dev/null 2>&1; then
	echo 'FAIL builder replaced an existing output' >&2
	exit 1
fi
if "$builder" "$stage/bundle" "$stage/template.img" "$stage/c" \
	"${manifest_sha%?}0" "$template_sha" >/dev/null 2>&1; then
	echo 'FAIL builder accepted a wrong manifest identity' >&2
	exit 1
fi

echo 'PASS direct charging rescue is exact, deterministic, slot-A-bound, bootloader-rollback-safe, and RAM-only'
