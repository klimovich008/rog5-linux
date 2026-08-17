#!/usr/bin/env bash
set -euo pipefail
set -f

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output=${1:?usage: build-alpine-charging-rescue.sh OUTPUT KERNEL VENDOR_IMAGE ALPINE_RAMDISK BOARD_DTB}
kernel=${2:?missing kernel}
vendor_image=${3:?missing vendor image}
alpine_ramdisk=${4:?missing Alpine ramdisk}
dtb=${5:?missing board DTB}
init=$repo/initramfs/alpine-charging-rescue-init
firmware_helper=$repo/initramfs/rog5-charging-firmware.sh

expected_release=5.4.210-qgki-perf-gc89cd02a7dfe
expected_kernel_size=46305792
expected_kernel_sha=54b8d9d23ace1126bf1059f1ab483c027b50865695c7b305a15311e30a217b33
expected_vendor_size=1201238016
expected_vendor_sha=c6dd3e4ab60f54a88cccf68f445d694449674ed4c91f777ed57fbdc0cce6befd
expected_alpine_size=5830004
expected_alpine_sha=64db1bf572e2fb8ac77a8a79ea283e81a57ff8a9a319f0cba68da18f6a8c9841
expected_dtb_size=839846
expected_dtb_sha=4a62a4b83ff8948667732e55d8f2e57e575e05e9d3a3aa64b3da1dc58fd78065

check_exact() {
	path=$1
	expected_size=$2
	expected_sha=$3
	label=$4
	[[ -f $path && ! -L $path ]] || fail "$label is not a regular file"
	[[ $(stat -c %s -- "$path") == "$expected_size" ]] ||
		fail "$label size mismatch"
	[[ $(sha256sum -- "$path" | cut -d ' ' -f 1) == "$expected_sha" ]] ||
		fail "$label hash mismatch"
}

for command in cp cpio debugfs file find gzip install mkdir mv sha256sum \
	sort stat strings touch; do
	command -v "$command" >/dev/null || fail "missing build command: $command"
done
[[ -x $init ]] || fail 'missing executable charging-rescue init'
[[ -f $firmware_helper && ! -L $firmware_helper ]] ||
	fail 'missing regular charging firmware helper'
case $output in
	''|/|.|..) fail 'unsafe charging-rescue output directory' ;;
esac
output_parent=$(realpath -e -- "$(dirname -- "$output")")
[[ -d $output_parent ]] || fail 'charging-rescue output parent is not a directory'
output=$output_parent/$(basename -- "$output")
[[ ! -e $output && ! -e $output.tmp ]] ||
	fail 'charging-rescue output or incomplete sibling already exists'

check_exact "$kernel" "$expected_kernel_size" "$expected_kernel_sha" kernel
check_exact "$vendor_image" "$expected_vendor_size" "$expected_vendor_sha" vendor-image
check_exact "$alpine_ramdisk" "$expected_alpine_size" "$expected_alpine_sha" alpine-ramdisk
check_exact "$dtb" "$expected_dtb_size" "$expected_dtb_sha" board-dtb
gzip -t "$alpine_ramdisk"
vendor_stats=$(debugfs -R stats "$vendor_image" 2>/dev/null) ||
	fail 'vendor image is not a readable ext filesystem'
grep -Fq 'Filesystem magic number:  0xEF53' <<<"$vendor_stats" ||
	fail 'vendor image filesystem magic mismatch'
grep -Fq 'Filesystem volume name:   vendor' <<<"$vendor_stats" ||
	fail 'vendor image volume label mismatch'
grep -Fq 'Filesystem state:         clean' <<<"$vendor_stats" ||
	fail 'vendor image filesystem is not clean'
file "$dtb" | grep -q 'Device Tree Blob version 17' || fail 'board DTB is not FDT v17'
kernel_version='Linux version 5.4.210-qgki-perf-gc89cd02a7dfe (cm@cm-build-53-192) (Android (6573524 based on r383902b) clang version 11.0.2 (https://android.googlesource.com/toolchain/llvm-project b397f81060ce6d701042b782172ed13bee898b79), LLD 11.0.2 (/buildbot/tmp/tmpF3FjA8 b397f81060ce6d701042b782172ed13bee898b79)) #1 SMP PREEMPT Mon Apr 10 20:49:31 CST 2023'
[[ $(strings "$kernel" | grep -Fxc "$kernel_version") -ge 1 ]] ||
	fail 'kernel release/build identity mismatch'

