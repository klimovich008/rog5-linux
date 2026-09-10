#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-a660-gmu-resume-entry-v8-export.sh ROOT BASE_ROOT}
base_root=${2:-/var/lib/rog5-network-root-a660-ucode-allocation-v7}
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

for command in cmp cut file find grep mktemp modinfo nm readelf realpath rm \
	sha256sum sort stat strings wc xargs; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
for tool in "$predecessor_verifier" "$consumed_test" \
	"$relocation_verifier" "$runtime_builder" "$runtime_verifier"; do
	[[ -x $tool ]] || fail "missing executable verifier or builder: $tool"
done
[[ -d $root && ! -L $root ]] || fail 'candidate export is not a directory'
[[ $base_root == /var/lib/rog5-network-root-a660-ucode-allocation-v7 ]] ||
	fail 'predecessor export path is not exact'
[[ -d $base_root && ! -L $base_root ]] ||
	fail 'consumed v7 predecessor export is not a directory'
root=$(realpath -e "$root")
base_root=$(realpath -e "$base_root")
[[ $base_root == /var/lib/rog5-network-root-a660-ucode-allocation-v7 ]] ||
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
check_hash "$base_root/etc/rog5/a660-ucode-allocation-v7-export" \
	"$predecessor_seal_sha" 'v7 predecessor seal'
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
check_hash "$expected_baseline" "$baseline_hash" 'generated v8 baseline'
check_hash "$expected_probe" "$probe_hash" 'generated v8 probe'

expected_seal=$work/expected-seal
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
} >"$expected_seal"

seal=$root/etc/rog5/a660-gmu-resume-entry-v8-export
[[ -f $seal && ! -L $seal ]] || fail 'v8 export seal is absent or linked'
[[ $(stat -c '%u:%g:%a' "$seal") == 0:0:444 ]] ||
	fail 'v8 export seal metadata changed'
cmp "$expected_seal" "$seal" ||
	fail 'v8 export seal is not byte-exact'

baseline=$root/usr/local/sbin/rog5-a660-gmu-resume-entry-v8-baseline
probe=$root/usr/local/sbin/rog5-a660-gmu-resume-entry-v8-probe
helper=$root/usr/local/libexec/rog5-a660-gmu-resume-entry-v8-open
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
check_hash "$helper" "$helper_hash" 'installed v8 one-open helper'
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
	usr/local/libexec/rog5-a660-ucode-allocation-v7-open \
	usr/local/sbin/rog5-a660-ucode-allocation-v7-baseline \
	usr/local/sbin/rog5-a660-ucode-allocation-v7-probe \
	etc/rog5/a660-ucode-allocation-v7-export
do
	[[ ! -e $root/$removed ]] ||
		fail "consumed v7 control remains: $removed"
done
[[ $(find "$root/usr/local/libexec" -maxdepth 1 -type f \
	-name 'rog5-a660-*-v*-open' | wc -l) == 1 ]]
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
check_hash "$msm_module" "$msm_hash" 'accepted v8 MSM module'
[[ $(modinfo -F name "$msm_module") == msm ]]
[[ $(modinfo -F depends "$msm_module") == \
	'drm_exec,drm_gpuvm,gpu-sched,mdt_loader,ubwc_config' ]]
[[ $(modinfo -F vermagic "$msm_module") == \
	"$release SMP preempt mod_unload aarch64" ]]
for parameter in \
	'gmu_resume_entry_only:Stop one exact A660 open at GMU resume entry before resource activation (bool)' \
	'ucode_allocation_only:Allocate and roll back exact A660 ucode once before GPU power (bool)' \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)'
do
	[[ $(modinfo -F parm "$msm_module" | grep -Fxc "$parameter") == 1 ]] ||
		fail "MSM diagnostic parameter changed: $parameter"
done
"$relocation_verifier" "$msm_module" >/dev/null
for symbol in \
	adreno_load_gpu adreno_runtime_resume a6xx_gmu_pm_resume a6xx_gmu_resume \
	msm_a660_gmu_resume_entry_only_mark_hit adreno_rollback_gpu_load_only \
	msm_gem_vma_map msm_gem_vma_unmap msm_gem_vma_close \
	msm_gem_unpin_iova msm_gem_free_object msm_gem_kernel_new \
	msm_gem_get_vaddr msm_gem_put_vaddr msm_gem_kernel_put \
	a6xx_ucode_unload a6xx_hfi_start msm_devfreq_resume a6xx_llc_activate \
	a6xx_gmu_set_initial_freq adreno_hw_init a6xx_hw_init \
	a6xx_zap_shader_init qcom_scm_is_available qcom_scm_gpu_init_regs \
	qcom_scm_pas_auth_and_reset qcom_scm_set_gpu_smmu_aperture
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
		! -path "$tree/usr/lib/modules/$release/kernel/drivers/gpu/drm/msm" \
		! -path "$tree/etc/rog5/a660-ucode-allocation-v7-export" \
		! -path "$tree/etc/rog5/a660-gmu-resume-entry-v8-export" \
		! -path "$tree/usr/local/libexec/rog5-a660-ucode-allocation-v7-open" \
		! -path "$tree/usr/local/libexec/rog5-a660-gmu-resume-entry-v8-open" \
		! -path "$tree/usr/local/sbin/rog5-a660-ucode-allocation-v7-baseline" \
		! -path "$tree/usr/local/sbin/rog5-a660-ucode-allocation-v7-probe" \
		! -path "$tree/usr/local/sbin/rog5-a660-gmu-resume-entry-v8-baseline" \
		! -path "$tree/usr/local/sbin/rog5-a660-gmu-resume-entry-v8-probe" \
		! -path "$tree/usr/lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko" \
		-printf '%P|%y|%m|%U|%G|%s|%l\n' | sort
}
unchanged_metadata "$base_root" >"$work/base.metadata"
unchanged_metadata "$root" >"$work/candidate.metadata"
cmp "$work/base.metadata" "$work/candidate.metadata" ||
	fail 'non-diagnostic tree metadata differs from consumed v7'

unchanged_hashes() {
	local tree=$1
	(
		cd "$tree"
		find . -xdev -type f \
			! -path './etc/rog5/a660-ucode-allocation-v7-export' \
			! -path './etc/rog5/a660-gmu-resume-entry-v8-export' \
			! -path './usr/local/libexec/rog5-a660-ucode-allocation-v7-open' \
			! -path './usr/local/libexec/rog5-a660-gmu-resume-entry-v8-open' \
			! -path './usr/local/sbin/rog5-a660-ucode-allocation-v7-baseline' \
			! -path './usr/local/sbin/rog5-a660-ucode-allocation-v7-probe' \
			! -path './usr/local/sbin/rog5-a660-gmu-resume-entry-v8-baseline' \
			! -path './usr/local/sbin/rog5-a660-gmu-resume-entry-v8-probe' \
			! -path "./usr/lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko" \
			-print0 | sort -z | xargs -0 sha256sum
	)
}
unchanged_hashes "$base_root" >"$work/base.sha256"
unchanged_hashes "$root" >"$work/candidate.sha256"
cmp "$work/base.sha256" "$work/candidate.sha256" ||
	fail 'non-diagnostic tree content differs from consumed v7'

echo 'PASS A660 GMU resume-entry v8 export modules=7 firmware=2 zap=absent helper=exact compiler=v8-relocations gmu_entry=EUCLEAN logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v7 root-owned mode 0555'
