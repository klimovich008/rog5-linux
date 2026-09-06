#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
base_root=${1:-/var/lib/rog5-network-root-a660-ucode-allocation-v6}
export_root=${2:-/var/lib/rog5-network-root-a660-ucode-allocation-v7}
registration_root=/var/lib/rog5-network-root-a660-registration-v3
release=7.1.4-rog5-a660reg1
archive_hash=ad3c4b441db6d2701e0e6bb945c1a4bf52d284e209873cb4b9250014386da680
msm_hash=fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45
helper_hash=d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae
baseline_hash=d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386
probe_hash=01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0
acceptance_sha=8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f
acceptance_report_sha=2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79
rejection=$repo/test-results/2026-07-26-a660-ucode-allocation-v6-live-rejected.md
rejection_sha=cfdd0837e6da7d06ba74e0557c6abeea396f12f02e345d9ab87ba1a47ade89e6
boundary_report=$repo/test-results/2026-07-26-a660-ucode-allocation-boundary.md
boundary_report_sha=a17847d18c21d5b2c039df4353a899abce37159ec0009b5afaa0dda6067d146f
predecessor_seal_sha=e9a9bf460b62d91c44fa15b8258ae5a5660ef387846530e8cf93fce67f7f17ea
predecessor_verifier=$repo/scripts/host/verify-a660-ucode-allocation-v6-export.sh
predecessor_verifier_sha=07629d95e62b7a459332d2e8341e52462ff056c2de15dbbe3370da9978fc074e
consumed_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v6.sh
consumed_test_sha=80f96dbea05221aefe967f79ad8e3d51cdd5cf75ff6a92d5aed26c3ec4e647df
relocation_verifier=$repo/scripts/device/verify-a660-ucode-vmap-relocations.sh
relocation_verifier_sha=56d63a17b6c89454691dbd74539c299d99e99b341831358d6f673f128a3181ae
runtime_builder=$repo/scripts/device/build-a660-ucode-allocation-v7-runtime.sh
runtime_builder_sha=ac4412f6710b1c6bb1d6f87bb6850157aa136a55301db84884843784bae6bf7c
runtime_verifier=$repo/scripts/device/verify-a660-ucode-allocation-v7-runtime-sources.sh
runtime_verifier_sha=7f73923dd8d1a3b30a0bfd3a76bc8eb51e262ad5dc6a72fc69620e5b9729540a

[[ $EUID == 0 ]] || fail 'run through PolicyKit; do not share a sudo password'
for command in chmod chown cmp cp cut install mktemp mv realpath rm \
	sha256sum stat; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
for tool in "$predecessor_verifier" "$consumed_test" \
	"$relocation_verifier" "$runtime_builder" "$runtime_verifier"; do
	[[ -x $tool ]] || fail "missing executable verifier or builder: $tool"
done
[[ $base_root == /var/lib/rog5-network-root-a660-ucode-allocation-v6 ]] ||
	fail 'predecessor export path is not exact'
[[ $export_root == /var/lib/rog5-network-root-a660-ucode-allocation-v7 ]] ||
	fail 'candidate export path is not exact'
[[ -d $base_root && ! -L $base_root ]] ||
	fail 'consumed v6 predecessor export is absent'
[[ ! -e $export_root ]] || fail 'candidate export already exists'

check_hash() {
	local file=$1 expected=$2 label=$3
	[[ -f $file && ! -L $file ]] || fail "$label is absent or linked"
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "$label hash mismatch"
}

check_hash "$predecessor_verifier" "$predecessor_verifier_sha" \
	'v6 export verifier'
check_hash "$consumed_test" "$consumed_test_sha" 'v6 consumption test'
check_hash "$relocation_verifier" "$relocation_verifier_sha" \
	'compiler-relocation verifier'
check_hash "$runtime_builder" "$runtime_builder_sha" 'v7 runtime builder'
check_hash "$runtime_verifier" "$runtime_verifier_sha" 'v7 runtime verifier'
check_hash "$rejection" "$rejection_sha" 'v6 live rejection report'
check_hash "$boundary_report" "$boundary_report_sha" \
	'ucode-allocation source boundary report'
check_hash "$base_root/etc/rog5/a660-ucode-allocation-v6-export" \
	"$predecessor_seal_sha" 'v6 predecessor seal'

"$predecessor_verifier" "$base_root" "$registration_root" >/dev/null
"$consumed_test" >/dev/null