declare -A module_size=(
	[adsp_loader_dlkm.ko]=22480
	[apr_dlkm.ko]=66632
	[q6_notifier_dlkm.ko]=30720
	[q6_pdr_dlkm.ko]=15936
	[snd_event_dlkm.ko]=21408
)
declare -A module_sha=(
	[adsp_loader_dlkm.ko]=68e67ce5953e471e6a7c1dc1a3c84546b13c687607fbcb359865c5501544f007
	[apr_dlkm.ko]=96e6a06df63414f2dfbdb41da3866507efa4689d8e20df3834a9b17c6f2b64a0
	[q6_notifier_dlkm.ko]=42843874514529077b6c9f41f9741a0873823c15d88a651982985729f438e244
	[q6_pdr_dlkm.ko]=89915e119f3f15312c7051c81d6954f18133d0e6c954559230d9d53fbb8bf975
	[snd_event_dlkm.ko]=eb2c8f92a03d01207e2441c1760f55e4fc7b5256365632f8ed950d8ee7692d9b
)

work=$(mktemp -d)
cleanup() {
	find "$work" -depth -mindepth 1 -delete 2>/dev/null || true
	rmdir "$work" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM
mkdir -p "$work/alpine" "$work/modules" "$work/root"
for name in "${!module_sha[@]}"; do
	debugfs -R "dump /lib/modules/$name $work/modules/$name" \
		"$vendor_image" >/dev/null 2>&1 ||
		fail "cannot extract exact WW33 module $name"
	check_exact "$work/modules/$name" "${module_size[$name]}" \
		"${module_sha[$name]}" "$name"
	[[ $(strings "$work/modules/$name" | grep -Fxc \
		'vermagic=5.4.210-qgki-perf-gc89cd02a7dfe SMP preempt mod_unload modversions aarch64') == 1 ]] ||
		fail "$name vermagic mismatch"
done

(
	cd "$work/alpine"
	gzip -dc "$alpine_ramdisk" | cpio -idm --quiet
)
cp -a "$work/alpine/." "$work/root/"
install -m 0755 "$init" "$work/root/init"
install -d -m 0755 "$work/root/libexec" \
	"$work/root/lib/modules/$expected_release/extra"
install -m 0644 "$firmware_helper" \
	"$work/root/libexec/rog5-charging-firmware.sh"
for name in "${!module_sha[@]}"; do
	install -m 0644 "$work/modules/$name" \
		"$work/root/lib/modules/$expected_release/extra/$name"
done
find "$work/root" -exec touch -h -d '@0' {} +

mkdir -p "$output.tmp"
(
	cd "$work/root"
	LC_ALL=C find . -print0 | LC_ALL=C sort -z |
		cpio --null -o --quiet --format=newc --owner=0:0 --reproducible |
		gzip -n >"$output.tmp/initramfs.cpio.gz"
)
install -m 0644 "$kernel" "$output.tmp/Image"
install -m 0644 "$dtb" "$output.tmp/board.dtb"
printf '%s\n' \
	'log_buf_len=256K earlycon=msm_geni_serial,0x98c000 rcupdate.rcu_expedited=1 rcu_nocbs=0-7 kpti=off console=ttyMSM0,115200n8 androidboot.hardware=qcom androidboot.console=ttyMSM0 androidboot.memcg=1 lpm_levels.sleep_disabled=1 video=vfb:640x400,bpp=32,memsize=3072000 msm_rtb.filter=0x237 service_locator.enable=1 androidboot.usbcontroller=a600000.dwc3 swiotlb=0 loop.max_part=7 cgroup.memory=nokmem,nosocket pcie_ports=compat loop.max_part=7 iptable_raw.raw_before_defrag=1 ip6table_raw.raw_before_defrag=1 buildvariant=user androidboot.mode=charger androidboot.force_normal_boot=0 rdinit=/init panic=10 oops=panic loglevel=8 ignore_loglevel printk.always_kmsg_dump=Y ramoops.mem_address=0x9b800000 ramoops.mem_size=0x400000 ramoops.record_size=0x100000 ramoops.console_size=0x300000 ramoops.pmsg_size=0 ramoops.ftrace_size=0 ramoops.dump_oops=1 rog5.charging_rescue=1' \
	>"$output.tmp/cmdline"
(
	cd "$output.tmp"
	sha256sum Image board.dtb cmdline initramfs.cpio.gz >SHA256SUMS
)
mv "$output.tmp" "$output"
trap - EXIT HUP INT TERM
cleanup

sha256sum "$output"/Image "$output"/board.dtb \
	"$output"/cmdline "$output"/initramfs.cpio.gz
echo 'PASS exact WW33 RAM-only headless charging-rescue payload built'
