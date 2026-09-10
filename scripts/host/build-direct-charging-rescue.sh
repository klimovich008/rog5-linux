#!/usr/bin/env bash
set -euo pipefail
set -f

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# -eq 5 ]] ||
	fail 'usage: build-direct-charging-rescue.sh BUNDLE TEMPLATE OUTPUT EXPECTED_MANIFEST_SHA256 EXPECTED_TEMPLATE_SHA256'

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
bundle=$(realpath -e -- "$1")
template=$(realpath -e -- "$2")
output=$3
expected_manifest=$4
expected_template=$5
tools=$repo/artifacts/android-boot-tools-v1
unpack=$tools/unpack_bootimg.py
avbtool=$tools/avbtool.py
repack=$repo/scripts/device/repack-android-boot-v3.sh
reboot_source=$repo/tools/reboot_bootloader/rog5-reboot-bootloader.c
partition_size=100663296
route_token=rog5.charging_route=fastboot-direct-v3

[[ $expected_manifest =~ ^[0-9a-f]{64}$ ]] ||
	fail 'expected manifest SHA-256 is invalid'
[[ $expected_template =~ ^[0-9a-f]{64}$ ]] ||
	fail 'expected template SHA-256 is invalid'
[[ -d $bundle && ! -L $bundle ]] || fail 'bundle is not one real directory'
[[ -f $template && ! -L $template ]] || fail 'template is not one regular file'
[[ $output = /* ]] || fail 'output must be absolute'
[[ ! -e $output && ! -L $output ]] || fail 'output already exists'
output_parent=$(dirname -- "$output")
[[ -d $output_parent && ! -L $output_parent ]] || fail 'output parent is absent'

for input in "$unpack" "$avbtool" "$repack" "$reboot_source"; do
	[[ -f $input && ! -L $input ]] || fail "missing build input: $input"
done
for command in clang cpio file find gzip head install readelf sed sort stat touch; do
	command -v "$command" >/dev/null || fail "missing build command: $command"
done
[[ $(stat -c %s "$template") == "$partition_size" ]] ||
	fail 'template is not one exact boot-partition image'
[[ $(sha256sum "$template" | awk '{print $1}') == "$expected_template" ]] ||
	fail 'template SHA-256 mismatch'

expected_names=$(printf '%s\n' Image SHA256SUMS board.dtb cmdline initramfs.cpio.gz)
actual_names=$(find "$bundle" -mindepth 1 -maxdepth 1 -printf '%f\n' | LC_ALL=C sort)
[[ $actual_names == "$expected_names" ]] || fail 'bundle members are not exact'
for name in Image SHA256SUMS board.dtb cmdline initramfs.cpio.gz; do
	[[ -f $bundle/$name && ! -L $bundle/$name ]] ||
		fail "bundle member is not one regular file: $name"
done
[[ $(sha256sum "$bundle/SHA256SUMS" | awk '{print $1}') == \
	"$expected_manifest" ]] || fail 'bundle manifest SHA-256 mismatch'
[[ $(wc -l <"$bundle/SHA256SUMS") -eq 4 ]] ||
	fail 'bundle manifest line count is not exact'
manifest_names=$(awk '{print $2}' "$bundle/SHA256SUMS" | LC_ALL=C sort)
[[ $manifest_names == $(printf '%s\n' Image board.dtb cmdline initramfs.cpio.gz) ]] ||
	fail 'bundle manifest members are not exact'
(cd "$bundle" && sha256sum -c SHA256SUMS >/dev/null) ||
	fail 'bundle manifest verification failed'
gzip -t "$bundle/initramfs.cpio.gz"

[[ $(wc -l <"$bundle/cmdline") -eq 1 ]] || fail 'source command line is not one line'
source_cmdline=$(<"$bundle/cmdline")
[[ -n $source_cmdline && $source_cmdline != *$'\r'* ]] ||
	fail 'source command line is invalid'
for token in \
	androidboot.mode=charger \
	androidboot.force_normal_boot=0 \
	rdinit=/init \
	panic=10 \
	oops=panic \
	rog5.charging_rescue=1; do
	[[ $(tr ' ' '\n' <<<"$source_cmdline" | grep -Fxc "$token") -eq 1 ]] ||
		fail "source command line lacks exact token: $token"
done
! tr ' ' '\n' <<<"$source_cmdline" | grep -Eq \
	'^(root=|init=|androidboot\.force_normal_boot=1|rog5\.charging_route=)' ||
	fail 'source command line contains a forbidden direct-boot token'
normalized_cmdline=
for token in $source_cmdline; do
	key=${token%%=*}
	filtered=
	previous=
	for current in $normalized_cmdline; do
		if [[ ${current%%=*} == "$key" ]]; then
			previous=$current
			continue
		fi
		filtered+="${filtered:+ }$current"
	done
	[[ -z $previous || $previous == "$token" ]] ||
		fail "source command line has conflicting duplicate key: $key"
	normalized_cmdline="${filtered:+$filtered }$token"
done
direct_cmdline="$normalized_cmdline $route_token"

work=$(mktemp -d "$output_parent/.direct-charging-rescue.XXXXXX")
publish=$(mktemp -d "$output_parent/.direct-charging-publish.XXXXXX")
cleanup() {
	find "$work" -depth -delete 2>/dev/null || true
	if [[ -n ${publish:-} && -e $publish ]]; then
		find "$publish" -depth -delete 2>/dev/null || true
	fi
}
trap cleanup EXIT HUP INT TERM
mkdir "$work/template-inspection" "$work/output-inspection" "$work/root"

gzip -dc "$bundle/initramfs.cpio.gz" >"$work/source-initramfs.cpio"
[[ $(head -c 6 "$work/source-initramfs.cpio") == 070701 ]] ||
	fail 'source initramfs is not one newc archive'
(
	cd "$work/root"
	cpio -idm --quiet --no-absolute-filenames <"$work/source-initramfs.cpio"
)
[[ -f $work/root/init && ! -L $work/root/init ]] ||
	fail 'source initramfs lacks one regular init'
[[ ! -e $work/root/sbin/rog5-reboot-bootloader &&
	! -L $work/root/sbin/rog5-reboot-bootloader ]] ||
	fail 'source initramfs already contains the direct reboot helper'
slot_b_pipeline=$'\t'"grep -Fxc 'androidboot.slot_suffix=_b' || true)"
slot_a_pipeline=$'\t'"grep -Fxc 'androidboot.slot_suffix=_a' || true)"
[[ $(grep -Fxc "slot_suffix_tokens=\$(tr ' ' '\\n' </proc/cmdline |" \
	"$work/root/init") -eq 1 ||
	$(grep -Fxc "slot_suffix_tokens=\$(grep -Fxc 'androidboot.slot_suffix=_b' /proc/cmdline || true)" \
	"$work/root/init") -eq 1 ]] || fail 'source init slot parser is unknown'
[[ $(grep -Fxc "$slot_b_pipeline" \
	"$work/root/init") -eq 1 ||
	$(grep -Fxc "slot_suffix_tokens=\$(grep -Fxc 'androidboot.slot_suffix=_b' /proc/cmdline || true)" \
	"$work/root/init") -eq 1 ]] || fail 'source initramfs lacks one slot-B token'
[[ $(grep -Fxc "[ \"\$slot_suffix_tokens\" -eq 1 ] || fail 'expected unique active slot-B suffix'" \
	"$work/root/init") -eq 1 ]] || fail 'source initramfs lacks one slot-B diagnostic'
[[ $(grep -Fxc $'\techo b >/proc/sysrq-trigger' "$work/root/init") -eq 1 ]] ||
	fail 'source initramfs lacks one SysRq rollback'
LC_ALL=C sed \
	-e 's/androidboot\.slot_suffix=_b/androidboot.slot_suffix=_a/g' \
	-e 's/active slot-B suffix/active slot-A suffix/g' \
	-e 's#\techo b >/proc/sysrq-trigger#\t/sbin/rog5-reboot-bootloader || fail '\''bootloader restart2 returned'\''#' \
	"$work/root/init" >"$work/direct-init"
install -m 0755 "$work/direct-init" "$work/root/init"
clang --target=aarch64-linux-gnu -fuse-ld=lld -nostdlib -static -fno-builtin \
	-Wall -Wextra -Werror -fno-pic -fno-pie -fno-stack-protector -Wl,-e,_start \
	-Wl,--build-id=none -Wl,-z,noexecstack \
	-o "$work/root/sbin/rog5-reboot-bootloader" "$reboot_source"
[[ $(grep -Fxc "$slot_a_pipeline" \
	"$work/root/init") -eq 1 ||
	$(grep -Fxc "slot_suffix_tokens=\$(grep -Fxc 'androidboot.slot_suffix=_a' /proc/cmdline || true)" \
	"$work/root/init") -eq 1 ]] || fail 'direct initramfs lacks one slot-A token'
[[ $(grep -Fxc "[ \"\$slot_suffix_tokens\" -eq 1 ] || fail 'expected unique active slot-A suffix'" \
	"$work/root/init") -eq 1 ]] || fail 'direct initramfs lacks one slot-A diagnostic'
[[ $(grep -Fxc $'\t/sbin/rog5-reboot-bootloader || fail '\''bootloader restart2 returned'\''' \
	"$work/root/init") -eq 1 ]] || fail 'direct init lacks one bootloader rollback'
! grep -Fq 'androidboot.slot_suffix=_b' "$work/root/init" ||
	fail 'direct initramfs retains slot-B token'
! grep -Fq 'active slot-B suffix' "$work/root/init" ||
	fail 'direct initramfs retains slot-B diagnostic'
! grep -Fq 'echo b >/proc/sysrq-trigger' "$work/root/init" ||
	fail 'direct initramfs retains unsafe slot-A SysRq rollback'
readelf -h "$work/root/sbin/rog5-reboot-bootloader" |
	grep -Fq 'Machine:                           AArch64' ||
	fail 'reboot helper is not AArch64'
! readelf -l "$work/root/sbin/rog5-reboot-bootloader" |
	grep -Eq 'INTERP|DYNAMIC' || fail 'reboot helper is dynamically linked'
find "$work/root" -exec touch -h -d '@0' {} +
(
	cd "$work/root"
	LC_ALL=C find . -print0 | LC_ALL=C sort -z |
		cpio --null -o --quiet --format=newc --owner=0:0 --reproducible |
		gzip -n >"$work/direct-initramfs.cpio.gz"
)
gzip -t "$work/direct-initramfs.cpio.gz"

python3 "$unpack" --boot_img "$template" --out "$work/template-inspection/unpacked" \
	--format=mkbootimg --null >"$work/template-inspection/args.nul"
tr '\000' '\n' <"$work/template-inspection/args.nul" >"$work/template-inspection/args.lines"
template_cmdline=$(awk '$0 == "--cmdline" {getline; print; exit}' \
	"$work/template-inspection/args.lines")
[[ -z $template_cmdline ]] || fail 'template command line is not empty'

"$repack" \
	"$template" \
	"$bundle/Image" \
	"$work/direct-initramfs.cpio.gz" \
	"$tools" \
	"$avbtool" \
	"$work/boot.raw.img" \
	"$work/boot.img" \
	"$partition_size" \
	"$direct_cmdline" >/dev/null

python3 "$unpack" --boot_img "$work/boot.img" \
	--out "$work/output-inspection/unpacked" >"$work/output-inspection/info.txt"
grep -Fqx 'boot image header version: 3' "$work/output-inspection/info.txt"
cmp "$work/output-inspection/unpacked/kernel" "$bundle/Image"
cmp "$work/output-inspection/unpacked/ramdisk" "$work/direct-initramfs.cpio.gz"
python3 "$unpack" --boot_img "$work/boot.img" \
	--out "$work/output-inspection/args" --format=mkbootimg --null \
	>"$work/output-inspection/args.nul"
tr '\000' '\n' <"$work/output-inspection/args.nul" \
	>"$work/output-inspection/args.lines"
actual_cmdline=$(awk '$0 == "--cmdline" {getline; print; exit}' \
	"$work/output-inspection/args.lines")
[[ $actual_cmdline == "$direct_cmdline" ]] ||
	fail 'direct boot command line changed during repack'
[[ $(tr ' ' '\n' <<<"$actual_cmdline" | grep -Fxc "$route_token") -eq 1 ]] ||
	fail 'direct route token is not exact'

install -m 0644 "$work/boot.raw.img" "$publish/boot.raw.img"
install -m 0644 "$work/boot.img" "$publish/boot.img"
raw_sha=$(sha256sum "$publish/boot.raw.img" | awk '{print $1}')
boot_sha=$(sha256sum "$publish/boot.img" | awk '{print $1}')
image_sha=$(sha256sum "$bundle/Image" | awk '{print $1}')
source_ramdisk_sha=$(sha256sum "$bundle/initramfs.cpio.gz" | awk '{print $1}')
ramdisk_sha=$(sha256sum "$work/direct-initramfs.cpio.gz" | awk '{print $1}')
reboot_helper_sha=$(sha256sum "$work/root/sbin/rog5-reboot-bootloader" |
	awk '{print $1}')
dtb_sha=$(sha256sum "$bundle/board.dtb" | awk '{print $1}')
cmdline_sha=$(printf '%s\n' "$direct_cmdline" | sha256sum | awk '{print $1}')
{
	printf '%s\n' \
		'format=rog5-direct-charging-rescue-v3' \
		'candidate=official-ww33-charging-direct-v3' \
		'operation=fastboot-boot-only' \
		'required_slot=a' \
		'initramfs_slot_contract=a' \
		'rollback_target=bootloader' \
		'persistent_phone_writes=none-requested' \
		'rollback_seconds=30' \
		"bundle_manifest_sha256=$expected_manifest" \
		"template_sha256=$expected_template" \
		"image_sha256=$image_sha" \
		"source_initramfs_sha256=$source_ramdisk_sha" \
		"initramfs_sha256=$ramdisk_sha" \
		"reboot_helper_sha256=$reboot_helper_sha" \
		"kexec_dtb_reference_sha256=$dtb_sha" \
		"cmdline_sha256=$cmdline_sha" \
		"raw_image_sha256=$raw_sha" \
		"boot_image_sha256=$boot_sha" \
		'expected_vendor_boot_a_backup_sha256=1e1250a5e55b562d080cfac8bfd3732b704e983f301f10ad69fac02a01827bc1' \
		'expected_selected_vendor_dtb_sha256=edc923c729fb06d748dbcf4d567df021c73f4047d12f0be31120006c61c321e3' \
		"command_line=$direct_cmdline"
} >"$publish/candidate.txt"
(cd "$publish" && sha256sum boot.raw.img boot.img candidate.txt >SHA256SUMS)

mv -T -- "$publish" "$output"
publish=
trap - EXIT HUP INT TERM
find "$work" -depth -delete

sha256sum "$output/boot.img"
echo 'PASS distinct WW33 charging payload composed for direct RAM-only fastboot entry'