base_root=$(realpath -e "$base_root")
stage=$export_root.partial.$$
[[ ! -e $stage ]] || fail 'candidate partial path already exists'
work=$(mktemp -d /var/tmp/rog5-a660-ucode-allocation-v7-export.XXXXXX)
succeeded=0
cleanup() {
	rm -rf -- "$work"
	if [[ $succeeded != 1 && -e $stage ]]; then
		case $stage in
			/var/lib/rog5-network-root-a660-ucode-allocation-v7.partial.*)
				rm -rf -- "$stage"
				;;
			*) echo "FAIL refusing unsafe partial cleanup: $stage" >&2 ;;
		esac
	fi
}
trap cleanup EXIT HUP INT TERM

expected_baseline=$work/rog5-a660-ucode-allocation-v7-baseline
expected_probe=$work/rog5-a660-ucode-allocation-v7-probe
"$runtime_builder" "$expected_baseline" "$expected_probe" >/dev/null
"$runtime_verifier" "$expected_baseline" "$expected_probe" >/dev/null
check_hash "$expected_baseline" "$baseline_hash" 'generated v7 baseline'
check_hash "$expected_probe" "$probe_hash" 'generated v7 probe'

install -d -m 0755 "$stage"
cp -a --reflink=always "$base_root/." "$stage/"
rm -f -- \
	"$stage/usr/local/libexec/rog5-a660-ucode-allocation-v6-open" \
	"$stage/usr/local/sbin/rog5-a660-ucode-allocation-v6-baseline" \
	"$stage/usr/local/sbin/rog5-a660-ucode-allocation-v6-probe" \
	"$stage/etc/rog5/a660-ucode-allocation-v6-export"

base_helper=$base_root/usr/local/libexec/rog5-a660-ucode-allocation-v6-open
check_hash "$base_helper" "$helper_hash" 'v6 one-open helper'
install -Dm0755 "$base_helper" \
	"$stage/usr/local/libexec/rog5-a660-ucode-allocation-v7-open"
install -Dm0755 "$expected_baseline" \
	"$stage/usr/local/sbin/rog5-a660-ucode-allocation-v7-baseline"
install -Dm0755 "$expected_probe" \
	"$stage/usr/local/sbin/rog5-a660-ucode-allocation-v7-probe"

seal=$stage/etc/rog5/a660-ucode-allocation-v7-export
{
	printf 'diagnostic_generation=v7\n'
	printf 'base_export=rog5-network-root-a660-ucode-allocation-v6\n'
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
	printf 'predecessor=v6_live_rejected_consumed\n'
	printf 'predecessor_report_sha256=%s\n' "$rejection_sha"
	printf 'predecessor_consumption_commit=664fd09\n'
	printf 'predecessor_seal_sha256=%s\n' "$predecessor_seal_sha"
	printf 'predecessor_export_verifier_sha256=%s\n' \
		"$predecessor_verifier_sha"
	printf 'predecessor_consumption_test_sha256=%s\n' "$consumed_test_sha"
	printf 'source_boundary_report_sha256=%s\n' "$boundary_report_sha"
	printf 'compiler_policy=PINNED_MSM_RELOCATIONS\n'
	printf 'compiler_verifier_sha256=%s\n' "$relocation_verifier_sha"
	printf 'runtime_builder_sha256=%s\n' "$runtime_builder_sha"
	printf 'runtime_verifier_sha256=%s\n' "$runtime_verifier_sha"
	printf 'firmware_policy=SQE_GMU_ONLY_ZAP_ABSENT\n'
	printf 'open_policy=EXACTLY_ONE_EUCLEAN\n'
	printf 'size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS\n'
	printf 'raw_size_contract=4,4096,43288\n'
	printf 'object_size_policy=SOURCE_PINNED_PAGE_ALIGN\n'
	printf 'object_size_contract=4096,4096,45056\n'
	printf 'trace_policy=PID_FILTERED_LOGICAL_VMAP_BALANCE\n'
	printf 'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL\n'
	printf 'v6_reuse=FORBIDDEN\n'
} >"$seal"
chown root:root "$seal"
chmod 0444 "$seal"
chmod 0555 "$stage"

"$repo/scripts/host/verify-a660-ucode-allocation-v7-export.sh" \
	"$stage" "$base_root"
mv "$stage" "$export_root"
succeeded=1
echo "PASS prepared A660 ucode-allocation v7 export at $export_root"
