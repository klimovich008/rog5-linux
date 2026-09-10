#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-asus-kexec-stage-slim.sh
profile=$repo/configs/kernel/rog5-stable-wrapper-slim-v1.json
fragment=$repo/configs/kernel/rog5-stable-wrapper-slim-v1.fragment
auditor=$repo/scripts/host/verify-stable-wrapper-slim-config.py

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for path in "$builder" "$auditor"; do
	[ -f "$path" ] && [ ! -L "$path" ] && [ -x "$path" ] ||
		fail "missing executable slim-wrapper input: $path"
done
for path in "$profile" "$fragment"; do
	[ -f "$path" ] && [ ! -L "$path" ] ||
		fail "missing slim-wrapper policy input: $path"
done
sh -n "$builder"
python3 -m py_compile "$auditor"

for token in \
	bee39a247b4eef5f5282bad7e09b75853b851ed8b9161981803a08d53b4ac8fb \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f \
	3fb9eaf91f32cf01c09cc8653feb4a52c421f4a95bdd8e022576211ad7cff9f0 \
	6d988b18c3ae70f5bd91be8e6051119911886be0b4eaeb3759eddf3f5a8ac744 \
	b5ed3261a858680b05a3a7247e2d7948e722f71be812fcdc66972594d22c097a \
	592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a \
	'kernel-source-seal.py' \
	'tree_format=rog5-kernel-source-tree-v1' \
	'staged_initramfs_sha256' \
	'CONFIG_USB_DWC3_GADGET=y' \
	'# CONFIG_MODULES is not set' \
	'status=experiment' \
	'authority=none' \
	'compile-only and not boot-authorized'; do
	grep -Fq "$token" "$builder" ||
		fail "slim-wrapper builder omits contract: $token"
done
for token in \
	'KBUILD_BUILD_USER=rog5-linux' \
	'KBUILD_BUILD_HOST=rog5-builder' \
	"KBUILD_BUILD_TIMESTAMP='Wed Apr 19 00:00:00 UTC 2023'" \
	'KCFLAGS=-Wno-error=strict-prototypes' \
	'grep -Fq "Linux version 5.4.210$localversion ("' \
	'make -C "$source_dir" O="$output_dir" olddefconfig' \
	'make -C "$source_dir" O="$output_dir" -j "$jobs" Image'; do
	grep -Fq "$token" "$builder" ||
		fail "slim-wrapper builder omits reproducibility input: $token"
done
if grep -Eq \
	'\b(fastboot|adb|ssh|scp|sudo|pkexec|systemctl)\b|/dev/(sd|nvme|ufs)' \
	"$builder"; then
	fail 'slim-wrapper builder contains phone, privilege, or storage transport'
fi

echo 'PASS slim-wrapper builder is config-pinned, reproducible, compile-only, and non-authoritative'
