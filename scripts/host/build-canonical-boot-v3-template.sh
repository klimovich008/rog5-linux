#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
tools=${ROG5_ANDROID_BOOT_TOOLS:-$repo/artifacts/android-boot-tools-v1}
output_root=${1:-$repo/artifacts/recovery-wrapper-inputs-v1}
mkbootimg=$tools/mkbootimg.py
unpack=$tools/unpack_bootimg.py
expected_mkbootimg=d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a
expected_unpack=7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef
output_name=rog5-canonical-boot-v3-template.raw.img
output_size=12288
output_sha=37baad36386ed88abdc64e86849cbbf0b26a35137edebaea83c3ac78414b7d6d
report_name=template-provenance.txt
cmdline='init=/init selinux=0 printk.devkmsg=on rog5linux.test=1 ramoops.mem_address=0x9b800000 ramoops.mem_size=0x400000 ramoops.record_size=0x100000 ramoops.console_size=0x300000 ramoops.pmsg_size=0 ramoops.ftrace_size=0 ramoops.dump_oops=1 rog5.recovery_timeout=300'

for command_name in awk chmod cmp cut dirname find grep mkdir mktemp mv \
	python3 realpath sha256sum stat tr; do
	command -v "$command_name" >/dev/null ||
		fail "missing canonical boot-template command: $command_name"
done
for input in "$mkbootimg" "$unpack"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing or linked Android boot tool: $input"
done
[[ $(sha256sum "$mkbootimg" | cut -d ' ' -f 1) == \
	"$expected_mkbootimg" ]] ||
	fail 'mkbootimg identity changed'
[[ $(sha256sum "$unpack" | cut -d ' ' -f 1) == "$expected_unpack" ]] ||
	fail 'unpack_bootimg identity changed'

case $output_root in
	''|/|/dev|/dev/*|/proc|/proc/*|/sys|/sys/*|/run|/run/*)
		fail 'unsafe canonical boot-template output root'
		;;
esac
output_parent=$(dirname "$output_root")
mkdir -p "$output_parent"
output_parent=$(realpath -e "$output_parent")
output_root=$output_parent/$(basename "$output_root")
[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'refusing existing canonical boot-template output root'

work=$(mktemp -d)
publish=$(mktemp -d "$output_parent/.recovery-wrapper-inputs-v1.XXXXXX")
cleanup() {
	find "$work" -depth -delete 2>/dev/null || true
	if [[ -n ${publish:-} && -e $publish ]]; then
		find "$publish" -depth -delete 2>/dev/null || true
	fi
}
trap cleanup EXIT HUP INT TERM
mkdir "$work/a" "$work/b" "$work/inspection"
printf 'rog5-template-kernel\n' >"$work/kernel"
printf 'rog5-template-ramdisk\n' >"$work/ramdisk"

build_one() {
	output=$1
	python3 "$mkbootimg" \
		--header_version 3 \
		--os_version 11.0.0 \
		--os_patch_level 2022-02 \
		--kernel "$work/kernel" \
		--ramdisk "$work/ramdisk" \
		--cmdline "$cmdline" \
		--output "$output"
}

build_one "$work/a/template.raw.img"
build_one "$work/b/template.raw.img"
cmp "$work/a/template.raw.img" "$work/b/template.raw.img" ||
	fail 'two canonical boot-v3 template builds differ'
[[ $(stat -c %s "$work/a/template.raw.img") == "$output_size" ]] ||
	fail 'canonical boot-v3 template size changed'
[[ $(sha256sum "$work/a/template.raw.img" | cut -d ' ' -f 1) == \
	"$output_sha" ]] ||
	fail 'canonical boot-v3 template hash changed'

python3 "$unpack" --boot_img "$work/a/template.raw.img" \
	--out "$work/inspection/unpacked" >"$work/inspection/info.txt"
grep -Fqx 'boot image header version: 3' "$work/inspection/info.txt"
grep -Fqx 'os version: 11.0.0' "$work/inspection/info.txt"
grep -Fqx 'os patch level: 2022-02' "$work/inspection/info.txt"
cmp "$work/inspection/unpacked/kernel" "$work/kernel"
cmp "$work/inspection/unpacked/ramdisk" "$work/ramdisk"
python3 "$unpack" --boot_img "$work/a/template.raw.img" \
	--out "$work/inspection/args" --format=mkbootimg --null \
	>"$work/inspection/args.nul"
tr '\000' '\n' <"$work/inspection/args.nul" \
	>"$work/inspection/args.lines"
actual_cmdline=$(
	awk '$0 == "--cmdline" { getline; print; exit }' \
		"$work/inspection/args.lines"
)
[[ $actual_cmdline == "$cmdline" ]] ||
	fail 'canonical boot-v3 template command line changed'
if grep -Eq 'rog5\.(recovery_cidr|ufs_discovery)=' \
	"$work/inspection/args.lines"; then
	fail 'canonical boot-v3 template contains a target or legacy network token'
fi

install -m 0644 "$work/a/template.raw.img" "$publish/$output_name"
{
	printf '%s\n' \
		'schema=rog5-canonical-boot-v3-template-v1' \
		'state=reproducible-successor' \
		'boot_authority=none' \
		"mkbootimg_sha256=$expected_mkbootimg" \
		"unpack_bootimg_sha256=$expected_unpack" \
		'header_version=3' \
		'os_version=11.0.0' \
		'os_patch_level=2022-02' \
		"cmdline=$cmdline" \
		"template_size=$output_size" \
		"template_sha256=$output_sha"
} >"$publish/$report_name"
chmod 0644 "$publish/$report_name"

mv -T -- "$publish" "$output_root"
publish=
trap - EXIT HUP INT TERM
find "$work" -depth -delete

sha256sum "$output_root/$output_name"
echo 'PASS twin-built compact canonical Android boot-v3 template; no boot authority'
