#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
base_root=${1:-/var/lib/rog5-network-root-a660-gmu-resume-entry-v9}
export_root=${2:-/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10}
release=7.1.4-rog5-a660reg1
archive_hash=87e5c3bae7d5034b64aea7212be8372506bf8b28cbdca7fb1b79bb20db50b9d0
msm_hash=c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d
helper_hash=d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae
oracle_hash=33ccadc6ae1e5f6f12ed83de0ddc192d30d204e229ec1b97aa813e1d0ac9c7e6
baseline_hash=a68960aa1ac84dbc6f3b469d8369d1c66dcd343f9adfc0a9f4e9909e9ee4245d
probe_hash=f28b1c28ec43da21747ce7e17247d33074bfa01f7c9c6171e80806a98eb70b36
acceptance_sha=8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f
acceptance_report_sha=2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79
predecessor_report=$repo/test-results/2026-07-27-a660-gmu-resume-entry-v9-live-accepted.md
predecessor_report_sha=57af6b4d0ddf6faaa708e7b409197dcf7aa8fcdb52a5a9612b59094aebc9dd2c
build_report=$repo/test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md
build_report_sha=9ae66678340437c4a38b2d6ee390cc375e661548be97cb108bb8f891a418dee4
runtime_report=$repo/test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-runtime-offline.md
runtime_report_sha=d74f277348d4d8537b7edbeee7b5aaaeab8e794a7ad63c2645cc393d0af4d959
kernel_patch=$repo/patches/linux-7.1.4/0016-drm-msm-add-a660-gmu-cx-runtime-pm-diagnostic.patch
kernel_patch_sha=5eef04eb711443acaaf4295e926577f90073b8ab62414cff3d18de2272d3a152
predecessor_seal_sha=137eb101708a8f96c063ed068caf7f8265641c43c228501fc578d5076be02bd5
predecessor_verifier=$repo/scripts/host/verify-a660-gmu-resume-entry-v9-export.sh
predecessor_verifier_sha=a3f526c6aa5e2f75af49a5b72b89ee24958ce23898e410e43749b482dde3179c
consumed_test=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v9.sh
consumed_test_sha=e876ff87452aa02e60f3135801a3f6d2da0042c680fd14bf0ae7319e9adc4a7f
runtime_builder=$repo/scripts/device/build-a660-gmu-cx-runtime-pm-v10-runtime.sh
runtime_builder_sha=a0bd091b1304581fe41bfcf1ceaa77a84fbbdd606d3797144a1e6685e1179942
runtime_verifier=$repo/scripts/device/verify-a660-gmu-cx-runtime-pm-v10-runtime-sources.sh
runtime_verifier_sha=7141c437962b49a90574dc8e14987fad9d291b5d8ea8b9c3371ebf0c8af187b3
trace_oracle=$repo/scripts/device/check-a660-gmu-cx-runtime-pm-v10-trace.sh
source_msm=$repo/artifacts/a660-gmu-cx-runtime-pm-v10-build/drivers/gpu/drm/msm/msm.ko
v10_verifier=$repo/scripts/host/verify-a660-gmu-cx-runtime-pm-v10-export.sh

[[ $EUID == 0 ]] || fail 'run through PolicyKit; do not share a sudo password'
for command in chmod chown cmp cp cut install mktemp mv realpath rm \
	sha256sum stat; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
for tool in "$predecessor_verifier" "$consumed_test" "$runtime_builder" \
	"$runtime_verifier" "$trace_oracle" "$v10_verifier"; do
	[[ -x $tool ]] || fail "missing executable verifier or builder: $tool"
done
[[ $base_root == /var/lib/rog5-network-root-a660-gmu-resume-entry-v9 ]] ||
	fail 'predecessor export path is not exact'
[[ $export_root == /var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10 ]] ||
	fail 'candidate export path is not exact'
[[ -d $base_root && ! -L $base_root ]] ||
	fail 'consumed v9 predecessor export is absent'
[[ ! -e $export_root ]] || fail 'candidate export already exists'

check_hash() {
	local file=$1 expected=$2 label=$3
	[[ -f $file && ! -L $file ]] || fail "$label is absent or linked"
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "$label hash mismatch"
}

check_hash "$predecessor_verifier" "$predecessor_verifier_sha" \
	'v9 export verifier'
check_hash "$consumed_test" "$consumed_test_sha" 'v9 consumption test'
check_hash "$runtime_builder" "$runtime_builder_sha" 'v10 runtime builder'
check_hash "$runtime_verifier" "$runtime_verifier_sha" 'v10 runtime verifier'
check_hash "$trace_oracle" "$oracle_hash" \
	'exact GMU/linked-CX v10 trace oracle'
check_hash "$predecessor_report" "$predecessor_report_sha" \
	'accepted and consumed v9 live report'
check_hash "$build_report" "$build_report_sha" \
	'reproducible v10 kernel build report'
check_hash "$runtime_report" "$runtime_report_sha" \
	'reproducible v10 runtime report'
check_hash "$kernel_patch" "$kernel_patch_sha" \
	'accepted GMU/CX runtime-PM kernel patch'
check_hash "$source_msm" "$msm_hash" 'accepted v10 MSM module'
check_hash "$base_root/etc/rog5/a660-gmu-resume-entry-v9-export" \
	"$predecessor_seal_sha" 'v9 predecessor seal'

"$predecessor_verifier" "$base_root" >/dev/null
"$consumed_test" >/dev/null

