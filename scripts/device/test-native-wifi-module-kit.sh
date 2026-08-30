#!/bin/sh
set -eu
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-native-wifi-modules.sh
sh -n "$builder"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
mkdir "$work/source" "$work/kit"
: >"$work/kit/build-meta.txt"
if "$builder" "$work/source" "$work/kit" "$work/output" >"$work/log" 2>&1; then
	echo 'FAIL missing BTF finalizer was accepted'; exit 1
fi
grep -Fq 'lacks resolve_btfids; refusing compilation' "$work/log"
[ ! -e "$work/output" ]
if JOBS=999 "$builder" "$work/source" "$work/kit" "$work/output" >"$work/log" 2>&1; then
	echo 'FAIL unsafe parallelism was accepted'; exit 1
fi
grep -Fq 'unsafe JOBS' "$work/log"
for required in 'drivers/bus/mhi/common.h' 'drivers/net/wireless/ath/*.[ch]' \
	'net/qrtr/qrtr.h' QRTR_MHI 'qrtr-mhi' 'KBUILD_BUILD_TIMESTAMP' \
	'kernel config and vmlinux unchanged'; do
	grep -Fq "$required" "$builder"
done
! grep -Eq 'SKIP_BTF|KBUILD_MODPOST_WARN|fastboot|adb' "$builder"
echo 'PASS module kit fails before compilation on missing BTF tools and preserves Wi-Fi control dependencies'
