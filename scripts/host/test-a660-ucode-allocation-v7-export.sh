#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-a660-ucode-allocation-v7-export.sh
verify=$repo/scripts/host/verify-a660-ucode-allocation-v7-export.sh
serve=$repo/scripts/host/serve-network-root.sh
builder=$repo/scripts/device/build-a660-ucode-allocation-v7-runtime.sh
runtime_verify=$repo/scripts/device/verify-a660-ucode-allocation-v7-runtime-sources.sh
relocation_verify=$repo/scripts/device/verify-a660-ucode-vmap-relocations.sh
consumed_v6_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v6.sh

for script in "$prepare" "$verify" "$serve" "$builder" "$runtime_verify" \
	"$relocation_verify" "$consumed_v6_test"; do
	[[ -x $script ]] || {
		echo "FAIL missing executable ucode-allocation v7 export tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done

for contract in \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v6' \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v7' \
	'cp -a --reflink=always' \
	ad3c4b441db6d2701e0e6bb945c1a4bf52d284e209873cb4b9250014386da680 \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386 \
	01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0 \
	cfdd0837e6da7d06ba74e0557c6abeea396f12f02e345d9ab87ba1a47ade89e6 \
	a17847d18c21d5b2c039df4353a899abce37159ec0009b5afaa0dda6067d146f \
	e9a9bf460b62d91c44fa15b8258ae5a5660ef387846530e8cf93fce67f7f17ea \
	'rog5-a660-ucode-allocation-v7-open' \
	'rog5-a660-ucode-allocation-v7-baseline' \
	'rog5-a660-ucode-allocation-v7-probe' \
	'diagnostic_generation=v7' \
	'base_export=rog5-network-root-a660-ucode-allocation-v6' \
	'predecessor=v6_live_rejected_consumed' \
	'predecessor_consumption_commit=664fd09' \
	'compiler_policy=PINNED_MSM_RELOCATIONS' \
	'size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS' \
	'raw_size_contract=4,4096,43288' \
	'object_size_policy=SOURCE_PINNED_PAGE_ALIGN' \
	'object_size_contract=4096,4096,45056' \
	'trace_policy=PID_FILTERED_LOGICAL_VMAP_BALANCE' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'v6_reuse=FORBIDDEN' \
	'credentials=preserved' \
	'base=consumed-v6' \
	'root-owned mode 0555'
do
	grep -Fq "$contract" "$prepare" "$verify" || {
		echo "FAIL ucode-allocation v7 export path omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$prepare" "$verify"
then
	echo 'FAIL ucode-allocation v7 offline export path controls the phone or storage' >&2
	exit 1
fi

for forbidden in \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v7)' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_NFS' \
	'verify-a660-ucode-allocation-v7-export.sh'
do
	if grep -Fq "$forbidden" "$serve"; then
		echo "FAIL offline-only v7 is server-runnable: $forbidden" >&2
		exit 1
	fi
done

"$consumed_v6_test" >/dev/null

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ $EUID == 0 ]] || {
		echo 'FAIL candidate mutation test requires PolicyKit root' >&2
		exit 1
	}
	[[ -n ${BASE_ROOT:-} ]]
	"$verify" "$CANDIDATE_ROOT" "$BASE_ROOT"

	mutation_parent=$(mktemp -d \
		/var/tmp/rog5-a660-ucode-allocation-v7-mutation.XXXXXX)
	[[ $mutation_parent == \
		/var/tmp/rog5-a660-ucode-allocation-v7-mutation.* ]]
	trap 'rm -rf -- "$mutation_parent"' EXIT HUP INT TERM

	mutate_and_reject() {
		local label=$1 before=$2 after=$3
		local mutation_root=$mutation_parent/$label
		local mutation_seal
		install -d -m 0755 "$mutation_root"
		cp -a --reflink=always "$CANDIDATE_ROOT/." "$mutation_root/"
		mutation_seal=$mutation_root/etc/rog5/a660-ucode-allocation-v7-export
		sed -i "s/$before/$after/" "$mutation_seal"
		chmod 0444 "$mutation_seal"
		chmod 0555 "$mutation_root"
		if "$verify" "$mutation_root" "$BASE_ROOT" >/dev/null 2>&1; then
			echo "FAIL v7 export verifier accepts mutated $label seal" >&2
			exit 1
		fi
	}

	mutate_and_reject predecessor \
		'predecessor=v6_live_rejected_consumed' \
		'predecessor=v6_live_rejected_unconsumed'
	mutate_and_reject raw-size \
		'raw_size_contract=4,4096,43288' \
		'raw_size_contract=4096,4096,45056'
fi

echo 'PASS A660 ucode-allocation v7 export is consumed-v6-derived, exact-delta, compiler/size/logical-vmap/snapshot guarded, credential-preserving, mutation-tested, offline-only, non-runnable, and non-flashing'
