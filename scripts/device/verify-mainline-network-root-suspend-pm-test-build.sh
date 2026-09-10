#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

output_dir=${1:?usage: verify-mainline-network-root-suspend-pm-test-build.sh BUILD_DIR}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
base_verifier=$repo/scripts/device/verify-mainline-network-root-build.sh
source_verifier=$repo/scripts/host/verify-suspend-pm-test-source-contract.py
accepted_config=$repo/artifacts/network-root-v3/config-7.1.4-network-root
feature_fragment=$repo/configs/kernel/rog5-suspend-pm-test.fragment
config=$output_dir/.config
meta=$output_dir/build-meta.txt
state=$output_dir/.rog5-kbuild-inputs-v1
work=$(mktemp -d)
trap 'rm -rf -- "$work"' 0 HUP INT TERM

for file in "$base_verifier" "$source_verifier" "$accepted_config" \
	"$feature_fragment" "$config" "$meta" "$state"; do
	[ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] ||
		fail "unsafe or missing candidate input: $file"
done
[ -x "$base_verifier" ] && [ -x "$source_verifier" ] ||
	fail 'candidate verifier dependency is not executable'
[ -s "$config" ] && [ -s "$meta" ] && [ -s "$state" ] ||
	fail 'suspend pm_test candidate contains an empty required artifact'

"$base_verifier" "$output_dir"

for symbol in \
	'CONFIG_ARCH_HAS_ZONE_DMA_SET=y' \
	'CONFIG_EXPERT=y' \
	'CONFIG_HAVE_ARCH_KCSAN=y' \
	'CONFIG_PCIE_BUS_DEFAULT=y' \
	'CONFIG_PM_DEBUG=y' \
	'CONFIG_PM_SLEEP_DEBUG=y' \
	'CONFIG_DPM_WATCHDOG=y'; do
	[ "$(grep -Fxc "$symbol" "$config")" -eq 1 ] ||
		fail "required suspend pm_test config changed: $symbol"
done
grep -Fqx '# CONFIG_PM_ADVANCED_DEBUG is not set' "$config" ||
	fail 'PM advanced debug became enabled'
grep -Fqx '# CONFIG_PM_TEST_SUSPEND is not set' "$config" ||
	fail 'boot-time RTC suspend test became enabled'
grep -Fqx '# CONFIG_RESET_SIMPLE is not set' "$config" ||
	fail 'EXPERT activated the unrelated simple reset driver'
[ "$(grep -Fxc 'CONFIG_DPM_WATCHDOG_TIMEOUT=30' "$config")" -eq 1 ] ||
	fail 'DPM watchdog timeout is not 30 seconds'
[ "$(grep -Fxc 'CONFIG_DPM_WATCHDOG_WARNING_TIMEOUT=15' "$config")" -eq 1 ] ||
	fail 'DPM watchdog warning timeout is not 15 seconds'

# EXPERT makes previously hidden disabled prompts visible in the serialized
# config. Compare every effective assignment while allowing only the exact
# requested PM transition, unavoidable arm64 capability/default markers, and
# the now-inexpressible MEDIA_HIDE menu marker. RESET_SIMPLE remains forbidden.
grep '^CONFIG_[A-Za-z0-9_]*=' "$accepted_config" | sort >"$work/accepted.assignments"
grep '^CONFIG_[A-Za-z0-9_]*=' "$config" | sort >"$work/candidate.assignments"
sed \
	-e '/^CONFIG_ARCH_HAS_ZONE_DMA_SET=y$/d' \
	-e '/^CONFIG_DPM_WATCHDOG=y$/d' \
	-e '/^CONFIG_DPM_WATCHDOG_TIMEOUT=30$/d' \
	-e '/^CONFIG_DPM_WATCHDOG_WARNING_TIMEOUT=15$/d' \
	-e '/^CONFIG_EXPERT=y$/d' \
	-e '/^CONFIG_HAVE_ARCH_KCSAN=y$/d' \
	-e '/^CONFIG_PCIE_BUS_DEFAULT=y$/d' \
	-e '/^CONFIG_PM_DEBUG=y$/d' \
	-e '/^CONFIG_PM_SLEEP_DEBUG=y$/d' \
	"$work/candidate.assignments" >"$work/candidate.normalized.assignments"
sed '/^CONFIG_MEDIA_HIDE_ANCILLARY_SUBDRV=y$/d' \
	"$work/accepted.assignments" >"$work/accepted.normalized.assignments"
cmp -s "$work/accepted.normalized.assignments" \
	"$work/candidate.normalized.assignments" ||
	fail 'candidate effective config differs beyond the exact suspend pm_test transition'

feature_sha256=$(sha256sum "$feature_fragment" | cut -d ' ' -f 1)
meta_feature=$(sed -n 's/^feature_fragment_sha256=//p' "$meta")
[ "$(printf '%s\n' "$meta_feature" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] &&
	[ "$meta_feature" = "$feature_sha256" ] ||
	fail 'feature metadata does not identify the repository fragment'
state_feature=$(sed -n 's/^feature_fragment_sha256=//p' "$state")
[ "$(printf '%s\n' "$state_feature" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] &&
	[ "$state_feature" = "$feature_sha256" ] ||
	fail 'build state does not identify the repository fragment'
state_path=$(sed -n 's/^feature_fragment_path=//p' "$state")
[ "$(printf '%s\n' "$state_path" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] ||
	fail 'build state does not identify the repository fragment'
case $state_path in
	*/configs/kernel/rog5-suspend-pm-test.fragment) ;;
	*) fail 'build state does not identify the repository fragment' ;;
esac

source_path=$(sed -n 's/^source_path=//p' "$state")
[ "$(printf '%s\n' "$source_path" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] &&
	[ -d "$source_path" ] && [ ! -L "$source_path" ] ||
	fail 'unsafe or missing retained source path'
"$source_verifier" "$source_path" >/dev/null

printf '%s\n' \
	'status=compile-only-pm-test-candidate' \
	'pm_test_level=devices' \
	'dpm_watchdog_seconds=30' \
	'hardware_acceptance=unproven' \
	'authority=none' \
	'real_suspend=forbidden'
echo 'PASS network-root suspend pm_test kernel changes only the debug/watchdog config contract'
