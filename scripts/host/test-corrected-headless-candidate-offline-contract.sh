#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/build-corrected-headless-candidate-offline.sh
initramfs_test=$repo/scripts/host/test-stable-recovery-initramfs.sh
wrapper_test=$repo/scripts/host/test-stable-recovery-wrapper-offline.sh

for path in "$builder" "$initramfs_test" "$wrapper_test"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable corrected-candidate input: ${path#"$repo"/}"
	bash -n "$path"
done

for token in \
	headless-network-root-v1 \
	86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46 \
	RECOVERY_TEST_PUBLIC_KEY \
	test-stable-recovery-initramfs.sh \
	test-stable-recovery-wrapper-offline.sh \
	prepare-recovery-candidate.py \
	rog5-bundle-verify-host-test \
	'openssl genpkey -algorithm ED25519' \
	'trap cleanup EXIT HUP INT TERM' \
	'authority=none'; do
	grep -Fq "$token" "$builder" ||
		fail "corrected-candidate builder omits contract token: $token"
done

grep -Fq 'RECOVERY_TEST_PUBLIC_KEY' "$initramfs_test" ||
	fail 'stable-recovery integration cannot consume the candidate trust root'
grep -Fq 'trust_root=%s' "$initramfs_test" ||
	fail 'stable-recovery integration does not report trust-root provenance'
grep -Fq 'components/rog5-recovery-control' "$initramfs_test" ||
	fail 'stable-recovery integration does not retain its verified components'
grep -Fq \
	'c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec' \
	"$wrapper_test" ||
	fail 'wrapper test does not pin the accepted snapshot builder'

if grep -Eq \
	'\b(fastboot|adb|ssh|scp|systemctl|pkexec|sudo)\b|/dev/(sd|nvme|ufs)' \
	"$builder"; then
	fail 'offline corrected-candidate builder contains phone, privilege, or storage transport'
fi
if grep -Eq \
	'ALLOW_(TEMPORARY_BOOT|HEADLESS_LIVE_GATE)|/var/lib/rog5-recovery-bundles' \
	"$builder"; then
	fail 'offline corrected-candidate builder contains a live-promotion surface'
fi

echo 'PASS corrected headless candidate is twin-built with one disposable offline trust root and no live transport'
