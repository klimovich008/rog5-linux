#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-adreno-smmu-export.sh ROOT BASE_ROOT}
base_root=${2:-/var/lib/rog5-network-root-v1}
kernel_release=7.1.4-g7a5cef0db479
boot_hash=37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf
module_hash=9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a

for command in cmp cut find grep mktemp readlink realpath rm sha256sum sort \
	stat wc xargs; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ -d $root && ! -L $root ]] || fail 'candidate export is not a directory'
[[ -d $base_root && ! -L $base_root ]] || fail 'base export is not a directory'
root=$(realpath -e "$root")
base_root=$(realpath -e "$base_root")
[[ $base_root == /var/lib/rog5-network-root-v1 ]] ||
	fail 'base export path is not exact'
[[ $root != / && $root != "$base_root" ]] ||
	fail 'unsafe or aliased export roots'
[[ $root == /var/lib/rog5-network-root-adreno-smmu-v21 ||
	$root =~ ^/var/lib/rog5-network-root-adreno-smmu-v21[.]partial[.][0-9]+$ ]] ||
	fail 'candidate export path is not exact'

"$repo/scripts/host/verify-network-root-export.sh" "$base_root" >/dev/null

seal=$root/etc/rog5/adreno-smmu-v21-export
[[ -f $seal && ! -L $seal ]]
[[ $(stat -c '%u:%g:%a' "$seal") == 0:0:444 ]]
grep -qx 'diagnostic_generation=v21' "$seal"
grep -qx 'base_export=rog5-network-root-v1' "$seal"
grep -qx "kernel_release=$kernel_release" "$seal"
grep -qx 'source_commit=d9ac316489f4258d389d6298659d5e9c22183400' \
	"$seal"
grep -qx 'source_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	"$seal"
grep -qx 'kernel_config_sha256=68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f' \
	"$seal"
grep -qx 'platform_source_sha256=c1967f53f66da20c515d32ca3242bd6f365b31f2678f7125bf71cc16ed56a258' \
	"$seal"
grep -qx 'device_header_sha256=68ad17f3670b7fcedbfa70e8cab1b2044dff1e7525697efc953527fec2825fbe' \
	"$seal"
grep -qx 'vsprintf_source_sha256=314241c733f99bf8b45e64c173d78b1449b4da3fdad90a63500166376d2774eb' \
	"$seal"
grep -qx 'of_platform_source_sha256=821937acef295d986caa4470166571b0d18cef2a2f9d1a730e1d0cb4cec70131' \
	"$seal"
grep -qx "boot_avb_sha256=$boot_hash" "$seal"
grep -qx "gpucc_module_sha256=$module_hash" "$seal"
grep -qx 'probe_timeout_seconds=90' "$seal"
grep -qx 'transition_timeout_seconds=150' "$seal"
grep -qx 'firmware_state=ABSENT' "$seal"
grep -qx 'driver_override_state=UNSET_NULL_REPRESENTATION' "$seal"
grep -qx 'driver_override_write=FORBIDDEN' "$seal"
grep -qx 'smmu_reprobe=EXACT_PLATFORM_DEVICE_ONCE' "$seal"
grep -qx 'smmu_acceptance=NOT_ACCEPTED' "$seal"

baseline=$repo/scripts/device/check-network-root-adreno-smmu-baseline.sh
disarm=$repo/scripts/device/disarm-network-root-watchdog.sh
probe=$repo/scripts/device/probe-network-root-adreno-smmu.sh
gate=$repo/scripts/device/run-network-root-adreno-smmu-gate.sh
driver_override_check=$repo/scripts/device/check-adreno-smmu-driver-override-state.sh
reprobe_verifier=$repo/scripts/device/verify-adreno-smmu-platform-reprobe-contract.sh
reprobe_test=$repo/scripts/device/test-adreno-smmu-platform-reprobe-contract.sh
grep -qx "baseline_sha256=$(sha256sum "$baseline" | cut -d ' ' -f 1)" \
	"$seal"
grep -qx "disarm_sha256=$(sha256sum "$disarm" | cut -d ' ' -f 1)" \
	"$seal"
grep -qx "probe_sha256=$(sha256sum "$probe" | cut -d ' ' -f 1)" \
	"$seal"
