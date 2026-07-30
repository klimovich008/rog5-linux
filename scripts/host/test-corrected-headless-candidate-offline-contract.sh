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
cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
cpio_path=$repo/scripts/host/qualified-cpio-path/cpio

for path in "$builder" "$initramfs_test" "$wrapper_test" "$cpio_shim" \
	"$cpio_path"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable corrected-candidate input: ${path#"$repo"/}"
	bash -n "$path"
done

for token in \
	headless-network-root-v1 \
	86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46 \
	RECOVERY_TEST_PUBLIC_KEY \
	'ROG5_RECOVERY_BASE_PROFILE=reconstructed-v18r-v1' \
	test-stable-recovery-initramfs.sh \
	test-stable-recovery-wrapper-offline.sh \
	prepare-recovery-candidate.py \
	rog5-bundle-verify-host-test \
	verify-steam-deck-builder.sh \
	qualified-tool-shims \
	qualified-cpio-path \
	'PATH="$qualified_cpio_path:/usr/bin:/bin:/usr/sbin:/sbin"' \
	run-private-arm64-binfmt.sh \
	'"$arm64_runner" env' \
	'ROG5_WRAPPER_BUILDER_PROFILE=steam-deck-asus-5.4-v1' \
	'ROG5_OFFLINE_WRAPPER_JOBS:-8' \
	'JOBS=$wrapper_jobs' \
	'podman run --rm --network=none' \
	'PASS qualified Steam Deck ASUS 5.4 kernel builder' \
	'openssl genpkey -algorithm ED25519' \
	'trap cleanup EXIT HUP INT TERM' \
	'authority=none'; do
	grep -Fq "$token" "$builder" ||
		fail "corrected-candidate builder omits contract token: $token"
done
grep -Fq '../qualified-tool-shims/cpio' "$cpio_path" ||
	fail 'isolated qualified cpio command does not delegate to the pinned shim'
for token in \
	'verify-steam-deck-builder.sh' \
	'--network=none' \
	'--security-opt label=disable' \
	'--workdir "$workdir"' \
	'"$image" cpio "$@"'; do
	grep -Fq -- "$token" "$cpio_shim" ||
		fail "qualified cpio shim omits contract token: $token"
done
if grep -Eq '\b(sudo|pkexec|ssh|fastboot|adb)\b|/dev/(sd|nvme|ufs)' \
	"$cpio_shim"; then
	fail 'qualified cpio shim contains privilege, phone, or storage transport'
fi

grep -Fq 'RECOVERY_TEST_PUBLIC_KEY' "$initramfs_test" ||
	fail 'stable-recovery integration cannot consume the candidate trust root'
grep -Fq 'trust_root=%s' "$initramfs_test" ||
	fail 'stable-recovery integration does not report trust-root provenance'
grep -Fq 'components/rog5-recovery-control' "$initramfs_test" ||
	fail 'stable-recovery integration does not retain its verified components'
for token in \
	'historical-2026-07-29' \
	'steam-deck-asus-5.4-v1' \
	'build-asus-kexec-stage-successor.sh' \
	'accepted-wrapper-v18-v1' \
	'95be17d48ec61d00a4e8c92be754c8a8345f93685ce05d412a6d3a6aceba6e02' \
	'verify-steam-deck-builder.sh' \
	'cache_publication=disabled-for-qualified-steam-deck-twin-build' \
	'wrapper output config identity changed' \
	'wrapper build metadata changed'; do
	grep -Fq "$token" "$wrapper_test" ||
		fail "wrapper test omits builder-boundary contract: $token"
done
grep -Fq \
	'c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec' \
	"$wrapper_test" ||
	fail 'wrapper test does not preserve the frozen historical builder profile'
if grep -Fq \
	'c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec' \
	"$builder"; then
	fail 'corrected candidate still pins a diagnostic historical OCI ID'
fi

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
