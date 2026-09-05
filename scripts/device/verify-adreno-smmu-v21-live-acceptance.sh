#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
report=${1:-$repo/test-results/2026-07-26-network-root-adreno-smmu-v21-live-accepted.md}
marker=${2:-$repo/manifests/acceptance/adreno-smmu-v21-live.accepted}
report_sha=0c7bb22301b8203531a7e8f098e8a719fd7f29d7de2cdf3c63730ecb792e9bbc
marker_sha=c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in cut grep sha256sum stat wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
for input in "$report" "$marker"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "acceptance input is missing, linked, or unreadable: $input"
done
[ "$(sha256sum "$report" | cut -d ' ' -f 1)" = "$report_sha" ] ||
	fail 'v21 live report hash mismatch'
[ "$(sha256sum "$marker" | cut -d ' ' -f 1)" = "$marker_sha" ] ||
	fail 'v21 acceptance marker hash mismatch'
[ "$(wc -l <"$marker")" -eq 24 ] ||
	fail 'v21 acceptance marker line count is not exact'

for contract in \
	'# Network-root Adreno SMMU v21 — live acceptance' \
	'327dfb12142fabb616ffa91fdcf84dc74654e4ba' \
	'37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf' \
	'PASS Adreno-SMMU probe GPUCC=1 SMMU=1 runtime=suspended firmware=0 render=0 storage=0 mounts=0 failed_units=0' \
	'exact_reprobe=1 driver_override=unset-null-representation watchdog=disarmed' \
	'V21 is consumed and must not be rerun.' \
	'consumed and must not be served or retried.' \
	'Nothing was flashed.'
do
	grep -Fq "$contract" "$report" ||
		fail "v21 live report omits: $contract"
done

for contract in \
	'format=rog5-adreno-smmu-live-acceptance-v1' \
	'device=asus-rog-phone5-anakin' \
	'kernel_release=7.1.4-g7a5cef0db479' \
	'candidate_git_checkpoint=327dfb12142fabb616ffa91fdcf84dc74654e4ba' \
	'evidence_git_checkpoint=8b4bad817686a690a5aeb6ca27b043aee119a14c' \
	"live_report_sha256=$report_sha" \
	'temporary_boot_sha256=37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf' \
	'acceptance_scope=GPUCC_CCF_AND_IDLE_ADRENO_SMMU' \
	'gpucc_bind=1' \
	'smmu_device=3da0000.iommu' \
	'smmu_driver=arm-smmu' \
	'smmu_bind=1' \
	'smmu_runtime=suspended' \
	'exact_reprobe=1' \
	'driver_override=unset-null-representation' \
	'firmware=0' \
	'render=0' \
	'storage=0' \
	'mounts=0' \
	'failed_units=0' \
	'fallback=PASSED' \
	'host_cleanup=PASSED' \
	'v21_reuse=FORBIDDEN' \
	'flash=NONE'
do
	[ "$(grep -Fxc "$contract" "$marker")" -eq 1 ] ||
		fail "v21 acceptance marker omits or duplicates: $contract"
done

if grep -Eqi \
	'serial(_number)?=|BEGIN .*PRIVATE KEY|ssh-ed25519|authorization:|bearer[[:space:]]' \
	"$marker"
then
	fail 'v21 acceptance marker contains private material'
fi

echo "PASS exact v21 live acceptance report=$report_sha marker=$marker_sha scope=idle-smmu consumed=yes flash=none"
