#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-a660-firmware-request-only-export.sh
verify=$repo/scripts/host/verify-a660-firmware-request-only-export.sh
serve=$repo/scripts/host/serve-network-root.sh

for script in "$prepare" "$verify" "$serve"; do
	[[ -x $script ]] || {
		echo "FAIL missing executable request-only export tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done

for contract in \
	'/var/lib/rog5-network-root-a660-registration-v3' \
	'/var/lib/rog5-network-root-a660-firmware-request-only-v4' \
	'cp -a --reflink=always' \
	04149f41648f12925a6f04261eed96bfecdd6174a10462c82c36213fef0d1bc9 \
	eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082 \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d \
	'usr/lib/firmware/qcom/a660_sqe.fw' \
	'usr/lib/firmware/qcom/a660_gmu.bin' \
	'usr/lib/firmware/qcom/sm8350/a660_zap.mbn' \
	'rog5-a660-firmware-request-only-open' \
	'rog5-a660-firmware-request-only-baseline' \
	'rog5-a660-firmware-request-only-probe' \
	'a660-registration-v3-live.accepted' \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f \
	2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79 \
	'firmware_request_generation=v4' \
	'firmware_policy=SQE_GMU_ONLY_ZAP_ABSENT' \
	'open_policy=EXACTLY_ONE_EUCLEAN' \
	'! -path "$tree/etc/rog5"' \
	'! -path "$tree/usr/lib/firmware/qcom"' \
	'! -path "$tree/usr/local/sbin"' \
	'! -path "$tree/usr/local"' \
	'verify-a660-registration-v3-live-acceptance.sh' \
	'verify-a660-registration-export.sh' \
	'credentials=preserved' \
	'base=registration-v3'
do
	grep -Fq "$contract" "$prepare" "$verify" "$serve" || {
		echo "FAIL request-only export path omits: $contract" >&2
		exit 1
	}
done

for consumed in \
	/var/lib/rog5-network-root-a660-registration \
	/var/lib/rog5-network-root-a660-registration-v2 \
	/var/lib/rog5-network-root-a660-registration-v3 \
	/var/lib/rog5-network-root-a660-firmware-request-only-v4 \
	/var/lib/rog5-network-root-adreno-smmu-v20 \
	/var/lib/rog5-network-root-adreno-smmu-v21
do
	if grep -Fq "$consumed)" "$serve"; then
		echo "FAIL NFS server allowlists consumed root: $consumed" >&2
		exit 1
	fi
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|rm[[:space:]]+-rf[[:space:]]+["$]*(base_root|export_root)' \
	"$prepare" "$verify"
then
	echo 'FAIL request-only export path controls phone or erases an export' >&2
	exit 1
fi

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ -n ${BASE_ROOT:-} ]]
	"$verify" "$CANDIDATE_ROOT" "$BASE_ROOT"
fi

echo 'PASS A660 request-only v4 export is exact-base, seven-module, SQE/GMU-only, ZAP-absent, helper-pinned, credential-preserving, and consumed'
