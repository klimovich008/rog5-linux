#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
runtime_test=$repo/scripts/device/test-a660-gmu-cx-runtime-pm-v10-runtime.sh
prepare=$repo/scripts/host/prepare-a660-gmu-cx-runtime-pm-v10-export.sh
verify=$repo/scripts/host/verify-a660-gmu-cx-runtime-pm-v10-export.sh
gate=$repo/scripts/device/run-network-root-a660-gmu-cx-runtime-pm-v10-gate.sh
gate_test=$repo/scripts/device/test-run-network-root-a660-gmu-cx-runtime-pm-v10-gate.sh
runner=$repo/scripts/host/run-a660-gmu-cx-runtime-pm-v10-live-gate.sh
runner_test=$repo/scripts/host/test-run-a660-gmu-cx-runtime-pm-v10-live-gate.sh
predecessor_verify=$repo/scripts/host/verify-a660-gmu-resume-entry-v9-export.sh
predecessor_consumed=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v9.sh
predecessor_report=$repo/test-results/2026-07-27-a660-gmu-resume-entry-v9-live-accepted.md
build_report=$repo/test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md
runtime_report=$repo/test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-runtime-offline.md

for input in "$runtime_test" "$prepare" "$verify" "$gate" "$gate_test" \
	"$runner" "$runner_test" "$predecessor_verify" "$predecessor_consumed"
do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 GMU/CX v10 root tool: $input" >&2
		exit 1
	}
done
for input in "$predecessor_report" "$build_report" "$runtime_report"; do
	[ -f "$input" ] && [ ! -L "$input" ] || {
		echo "FAIL missing immutable A660 GMU/CX v10 input: $input" >&2
		exit 1
	}
done
[ "$(sha256sum "$predecessor_report" | cut -d ' ' -f 1)" = \
	57af6b4d0ddf6faaa708e7b409197dcf7aa8fcdb52a5a9612b59094aebc9dd2c ]
[ "$(sha256sum "$build_report" | cut -d ' ' -f 1)" = \
	9ae66678340437c4a38b2d6ee390cc375e661548be97cb108bb8f891a418dee4 ]
[ "$(sha256sum "$runtime_report" | cut -d ' ' -f 1)" = \
	d74f277348d4d8537b7edbeee7b5aaaeab8e794a7ad63c2645cc393d0af4d959 ]
grep -Fq 'permanently consumed v9 runtime controls' "$runtime_report"

for input in "$runtime_test" "$gate" "$gate_test"; do
	sh -n "$input"
done
for input in "$prepare" "$verify" "$runner" "$runner_test" \
	"$predecessor_verify"; do
	bash -n "$input"
done

for contract in \
	'/var/lib/rog5-network-root-a660-gmu-resume-entry-v9' \
	'/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10' \
	'cp -a --reflink=always' \
	'diagnostic_generation=v10' \
	'base_export=rog5-network-root-a660-gmu-resume-entry-v9' \
	'predecessor=v9_live_accepted_consumed' \
	'predecessor_consumption_commit=3d708cd' \
	57af6b4d0ddf6faaa708e7b409197dcf7aa8fcdb52a5a9612b59094aebc9dd2c \
	9ae66678340437c4a38b2d6ee390cc375e661548be97cb108bb8f891a418dee4 \
	d74f277348d4d8537b7edbeee7b5aaaeab8e794a7ad63c2645cc393d0af4d959 \
	87e5c3bae7d5034b64aea7212be8372506bf8b28cbdca7fb1b79bb20db50b9d0 \
	c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d \
	33ccadc6ae1e5f6f12ed83de0ddc192d30d204e229ec1b97aa813e1d0ac9c7e6 \
	a68960aa1ac84dbc6f3b469d8369d1c66dcd343f9adfc0a9f4e9909e9ee4245d \
	f28b1c28ec43da21747ce7e17247d33074bfa01f7c9c6171e80806a98eb70b36 \
	'rog5-a660-gmu-cx-runtime-pm-v10-open' \
	'rog5-a660-gmu-cx-runtime-pm-v10-trace-oracle' \
	'rog5-a660-gmu-cx-runtime-pm-v10-baseline' \
	'rog5-a660-gmu-cx-runtime-pm-v10-probe' \
	'kernel/module delta=v10-msm-only' \
	'trace_policy=PID_FILTERED_S32_EXACT_GMU_LINKED_CX_RPM_AND_LOGICAL_VMAP' \
	'gmu_cx_runtime_pm_parameter_mode=0400' \
	'v9_reuse=FORBIDDEN' \
	'ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_GATE' \
	'ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_REBOOT' \
	'ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10=1 "$probe"' \
	'gmu_runtime_pm=1/1 cx_runtime_pm=1/1' \
	'gx_runtime_pm=0' \
	'clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0' \
	'gem_snapshot=equal' \
	'credentials=preserved' \
	'base=consumed-v9' \
	'root-owned mode 0555'
do
	if ! grep -Fq "$contract" "$runtime_test" "$prepare" "$verify" \
		"$gate" "$gate_test" "$runner" "$runner_test"
	then
		echo "FAIL A660 GMU/CX v10 root path omits: $contract" >&2
		exit 1
	fi
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$prepare" "$verify"
then
	echo 'FAIL A660 GMU/CX v10 offline root path controls a device or storage' >&2
	exit 1
fi

"$runtime_test" >/dev/null
"$gate_test" >/dev/null
"$runner_test" >/dev/null
"$predecessor_consumed" >/dev/null

echo 'PASS A660 GMU/CX runtime-PM v10 root is consumed-v9-derived, exact-delta, runtime-mutation-tested, storage-free, target-gated, one-shot, and server-inactive'
