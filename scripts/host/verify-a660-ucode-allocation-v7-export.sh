#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-a660-ucode-allocation-v7-export.sh ROOT BASE_ROOT}
base_root=${2:-/var/lib/rog5-network-root-a660-ucode-allocation-v6}
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

for command in cmp cut file find grep mktemp modinfo nm readelf realpath rm \
	sha256sum sort stat strings wc xargs; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
for tool in "$predecessor_verifier" "$consumed_test" \
	"$relocation_verifier" "$runtime_builder" "$runtime_verifier"; do
	[[ -x $tool ]] || fail "missing executable verifier or builder: $tool"
done
[[ -d $root && ! -L $root ]] || fail 'candidate export is not a directory'
[[ $base_root == /var/lib/rog5-network-root-a660-ucode-allocation-v6 ]] ||
	fail 'predecessor export path is not exact'
[[ -d $base_root && ! -L $base_root ]] ||
	fail 'v6 predecessor export is not a directory'
root=$(realpath -e "$root")
base_root=$(realpath -e "$base_root")
[[ $base_root == /var/lib/rog5-network-root-a660-ucode-allocation-v6 ]] ||
	fail 'predecessor export resolves unexpectedly'
[[ $root != / && $base_root != / && $root != "$base_root" ]] ||
	fail 'unsafe or aliased export roots'
[[ $(stat -c '%u:%g:%a' "$root") == 0:0:555 ]] ||
	fail 'candidate export root is not root-owned mode 0555'

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

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
expected_baseline=$work/expected-baseline
expected_probe=$work/expected-probe
"$runtime_builder" "$expected_baseline" "$expected_probe" >/dev/null
"$runtime_verifier" "$expected_baseline" "$expected_probe" >/dev/null
check_hash "$expected_baseline" "$baseline_hash" 'generated v7 baseline'
check_hash "$expected_probe" "$probe_hash" 'generated v7 probe'

expected_seal=$work/expected-seal
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
} >"$expected_seal"

seal=$root/etc/rog5/a660-ucode-allocation-v7-export
[[ -f $seal && ! -L $seal ]] || fail 'v7 export seal is absent or linked'
[[ $(stat -c '%u:%g:%a' "$seal") == 0:0:444 ]] ||
	fail 'v7 export seal metadata changed'
cmp "$expected_seal" "$seal" ||
	fail 'v7 export seal is not byte-exact'

baseline=$root/usr/local/sbin/rog5-a660-ucode-allocation-v7-baseline
probe=$root/usr/local/sbin/rog5-a660-ucode-allocation-v7-probe
helper=$root/usr/local/libexec/rog5-a660-ucode-allocation-v7-open
for source_target in \
	"$expected_baseline:$baseline:755" \
	"$expected_probe:$probe:755"
