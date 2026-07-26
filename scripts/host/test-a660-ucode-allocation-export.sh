#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-a660-ucode-allocation-export.sh
verify=$repo/scripts/host/verify-a660-ucode-allocation-export.sh
serve=$repo/scripts/host/serve-network-root.sh
live_runner=$repo/scripts/host/run-a660-ucode-allocation-live-gate.sh
live_runner_test=$repo/scripts/host/test-run-a660-ucode-allocation-live-gate.sh
live_window_test=$repo/scripts/host/test-serve-a660-ucode-allocation-live-window.sh

for script in "$prepare" "$verify" "$serve" "$live_runner" \
	"$live_runner_test" "$live_window_test"; do
	[[ -x $script ]] || {
		echo "FAIL missing executable ucode-allocation export tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done

for contract in \
	'/var/lib/rog5-network-root-a660-registration-v3' \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v5' \
	'cp -a --reflink=always' \
	ad3c4b441db6d2701e0e6bb945c1a4bf52d284e209873cb4b9250014386da680 \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d \
	'usr/lib/firmware/qcom/a660_sqe.fw' \
	'usr/lib/firmware/qcom/a660_gmu.bin' \
	'usr/lib/firmware/qcom/sm8350/a660_zap.mbn' \
	'rog5-a660-ucode-allocation-open' \
	'rog5-a660-ucode-allocation-baseline' \
	'rog5-a660-ucode-allocation-probe' \
	'a660-registration-v3-live.accepted' \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f \
	2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79 \
	'diagnostic_generation=v5' \
	'firmware_policy=SQE_GMU_ONLY_ZAP_ABSENT' \
	'open_policy=EXACTLY_ONE_EUCLEAN' \
	'trace_policy=PID_FILTERED_EXACT_BALANCE' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'v4_reuse=FORBIDDEN' \
	'! -path "$tree/etc/rog5"' \
	'! -path "$tree/usr/lib/firmware/qcom"' \
	'! -path "$tree/usr/local/sbin"' \
	'! -path "$tree/usr/local"' \
	'verify-a660-registration-v3-live-acceptance.sh' \
	'verify-a660-registration-export.sh' \
	'credentials=preserved' \
	'base=registration-v3' \
	'root-owned mode 0555'
do
	grep -Fq "$contract" "$prepare" "$verify" || {
		echo "FAIL ucode-allocation export path omits: $contract" >&2
		exit 1
	}
done

"$live_runner_test" >/dev/null
"$live_window_test" >/dev/null

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|rm[[:space:]]+-rf[[:space:]]+["$]*(base_root|export_root)' \
	"$prepare" "$verify"
then
	echo 'FAIL ucode-allocation export path controls phone or erases an export' >&2
	exit 1
fi

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ -n ${BASE_ROOT:-} ]]
	"$verify" "$CANDIDATE_ROOT" "$BASE_ROOT"
fi

echo 'PASS A660 ucode-allocation v5 export contract is exact-base, seven-module, SQE/GMU-only, ZAP-absent, trace-backed, credential-preserving, host-runner-tested, explicit-window-only, and non-flashing'
