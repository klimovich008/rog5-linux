#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-adreno-smmu-export.sh
verify=$repo/scripts/host/verify-adreno-smmu-export.sh
serve=$repo/scripts/host/serve-network-root.sh

for script in "$prepare" "$verify" "$serve"; do
	[[ -x $script ]] || {
		echo "FAIL missing executable Adreno-SMMU export tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done

for contract in \
	'/var/lib/rog5-network-root-v1' \
	'/var/lib/rog5-network-root-adreno-smmu-v20' \
	'cp -a --reflink=always' \
	'7.1.4-g7a5cef0db479' \
	'usr/lib/firmware/qcom/a660_sqe.fw' \
	'usr/lib/firmware/qcom/a660_gmu.bin' \
	'usr/lib/firmware/qcom/sm8350/a660_zap.mbn' \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d \
	37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf \
	9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a \
	'diagnostic_generation=v20' \
	'source_commit=d9ac316489f4258d389d6298659d5e9c22183400' \
	'source_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	'probe_timeout_seconds=90' \
	'transition_timeout_seconds=150' \
	'smmu_reprobe=EXACT_PLATFORM_DEVICE_ONCE' \
	'smmu_acceptance=NOT_ACCEPTED' \
	'module_files=' \
	'credentials=preserved' \
	'base=unchanged' \
	'verify-network-root-export.sh'
do
	grep -Fq "$contract" "$prepare" "$verify" || {
		echo "FAIL Adreno-SMMU export path omits: $contract" >&2
		exit 1
	}
done

grep -Fq \
	'/var/lib/rog5-network-root-adreno-smmu-v20)' "$serve" ||
	{
		echo 'FAIL NFS server omits the exact v20 export allowlist' >&2
		exit 1
	}
grep -Fq 'verify-adreno-smmu-export.sh' "$serve" ||
	{
		echo 'FAIL NFS server omits the v20 export verifier' >&2
		exit 1
	}
if grep -Fq '/var/lib/rog5-network-root-adreno-smmu-v19)' "$serve"; then
	echo 'FAIL NFS server still allowlists consumed v19' >&2
	exit 1
fi

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|rm[[:space:]]+-rf[[:space:]]+["$]*(base_root|export_root)' \
	"$prepare" "$verify"
then
	echo 'FAIL Adreno-SMMU export path can control the phone or erase an export' >&2
	exit 1
fi

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ -n ${BASE_ROOT:-} ]]
	"$verify" "$CANDIDATE_ROOT" "$BASE_ROOT"
fi

echo 'PASS v20 export is copy-on-write, firmware-free, module-complete, credential-preserving, and exclusively server-allowlisted'
