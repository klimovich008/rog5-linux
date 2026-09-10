#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
base_root=${1:-/var/lib/rog5-network-root-a660-ucode-allocation-v7}
export_root=${2:-/var/lib/rog5-network-root-a660-gmu-resume-entry-v8}
release=7.1.4-rog5-a660reg1
archive_hash=38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7
msm_hash=b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861
helper_hash=d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae
baseline_hash=3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23
probe_hash=832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255
acceptance_sha=8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f
acceptance_report_sha=2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79
live_report=$repo/test-results/2026-07-26-a660-ucode-allocation-v7-live-accepted.md
live_report_sha=ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a
boundary_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-boundary.md
boundary_report_sha=41c06dcd895fcc873638ddf40dce0b0d5dd5bbf9e148f5d3abd5521b072c320d
build_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-v8-offline.md
build_report_sha=6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c
kernel_patch=$repo/patches/linux-7.1.4/0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch
kernel_patch_sha=a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051
predecessor_seal_sha=c679ff6cbed6aefb28b7537cd30c561948e4d4672cd9320a8e70fd3d79b4f046
predecessor_verifier=$repo/scripts/host/verify-a660-ucode-allocation-v7-export.sh
predecessor_verifier_sha=c3db1233fc644c0019b9337dac9253f3cf7ec1588b237df314ff414c78273939
consumed_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v7.sh
consumed_test_sha=4945156290345ead855c5abf557db0352d4cbd7ada274050afbea47d594d9a3a
relocation_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-vmap-relocations.sh
relocation_verifier_sha=e602f61702093050f5faba7a28c8efe54f50bf74a68369aa6096c94427389bf1
runtime_builder=$repo/scripts/device/build-a660-gmu-resume-entry-v8-runtime.sh
runtime_builder_sha=95cc98935677617ddf504701858b4a068a25b71a9a9853735a26c7e590cb5a9d
runtime_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-v8-runtime-sources.sh
runtime_verifier_sha=62ece65d45159b38adf08b381f2531883c371ee4e7661358d61a4617766a9e85
source_msm=$repo/artifacts/a660-gmu-resume-entry-build-a/drivers/gpu/drm/msm/msm.ko

[[ $EUID == 0 ]] || fail 'run through PolicyKit; do not share a sudo password'
for command in chmod chown cmp cp cut install mktemp mv realpath rm \
	sha256sum stat; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
for tool in "$predecessor_verifier" "$consumed_test" \
	"$relocation_verifier" "$runtime_builder" "$runtime_verifier"; do
	[[ -x $tool ]] || fail "missing executable verifier or builder: $tool"
done
[[ $base_root == /var/lib/rog5-network-root-a660-ucode-allocation-v7 ]] ||
	fail 'predecessor export path is not exact'
[[ $export_root == /var/lib/rog5-network-root-a660-gmu-resume-entry-v8 ]] ||
	fail 'candidate export path is not exact'
[[ -d $base_root && ! -L $base_root ]] ||
	fail 'consumed v7 predecessor export is absent'
[[ ! -e $export_root ]] || fail 'candidate export already exists'

check_hash() {
	local file=$1 expected=$2 label=$3
	[[ -f $file && ! -L $file ]] || fail "$label is absent or linked"
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "$label hash mismatch"
}

check_hash "$predecessor_verifier" "$predecessor_verifier_sha" \
	'v7 export verifier'
check_hash "$consumed_test" "$consumed_test_sha" 'v7 consumption test'
check_hash "$relocation_verifier" "$relocation_verifier_sha" \
	'v8 compiler-relocation verifier'
check_hash "$runtime_builder" "$runtime_builder_sha" 'v8 runtime builder'
check_hash "$runtime_verifier" "$runtime_verifier_sha" 'v8 runtime verifier'
check_hash "$live_report" "$live_report_sha" \
	'accepted and consumed v7 live report'
check_hash "$boundary_report" "$boundary_report_sha" \
	'GMU resume-entry source boundary report'
check_hash "$build_report" "$build_report_sha" \
	'reproducible v8 kernel build report'
check_hash "$kernel_patch" "$kernel_patch_sha" \
	'accepted GMU resume-entry kernel patch'
check_hash "$source_msm" "$msm_hash" 'accepted v8 MSM module'
check_hash "$base_root/etc/rog5/a660-ucode-allocation-v7-export" \
	"$predecessor_seal_sha" 'v7 predecessor seal'

"$predecessor_verifier" "$base_root" >/dev/null
"$consumed_test" >/dev/null
"$relocation_verifier" "$source_msm" >/dev/null

base_root=$(realpath -e "$base_root")
stage=$export_root.partial.$$
[[ ! -e $stage ]] || fail 'candidate partial path already exists'
work=$(mktemp -d /var/tmp/rog5-a660-gmu-resume-entry-v8-export.XXXXXX)
succeeded=0
cleanup() {
	rm -rf -- "$work"
	if [[ $succeeded != 1 && -e $stage ]]; then
		case $stage in
			/var/lib/rog5-network-root-a660-gmu-resume-entry-v8.partial.*)
				rm -rf -- "$stage"
				;;
			*) echo "FAIL refusing unsafe partial cleanup: $stage" >&2 ;;
		esac
	fi
}
trap cleanup EXIT HUP INT TERM

