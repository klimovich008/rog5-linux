#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/load-stock-charging-recovery.sh}
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/bin" "$stage/drivers/hh-watchdog" \
	"$stage/payload" "$stage/sys/good/of_node"

printf 'kernel\n' >"$stage/payload/Image"
printf 'dtb\n' >"$stage/payload/board.dtb"
printf 'initramfs\n' | gzip -n >"$stage/payload/initramfs.cpio.gz"
printf '%s\n' \
	'console=ttyMSM0,115200n8 androidboot.hardware=qcom androidboot.usbcontroller=a600000.dwc3 service_locator.enable=1 androidboot.mode=charger androidboot.force_normal_boot=0 rdinit=/init panic=10 oops=panic' \
	>"$stage/payload/cmdline"
(cd "$stage/payload" &&
	sha256sum Image board.dtb cmdline initramfs.cpio.gz >SHA256SUMS)

ln -s "$stage/drivers/hh-watchdog" "$stage/sys/good/driver"
printf 'qcom,hh-watchdog\000' >"$stage/sys/good/of_node/compatible"
printf '0\n' >"$stage/sys/good/disable"
printf '%s\n' '#!/bin/sh' 'exit 0' >"$stage/bin/dmesg"
printf '%s\n' '#!/bin/sh' 'printf "%s\n" "$@" >"$KEXEC_RECORD"' \
	>"$stage/bin/kexec"
chmod +x "$stage/bin/dmesg" "$stage/bin/kexec"

export KEXEC_RECORD=$stage/kexec.args
PATH=$stage/bin:$PATH PAYLOAD=$stage/payload SYS_DEVICES=$stage/sys \
	"$target" >/dev/null
grep -qx 1 "$stage/sys/good/disable"
grep -qx -- -c "$KEXEC_RECORD"
grep -qx -- -l "$KEXEC_RECORD"
grep -qx -- "--dtb=$stage/payload/board.dtb" "$KEXEC_RECORD"
grep -qx -- "--initrd=$stage/payload/initramfs.cpio.gz" "$KEXEC_RECORD"
grep -q 'androidboot.mode=charger' "$KEXEC_RECORD"

printf '%s\n' \
	'console=ttyMSM0,115200n8 androidboot.hardware=qcom androidboot.usbcontroller=a600000.dwc3 service_locator.enable=1 androidboot.mode=normal rdinit=/init panic=10 oops=panic' \
	>"$stage/payload/cmdline"
(cd "$stage/payload" &&
	sha256sum Image board.dtb cmdline initramfs.cpio.gz >SHA256SUMS)
printf '0\n' >"$stage/sys/good/disable"
rm -f "$KEXEC_RECORD"
if PATH=$stage/bin:$PATH PAYLOAD=$stage/payload SYS_DEVICES=$stage/sys \
	"$target" >/dev/null 2>&1; then
	echo 'FAIL normal-mode command line was accepted' >&2
	exit 1
fi
[ ! -e "$KEXEC_RECORD" ]
grep -qx 0 "$stage/sys/good/disable"

printf '%s\n' \
	'console=ttyMSM0,115200n8 androidboot.hardware=qcom androidboot.usbcontroller=a600000.dwc3 service_locator.enable=1 androidboot.mode=charger androidboot.force_normal_boot=0 rdinit=/init panic=10 oops=panic' \
	>"$stage/payload/cmdline"
(cd "$stage/payload" &&
	sha256sum Image board.dtb cmdline initramfs.cpio.gz >SHA256SUMS)
printf 'qcom,wrong-watchdog\000' >"$stage/sys/good/of_node/compatible"
if PATH=$stage/bin:$PATH PAYLOAD=$stage/payload SYS_DEVICES=$stage/sys \
	"$target" >/dev/null 2>&1; then
	echo 'FAIL wrong watchdog identity was accepted' >&2
	exit 1
fi
[ ! -e "$KEXEC_RECORD" ]

echo 'PASS stock charging loader verifies payload, charger mode, watchdog, and load-only execution'
