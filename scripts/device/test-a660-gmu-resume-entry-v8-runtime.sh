#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-a660-gmu-resume-entry-v8-runtime.sh
verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-v8-runtime-sources.sh
baseline_patch=$repo/patches/runtime/a660-gmu-resume-entry-v8-baseline.patch
probe_patch=$repo/patches/runtime/a660-gmu-resume-entry-v8-probe.patch

for input in "$builder" "$verifier"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 GMU resume-entry v8 runtime tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done
for input in "$baseline_patch" "$probe_patch"; do
	[ -f "$input" ] && [ ! -L "$input" ] || {
		echo "FAIL missing A660 GMU resume-entry v8 runtime patch: $input" >&2
		exit 1
	}
done

for contract in \
	'build-a660-ucode-allocation-v7-runtime.sh' \
	'verify-a660-gmu-resume-entry-patch.sh' \
	'2026-07-26-a660-ucode-allocation-v7-live-accepted.md' \
	'2026-07-26-a660-gmu-resume-entry-boundary.md' \
	'2026-07-26-a660-gmu-resume-entry-v8-offline.md' \
	ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a \
	a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051 \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	'gmu_resume_entry_only:Stop one exact A660 open at GMU resume entry before resource activation (bool)' \
	'firmware_request_only=N' \
	'ucode_allocation_only=N' \
	'gmu_resume_entry_only=Y' \
	'A660 GMU resume entry reached before resource activation; reject resume' \
	'A660 GMU resume entry passed and rolled back; reject open' \
	'OPEN_ERRNO=117' \
	'adreno_load_gpu' \
	'adreno_runtime_resume' \
	'a6xx_gmu_pm_resume' \
	'a6xx_gmu_resume' \
	'adreno_rollback_gpu_load_only' \
	'a6xx_ucode_unload' \
	'__pm_runtime_resume' \
	'clk_set_rate' \
	'enable_irq' \
	'a6xx_hfi_start' \
	'msm_devfreq_resume' \
	'a6xx_llc_activate' \
	'adreno_hw_init' \
	'a6xx_hw_init' \
	'a6xx_zap_shader_init' \
	'qcom_scm_pas_auth_and_reset' \
	'qcom_scm_set_gpu_smmu_aperture' \
	'logical_gets=4' \
	'logical_puts=4' \
	'gem_snapshot=equal' \
	'inner_runtime_pm=0' \
	'clocks=0' \
	'irq=0' \
	'hfi=0' \
	'hw_init=0' \
	'scm=0' \
	'v8 retained accepted v7 allocation and rollback state'
do
	grep -Fq "$contract" "$builder" "$verifier" "$baseline_patch" \
		"$probe_patch" || {
		echo "FAIL A660 GMU resume-entry v8 runtime path omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$builder" "$verifier"
then
	echo 'FAIL A660 GMU resume-entry v8 runtime tooling controls a device or storage' >&2
	exit 1
fi

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
install -d "$stage/a" "$stage/b" "$stage/mutations"
"$builder" "$stage/a/baseline" "$stage/a/probe" >/dev/null
"$builder" "$stage/b/baseline" "$stage/b/probe" >/dev/null
cmp "$stage/a/baseline" "$stage/b/baseline"
cmp "$stage/a/probe" "$stage/b/probe"
"$verifier" "$stage/a/baseline" "$stage/a/probe" >/dev/null
"$verifier" "$stage/b/baseline" "$stage/b/probe" >/dev/null

set +e
"$builder" "$stage/a/baseline" "$stage/a/probe" >/dev/null 2>&1
existing_output=$?
"$builder" "$stage/missing/baseline" "$stage/missing/probe" \
	>/dev/null 2>&1
missing_parent=$?
set -e
[ "$existing_output" -ne 0 ]
[ "$missing_parent" -ne 0 ]

expect_rejected() {
	name=$1
	mutated_baseline=$2
	mutated_probe=$3
	if ALLOW_UNPINNED_A660_GMU_ENTRY_V8_RUNTIME=1 \
		"$verifier" "$mutated_baseline" "$mutated_probe" \
		>"$stage/mutations/$name.log" 2>&1
	then
		echo "FAIL v8 runtime verifier accepts mutation: $name" >&2
		exit 1
	fi
}

mutation=0
mutate_probe() {
	name=$1
	expression=$2
	mutation=$((mutation + 1))
	output=$stage/mutations/probe.$mutation
	sed "$expression" "$stage/a/probe" >"$output"
	expect_rejected "$name" "$stage/a/baseline" "$output"
}

mutate_baseline() {
	name=$1
	expression=$2
	mutation=$((mutation + 1))
	output=$stage/mutations/baseline.$mutation
	sed "$expression" "$stage/a/baseline" >"$output"
	expect_rejected "$name" "$output" "$stage/a/probe"
}

mutate_probe enable-old-ucode-mode \
	's/gmu_resume_entry_only=1/ucode_allocation_only=1/'
mutate_probe skip-gmu-resume \
	"/require_event_count rog5_gmu_v8_resume 1/d"
mutate_probe allow-clock-rate \
	"s/rog5_gmu_v8_clk_rate 0/rog5_gmu_v8_clk_rate 1/"
mutate_probe allow-irq \
	"s/rog5_gmu_v8_enable_irq 0/rog5_gmu_v8_enable_irq 1/"
mutate_probe missing-snapshot \
	'/cmp "$state_dir\/gem.before" "$state_dir\/gem.after"/d'
mutate_probe successful-open \
	's/OPEN_ERRNO=117/OPEN_OK/'
mutate_baseline wrong-predecessor \
	's/predecessor=v7_live_accepted_consumed/predecessor=v7_live_pending/'
mutate_baseline writable-entry-mode \
	's/gmu_entry_parameter_mode=0400/gmu_entry_parameter_mode=0600/'

echo 'PASS A660 GMU resume-entry v8 runtime is reproducibly generated and rejects mode, resume, clock, IRQ, snapshot, errno, predecessor, and writable-parameter mutations'
