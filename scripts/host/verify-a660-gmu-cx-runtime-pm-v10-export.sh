#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-a660-gmu-cx-runtime-pm-v10-export.sh ROOT BASE_ROOT}
base_root=${2:-/var/lib/rog5-network-root-a660-gmu-resume-entry-v9}
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

for command in cmp cut file find grep mktemp modinfo nm readelf realpath \
	rm sha256sum sort stat strings wc xargs; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
for tool in "$predecessor_verifier" "$consumed_test" "$runtime_builder" \
	"$runtime_verifier" "$trace_oracle"; do
	[[ -x $tool ]] || fail "missing executable verifier or builder: $tool"
done
[[ -d $root && ! -L $root ]] || fail 'candidate export is not a directory'
[[ $base_root == /var/lib/rog5-network-root-a660-gmu-resume-entry-v9 ]] ||
	fail 'predecessor export path is not exact'
[[ -d $base_root && ! -L $base_root ]] ||
	fail 'consumed v9 predecessor export is not a directory'
root=$(realpath -e "$root")
base_root=$(realpath -e "$base_root")
[[ $base_root == /var/lib/rog5-network-root-a660-gmu-resume-entry-v9 ]] ||
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
grep -Fq "$archive_hash" "$build_report" ||
	fail 'kernel build report omits accepted module archive'
grep -Fq "$msm_hash" "$build_report" ||
	fail 'kernel build report omits accepted MSM module'

"$predecessor_verifier" "$base_root" >/dev/null
"$consumed_test" >/dev/null

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
expected_baseline=$work/expected-baseline
expected_probe=$work/expected-probe
"$runtime_builder" "$expected_baseline" "$expected_probe" >/dev/null
"$runtime_verifier" "$expected_baseline" "$expected_probe" >/dev/null
check_hash "$expected_baseline" "$baseline_hash" 'generated v10 baseline'
check_hash "$expected_probe" "$probe_hash" 'generated v10 probe'

expected_seal=$work/expected-seal
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
} >"$expected_seal"

seal=$root/etc/rog5/a660-gmu-cx-runtime-pm-v10-export
[[ -f $seal && ! -L $seal ]] || fail 'v10 export seal is absent or linked'
[[ $(stat -c '%u:%g:%a' "$seal") == 0:0:444 ]] ||
	fail 'v10 export seal metadata changed'
cmp "$expected_seal" "$seal" ||
	fail 'v10 export seal is not byte-exact'

baseline=$root/usr/local/sbin/rog5-a660-gmu-cx-runtime-pm-v10-baseline
probe=$root/usr/local/sbin/rog5-a660-gmu-cx-runtime-pm-v10-probe
helper=$root/usr/local/libexec/rog5-a660-gmu-cx-runtime-pm-v10-open
oracle=$root/usr/local/libexec/rog5-a660-gmu-cx-runtime-pm-v10-trace-oracle
for source_target in \
	"$expected_baseline:$baseline:755" \
	"$expected_probe:$probe:755" \
	"$trace_oracle:$oracle:755"
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
sh -n "$oracle"

[[ -f $helper && ! -L $helper ]]
[[ $(stat -c '%u:%g:%a:%s' "$helper") == 0:0:755:896 ]]
check_hash "$helper" "$helper_hash" 'installed v10 one-open helper'
file "$helper" | grep -Fq \
	'ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, stripped'
if readelf -lW "$helper" |
	grep -Eq '(^|[[:space:]])(INTERP|DYNAMIC)([[:space:]]|$)'
then
	fail 'installed one-open helper gained an interpreter or dynamic segment'
fi
[[ $(strings -a "$helper" | grep -Fxc '/dev/dri/renderD128') == 1 ]]
[[ $(strings -a "$helper" | grep -Fxc 'OPEN_ERRNO=117') == 1 ]]
check_hash "$oracle" "$oracle_hash" 'installed v10 trace oracle'

for removed in \
	usr/local/libexec/rog5-a660-gmu-resume-entry-v9-open \
	usr/local/libexec/rog5-a660-gmu-resume-entry-v9-trace-oracle \
	usr/local/sbin/rog5-a660-gmu-resume-entry-v9-baseline \
	usr/local/sbin/rog5-a660-gmu-resume-entry-v9-probe \
	etc/rog5/a660-gmu-resume-entry-v9-export
do
	[[ ! -e $root/$removed ]] ||
		fail "consumed v9 control remains: $removed"