grep -qx "gate_sha256=$(sha256sum "$gate" | cut -d ' ' -f 1)" \
	"$seal"
grep -qx \
	"driver_override_checker_sha256=$(sha256sum "$driver_override_check" | cut -d ' ' -f 1)" \
	"$seal"
grep -qx \
	"reprobe_verifier_sha256=$(sha256sum "$reprobe_verifier" | cut -d ' ' -f 1)" \
	"$seal"
grep -qx \
	"reprobe_test_sha256=$(sha256sum "$reprobe_test" | cut -d ' ' -f 1)" \
	"$seal"

module_root=$root/usr/lib/modules/$kernel_release
base_module_root=$base_root/usr/lib/modules/$kernel_release
[[ -d $module_root && ! -L $module_root ]]
[[ -d $base_module_root && ! -L $base_module_root ]]
module_files=$(find "$module_root" -type f | wc -l)
base_module_files=$(find "$base_module_root" -type f | wc -l)
((module_files > 100))
[[ $module_files == "$base_module_files" ]]
grep -qx "module_files=$module_files" "$seal"

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
	base_file=$base_root/$relative
	[[ -f $base_file && ! -L $base_file ]]
	[[ $(sha256sum "$base_file" | cut -d ' ' -f 1) == \
		"${firmware_hashes[$index]}" ]]
	[[ ! -e $root/$relative ]]
done
firmware_files=$(find "$root/usr/lib/firmware" -type f \
	\( -name a660_sqe.fw -o -name a660_gmu.bin -o -name a660_zap.mbn \) \
	-print)
[[ -z $firmware_files ]] || fail 'A660 firmware remains in candidate export'

for relative in \
	etc/rog5 \
	usr/lib/firmware/qcom \
	usr/lib/firmware/qcom/sm8350
do
	[[ $(stat -c '%u:%g:%a' "$root/$relative") == \
		"$(stat -c '%u:%g:%a' "$base_root/$relative")" ]]
done

for relative in \
	root/.ssh/authorized_keys \
	home/rog5/.ssh/authorized_keys \
	etc/ssh/ssh_host_ed25519_key \
	etc/ssh/ssh_host_ed25519_key.pub
do
	cmp "$root/$relative" "$base_root/$relative"
	[[ $(stat -c '%u:%g:%a' "$root/$relative") == \
		"$(stat -c '%u:%g:%a' "$base_root/$relative")" ]]
done

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
unchanged_metadata() {
	tree=$1
	(
		cd "$tree"
		find . -xdev \
			! -path './usr/lib/firmware/qcom' \
			! -path './usr/lib/firmware/qcom/sm8350' \
			! -path './usr/lib/firmware/qcom/a660_sqe.fw' \
			! -path './usr/lib/firmware/qcom/a660_gmu.bin' \
			! -path './usr/lib/firmware/qcom/sm8350/a660_zap.mbn' \
			! -path './etc/rog5' \
			! -path './etc/rog5/adreno-smmu-v21-export' \
			-printf '%P|%y|%m|%U|%G|%s|%T@|%l\n' |
			LC_ALL=C sort
	)
}
unchanged_metadata "$base_root" >"$work/base.metadata"
unchanged_metadata "$root" >"$work/candidate.metadata"
cmp "$work/base.metadata" "$work/candidate.metadata"

unchanged_hashes() {
	tree=$1
	(
		cd "$tree"
		find . -xdev -type f \
			! -path './usr/lib/firmware/qcom/a660_sqe.fw' \
			! -path './usr/lib/firmware/qcom/a660_gmu.bin' \
			! -path './usr/lib/firmware/qcom/sm8350/a660_zap.mbn' \
			! -path './etc/rog5/adreno-smmu-v21-export' \
			-print0 | LC_ALL=C sort -z | xargs -0 sha256sum
	)
}
unchanged_hashes "$base_root" >"$work/base.sha256"
unchanged_hashes "$root" >"$work/candidate.sha256"
cmp "$work/base.sha256" "$work/candidate.sha256"

echo "PASS isolated v21 export module_files=$module_files firmware=0 credentials=preserved base=unchanged reprobe=exact-once driver_override=unset-null-representation"
