#!/bin/sh
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
consumed_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v5.sh
serve=$repo/scripts/host/serve-network-root.sh
rejection=$repo/test-results/2026-07-26-a660-ucode-allocation-v5-live-rejected.md

for input in "$runtime_builder" "$runtime_verifier" "$runtime_test" \
	"$probe_test" "$gate" "$gate_test" "$prepare" "$verify_export" \
	"$export_test" "$relocation_verifier" "$relocation_test" \
	"$consumed_test" "$serve"
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

for input in "$runtime_builder" "$runtime_verifier" "$runtime_test" \
	"$probe_test" "$gate" "$gate_test"
do
	sh -n "$input"
done
for input in "$prepare" "$verify_export" "$export_test" \
	"$relocation_verifier" "$serve"
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
		"$rejection"
	then
		echo "FAIL A660 ucode-allocation v6 path omits: $contract" >&2
		exit 1
	fi
done

if grep -Fq '/var/lib/rog5-network-root-a660-ucode-allocation-v6)' "$serve"; then
	echo 'FAIL pre-live HOLD root is runnable through bounded NFS server' >&2
	exit 1
fi
[ ! -e "$repo/scripts/host/run-a660-ucode-allocation-v6-live-gate.sh" ] ||
	{
		echo 'FAIL pre-live HOLD unexpectedly has a v6 live runner' >&2
		exit 1
	}

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
"$relocation_test"
"$consumed_test"

echo 'PASS A660 ucode-allocation v6 is compiler-pinned, logical-vmap-balanced, snapshot-guarded, storage-isolated, non-runnable, and pre-live HOLD'