done
[[ $(find "$root/usr/local/libexec" -maxdepth 1 -type f \
	-name 'rog5-a660-*-v*-open' | wc -l) == 1 ]]
[[ $(find "$root/usr/local/libexec" -maxdepth 1 -type f \
	-name 'rog5-a660-*-v*-trace-oracle' | wc -l) == 1 ]]
[[ $(find "$root/usr/local/sbin" -maxdepth 1 -type f \
	-name 'rog5-a660-*-v*-baseline' | wc -l) == 1 ]]
[[ $(find "$root/usr/local/sbin" -maxdepth 1 -type f \
	-name 'rog5-a660-*-v*-probe' | wc -l) == 1 ]]
[[ $(find "$root/etc/rog5" -maxdepth 1 -type f \
	-name 'a660-*-v*-export' | wc -l) == 1 ]]

module_root=$root/usr/lib/modules/$release
msm_module=$module_root/kernel/drivers/gpu/drm/msm/msm.ko
[[ $(find "$module_root" -type f -name '*.ko' | wc -l) == 7 ]]
[[ $(stat -c '%u:%g:%a' "$msm_module") == 0:0:644 ]]
check_hash "$msm_module" "$msm_hash" 'accepted v10 MSM module'
[[ $(modinfo -F name "$msm_module") == msm ]]
[[ $(modinfo -F depends "$msm_module") == \
	'drm_exec,drm_gpuvm,gpu-sched,mdt_loader,ubwc_config' ]]
[[ $(modinfo -F vermagic "$msm_module") == \
	"$release SMP preempt mod_unload aarch64" ]]
for parameter in \
	'gmu_cx_runtime_pm_only:Resume and synchronously roll back exact A660 GMU/CX power once before GX (bool)' \
	'gmu_resume_entry_only:Stop one exact A660 open at GMU resume entry before resource activation (bool)' \
	'ucode_allocation_only:Allocate and roll back exact A660 ucode once before GPU power (bool)' \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)'
do
	[[ $(modinfo -F parm "$msm_module" | grep -Fxc "$parameter") == 1 ]] ||
		fail "MSM diagnostic parameter changed: $parameter"
done
readelf -S "$msm_module" | grep -Eq '[[:space:]][.]BTF[[:space:]]' ||
	fail 'accepted v10 MSM module lacks BTF'
for symbol in \
	msm_a660_gmu_cx_runtime_pm_only_mark_attempt \
	msm_a660_gmu_cx_runtime_pm_only_mark_passed \
	msm_a660_gmu_cx_runtime_pm_only_was_passed \
	adreno_load_gpu adreno_runtime_resume a6xx_gmu_pm_resume a6xx_gmu_resume \
	adreno_rollback_gpu_load_only msm_gem_vma_map msm_gem_vma_unmap \
	msm_gem_vma_close msm_gem_unpin_iova msm_gem_free_object \
	msm_gem_kernel_new msm_gem_get_vaddr msm_gem_put_vaddr \
	msm_gem_kernel_put a6xx_ucode_unload a6xx_hfi_start \
	msm_devfreq_resume a6xx_llc_activate a6xx_gmu_set_initial_freq \
	adreno_hw_init a6xx_hw_init a6xx_zap_shader_init
do
	[[ $(nm -a "$msm_module" | grep -Ec "[[:space:]]$symbol$") == 1 ]] ||
		fail "MSM trace symbol is not unique: $symbol"
done

declare -A unchanged_modules=(
	[kernel/drivers/clk/qcom/gpucc-sm8350.ko]=c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563
	[kernel/drivers/gpu/drm/drm_exec.ko]=71c32424623f826bb6b7f217fb84f624721d90e53eb89cc9d205af66aca9f886
	[kernel/drivers/gpu/drm/drm_gpuvm.ko]=981d3f322e18c3b815de7dcba0f829d2ca36f25c85347bb233e7e1baa73386f8
	[kernel/drivers/gpu/drm/scheduler/gpu-sched.ko]=f53fba10fe10cfeca45abc6d808ca2f5a116832b9595de8f09af66206204b1f4
	[kernel/drivers/soc/qcom/mdt_loader.ko]=001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3
	[kernel/drivers/soc/qcom/ubwc_config.ko]=4220552fbf17562128c956c3cfdbb8abd22e26f2c6a7f22e94422ef34b10e587
)
for relative in "${!unchanged_modules[@]}"; do
	check_hash "$module_root/$relative" "${unchanged_modules[$relative]}" \
		"unchanged module $relative"
