#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/rebuild-headless-network-root-initramfs.sh
cpio_path=$repo/scripts/host/qualified-cpio-path/cpio

for script in "$builder" "$cpio_path"; do
	[[ -f $script && ! -L $script && -x $script ]] ||
		fail "missing executable headless-initramfs contract input: ${script#"$repo"/}"
	bash -n "$script"
done

for token in \
	4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac \
	bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58 \
	819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5 \
	18fc6f392d4a84cf15eab867de89b7a8760c54568793d5fe07f5a50725402278 \
	a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e \
	'verify-steam-deck-recovery-builders.sh' \
	'run-private-arm64-binfmt.sh' \
	'--pull=never' \
	'--network=none' \
	'--platform linux/arm64' \
	'--env CC=gcc' \
	'qualified-cpio-path' \
	'NETWORK_ROOT_VERIFIER="$verifier"' \
	'two qualified persistent-root verifier builds differ' \
	'two qualified headless initramfs builds differ' \
	'state=exact-historical-bytes-reproduced' \
	'boot_authority=none' \
	'mv -T -- "$publish" "$output_root"'; do
	grep -Fq -- "$token" "$builder" ||
		fail "headless-initramfs builder omits contract token: $token"
done
grep -Fq '../qualified-tool-shims/cpio' "$cpio_path" ||
	fail 'isolated cpio command does not delegate to the qualified shim'

if grep -Eq \
	'\b(fastboot|adb|sudo|pkexec)\b|(^|[;&|[:space:]])(ssh|scp)([[:space:]]|$)|/dev/(sd|nvme|ufs)' \
	"$builder" "$cpio_path"; then
	fail 'headless-initramfs rebuild contains live, privilege, or storage transport'
fi

echo 'PASS headless initramfs rebuild is twin-built, exact-identity, rootless, and host-isolated'
