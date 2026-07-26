#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
runtime_builder=$repo/scripts/device/build-a660-ucode-allocation-v6-runtime.sh
runtime_verifier=$repo/scripts/device/verify-a660-ucode-allocation-v6-runtime-sources.sh
runtime_test=$repo/scripts/device/test-a660-ucode-allocation-v6-runtime.sh
probe_test=$repo/scripts/device/test-probe-network-root-a660-ucode-allocation-v6.sh
gate=$repo/scripts/device/run-network-root-a660-ucode-allocation-v6-gate.sh
gate_test=$repo/scripts/device/test-run-network-root-a660-ucode-allocation-v6-gate.sh
prepare=$repo/scripts/host/prepare-a660-ucode-allocation-v6-export.sh
verify_export=$repo/scripts/host/verify-a660-ucode-allocation-v6-export.sh
export_test=$repo/scripts/host/test-a660-ucode-allocation-v6-export.sh
relocation_verifier=$repo/scripts/device/verify-a660-ucode-vmap-relocations.sh
relocation_test=$repo/scripts/device/test-a660-ucode-vmap-relocations.sh
consumed_v5_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v5.sh
consumed_v6_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v6.sh
live_runner=$repo/scripts/host/run-a660-ucode-allocation-v6-live-gate.sh
live_runner_test=$repo/scripts/host/test-run-a660-ucode-allocation-v6-live-gate.sh
serve=$repo/scripts/host/serve-network-root.sh
rejection=$repo/test-results/2026-07-26-a660-ucode-allocation-v5-live-rejected.md
report=$repo/test-results/2026-07-26-a660-ucode-allocation-v6-offline.md
hold_report=$repo/test-results/2026-07-26-a660-ucode-allocation-v6-prelive-hold.md
go_report=$repo/test-results/2026-07-26-a660-ucode-allocation-v6-prelive-go.md
live_report=$repo/test-results/2026-07-26-a660-ucode-allocation-v6-live-rejected.md

for input in "$runtime_builder" "$runtime_verifier" "$runtime_test" \
	"$probe_test" "$gate" "$gate_test" "$prepare" "$verify_export" \
	"$export_test" "$relocation_verifier" "$relocation_test" \
	"$consumed_v5_test" "$consumed_v6_test" "$live_runner" \
	"$live_runner_test" "$serve"
do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 ucode-allocation v6 tool: $input" >&2
		exit 1
	}
done
[ -f "$rejection" ] && [ ! -L "$rejection" ] || {
	echo 'FAIL missing immutable v5 live rejection report' >&2
	exit 1
}
[ -f "$report" ] && [ ! -L "$report" ] || {
	echo 'FAIL missing A660 ucode-allocation v6 offline report' >&2
	exit 1
}
[ -f "$hold_report" ] && [ ! -L "$hold_report" ] || {
	echo 'FAIL missing A660 ucode-allocation v6 pre-live HOLD report' >&2
	exit 1
}
[ -f "$go_report" ] && [ ! -L "$go_report" ] || {
	echo 'FAIL missing A660 ucode-allocation v6 pre-live GO report' >&2
	exit 1
}
[ -f "$live_report" ] && [ ! -L "$live_report" ] || {
	echo 'FAIL missing A660 ucode-allocation v6 live rejection report' >&2
	exit 1
}
[ "$(sha256sum "$live_report" | cut -d ' ' -f 1)" = \
	cfdd0837e6da7d06ba74e0557c6abeea396f12f02e345d9ab87ba1a47ade89e6 ] || {
	echo 'FAIL A660 ucode-allocation v6 live rejection report hash changed' >&2
	exit 1
}

for input in "$runtime_builder" "$runtime_verifier" "$runtime_test" \
	"$probe_test" "$gate" "$gate_test"
do
	sh -n "$input"
done
for input in "$prepare" "$verify_export" "$export_test" \
	"$relocation_verifier" "$live_runner" "$live_runner_test" \
	"$serve"
do
	bash -n "$input"
done

for contract in \
	'/var/lib/rog5-network-root-a660-registration-v3' \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v6' \
	'diagnostic_generation=v6' \
	'predecessor=v5_live_rejected_consumed' \
	0c65c98cc03a49d9e5c8a15b391dbe2b6014b5e791a8659c06cd7c2d0bf52fb9 \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	'compiler_policy=PINNED_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_LOGICAL_VMAP_BALANCE' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'v5_reuse=FORBIDDEN' \
	'msm_gem_kernel_new' \
	'msm_gem_kernel_put' \
	'kernel_news=3' \
	'kernel_puts=2' \
	'wrapper_gets=1' \
	'wrapper_puts=2' \
	'logical_gets=4' \
	'logical_puts=4' \
	'gem_snapshot=equal' \
	'raw kernel-new entry sizes `4`, `4096`, and `43288`' \
	'page-rounded object sizes' \
	'V6 must never be re-enabled or retried.' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6_LIVE_GATE' \
	'HostKeyAlias=rog5-network-root' \
	'umask 077' \
	'power=0' \
	'hfi=0' \
	'scm=0' \
	'storage=0' \
	'watchdog=disarmed' \
	'root-owned mode 0555'
do
	if ! grep -Fq "$contract" "$runtime_builder" "$runtime_verifier" \
		"$runtime_test" "$probe_test" "$gate" "$gate_test" "$prepare" \
		"$verify_export" "$export_test" "$relocation_verifier" \
		"$live_runner" "$live_runner_test" \
		"$rejection" "$report" "$hold_report" "$go_report" "$live_report"
	then
		echo "FAIL A660 ucode-allocation v6 path omits: $contract" >&2
		exit 1
	fi
done

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
		! grep -Fq '2026-07-26-a660-ucode-allocation-v6-offline.md' \
			"$status_file" ||
		! grep -Fq '2026-07-26-a660-ucode-allocation-v6-prelive-hold.md' \
			"$status_file" ||
		! grep -Fq '2026-07-26-a660-ucode-allocation-v6-prelive-go.md' \
			"$status_file" ||
		! grep -Fq '2026-07-26-a660-ucode-allocation-v6-live-rejected.md' \
			"$status_file"
	then
		echo "FAIL project status omits A660 v6 report chain: $status_file" >&2
		exit 1
	fi
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$runtime_builder" "$runtime_verifier" "$prepare" "$verify_export"
then
	echo 'FAIL A660 ucode-allocation v6 offline path controls the phone or storage' >&2
	exit 1
fi

"$runtime_test"
"$probe_test"
"$gate_test"
"$export_test"
"$live_runner_test"
"$relocation_test"
"$consumed_v5_test"
"$consumed_v6_test"

echo 'PASS A660 ucode-allocation v6 is compiler-pinned, logical-vmap-balanced, snapshot-guarded, live-rejected, consumed, and non-runnable'
