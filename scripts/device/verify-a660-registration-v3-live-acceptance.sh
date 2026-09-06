#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
report=${1:-$repo/test-results/2026-07-26-a660-registration-v3-live-accepted.md}
marker=${2:-$repo/manifests/acceptance/a660-registration-v3-live.accepted}
report_sha=2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79
marker_sha=8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in cut grep sha256sum wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
for input in "$report" "$marker"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "acceptance input is missing, linked, or unreadable: $input"
done
[ "$(sha256sum "$report" | cut -d ' ' -f 1)" = "$report_sha" ] ||
	fail 'A660 v3 live report hash mismatch'
[ "$(sha256sum "$marker" | cut -d ' ' -f 1)" = "$marker_sha" ] ||
	fail 'A660 v3 acceptance marker hash mismatch'
[ "$(wc -l <"$marker")" -eq 36 ] ||
	fail 'A660 v3 acceptance marker line count is not exact'

for contract in \
	'# A660 registration v3 — live acceptance' \
	'8b633fba764093071a829946858da02445606d14' \
	'c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c' \
	'PASS A660 registration GPUCC=1 SMMU=1 GPU=1 GMU=1 iommu=2 render=1 drm_fds=0 firmware=0 storage=0 mounts=0 failed_units=0' \
	'exact_reprobe=1 driver_override=unset-null-representation watchdog=disarmed' \
	'Registration v3 is consumed and must not be rerun.' \
	'V3 is consumed and must not' \
	'be served or retried.' \
	'Nothing was flashed.'
do
	grep -Fq "$contract" "$report" ||
		fail "A660 v3 live report omits: $contract"
done

for contract in \
	'format=rog5-a660-registration-live-acceptance-v1' \
	'device=asus-rog-phone5-anakin' \
	'kernel_release=7.1.4-rog5-a660reg1' \
	'candidate_git_checkpoint=8b633fba764093071a829946858da02445606d14' \
	'evidence_git_checkpoint=5a8d18f6c4a85c7828d3a9f87fe6d5a5d75b703d' \
	"live_report_sha256=$report_sha" \
	'temporary_boot_sha256=c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c' \
	'acceptance_scope=GPUCC_SMMU_A660_GMU_REGISTRATION_UNOPENED_RENDER' \
	'module_count=7' \
	'gpucc_bind=1' \
	'smmu_device=3da0000.iommu' \
	'smmu_driver=arm-smmu' \
	'smmu_bind=1' \
	'smmu_runtime=suspended' \
	'exact_reprobe=1' \
	'driver_override=unset-null-representation' \
	'a660_device=3d00000.gpu' \
	'a660_driver=adreno' \
	'a660_bind=1' \
	'gmu_device=3d6a000.gmu' \
	'gmu_separate_driver=0' \
	'gmu_runtime=suspended' \
	'iommu_attachments=2' \
	'render_nodes=1' \
	'drm_fds=0' \
	'display_connectors=0' \
	'settle_seconds=30' \
	'firmware=0' \
	'storage=0' \
	'mounts=0' \
	'failed_units=0' \
	'thermal_max_mC=38100' \
	'fallback=PASSED' \
	'host_cleanup=PASSED' \
	'v3_reuse=FORBIDDEN' \
	'flash=NONE'
do
	[ "$(grep -Fxc "$contract" "$marker")" -eq 1 ] ||
		fail "A660 v3 acceptance marker omits or duplicates: $contract"
done

if grep -Eqi \
	'serial(_number)?=|BEGIN .*PRIVATE KEY|ssh-ed25519|authorization:|bearer[[:space:]]' \
	"$marker"
then
	fail 'A660 v3 acceptance marker contains private material'
fi

echo "PASS exact A660 v3 live acceptance report=$report_sha marker=$marker_sha scope=registration-unopened consumed=yes firmware=0 flash=none"