do
	source=${source_target%%:*}
	remainder=${source_target#*:}
	target=${remainder%:*}
	mode=${source_target##*:}
	[[ -f $target && ! -L $target ]] ||
		fail "installed runtime is absent or linked: $target"
	cmp "$source" "$target"
	[[ $(stat -c '%u:%g:%a' "$target") == "0:0:$mode" ]] ||
		fail "installed runtime metadata changed: $target"
done

[[ -f $helper && ! -L $helper ]]
[[ $(stat -c '%u:%g:%a:%s' "$helper") == 0:0:755:896 ]]
check_hash "$helper" "$helper_hash" 'installed v7 one-open helper'
file "$helper" |
	grep -Fq \
	'ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, stripped'
if readelf -lW "$helper" |
	grep -Eq '(^|[[:space:]])(INTERP|DYNAMIC)([[:space:]]|$)'
then
	fail 'installed one-open helper gained an interpreter or dynamic segment'
fi
[[ $(strings -a "$helper" | grep -Fxc '/dev/dri/renderD128') == 1 ]]
[[ $(strings -a "$helper" | grep -Fxc 'OPEN_ERRNO=117') == 1 ]]

for removed in \
	usr/local/libexec/rog5-a660-ucode-allocation-v6-open \
	usr/local/sbin/rog5-a660-ucode-allocation-v6-baseline \
	usr/local/sbin/rog5-a660-ucode-allocation-v6-probe \
	etc/rog5/a660-ucode-allocation-v6-export
do
	[[ ! -e $root/$removed ]] ||
		fail "rejected v6 control remains: $removed"
done
[[ $(find "$root/usr/local/libexec" -maxdepth 1 -type f \
	-name 'rog5-a660-ucode-allocation-v*-open' | wc -l) == 1 ]]
[[ $(find "$root/usr/local/sbin" -maxdepth 1 -type f \
	-name 'rog5-a660-ucode-allocation-v*-baseline' | wc -l) == 1 ]]
[[ $(find "$root/usr/local/sbin" -maxdepth 1 -type f \
	-name 'rog5-a660-ucode-allocation-v*-probe' | wc -l) == 1 ]]

module_root=$root/usr/lib/modules/$release
msm_module=$module_root/kernel/drivers/gpu/drm/msm/msm.ko
[[ $(find "$module_root" -type f -name '*.ko' | wc -l) == 7 ]]
[[ $(stat -c '%u:%g:%a' "$msm_module") == 0:0:644 ]]
check_hash "$msm_module" "$msm_hash" 'accepted MSM module'
[[ $(modinfo -F name "$msm_module") == msm ]]
[[ $(modinfo -F depends "$msm_module") == \
	'drm_exec,drm_gpuvm,gpu-sched,mdt_loader,ubwc_config' ]]
[[ $(modinfo -F vermagic "$msm_module") == \
	"$release SMP preempt mod_unload aarch64" ]]
"$relocation_verifier" "$msm_module" >/dev/null
for symbol in adreno_load_ucode_only msm_gem_vma_map msm_gem_vma_unmap \
	msm_gem_vma_close msm_gem_unpin_iova msm_gem_free_object \
	msm_gem_kernel_new msm_gem_get_vaddr msm_gem_put_vaddr \
	msm_gem_kernel_put a6xx_ucode_unload
do
	[[ $(nm -a "$msm_module" | grep -Ec "[[:space:]]$symbol$") == 1 ]] ||
		fail "MSM trace symbol is not unique: $symbol"
done

firmware_root=$root/usr/lib/firmware
check_hash "$firmware_root/qcom/a660_sqe.fw" \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	'SQE firmware'
check_hash "$firmware_root/qcom/a660_gmu.bin" \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	'GMU firmware'
[[ $(stat -c '%u:%g:%a' "$firmware_root/qcom/a660_sqe.fw") == 0:0:644 ]]
[[ $(stat -c '%u:%g:%a' "$firmware_root/qcom/a660_gmu.bin") == 0:0:644 ]]
[[ ! -e $firmware_root/qcom/sm8350/a660_zap.mbn ]]
[[ $(find "$root" -xdev -type f \
	\( -name a660_sqe.fw -o -name a660_gmu.bin -o -name a660_zap.mbn \) |
	wc -l) == 2 ]]

for relative in \
	root/.ssh/authorized_keys \
	home/rog5/.ssh/authorized_keys \
	etc/ssh/ssh_host_ed25519_key \
	etc/ssh/ssh_host_ed25519_key.pub \
	etc/rog5/a660-registration-v3-live.accepted
do
	cmp "$root/$relative" "$base_root/$relative"
	[[ $(stat -c '%u:%g:%a' "$root/$relative") == \
		"$(stat -c '%u:%g:%a' "$base_root/$relative")" ]]
done
check_hash "$root/etc/rog5/a660-registration-v3-live.accepted" \
	"$acceptance_sha" 'registration-v3 acceptance marker'

unchanged_metadata() {
	local tree=$1
	find "$tree" -xdev \
		! -path "$tree/etc/rog5" \
		! -path "$tree/usr/local/libexec" \
		! -path "$tree/usr/local/sbin" \
		! -path "$tree/etc/rog5/a660-ucode-allocation-v6-export" \
		! -path "$tree/etc/rog5/a660-ucode-allocation-v7-export" \
		! -path "$tree/usr/local/libexec/rog5-a660-ucode-allocation-v6-open" \
		! -path "$tree/usr/local/libexec/rog5-a660-ucode-allocation-v7-open" \
		! -path "$tree/usr/local/sbin/rog5-a660-ucode-allocation-v6-baseline" \
		! -path "$tree/usr/local/sbin/rog5-a660-ucode-allocation-v6-probe" \
		! -path "$tree/usr/local/sbin/rog5-a660-ucode-allocation-v7-baseline" \
		! -path "$tree/usr/local/sbin/rog5-a660-ucode-allocation-v7-probe" \
		-printf '%P|%y|%m|%U|%G|%s|%l\n' | sort
}
unchanged_metadata "$base_root" >"$work/base.metadata"
unchanged_metadata "$root" >"$work/candidate.metadata"
cmp "$work/base.metadata" "$work/candidate.metadata" ||
	fail 'non-diagnostic tree metadata differs from consumed v6'

unchanged_hashes() {
	local tree=$1
	(
		cd "$tree"
		find . -xdev -type f \
			! -path './etc/rog5/a660-ucode-allocation-v6-export' \
			! -path './etc/rog5/a660-ucode-allocation-v7-export' \
			! -path './usr/local/libexec/rog5-a660-ucode-allocation-v6-open' \
			! -path './usr/local/libexec/rog5-a660-ucode-allocation-v7-open' \
			! -path './usr/local/sbin/rog5-a660-ucode-allocation-v6-baseline' \
			! -path './usr/local/sbin/rog5-a660-ucode-allocation-v6-probe' \
			! -path './usr/local/sbin/rog5-a660-ucode-allocation-v7-baseline' \
			! -path './usr/local/sbin/rog5-a660-ucode-allocation-v7-probe' \
			-print0 | sort -z | xargs -0 sha256sum
	)
}
unchanged_hashes "$base_root" >"$work/base.sha256"
unchanged_hashes "$root" >"$work/candidate.sha256"
cmp "$work/base.sha256" "$work/candidate.sha256" ||
	fail 'non-diagnostic tree content differs from consumed v6'

echo 'PASS A660 ucode-allocation v7 export modules=7 firmware=2 zap=absent helper=exact raw_sizes=4,4096,43288 object_sizes=4096,4096,45056 compiler=relocations logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v6 root-owned mode 0555'
