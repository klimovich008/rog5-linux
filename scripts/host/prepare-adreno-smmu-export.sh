#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
base_root=${1:-/var/lib/rog5-network-root-v1}
export_root=${2:-/var/lib/rog5-network-root-adreno-smmu-v21}
kernel_release=7.1.4-g7a5cef0db479
boot_hash=37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf
module_hash=9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a

[[ $EUID == 0 ]] || fail 'run through PolicyKit; do not share a sudo password'
for command in chmod chown cp cut find install mv realpath rm sha256sum stat \
	touch wc; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ $base_root == /var/lib/rog5-network-root-v1 ]] ||
	fail 'base export path is not exact'
[[ $export_root == /var/lib/rog5-network-root-adreno-smmu-v21 ]] ||
	fail 'candidate export path is not exact'
[[ -d $base_root && ! -L $base_root ]] || fail 'accepted base export is absent'
[[ ! -e $export_root ]] || fail 'candidate export already exists'

"$repo/scripts/host/verify-network-root-export.sh" "$base_root" >/dev/null

stage=$export_root.partial.$$
[[ ! -e $stage ]] || fail 'candidate partial path already exists'
succeeded=0
report_retained_stage() {
	if [[ $succeeded != 1 && -e $stage ]]; then
		echo "INFO retained failed candidate export for inspection: $stage" >&2
	fi
}
trap report_retained_stage EXIT

install -d -m 0755 "$stage"
cp -a --reflink=always "$base_root/." "$stage/"

firmware_paths=(
	usr/lib/firmware/qcom/a660_sqe.fw
	usr/lib/firmware/qcom/a660_gmu.bin
	usr/lib/firmware/qcom/sm8350/a660_zap.mbn
)
firmware_hashes=(
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d
)
for index in "${!firmware_paths[@]}"; do
	relative=${firmware_paths[$index]}
	file=$stage/$relative
	[[ -f $file && ! -L $file ]] ||
		fail "candidate firmware input is not exact: $relative"
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == \
		"${firmware_hashes[$index]}" ]] ||
		fail "candidate firmware input hash mismatch: $relative"
	rm -f -- "$file"
done
touch -r "$base_root/usr/lib/firmware/qcom" \
	"$stage/usr/lib/firmware/qcom"
touch -r "$base_root/usr/lib/firmware/qcom/sm8350" \
	"$stage/usr/lib/firmware/qcom/sm8350"

baseline=$repo/scripts/device/check-network-root-adreno-smmu-baseline.sh
disarm=$repo/scripts/device/disarm-network-root-watchdog.sh
probe=$repo/scripts/device/probe-network-root-adreno-smmu.sh
gate=$repo/scripts/device/run-network-root-adreno-smmu-gate.sh
driver_override_check=$repo/scripts/device/check-adreno-smmu-driver-override-state.sh
reprobe_verifier=$repo/scripts/device/verify-adreno-smmu-platform-reprobe-contract.sh
reprobe_test=$repo/scripts/device/test-adreno-smmu-platform-reprobe-contract.sh
for helper in "$baseline" "$disarm" "$probe" "$gate" \
	"$driver_override_check" "$reprobe_verifier" "$reprobe_test"; do
	[[ -f $helper && ! -L $helper && -x $helper ]] ||
		fail "missing exact live helper: $helper"
done

module_root=$stage/usr/lib/modules/$kernel_release
[[ -d $module_root && ! -L $module_root ]] ||
	fail 'candidate module tree is absent'
module_files=$(find "$module_root" -type f | wc -l)
((module_files > 100)) || fail 'candidate module tree is incomplete'

seal=$stage/etc/rog5/adreno-smmu-v21-export
{
	printf 'diagnostic_generation=v21\n'
	printf 'base_export=rog5-network-root-v1\n'
	printf 'kernel_release=%s\n' "$kernel_release"
	printf 'source_commit=d9ac316489f4258d389d6298659d5e9c22183400\n'
	printf 'source_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92\n'
	printf 'kernel_config_sha256=68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f\n'
	printf 'platform_source_sha256=c1967f53f66da20c515d32ca3242bd6f365b31f2678f7125bf71cc16ed56a258\n'
	printf 'device_header_sha256=68ad17f3670b7fcedbfa70e8cab1b2044dff1e7525697efc953527fec2825fbe\n'
	printf 'vsprintf_source_sha256=314241c733f99bf8b45e64c173d78b1449b4da3fdad90a63500166376d2774eb\n'
	printf 'of_platform_source_sha256=821937acef295d986caa4470166571b0d18cef2a2f9d1a730e1d0cb4cec70131\n'
	printf 'module_files=%s\n' "$module_files"
	printf 'boot_avb_sha256=%s\n' "$boot_hash"
	printf 'gpucc_module_sha256=%s\n' "$module_hash"
	printf 'baseline_sha256=%s\n' \
		"$(sha256sum "$baseline" | cut -d ' ' -f 1)"
	printf 'disarm_sha256=%s\n' \
		"$(sha256sum "$disarm" | cut -d ' ' -f 1)"
	printf 'probe_sha256=%s\n' \
		"$(sha256sum "$probe" | cut -d ' ' -f 1)"
	printf 'gate_sha256=%s\n' \
		"$(sha256sum "$gate" | cut -d ' ' -f 1)"
	printf 'driver_override_checker_sha256=%s\n' \
		"$(sha256sum "$driver_override_check" | cut -d ' ' -f 1)"
	printf 'reprobe_verifier_sha256=%s\n' \
		"$(sha256sum "$reprobe_verifier" | cut -d ' ' -f 1)"
	printf 'reprobe_test_sha256=%s\n' \
		"$(sha256sum "$reprobe_test" | cut -d ' ' -f 1)"
	printf 'probe_timeout_seconds=90\n'
	printf 'transition_timeout_seconds=150\n'
	printf 'firmware_state=ABSENT\n'
	printf 'driver_override_state=UNSET_NULL_REPRESENTATION\n'
	printf 'driver_override_write=FORBIDDEN\n'
	printf 'smmu_reprobe=EXACT_PLATFORM_DEVICE_ONCE\n'
	printf 'smmu_acceptance=NOT_ACCEPTED\n'
} >"$seal"
chown root:root "$seal"
chmod 0444 "$seal"
touch -r "$base_root/etc/rog5" "$stage/etc/rog5"

"$repo/scripts/host/verify-adreno-smmu-export.sh" \
	"$stage" "$base_root"
mv "$stage" "$export_root"
succeeded=1
echo "PASS prepared isolated v21 Adreno-SMMU export at $export_root"
