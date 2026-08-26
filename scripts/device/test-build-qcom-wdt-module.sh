#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
builder=$repo/scripts/device/build-qcom-wdt-module.sh

sh -n "$builder"
for contract in \
	'expected_commit=359318de534f196c1281de7195fbf5868c6f7333' \
	'expected_release=7.1.4-g359318de534f' \
	'expected_config=6329b42fac5876d3f42557802bd530ba2c077aa73c4543f0bbc37ea65902eeb4' \
	'expected_symvers=d897132b20f99921f445f637fee62724dfb1a5a20b2f8761dc03ef367e2000d8' \
	'expected_vmlinux=4a539ba93d86153e05118d15899084832ad95d4426ee9608781ebf0dce8dc96d' \
	'expected_builder=bdb4bbda79ab38a55c72d23b269f5c3f5cb14d153e373ce50932c17538e9ccaf' \
	'expected_module=3fcea56eab46bc5ea006461e3c18c21875c046b7b12db3262bf8cd400f0e16c6' \
	'M="$module_output" modules' \
	'watchdog module lacks running-kernel BTF ABI' \
	'watchdog module struct module size differs from the running kernel' \
	'build dirtied source'; do
	grep -Fq "$contract" "$builder" || exit 1
done
! grep -Fq 'M=drivers/watchdog' "$builder"
! grep -Eq 'fastboot|adb|/dev/sd|mkfs|sgdisk' "$builder"

echo 'PASS watchdog module builder is exact-source, external-output, ABI-bound, and phone-free'
