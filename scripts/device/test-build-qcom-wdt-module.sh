#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
builder=$repo/scripts/device/build-qcom-wdt-module.sh

sh -n "$builder"
for contract in \
	'expected_commit=359318de534f196c1281de7195fbf5868c6f7333' \
	'expected_release=7.1.4-g359318de534f' \
	'expected_symvers=d897132b20f99921f445f637fee62724dfb1a5a20b2f8761dc03ef367e2000d8' \
	'expected_module=0b83b3b5aecc77390f82f2aabc1e24f3ef590e331986a7772a480f214a7b42c2' \
	'M="$module_output" modules' \
	'watchdog module unexpectedly carries build-specific BTF' \
	'build dirtied source'; do
	grep -Fq "$contract" "$builder" || exit 1
done
! grep -Fq 'M=drivers/watchdog' "$builder"
! grep -Eq 'fastboot|adb|/dev/sd|mkfs|sgdisk' "$builder"

echo 'PASS watchdog module builder is exact-source, external-output, ABI-bound, and phone-free'
