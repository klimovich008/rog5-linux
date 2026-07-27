#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
runtime_test=$repo/scripts/device/test-a660-gmu-resume-entry-v9-runtime.sh
prepare=$repo/scripts/host/prepare-a660-gmu-resume-entry-v9-export.sh
verify=$repo/scripts/host/verify-a660-gmu-resume-entry-v9-export.sh
gate=$repo/scripts/device/run-network-root-a660-gmu-resume-entry-v9-gate.sh
gate_test=$repo/scripts/device/test-run-network-root-a660-gmu-resume-entry-v9-gate.sh
predecessor_verify=$repo/scripts/host/verify-a660-gmu-resume-entry-v8-export.sh
predecessor_consumed=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v8.sh
predecessor_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md
runtime_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-v9-runtime-offline.md

for input in "$runtime_test" "$prepare" "$verify" "$gate" "$gate_test" \
	"$predecessor_verify" "$predecessor_consumed"
do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 GMU resume-entry v9 root tool: $input" >&2
		exit 1
	}
done

for input in "$predecessor_report" "$runtime_report"; do
	[ -f "$input" ] && [ ! -L "$input" ] || {
		echo "FAIL missing immutable A660 GMU resume-entry v9 input: $input" >&2
		exit 1
	}
done
[ "$(sha256sum "$predecessor_report" | cut -d ' ' -f 1)" = \
	fe5a6130cce3063ef6a0b1093d492d2a35763781f23af029c2959548cb092a9c ]
[ "$(sha256sum "$runtime_report" | cut -d ' ' -f 1)" = \
	a9b99930799902cabf6c65bd877a21588b63ccb6b617d1ac526b9e0d159bf60d ]

for input in "$runtime_test" "$gate" "$gate_test" "$predecessor_consumed"; do
	sh -n "$input"
done
for input in "$prepare" "$verify" "$predecessor_verify"; do
	bash -n "$input"
done

for contract in \
	'/var/lib/rog5-network-root-a660-gmu-resume-entry-v8' \
	'/var/lib/rog5-network-root-a660-gmu-resume-entry-v9' \
	'cp -a --reflink=always' \
	'diagnostic_generation=v9' \
	'base_export=rog5-network-root-a660-gmu-resume-entry-v8' \
	'predecessor=v8_live_rejected_consumed' \
	'predecessor_consumption_commit=ff1250f' \
	fe5a6130cce3063ef6a0b1093d492d2a35763781f23af029c2959548cb092a9c \
	a6c14600ed17a52641f8700393d095e7cd86f2aa0d01c1f1f6bf649e283f2923 \
	38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7 \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	48325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223 \
	337535cda800963bc1887203d1f60d9340b8fc5e9956f652a75bf26ada5d4ecc \
	078bb4cb2e6e1edac0182a22023121f2f6fbef2ec02715b7f3f6a5fe9338f387 \
	'rog5-a660-gmu-resume-entry-v9-open' \
	'rog5-a660-gmu-resume-entry-v9-trace-oracle' \
	'rog5-a660-gmu-resume-entry-v9-baseline' \
	'rog5-a660-gmu-resume-entry-v9-probe' \
	'compiler_policy=PINNED_V8_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_SIGNED32_GPU_DEVICE_AND_LOGICAL_VMAP' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'gmu_entry_parameter_mode=0400' \
	'v7_reuse=FORBIDDEN' \
	'v8_reuse=FORBIDDEN' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_GATE' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_REBOOT' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9=1 "$probe"' \
	'gpu_runtime_pm=1 generic_runtime_pm=device-classified' \
	'inner_runtime_pm=0 clocks=0 irq=0 hfi=0' \
	'logical_gets=4 logical_puts=4 gem_snapshot=equal' \
	'credentials=preserved' \
	'base=consumed-v8' \
	'root-owned mode 0555'
do
	if ! grep -Fq "$contract" "$runtime_test" "$prepare" "$verify" \
		"$gate" "$gate_test"
	then
		echo "FAIL A660 GMU resume-entry v9 root path omits: $contract" >&2
		exit 1
	fi
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$prepare" "$verify"
then
	echo 'FAIL A660 GMU resume-entry v9 offline root path controls a device or storage' >&2
	exit 1
fi

"$runtime_test"
"$gate_test"
"$predecessor_consumed"

echo 'PASS A660 GMU resume-entry v9 root is consumed-v8-derived, exact-delta, signed-device-oracle guarded, runtime-mutation-tested, storage-free, target-gated, and HOLD'
