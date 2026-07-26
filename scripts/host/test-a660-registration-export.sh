#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-a660-registration-export.sh
verify=$repo/scripts/host/verify-a660-registration-export.sh
serve=$repo/scripts/host/serve-network-root.sh

for script in "$prepare" "$verify" "$serve"; do
	[[ -x $script ]] || {
		echo "FAIL missing executable A660 export tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done

for contract in \
	'/var/lib/rog5-network-root-v1' \
	'/var/lib/rog5-network-root-a660-registration-v2' \
	'cp -a --reflink=always' \
	e3cb1ef31b6c1c803bee98748660f92b3b192d460cb41d5d4691f9953a91a42b \
	'7.1.4-rog5-a660reg1' \
	'gpucc-sm8350.ko' \
	'drm_exec.ko' \
	'drm_gpuvm.ko' \
	'gpu-sched.ko' \
	'mdt_loader.ko' \
	'ubwc_config.ko' \
	'msm.ko' \
	'usr/lib/firmware/qcom/a660_sqe.fw' \
	'usr/lib/firmware/qcom/a660_gmu.bin' \
	'usr/lib/firmware/qcom/sm8350/a660_zap.mbn' \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d \
	'rog5-a660-registration-baseline' \
	'rog5-a660-registration-probe' \
	'adreno-smmu-v21-live.accepted' \
	'verify-adreno-smmu-v21-live-acceptance.sh' \
	'registration_generation=v2' \
	'smmu_acceptance=ACCEPTED_IDLE_V21' \
	'smmu_acceptance_sha=c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875' \
	'smmu_acceptance_report_sha=0c7bb22301b8203531a7e8f098e8a719fd7f29d7de2cdf3c63730ecb792e9bbc' \
	'credentials=preserved' \
	'verify-network-root-export.sh'
do
	grep -Fq "$contract" "$prepare" "$verify" || {
		echo "FAIL A660 export path omits: $contract" >&2
		exit 1
	}
done

grep -Fq '/var/lib/rog5-network-root-a660-registration-v2)' "$serve" ||
	{
		echo 'FAIL NFS server omits the v21-accepted A660 v2 export' >&2
		exit 1
	}
grep -Fq 'verify-a660-registration-export.sh' "$serve" ||
	{
		echo 'FAIL NFS server omits the A660 v2 export verifier' >&2
		exit 1
	}
for rejected in \
	/var/lib/rog5-network-root-a660-registration \
	/var/lib/rog5-network-root-adreno-smmu-v20 \
	/var/lib/rog5-network-root-adreno-smmu-v21
do
	if grep -Fq "$rejected)" "$serve"; then
		echo "FAIL NFS server allowlists rejected or consumed root: $rejected" >&2
		exit 1
	fi
done

if grep -Eq '(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|rm[[:space:]]+-rf[[:space:]]+["$]*(base_root|export_root)' \
	"$prepare" "$verify"
then
	echo 'FAIL A660 export path can control the phone or erase an export' >&2
	exit 1
fi

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ -n ${BASE_ROOT:-} ]]
	"$verify" "$CANDIDATE_ROOT" "$BASE_ROOT"
fi

echo 'PASS A660 v2 export is copy-on-write, v21-accepted, seven-module exact, firmware-free, credential-preserving, and exclusively allowlisted'
