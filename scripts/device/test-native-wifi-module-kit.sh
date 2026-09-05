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
	'net/qrtr/qrtr.h' QRTR_MHI 'qrtr-mhi' CRYPTO_SHA256 'crypto/sha256.c' 'KBUILD_BUILD_TIMESTAMP' \
	'kernel config and vmlinux unchanged'; do
	grep -Fq "$required" "$builder"
done
grep -Fq 'export KAFLAGS=$KCFLAGS' "$builder"
! grep -Eq 'SKIP_BTF|KBUILD_MODPOST_WARN|fastboot|adb' "$builder"
roots=$repo/configs/kernel/rog5-native-wifi-module-roots
for module in sha256 crypto-aes ctr ccm gcm cmac qrtr-mhi cfg80211 ath11k_pci; do
	grep -Fxq "$module" "$roots"
done
[ "$(grep -nx sha256 "$roots" | cut -d: -f1)" -lt "$(grep -nx cfg80211 "$roots" | cut -d: -f1)" ]
[ "$(grep -nx qrtr-mhi "$roots" | cut -d: -f1)" -lt "$(grep -nx ath11k_pci "$roots" | cut -d: -f1)" ]
awk '/^: >.*load-closure[.]tmp/ { copy=1 } copy { print } /^rm .*load-closure[.]tmp/ { exit }' \
	"$builder" >"$work/closure.sh"
printf 'sha256\nmissing\n' >"$work/roots"
output=$work
module_roots=$work/roots
root=$work/root
release=test
modprobe() {
	for argument do last=$argument; done
	[ "$last" != missing ] || return 1
	printf 'insmod fixture/%s.ko\n' "$last"
}
if (. "$work/closure.sh") >"$work/closure.log" 2>&1; then
	echo 'FAIL dependency lookup failure was hidden by output sorting'; exit 1
fi
[ ! -e "$work/load-closure.txt" ]
echo 'PASS module kit fails before compilation on missing BTF tools and preserves Wi-Fi control dependencies'
