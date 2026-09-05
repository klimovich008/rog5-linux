#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
builder=$repo/scripts/device/build-softdog-module.sh

sh -n "$builder"
for contract in \
	'expected_commit=359318de534f196c1281de7195fbf5868c6f7333' \
	'expected_release=7.1.4-g359318de534f' \
	'expected_source=e4605a97b2734bb278fc76a4ef8863818cfde242f567f2da517b938537ad3dfc' \
	'expected_module=ab0175a40b7dd6186d07b4166d5c2ea3ef3f94f9f0ddf9e08d19e431be294dc4' \
	'M="$module_output" modules' \
	'softdog lacks running BTF ABI' \
	'softdog struct module size changed' \
	'build dirtied source'; do
	grep -Fq "$contract" "$builder" || exit 1
done
! grep -Eq 'fastboot|adb|/dev/sd|mkfs|sgdisk' "$builder"

echo 'PASS softdog module builder is exact-source, external-output, ABI-bound, and phone-free'
