#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
runtime_test=$repo/scripts/device/test-a660-gmu-resume-entry-v8-runtime.sh
gate=$repo/scripts/device/run-network-root-a660-gmu-resume-entry-v8-gate.sh
gate_test=$repo/scripts/device/test-run-network-root-a660-gmu-resume-entry-v8-gate.sh
prepare=$repo/scripts/host/prepare-a660-gmu-resume-entry-v8-export.sh
verify=$repo/scripts/host/verify-a660-gmu-resume-entry-v8-export.sh
export_test=$repo/scripts/host/test-a660-gmu-resume-entry-v8-export.sh
live_runner=$repo/scripts/host/run-a660-gmu-resume-entry-v8-live-gate.sh
live_runner_test=$repo/scripts/host/test-run-a660-gmu-resume-entry-v8-live-gate.sh
consumed_v8_test=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v8.sh
predecessor_verify=$repo/scripts/host/verify-a660-ucode-allocation-v7-export.sh
predecessor_consumed=$repo/scripts/host/test-consume-a660-ucode-allocation-v7.sh
serve=$repo/scripts/host/serve-network-root.sh
hold_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-hold.md
go_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-go.md
rejected_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md

for input in "$runtime_test" "$gate" "$gate_test" "$prepare" "$verify" \
	"$export_test" "$live_runner" "$live_runner_test" "$predecessor_verify" \
	"$consumed_v8_test" "$predecessor_consumed" "$serve"
do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 GMU resume-entry v8 root tool: $input" >&2
		exit 1
	}
done

for input in "$hold_report" "$go_report" "$rejected_report"; do
	[ -f "$input" ] && [ ! -L "$input" ] || {
		echo "FAIL missing immutable A660 GMU resume-entry v8 input: $input" >&2
		exit 1
	}
done
[ "$(sha256sum "$go_report" | cut -d ' ' -f 1)" = \
	432cdfa196f5a418060adba0e902108bc1eeaf8dd466d3e5b0b73a29221bf242 ]
[ "$(sha256sum "$rejected_report" | cut -d ' ' -f 1)" = \
	fe5a6130cce3063ef6a0b1093d492d2a35763781f23af029c2959548cb092a9c ]

for input in "$runtime_test" "$gate" "$gate_test" "$consumed_v8_test"; do
	sh -n "$input"
done
for input in "$prepare" "$verify" "$export_test" "$predecessor_verify" \
	"$live_runner" "$live_runner_test" "$serve"
do
	bash -n "$input"
done

for contract in \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v7' \
	'/var/lib/rog5-network-root-a660-gmu-resume-entry-v8' \
	'cp -a --reflink=always' \
	'diagnostic_generation=v8' \
	'base_export=rog5-network-root-a660-ucode-allocation-v7' \
	'predecessor=v7_live_accepted_consumed' \
	'predecessor_consumption_commit=12ad39c' \
	ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a \
	c679ff6cbed6aefb28b7537cd30c561948e4d4672cd9320a8e70fd3d79b4f046 \
	38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7 \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23 \
	832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255 \
	41c06dcd895fcc873638ddf40dce0b0d5dd5bbf9e148f5d3abd5521b072c320d \
	6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c \
	a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051 \
	'rog5-a660-gmu-resume-entry-v8-open' \
	'rog5-a660-gmu-resume-entry-v8-baseline' \
	'rog5-a660-gmu-resume-entry-v8-probe' \
	'compiler_policy=PINNED_V8_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_GMU_ENTRY_AND_LOGICAL_VMAP' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'gmu_entry_parameter_mode=0400' \
	'v7_reuse=FORBIDDEN' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_GATE' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_REBOOT' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_LIVE_GATE' \
	'HostKeyAlias=rog5-network-root' \
	'umask 077' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8=1 "$probe"' \
	'gmu_resume_entry_only=Y' \
	'firmware_request_only=N' \
	'ucode_allocation_only=N' \
	'logical_gets=4' \
	'logical_puts=4' \
	'gem_snapshot=equal' \
	'outer_runtime_pm=1' \
	'inner_runtime_pm=0' \
	'clocks=0' \
	'irq=0' \
	'hfi=0' \
	'hw_init=0' \
	'scm=0' \
	'credentials=preserved' \
	'base=consumed-v7' \
	'root-owned mode 0555'
do
	if ! grep -Fq "$contract" "$runtime_test" "$gate" "$gate_test" \
		"$prepare" "$verify" "$export_test" "$live_runner" \
		"$live_runner_test" "$consumed_v8_test"
	then
		echo "FAIL A660 GMU resume-entry v8 root path omits: $contract" >&2
		exit 1
	fi
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$prepare" "$verify"
then
	echo 'FAIL A660 GMU resume-entry v8 offline root path controls a device or storage' >&2
	exit 1
fi

for status_file in \
	"$repo/README.md" \
	"$repo/ROADMAP.md" \
	"$repo/docs/builds-and-artifacts.md" \
	"$repo/docs/current-state.md" \
	"$repo/docs/kernel-port.md" \
	"$repo/docs/network-root.md" \
	"$repo/docs/port-status.md" \
	"$repo/docs/test-plan.md"
do
	if [ ! -f "$status_file" ] || [ -L "$status_file" ] ||
		! grep -Fq \
			'2026-07-26-a660-gmu-resume-entry-v8-prelive-hold.md' \
			"$status_file" ||
		! grep -Fq \
			'2026-07-26-a660-gmu-resume-entry-v8-prelive-go.md' \
			"$status_file" ||
		! grep -Fq \
			'2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md' \
			"$status_file"
	then
		echo "FAIL project status omits A660 v8 report chain: $status_file" >&2
		exit 1
	fi
done

"$runtime_test"
"$gate_test"
"$export_test"
"$live_runner_test"
"$consumed_v8_test"
"$predecessor_consumed"

echo 'PASS A660 GMU resume-entry v8 root is consumed-v7-derived, exact-delta, mutation-tested, host-runner-tested, storage-free, permanently consumed, server-non-runnable, and live-safe-rejection-pinned'
