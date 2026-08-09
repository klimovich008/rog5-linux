#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
verifier=$repo/scripts/device/verify-mainline-network-root-suspend-pm-test-build.sh
accepted=$repo/artifacts/network-root-v3/config-7.1.4-network-root
feature=$repo/configs/kernel/rog5-suspend-pm-test.fragment
source_contract=$repo/scripts/host/verify-suspend-pm-test-source-contract.py
source_tree=$repo/build/linux-stable-v7.1.4-source
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

[[ -x $verifier && -x $source_contract && -r $feature ]] ||
	fail 'missing suspend pm_test candidate contract'
[[ -d $source_tree ]] || {
	echo 'SKIP retained accepted Linux source is optional in CI'
	exit 0
}

fixture_repo=$work/repo
fixture_verifier=$fixture_repo/scripts/device/verify-mainline-network-root-suspend-pm-test-build.sh
output=$work/output
fixture_accepted=$fixture_repo/artifacts/network-root-v3/config-7.1.4-network-root
fixture_feature=$fixture_repo/configs/kernel/rog5-suspend-pm-test.fragment
fixture_source_contract=$fixture_repo/scripts/host/verify-suspend-pm-test-source-contract.py
fixture_source=$work/linux
mkdir -p "$fixture_repo/scripts/device" "$fixture_repo/scripts/host" \
	"$fixture_repo/artifacts/network-root-v3" "$fixture_repo/configs/kernel" \
	"$output" "$fixture_source"
cp -- "$verifier" "$fixture_verifier"
cp -- "$source_contract" "$fixture_source_contract"
cp -- "$accepted" "$fixture_accepted"
cp -- "$feature" "$fixture_feature"
for relative in kernel/power/Kconfig kernel/power/main.c kernel/power/suspend.c \
	drivers/base/power/main.c drivers/firmware/psci/psci.c; do
	mkdir -p "$fixture_source/${relative%/*}"
	cp -- "$source_tree/$relative" "$fixture_source/$relative"
done
printf '%s\n' '#!/bin/sh' 'exit 0' \
	>"$fixture_repo/scripts/device/verify-mainline-network-root-build.sh"
chmod 0755 "$fixture_repo/scripts/device/verify-mainline-network-root-build.sh" \
	"$fixture_verifier" "$fixture_source_contract"

sed \
	-e 's/^# CONFIG_EXPERT is not set$/CONFIG_EXPERT=y/' \
	-e 's/^# CONFIG_PM_DEBUG is not set$/CONFIG_PM_DEBUG=y/' \
	-e '/^CONFIG_MEDIA_HIDE_ANCILLARY_SUBDRV=y$/d' \
	-e '/^CONFIG_PM_DEBUG=y$/a # CONFIG_PM_ADVANCED_DEBUG is not set\n# CONFIG_PM_TEST_SUSPEND is not set\nCONFIG_PM_SLEEP_DEBUG=y\nCONFIG_DPM_WATCHDOG=y\nCONFIG_DPM_WATCHDOG_TIMEOUT=30\nCONFIG_DPM_WATCHDOG_WARNING_TIMEOUT=15\n# CONFIG_RESET_SIMPLE is not set\nCONFIG_ARCH_HAS_ZONE_DMA_SET=y\nCONFIG_HAVE_ARCH_KCSAN=y\nCONFIG_PCIE_BUS_DEFAULT=y' \
	"$fixture_accepted" >"$output/.config"
feature_sha=$(sha256sum "$fixture_feature" | cut -d' ' -f1)
printf 'feature_fragment_sha256=%s\n' "$feature_sha" >"$output/build-meta.txt"
printf '%s\n' \
	'format=rog5-kbuild-inputs-v1' \
	"source_path=$fixture_source" \
	'feature_fragment_path=/workspace/repo/configs/kernel/rog5-suspend-pm-test.fragment' \
	"feature_fragment_sha256=$feature_sha" \
	>"$output/.rog5-kbuild-inputs-v1"
chmod 0600 "$output/.rog5-kbuild-inputs-v1"

expect_failure() {
	expected=$1
	shift
	if "$@" >"$work/failure.out" 2>"$work/failure.err"; then
		fail "unexpected success: $*"
	fi
	grep -Fq "$expected" "$work/failure.err" || {
		cat "$work/failure.err" >&2
		fail "wrong refusal; expected: $expected"
	}
}

"$fixture_verifier" "$output" >"$work/pass.out"
grep -Fxq 'status=compile-only-pm-test-candidate' "$work/pass.out"
grep -Fxq 'real_suspend=forbidden' "$work/pass.out"

cp -- "$output/.config" "$work/config.good"
sed -i 's/^CONFIG_EXPERT=y$/# CONFIG_EXPERT is not set/' "$output/.config"
expect_failure 'required suspend pm_test config changed: CONFIG_EXPERT=y' \
	"$fixture_verifier" "$output"
cp -- "$work/config.good" "$output/.config"

printf '%s\n' 'CONFIG_HOSTILE_EXTRA=y' >>"$output/.config"
expect_failure 'candidate effective config differs beyond the exact suspend pm_test transition' \
	"$fixture_verifier" "$output"
cp -- "$work/config.good" "$output/.config"

sed -i 's/^# CONFIG_RESET_SIMPLE is not set$/CONFIG_RESET_SIMPLE=y/' "$output/.config"
expect_failure 'EXPERT activated the unrelated simple reset driver' \
	"$fixture_verifier" "$output"
cp -- "$work/config.good" "$output/.config"

sed -i 's/^CONFIG_DPM_WATCHDOG_TIMEOUT=30$/CONFIG_DPM_WATCHDOG_TIMEOUT=120/' \
	"$output/.config"
expect_failure 'DPM watchdog timeout is not 30 seconds' \
	"$fixture_verifier" "$output"
cp -- "$work/config.good" "$output/.config"

sed -i 's/^# CONFIG_PM_TEST_SUSPEND is not set$/CONFIG_PM_TEST_SUSPEND=y/' \
	"$output/.config"
expect_failure 'boot-time RTC suspend test became enabled' \
	"$fixture_verifier" "$output"
cp -- "$work/config.good" "$output/.config"

cp -- "$output/build-meta.txt" "$work/meta.good"
printf '%s\n' 'feature_fragment_sha256=hostile' >"$output/build-meta.txt"
expect_failure 'feature metadata does not identify the repository fragment' \
	"$fixture_verifier" "$output"
cp -- "$work/meta.good" "$output/build-meta.txt"

sed -i 's#^source_path=.*#source_path=/nonexistent/hostile#' \
	"$output/.rog5-kbuild-inputs-v1"
expect_failure 'unsafe or missing retained source path' \
	"$fixture_verifier" "$output"

echo 'PASS suspend pm_test build contract permits only the debug/watchdog delta and rejects hostile candidates'