done

firmware_root=$root/usr/lib/firmware
check_hash "$firmware_root/qcom/a660_sqe.fw" \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	'SQE firmware'
check_hash "$firmware_root/qcom/a660_gmu.bin" \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	'GMU firmware'
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

for relative in etc/rog5 usr/local/libexec usr/local/sbin; do
	[[ -d $root/$relative && ! -L $root/$relative ]] ||
		fail "diagnostic parent directory changed type: $relative"
	[[ $(stat -c '%u:%g:%a' "$root/$relative") == \
		"$(stat -c '%u:%g:%a' "$base_root/$relative")" ]] ||
		fail "diagnostic parent directory metadata changed: $relative"
done

unchanged_metadata() {
	local tree=$1
	find "$tree" -xdev \
		! -path "$tree/etc/rog5" \
		! -path "$tree/usr/local/libexec" \
		! -path "$tree/usr/local/sbin" \
		! -path "$tree/etc/rog5/a660-gmu-resume-entry-v9-export" \
		! -path "$tree/etc/rog5/a660-gmu-cx-runtime-pm-v10-export" \
		! -path "$tree/usr/local/libexec/rog5-a660-gmu-resume-entry-v9-open" \
		! -path "$tree/usr/local/libexec/rog5-a660-gmu-resume-entry-v9-trace-oracle" \
		! -path "$tree/usr/local/libexec/rog5-a660-gmu-cx-runtime-pm-v10-open" \
		! -path "$tree/usr/local/libexec/rog5-a660-gmu-cx-runtime-pm-v10-trace-oracle" \
		! -path "$tree/usr/local/sbin/rog5-a660-gmu-resume-entry-v9-baseline" \
		! -path "$tree/usr/local/sbin/rog5-a660-gmu-resume-entry-v9-probe" \
		! -path "$tree/usr/local/sbin/rog5-a660-gmu-cx-runtime-pm-v10-baseline" \
		! -path "$tree/usr/local/sbin/rog5-a660-gmu-cx-runtime-pm-v10-probe" \
		! -path "$tree/usr/lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko" \
		-printf '%P|%y|%m|%U|%G|%s|%l\n' | sort
}
unchanged_metadata "$base_root" >"$work/base.metadata"
unchanged_metadata "$root" >"$work/candidate.metadata"
cmp "$work/base.metadata" "$work/candidate.metadata" ||
	fail 'non-diagnostic tree metadata differs from consumed v9'

unchanged_hashes() {
	local tree=$1
	(
		cd "$tree"
		find . -xdev -type f \
			! -path './etc/rog5/a660-gmu-resume-entry-v9-export' \
			! -path './etc/rog5/a660-gmu-cx-runtime-pm-v10-export' \
			! -path './usr/local/libexec/rog5-a660-gmu-resume-entry-v9-open' \
			! -path './usr/local/libexec/rog5-a660-gmu-resume-entry-v9-trace-oracle' \
			! -path './usr/local/libexec/rog5-a660-gmu-cx-runtime-pm-v10-open' \
			! -path './usr/local/libexec/rog5-a660-gmu-cx-runtime-pm-v10-trace-oracle' \
			! -path './usr/local/sbin/rog5-a660-gmu-resume-entry-v9-baseline' \
			! -path './usr/local/sbin/rog5-a660-gmu-resume-entry-v9-probe' \
			! -path './usr/local/sbin/rog5-a660-gmu-cx-runtime-pm-v10-baseline' \
			! -path './usr/local/sbin/rog5-a660-gmu-cx-runtime-pm-v10-probe' \
			! -path "./usr/lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko" \
			-print0 | sort -z | xargs -0 sha256sum
	)
}
unchanged_hashes "$base_root" >"$work/base.sha256"
unchanged_hashes "$root" >"$work/candidate.sha256"
cmp "$work/base.sha256" "$work/candidate.sha256" ||
	fail 'non-diagnostic tree content differs from consumed v9'

"$runtime_verifier" "$baseline" "$probe" >/dev/null

echo 'PASS A660 GMU/CX runtime-PM v10 export modules=7 firmware=2 zap=absent helper=exact oracle=gmu-linked-cx module=v10-msm-only gmu_runtime_pm=1/1 cx_runtime_pm=1/1 gx_runtime_pm=0 clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0 logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v9 root-owned mode 0555'
