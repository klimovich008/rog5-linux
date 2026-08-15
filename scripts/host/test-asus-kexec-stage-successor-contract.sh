#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
historical=$repo/scripts/device/build-asus-kexec-stage.sh
successor=$repo/scripts/device/build-asus-kexec-stage-successor.sh
expected_historical=aaaa423aefc9b90dd30738bf42a0209574437599da2062b9dd8cc685d6e15b94

for script in "$historical" "$successor"; do
	[[ -f $script && ! -L $script && -x $script ]] ||
		fail "missing executable ASUS wrapper builder: ${script#"$repo"/}"
	sh -n "$script"
done
[[ $(sha256sum "$historical" | cut -d ' ' -f 1) == \
	"$expected_historical" ]] ||
	fail 'frozen historical ASUS wrapper builder changed'

for token in \
	accepted-wrapper-v18-v1 \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f \
	'FAIL unsupported ASUS reference-config profile' \
	'--enable KEXEC' \
	'--disable KEXEC_FILE' \
	'--disable UAPI_HEADER_TEST' \
	'--disable LOCALVERSION_AUTO' \
	'--set-str INITRAMFS_SOURCE' \
	'--set-str LOCALVERSION' \
	'CONFIG_KEXEC=y' \
	'reference_config_profile=%s' \
	'debug_prefix_map=-fdebug-prefix-map=$output_dir=/rog5-build' \
	'export KCFLAGS="-Wno-error=strict-prototypes $debug_prefix_map"' \
	'export KAFLAGS=$debug_prefix_map' \
	'config_sha256=%s' \
	'image_sha256=%s' \
	'Wed Apr 19 00:00:00 UTC 2023'; do
	grep -Fq -- "$token" "$successor" ||
		fail "ASUS wrapper successor omits contract token: $token"
done

if grep -Eq \
	'\b(fastboot|adb|sudo|pkexec|ssh|scp|curl|wget)\b|/dev/(sd|nvme|ufs)' \
	"$successor"; then
	fail 'ASUS wrapper successor contains phone, privilege, network, or storage transport'
fi

echo 'PASS ASUS wrapper successor uses the exact accepted config seed without changing the frozen historical builder'
