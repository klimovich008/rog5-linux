#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
base_root=${1:-/var/lib/rog5-network-root-v1}
export_root=${2:-/var/lib/rog5-network-root-adreno-smmu-v19}
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
[[ $export_root == /var/lib/rog5-network-root-adreno-smmu-v19 ]] ||
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
for helper in "$baseline" "$disarm" "$probe"; do
	[[ -f $helper && ! -L $helper && -x $helper ]] ||
		fail "missing exact live helper: $helper"
done

module_root=$stage/usr/lib/modules/$kernel_release
[[ -d $module_root && ! -L $module_root ]] ||
	fail 'candidate module tree is absent'
module_files=$(find "$module_root" -type f | wc -l)
((module_files > 100)) || fail 'candidate module tree is incomplete'

seal=$stage/etc/rog5/adreno-smmu-v19-export
{
	printf 'base_export=rog5-network-root-v1\n'
	printf 'kernel_release=%s\n' "$kernel_release"
	printf 'module_files=%s\n' "$module_files"
	printf 'boot_avb_sha256=%s\n' "$boot_hash"
	printf 'gpucc_module_sha256=%s\n' "$module_hash"
	printf 'baseline_sha256=%s\n' \
		"$(sha256sum "$baseline" | cut -d ' ' -f 1)"
	printf 'disarm_sha256=%s\n' \
		"$(sha256sum "$disarm" | cut -d ' ' -f 1)"
	printf 'probe_sha256=%s\n' \
		"$(sha256sum "$probe" | cut -d ' ' -f 1)"
	printf 'firmware_state=ABSENT\n'
	printf 'smmu_acceptance=NOT_ACCEPTED\n'
} >"$seal"
chown root:root "$seal"
chmod 0444 "$seal"
touch -r "$base_root/etc/rog5" "$stage/etc/rog5"

"$repo/scripts/host/verify-adreno-smmu-export.sh" \
	"$stage" "$base_root"
mv "$stage" "$export_root"
succeeded=1
echo "PASS prepared isolated v19 Adreno-SMMU export at $export_root"
