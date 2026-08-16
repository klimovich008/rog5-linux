#!/usr/bin/env bash
set -euo pipefail
set -f

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output=${1:?usage: build-alpine-charging-rescue.sh OUTPUT KERNEL VENDOR_RAMDISK ALPINE_RAMDISK BOARD_DTB EXTRA_MODULE_DIR}
kernel=${2:?missing kernel}
vendor_ramdisk=${3:?missing vendor ramdisk}
alpine_ramdisk=${4:?missing Alpine ramdisk}
dtb=${5:?missing board DTB}
extra_modules=${6:?missing extra-module directory}
init=$repo/initramfs/alpine-charging-rescue-init

expected_kernel_size=37915136
expected_kernel_sha=6dff1ff234fab4fa37f30ad5862cd58b693c9f4441d9ed242acbe285d559c78f
expected_vendor_size=1893230
expected_vendor_sha=5e1512ed8d7fcc0279c5a0b8c7b0b23be0c843cc5479c596c128c5fdcd2bbc8d
expected_alpine_size=5830004
expected_alpine_sha=64db1bf572e2fb8ac77a8a79ea283e81a57ff8a9a319f0cba68da18f6a8c9841
expected_dtb_size=839798
expected_dtb_sha=c37d9212ee56dc4ee9d14f4a66fd0e85f8532217d145c92e0fbe44323139654b

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

for command in cp cpio file find gzip install mkdir mv sha256sum sort stat strings touch; do
	command -v "$command" >/dev/null || fail "missing build command: $command"
done
[[ -x $init ]] || fail 'missing executable charging-rescue init'
[[ -d $extra_modules && ! -L $extra_modules ]] ||
	fail 'extra-module directory is not a real directory'
case $output in
	''|/|.|..) fail 'unsafe charging-rescue output directory' ;;
esac
[[ ! -e $output && ! -e $output.tmp ]] ||
	fail 'charging-rescue output or incomplete sibling already exists'

check_exact "$kernel" "$expected_kernel_size" "$expected_kernel_sha" kernel
check_exact "$vendor_ramdisk" "$expected_vendor_size" "$expected_vendor_sha" vendor-ramdisk
check_exact "$alpine_ramdisk" "$expected_alpine_size" "$expected_alpine_sha" alpine-ramdisk
check_exact "$dtb" "$expected_dtb_size" "$expected_dtb_sha" board-dtb
gzip -t "$vendor_ramdisk"
gzip -t "$alpine_ramdisk"
file "$dtb" | grep -q 'Device Tree Blob version 17' || fail 'board DTB is not FDT v17'
kernel_version='Linux version 5.4.210-qgki-perf (root@rog5-linux) (Alpine clang version 22.1.3, LLD 22.1.3) #21 SMP PREEMPT Wed Jul 22 06:11:19 CEST 2026'
[[ $(strings "$kernel" | grep -Fxc "$kernel_version") == 1 ]] ||
	fail 'kernel release/build identity mismatch'

declare -A module_sha=(
	[adsp_loader_dlkm.ko]=366668d1f7bc2e18c886d314c7888cce5d455b19432c4db4c7824e540b50f26e
	[apr_dlkm.ko]=e2bbb3867b28e34acf201055f12be2d3508a30dacc1be3863637f728218852bc
	[q6_notifier_dlkm.ko]=dc12f30cb1e9c48efa137b331b772b08401791317a23313905d7f9f5348381c5
	[q6_pdr_dlkm.ko]=6fabaf16adce837dc50256eb43348fe62db873f3d1c0339e0ec61793e9830752
	[qti_battery_charger_main.ko]=1878a73d53d9e85f7e0abdadb1e0197b8837e402016ffeb012c6e1763f350af9
	[snd_event_dlkm.ko]=4606359e1cdb7bcae52483facabbf766cfba203f6751ddf726342aab7fccd2a5
)
actual_names=$(find "$extra_modules" -mindepth 1 -maxdepth 1 -type f -name '*.ko' \
	-printf '%f\n' | LC_ALL=C sort)
expected_names=$(printf '%s\n' "${!module_sha[@]}" | LC_ALL=C sort)
[[ $actual_names == "$expected_names" ]] || fail 'extra-module name set mismatch'
for name in "${!module_sha[@]}"; do
	check_exact "$extra_modules/$name" \
		"$(stat -c %s -- "$extra_modules/$name")" "${module_sha[$name]}" "$name"
	[[ $(strings "$extra_modules/$name" | grep -Fxc \
		'vermagic=5.4.210-qgki-perf SMP preempt mod_unload modversions aarch64') == 1 ]] ||
		fail "$name vermagic mismatch"
done

work=$(mktemp -d)
cleanup() {
	find "$work" -depth -mindepth 1 -delete 2>/dev/null || true
	rmdir "$work" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM
mkdir -p "$work/vendor" "$work/alpine" "$work/root"
(
	cd "$work/vendor"
	gzip -dc "$vendor_ramdisk" | cpio -idm --quiet
)
(
	cd "$work/alpine"
	gzip -dc "$alpine_ramdisk" | cpio -idm --quiet
)
cp -a "$work/vendor/." "$work/root/"
cp -a "$work/alpine/." "$work/root/"
install -m 0755 "$init" "$work/root/init"
install -d -m 0755 "$work/root/lib/modules/5.4.210-qgki-perf/extra"
for name in "${!module_sha[@]}"; do
	install -m 0644 "$extra_modules/$name" \
		"$work/root/lib/modules/5.4.210-qgki-perf/extra/$name"
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
	'console=ttyMSM0,115200n8 androidboot.hardware=qcom androidboot.usbcontroller=a600000.dwc3 service_locator.enable=1 androidboot.mode=charger rdinit=/init panic=10 oops=panic rog5.charging_rescue=1' \
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
echo 'PASS exact 5.4.210 RAM-only headless charging-rescue payload built'
