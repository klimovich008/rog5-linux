#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
archive=${1:-$repo/artifacts/a660-registration-build-a/modules.tar.gz}
base_root=${2:-/var/lib/rog5-network-root-v1}
export_root=${3:-/var/lib/rog5-network-root-a660-registration-v3}
release=7.1.4-rog5-a660reg1
archive_hash=e3cb1ef31b6c1c803bee98748660f92b3b192d460cb41d5d4691f9953a91a42b
acceptance=$repo/manifests/acceptance/adreno-smmu-v21-live.accepted
acceptance_sha=c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875
acceptance_report_sha=0c7bb22301b8203531a7e8f098e8a719fd7f29d7de2cdf3c63730ecb792e9bbc

[[ $EUID == 0 ]] || fail 'run through PolicyKit; do not share a sudo password'
for command in chmod chown cmp cp cut find install mktemp modinfo mv \
	readlink realpath rm sha256sum stat tar; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ $base_root == /var/lib/rog5-network-root-v1 ]] ||
	fail 'base export path is not exact'
[[ $export_root == /var/lib/rog5-network-root-a660-registration-v3 ]] ||
	fail 'candidate export path is not exact'
[[ -d $base_root && ! -L $base_root ]] || fail 'accepted base export is absent'
[[ ! -e $export_root ]] || fail 'candidate export already exists'

archive=$(realpath -e "$archive")
[[ $archive == \
	"$repo/artifacts/a660-registration-build-a/modules.tar.gz" ]] ||
	fail 'module archive path is not the accepted Build A artifact'
[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$archive_hash" ]] ||
	fail 'module archive hash mismatch'
"$repo/scripts/device/verify-adreno-smmu-v21-live-acceptance.sh" \
	"$repo/test-results/2026-07-26-network-root-adreno-smmu-v21-live-accepted.md" \
	"$acceptance" >/dev/null
[[ $(sha256sum "$acceptance" | cut -d ' ' -f 1) == "$acceptance_sha" ]]

"$repo/scripts/host/verify-network-root-export.sh" "$base_root" >/dev/null

stage=$export_root.partial.$$
[[ ! -e $stage ]] || fail 'candidate partial path already exists'
work=$(mktemp -d /var/tmp/rog5-a660-registration-export.XXXXXX)
succeeded=0
report_retained_stage() {
	rm -rf "$work"
	if [[ $succeeded != 1 && -e $stage ]]; then
		echo "INFO retained failed candidate export for inspection: $stage" >&2
	fi
}
trap report_retained_stage EXIT

install -d -m 0755 "$stage"
cp -a --reflink=always "$base_root/." "$stage/"

module_paths=(
	drivers/clk/qcom/gpucc-sm8350.ko
	drivers/gpu/drm/drm_exec.ko
	drivers/gpu/drm/drm_gpuvm.ko
	drivers/gpu/drm/scheduler/gpu-sched.ko
	drivers/soc/qcom/mdt_loader.ko
	drivers/soc/qcom/ubwc_config.ko
	drivers/gpu/drm/msm/msm.ko
)
members=()
for relative in "${module_paths[@]}"; do
	members+=("lib/modules/$release/kernel/$relative")
done
tar -xzf "$archive" -C "$work" "${members[@]}"
for relative in "${module_paths[@]}"; do
	member=lib/modules/$release/kernel/$relative
	install -Dm0644 "$work/$member" \
		"$stage/usr/lib/modules/$release/kernel/$relative"
done

module_root=$stage/usr/lib/modules/$release
{
	printf '%s\n' \
		'kernel/drivers/clk/qcom/gpucc-sm8350.ko:' \
		'kernel/drivers/gpu/drm/drm_exec.ko:' \
		'kernel/drivers/gpu/drm/drm_gpuvm.ko: kernel/drivers/gpu/drm/drm_exec.ko' \
		'kernel/drivers/gpu/drm/scheduler/gpu-sched.ko:' \
		'kernel/drivers/soc/qcom/mdt_loader.ko:' \
		'kernel/drivers/soc/qcom/ubwc_config.ko:' \
		'kernel/drivers/gpu/drm/msm/msm.ko: kernel/drivers/gpu/drm/drm_exec.ko kernel/drivers/gpu/drm/drm_gpuvm.ko kernel/drivers/gpu/drm/scheduler/gpu-sched.ko kernel/drivers/soc/qcom/mdt_loader.ko kernel/drivers/soc/qcom/ubwc_config.ko'
} >"$module_root/modules.dep"
chown root:root "$module_root/modules.dep"
chmod 0644 "$module_root/modules.dep"

check_hash() {
	file=$1
	expected=$2
	[[ -f $file && ! -L $file ]]
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$expected" ]]
}

check_hash "$stage/usr/lib/firmware/qcom/a660_sqe.fw" \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76
check_hash "$stage/usr/lib/firmware/qcom/a660_gmu.bin" \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7
check_hash "$stage/usr/lib/firmware/qcom/sm8350/a660_zap.mbn" \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d
rm -f -- \
	"$stage/usr/lib/firmware/qcom/a660_sqe.fw" \
	"$stage/usr/lib/firmware/qcom/a660_gmu.bin" \
	"$stage/usr/lib/firmware/qcom/sm8350/a660_zap.mbn"

baseline=$repo/scripts/device/check-network-root-a660-registration-baseline.sh
probe=$repo/scripts/device/probe-network-root-a660-registration.sh
driver_override_check=$repo/scripts/device/check-adreno-smmu-driver-override-state.sh
install -Dm0755 "$baseline" \
	"$stage/usr/local/sbin/rog5-a660-registration-baseline"
install -Dm0755 "$probe" \
	"$stage/usr/local/sbin/rog5-a660-registration-probe"
install -Dm0755 "$driver_override_check" \
	"$stage/usr/local/sbin/rog5-adreno-smmu-driver-override-check"
install -Dm0444 "$acceptance" \
	"$stage/etc/rog5/adreno-smmu-v21-live.accepted"

seal=$stage/etc/rog5/a660-registration-export
{
	printf 'registration_generation=v3\n'
	printf 'base_export=rog5-network-root-v1\n'
	printf 'kernel_release=%s\n' "$release"
	printf 'module_archive_sha256=%s\n' "$archive_hash"
	printf 'baseline_sha256=%s\n' \
		"$(sha256sum "$baseline" | cut -d ' ' -f 1)"
	printf 'probe_sha256=%s\n' \
		"$(sha256sum "$probe" | cut -d ' ' -f 1)"
	printf 'driver_override_check_sha256=%s\n' \
		"$(sha256sum "$driver_override_check" | cut -d ' ' -f 1)"
	printf 'smmu_acceptance=ACCEPTED_IDLE_V21\n'
	printf 'smmu_acceptance_sha=c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875\n'
	printf 'smmu_acceptance_report_sha=0c7bb22301b8203531a7e8f098e8a719fd7f29d7de2cdf3c63730ecb792e9bbc\n'
	printf 'smmu_reprobe=EXACT_PLATFORM_DEVICE_AT_MOST_ONCE\n'
} >"$seal"
chown root:root "$seal"
chmod 0444 "$seal"

"$repo/scripts/host/verify-a660-registration-export.sh" \
	"$stage" "$base_root"
mv "$stage" "$export_root"
succeeded=1
echo "PASS prepared v21-accepted exact-reprobe A660 registration v3 export at $export_root"