base_root=$(realpath -e "$base_root")
stage=$export_root.partial.$$
[[ ! -e $stage ]] || fail 'candidate partial path already exists'
work=$(mktemp -d /var/tmp/rog5-a660-gmu-cx-runtime-pm-v10-export.XXXXXX)
succeeded=0
cleanup() {
	rm -rf -- "$work"
	if [[ $succeeded != 1 && -e $stage ]]; then
		case $stage in
			/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10.partial.*)
				rm -rf -- "$stage"
				;;
			*) echo "FAIL refusing unsafe partial cleanup: $stage" >&2 ;;
		esac
	fi
}
trap cleanup EXIT HUP INT TERM

expected_baseline=$work/rog5-a660-gmu-cx-runtime-pm-v10-baseline
expected_probe=$work/rog5-a660-gmu-cx-runtime-pm-v10-probe
"$runtime_builder" "$expected_baseline" "$expected_probe" >/dev/null
"$runtime_verifier" "$expected_baseline" "$expected_probe" >/dev/null
check_hash "$expected_baseline" "$baseline_hash" 'generated v10 baseline'
check_hash "$expected_probe" "$probe_hash" 'generated v10 probe'

install -d -m 0755 "$stage"
cp -a --reflink=always "$base_root/." "$stage/"
rm -f -- \
	"$stage/usr/local/libexec/rog5-a660-gmu-resume-entry-v9-open" \
	"$stage/usr/local/libexec/rog5-a660-gmu-resume-entry-v9-trace-oracle" \
	"$stage/usr/local/sbin/rog5-a660-gmu-resume-entry-v9-baseline" \
	"$stage/usr/local/sbin/rog5-a660-gmu-resume-entry-v9-probe" \
	"$stage/etc/rog5/a660-gmu-resume-entry-v9-export"

base_helper=$base_root/usr/local/libexec/rog5-a660-gmu-resume-entry-v9-open
check_hash "$base_helper" "$helper_hash" 'v9 one-open helper'
install -Dm0755 "$base_helper" \
	"$stage/usr/local/libexec/rog5-a660-gmu-cx-runtime-pm-v10-open"
install -Dm0755 "$trace_oracle" \
	"$stage/usr/local/libexec/rog5-a660-gmu-cx-runtime-pm-v10-trace-oracle"
install -Dm0755 "$expected_baseline" \
	"$stage/usr/local/sbin/rog5-a660-gmu-cx-runtime-pm-v10-baseline"
install -Dm0755 "$expected_probe" \
	"$stage/usr/local/sbin/rog5-a660-gmu-cx-runtime-pm-v10-probe"
install -Dm0644 "$source_msm" \
	"$stage/usr/lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko"

seal=$stage/etc/rog5/a660-gmu-cx-runtime-pm-v10-export
{
	printf 'diagnostic_generation=v10\n'
	printf 'base_export=rog5-network-root-a660-gmu-resume-entry-v9\n'
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
	printf 'trace_oracle_sha256=%s\n' "$oracle_hash"
	printf 'baseline_sha256=%s\n' "$baseline_hash"
	printf 'probe_sha256=%s\n' "$probe_hash"
	printf 'registration_acceptance=ACCEPTED_A660_REGISTRATION_V3\n'
	printf 'registration_acceptance_sha256=%s\n' "$acceptance_sha"
	printf 'registration_report_sha256=%s\n' "$acceptance_report_sha"
	printf 'predecessor=v9_live_accepted_consumed\n'
	printf 'predecessor_report_sha256=%s\n' "$predecessor_report_sha"
	printf 'predecessor_consumption_commit=3d708cd\n'
	printf 'predecessor_seal_sha256=%s\n' "$predecessor_seal_sha"
	printf 'predecessor_export_verifier_sha256=%s\n' \
		"$predecessor_verifier_sha"
	printf 'predecessor_consumption_test_sha256=%s\n' "$consumed_test_sha"
	printf 'offline_acceptance_report_sha256=%s\n' "$build_report_sha"
	printf 'runtime_report_sha256=%s\n' "$runtime_report_sha"
	printf 'gmu_cx_runtime_pm_patch_sha256=%s\n' "$kernel_patch_sha"
	printf 'runtime_builder_sha256=%s\n' "$runtime_builder_sha"
	printf 'runtime_verifier_sha256=%s\n' "$runtime_verifier_sha"
	printf 'firmware_policy=SQE_GMU_ONLY_ZAP_ABSENT\n'
	printf 'open_policy=EXACTLY_ONE_EUCLEAN\n'
	printf 'size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS\n'
	printf 'raw_size_contract=4,4096,43288\n'
	printf 'object_size_policy=SOURCE_PINNED_PAGE_ALIGN\n'
	printf 'object_size_contract=4096,4096,45056\n'
	printf 'trace_policy=PID_FILTERED_S32_EXACT_GMU_LINKED_CX_RPM_AND_LOGICAL_VMAP\n'
	printf 'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL\n'
	printf 'gmu_cx_runtime_pm_parameter_mode=0400\n'
	printf 'v7_reuse=FORBIDDEN\n'
	printf 'v8_reuse=FORBIDDEN\n'
	printf 'v9_reuse=FORBIDDEN\n'
	printf 'kernel/module delta=v10-msm-only\n'
} >"$seal"
chown root:root \
	"$stage/usr/local/libexec/rog5-a660-gmu-cx-runtime-pm-v10-open" \
	"$stage/usr/local/libexec/rog5-a660-gmu-cx-runtime-pm-v10-trace-oracle" \
	"$stage/usr/local/sbin/rog5-a660-gmu-cx-runtime-pm-v10-baseline" \
	"$stage/usr/local/sbin/rog5-a660-gmu-cx-runtime-pm-v10-probe" \
	"$stage/usr/lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko" \
	"$seal"
chmod 0444 "$seal"
chmod 0555 "$stage"

"$v10_verifier" "$stage" "$base_root"
mv "$stage" "$export_root"
succeeded=1
echo "PASS prepared A660 GMU/CX runtime-PM v10 export at $export_root"
