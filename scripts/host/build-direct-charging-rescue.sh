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
partition_size=100663296
route_token=rog5.charging_route=fastboot-direct-v1

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

for input in "$unpack" "$avbtool" "$repack"; do
	[[ -f $input && ! -L $input ]] || fail "missing build input: $input"
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
mkdir "$work/template-inspection" "$work/output-inspection"

python3 "$unpack" --boot_img "$template" --out "$work/template-inspection/unpacked" \
	--format=mkbootimg --null >"$work/template-inspection/args.nul"
tr '\000' '\n' <"$work/template-inspection/args.nul" >"$work/template-inspection/args.lines"
template_cmdline=$(awk '$0 == "--cmdline" {getline; print; exit}' \
	"$work/template-inspection/args.lines")
[[ -z $template_cmdline ]] || fail 'template command line is not empty'

"$repack" \
	"$template" \
	"$bundle/Image" \
	"$bundle/initramfs.cpio.gz" \
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
cmp "$work/output-inspection/unpacked/ramdisk" "$bundle/initramfs.cpio.gz"
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
ramdisk_sha=$(sha256sum "$bundle/initramfs.cpio.gz" | awk '{print $1}')
dtb_sha=$(sha256sum "$bundle/board.dtb" | awk '{print $1}')
cmdline_sha=$(printf '%s\n' "$direct_cmdline" | sha256sum | awk '{print $1}')
{
	printf '%s\n' \
		'format=rog5-direct-charging-rescue-v1' \
		'candidate=official-ww33-charging-direct-v1' \
		'operation=fastboot-boot-only' \
		'required_slot=a' \
		'persistent_phone_writes=none-requested' \
		'rollback_seconds=30' \
		"bundle_manifest_sha256=$expected_manifest" \
		"template_sha256=$expected_template" \
		"image_sha256=$image_sha" \
		"initramfs_sha256=$ramdisk_sha" \
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
