#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-a660-gmu-resume-entry-v8-export.sh
verify=$repo/scripts/host/verify-a660-gmu-resume-entry-v8-export.sh
serve=$repo/scripts/host/serve-network-root.sh
builder=$repo/scripts/device/build-a660-gmu-resume-entry-v8-runtime.sh
runtime_verify=$repo/scripts/device/verify-a660-gmu-resume-entry-v8-runtime-sources.sh
relocation_verify=$repo/scripts/device/verify-a660-gmu-resume-entry-vmap-relocations.sh
consumed_v7_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v7.sh
gate=$repo/scripts/device/run-network-root-a660-gmu-resume-entry-v8-gate.sh
gate_test=$repo/scripts/device/test-run-network-root-a660-gmu-resume-entry-v8-gate.sh
live_runner=$repo/scripts/host/run-a660-gmu-resume-entry-v8-live-gate.sh
live_runner_test=$repo/scripts/host/test-run-a660-gmu-resume-entry-v8-live-gate.sh

for script in "$prepare" "$verify" "$serve" "$builder" "$runtime_verify" \
	"$relocation_verify" "$consumed_v7_test" "$gate" "$gate_test"; do
	[[ -x $script ]] || {
		echo "FAIL missing executable GMU resume-entry v8 export tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done

for contract in \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v7' \
	'/var/lib/rog5-network-root-a660-gmu-resume-entry-v8' \
	'cp -a --reflink=always' \
	38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7 \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23 \
	832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255 \
	ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a \
	c679ff6cbed6aefb28b7537cd30c561948e4d4672cd9320a8e70fd3d79b4f046 \
	41c06dcd895fcc873638ddf40dce0b0d5dd5bbf9e148f5d3abd5521b072c320d \
	6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c \
	a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051 \
	'rog5-a660-gmu-resume-entry-v8-open' \
	'rog5-a660-gmu-resume-entry-v8-baseline' \
	'rog5-a660-gmu-resume-entry-v8-probe' \
	'diagnostic_generation=v8' \
	'base_export=rog5-network-root-a660-ucode-allocation-v7' \
	'predecessor=v7_live_accepted_consumed' \
	'predecessor_consumption_commit=12ad39c' \
	'compiler_policy=PINNED_V8_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_GMU_ENTRY_AND_LOGICAL_VMAP' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'gmu_entry_parameter_mode=0400' \
	'v7_reuse=FORBIDDEN' \
	'gmu_resume_entry_only' \
	'firmware_request_only' \
	'ucode_allocation_only' \
	'credentials=preserved' \
	'base=consumed-v7' \
	'root-owned mode 0555'
do
	grep -Fq "$contract" "$prepare" "$verify" "$gate" "$gate_test" || {
		echo "FAIL GMU resume-entry v8 export path omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$prepare" "$verify"
then
	echo 'FAIL GMU resume-entry v8 offline export path controls the phone or storage' >&2
	exit 1
fi

for forbidden in \
	'/var/lib/rog5-network-root-a660-gmu-resume-entry-v8)' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_NFS' \
	'verify-a660-gmu-resume-entry-v8-export.sh'
do
	if grep -Fq "$forbidden" "$serve"; then
		echo "FAIL v8 export is prematurely NFS-runnable: $forbidden" >&2
		exit 1
	fi
done
[[ ! -e $live_runner && ! -e $live_runner_test ]] || {
	echo 'FAIL v8 live runner exists before export acceptance' >&2
	exit 1
}

"$consumed_v7_test" >/dev/null
"$gate_test" >/dev/null

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ $EUID == 0 ]] || {
		echo 'FAIL candidate mutation test requires PolicyKit root' >&2
		exit 1
	}
	[[ -n ${BASE_ROOT:-} ]]
	"$verify" "$CANDIDATE_ROOT" "$BASE_ROOT"

	mutation_parent=$(mktemp -d \
		/var/tmp/rog5-a660-gmu-resume-entry-v8-mutation.XXXXXX)
	[[ $mutation_parent == \
		/var/tmp/rog5-a660-gmu-resume-entry-v8-mutation.* ]]
	trap 'rm -rf -- "$mutation_parent"' EXIT HUP INT TERM

	copy_candidate() {
		local label=$1
		local mutation_root=$mutation_parent/$label
		install -d -m 0755 "$mutation_root"
		cp -a --reflink=always "$CANDIDATE_ROOT/." "$mutation_root/"
		printf '%s\n' "$mutation_root"
	}

	mutate_seal_and_reject() {
		local label=$1 before=$2 after=$3
		local mutation_root mutation_seal
		mutation_root=$(copy_candidate "$label")
		mutation_seal=$mutation_root/etc/rog5/a660-gmu-resume-entry-v8-export
		sed -i "s/$before/$after/" "$mutation_seal"
		grep -Fq "$after" "$mutation_seal"
		chmod 0444 "$mutation_seal"
		chmod 0555 "$mutation_root"
		if "$verify" "$mutation_root" "$BASE_ROOT" >/dev/null 2>&1; then
			echo "FAIL v8 export verifier accepts mutated $label seal" >&2
			exit 1
		fi
	}

	mutate_seal_and_reject predecessor \
		'predecessor=v7_live_accepted_consumed' \
		'predecessor=v7_live_accepted_pending'
	mutate_seal_and_reject parameter-mode \
		'gmu_entry_parameter_mode=0400' \
		'gmu_entry_parameter_mode=0600'
	mutate_seal_and_reject build-report \
		'kernel_build_report_sha256=6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c' \
		'kernel_build_report_sha256=0c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c'
	mutate_seal_and_reject trace-policy \
		'trace_policy=PID_FILTERED_GMU_ENTRY_AND_LOGICAL_VMAP' \
		'trace_policy=UNFILTERED_GMU_ENTRY'

	module_root=$(copy_candidate predecessor-msm)
	install -m0644 \
		"$BASE_ROOT/usr/lib/modules/7.1.4-rog5-a660reg1/kernel/drivers/gpu/drm/msm/msm.ko" \
		"$module_root/usr/lib/modules/7.1.4-rog5-a660reg1/kernel/drivers/gpu/drm/msm/msm.ko"
	chmod 0555 "$module_root"
	if "$verify" "$module_root" "$BASE_ROOT" >/dev/null 2>&1; then
		echo 'FAIL v8 export verifier accepts predecessor MSM module' >&2
		exit 1
	fi
fi

echo 'PASS A660 GMU resume-entry v8 export is consumed-v7-derived, exact-delta, compiler/entry/logical-vmap/snapshot guarded, credential-preserving, mutation-tested, non-runnable, and non-flashing'
