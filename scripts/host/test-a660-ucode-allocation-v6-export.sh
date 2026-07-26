#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-a660-ucode-allocation-v6-export.sh
verify=$repo/scripts/host/verify-a660-ucode-allocation-v6-export.sh
serve=$repo/scripts/host/serve-network-root.sh
builder=$repo/scripts/device/build-a660-ucode-allocation-v6-runtime.sh
runtime_verify=$repo/scripts/device/verify-a660-ucode-allocation-v6-runtime-sources.sh
relocation_verify=$repo/scripts/device/verify-a660-ucode-vmap-relocations.sh
consumed_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v5.sh
live_runner=$repo/scripts/host/run-a660-ucode-allocation-v6-live-gate.sh
live_runner_test=$repo/scripts/host/test-run-a660-ucode-allocation-v6-live-gate.sh

for script in "$prepare" "$verify" "$serve" "$builder" "$runtime_verify" \
	"$relocation_verify" "$consumed_test" "$live_runner" \
	"$live_runner_test"; do
	[[ -x $script ]] || {
		echo "FAIL missing executable ucode-allocation v6 export tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done

for contract in \
	'/var/lib/rog5-network-root-a660-registration-v3' \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v6' \
	'cp -a --reflink=always' \
	ad3c4b441db6d2701e0e6bb945c1a4bf52d284e209873cb4b9250014386da680 \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d \
	0c65c98cc03a49d9e5c8a15b391dbe2b6014b5e791a8659c06cd7c2d0bf52fb9 \
	56d63a17b6c89454691dbd74539c299d99e99b341831358d6f673f128a3181ae \
	5ad24829bd347fcc22239d761029f3c0f8064efa1b16e9f01b6cf745902df854 \
	b90e33524da2558659a733c48d5670d2136208a9186d5abb3ecd79f1e28f2725 \
	'rog5-a660-ucode-allocation-v6-open' \
	'rog5-a660-ucode-allocation-v6-baseline' \
	'rog5-a660-ucode-allocation-v6-probe' \
	'a660-registration-v3-live.accepted' \
	'diagnostic_generation=v6' \
	'predecessor=v5_live_rejected_consumed' \
	'compiler_policy=PINNED_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_LOGICAL_VMAP_BALANCE' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'v5_reuse=FORBIDDEN' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6_LIVE_GATE' \
	'HostKeyAlias=rog5-network-root' \
	'umask 077' \
	'verify-a660-ucode-vmap-relocations.sh' \
	'verify-a660-registration-export.sh' \
	'credentials=preserved' \
	'base=registration-v3' \
	'root-owned mode 0555'
do
	grep -Fq "$contract" "$prepare" "$verify" "$live_runner" \
		"$live_runner_test" || {
		echo "FAIL ucode-allocation v6 export path omits: $contract" >&2
		exit 1
	}
done

if grep -Fq '/var/lib/rog5-network-root-a660-ucode-allocation-v6)' \
	"$serve"; then
	echo 'FAIL pre-live HOLD root is runnable through bounded NFS server' >&2
	exit 1
fi
if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|rm[[:space:]]+-rf[[:space:]]+["$]*(base_root|export_root)' \
	"$prepare" "$verify"
then
	echo 'FAIL ucode-allocation v6 export path controls the phone or storage' >&2
	exit 1
fi

"$consumed_test" >/dev/null
"$live_runner_test" >/dev/null

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ -n ${BASE_ROOT:-} ]]
	"$verify" "$CANDIDATE_ROOT" "$BASE_ROOT"

	mutation_parent=$(mktemp -d \
		/var/tmp/rog5-a660-ucode-allocation-v6-mutation.XXXXXX)
	[[ $mutation_parent == \
		/var/tmp/rog5-a660-ucode-allocation-v6-mutation.* ]]
	trap 'rm -rf -- "$mutation_parent"' EXIT
	mutation_root=$mutation_parent/root
	install -d -m 0755 "$mutation_root"
	cp -a --reflink=always "$CANDIDATE_ROOT/." "$mutation_root/"
	sed -i \
		's/predecessor=v5_live_rejected_consumed/predecessor=v5_live_rejected_unconsumed/' \
		"$mutation_root/etc/rog5/a660-ucode-allocation-v6-export"
	chmod 0444 "$mutation_root/etc/rog5/a660-ucode-allocation-v6-export"
	chmod 0555 "$mutation_root"
	if "$verify" "$mutation_root" "$BASE_ROOT" >/dev/null 2>&1; then
		echo 'FAIL v6 export verifier accepts a mutated predecessor seal' >&2
		exit 1
	fi
fi

echo 'PASS A660 ucode-allocation v6 export is exact-base, compiler-pinned, logical-vmap/snapshot guarded, credential-preserving, consumed-v5-derived, mutation-tested, host-runner-tested, non-runnable, and non-flashing'