expected_baseline=$work/rog5-a660-gmu-resume-entry-v8-baseline
expected_probe=$work/rog5-a660-gmu-resume-entry-v8-probe
"$runtime_builder" "$expected_baseline" "$expected_probe" >/dev/null
"$runtime_verifier" "$expected_baseline" "$expected_probe" >/dev/null
check_hash "$expected_baseline" "$baseline_hash" 'generated v8 baseline'
check_hash "$expected_probe" "$probe_hash" 'generated v8 probe'

install -d -m 0755 "$stage"
cp -a --reflink=always "$base_root/." "$stage/"
rm -f -- \
	"$stage/usr/local/libexec/rog5-a660-ucode-allocation-v7-open" \
	"$stage/usr/local/sbin/rog5-a660-ucode-allocation-v7-baseline" \
	"$stage/usr/local/sbin/rog5-a660-ucode-allocation-v7-probe" \
	"$stage/etc/rog5/a660-ucode-allocation-v7-export"

base_helper=$base_root/usr/local/libexec/rog5-a660-ucode-allocation-v7-open
check_hash "$base_helper" "$helper_hash" 'v7 one-open helper'
install -Dm0755 "$base_helper" \
	"$stage/usr/local/libexec/rog5-a660-gmu-resume-entry-v8-open"
install -Dm0755 "$expected_baseline" \
	"$stage/usr/local/sbin/rog5-a660-gmu-resume-entry-v8-baseline"
install -Dm0755 "$expected_probe" \
	"$stage/usr/local/sbin/rog5-a660-gmu-resume-entry-v8-probe"
install -m0644 "$source_msm" \
	"$stage/usr/lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko"

seal=$stage/etc/rog5/a660-gmu-resume-entry-v8-export
{
	printf 'diagnostic_generation=v8\n'
	printf 'base_export=rog5-network-root-a660-ucode-allocation-v7\n'
	printf 'kernel_release=%s\n' "$release"
	printf 'module_archive_sha256=%s\n' "$archive_hash"
	printf 'msm_module_sha256=%s\n' "$msm_hash"
	printf 'sqe_firmware_sha256=%s\n' \
		d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76
	printf 'gmu_firmware_sha256=%s\n' \
		8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7
	printf 'zap_firmware_sha256=%s\n' \
		5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d
	printf 'zap=absent\n'
	printf 'helper_sha256=%s\n' "$helper_hash"
	printf 'baseline_sha256=%s\n' "$baseline_hash"
	printf 'probe_sha256=%s\n' "$probe_hash"
	printf 'registration_acceptance=ACCEPTED_A660_REGISTRATION_V3\n'
	printf 'registration_acceptance_sha256=%s\n' "$acceptance_sha"
	printf 'registration_report_sha256=%s\n' "$acceptance_report_sha"
	printf 'predecessor=v7_live_accepted_consumed\n'
	printf 'predecessor_report_sha256=%s\n' "$live_report_sha"
	printf 'predecessor_consumption_commit=12ad39c\n'
	printf 'predecessor_seal_sha256=%s\n' "$predecessor_seal_sha"
	printf 'predecessor_export_verifier_sha256=%s\n' \
		"$predecessor_verifier_sha"
	printf 'predecessor_consumption_test_sha256=%s\n' "$consumed_test_sha"
	printf 'source_boundary_report_sha256=%s\n' "$boundary_report_sha"
	printf 'kernel_build_report_sha256=%s\n' "$build_report_sha"
	printf 'gmu_entry_patch_sha256=%s\n' "$kernel_patch_sha"
	printf 'compiler_policy=PINNED_V8_MSM_RELOCATIONS\n'
	printf 'compiler_verifier_sha256=%s\n' "$relocation_verifier_sha"
	printf 'runtime_builder_sha256=%s\n' "$runtime_builder_sha"
	printf 'runtime_verifier_sha256=%s\n' "$runtime_verifier_sha"
	printf 'firmware_policy=SQE_GMU_ONLY_ZAP_ABSENT\n'
	printf 'open_policy=EXACTLY_ONE_EUCLEAN\n'
	printf 'size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS\n'
	printf 'raw_size_contract=4,4096,43288\n'
	printf 'object_size_policy=SOURCE_PINNED_PAGE_ALIGN\n'
	printf 'object_size_contract=4096,4096,45056\n'
	printf 'trace_policy=PID_FILTERED_GMU_ENTRY_AND_LOGICAL_VMAP\n'
	printf 'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL\n'
	printf 'gmu_entry_parameter_mode=0400\n'
	printf 'v7_reuse=FORBIDDEN\n'
} >"$seal"
chown root:root "$seal"
chmod 0444 "$seal"
chmod 0555 "$stage"

"$repo/scripts/host/verify-a660-gmu-resume-entry-v8-export.sh" \
	"$stage" "$base_root"
mv "$stage" "$export_root"
succeeded=1
echo "PASS prepared A660 GMU resume-entry v8 export at $export_root"
