#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
report=${1:-$repo/test-results/2026-07-26-a660-firmware-request-only-v4-live-accepted.md}
marker=${2:-$repo/manifests/acceptance/a660-firmware-request-only-v4-live.accepted}
report_sha=f5e1226923f82528e8cc2ad2727d38834c64761d7691559e295da43fafcfbd8c
marker_sha=912846d98ef6ee9fb3c0fa9f0b455c49d47a2f43ff72e2ba1d14c1c284cbfe32

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
	fail 'A660 request-only v4 live report hash mismatch'
[ "$(sha256sum "$marker" | cut -d ' ' -f 1)" = "$marker_sha" ] ||
	fail 'A660 request-only v4 acceptance marker hash mismatch'
[ "$(wc -l <"$marker")" -eq 51 ] ||
	fail 'A660 request-only v4 acceptance marker line count is not exact'

for contract in \
	'# A660 SQE/GMU request-only v4 — live acceptance' \
	'2cb3d85439b1bc72f96b8d401207c53d9d77cf1e' \
	'68607c37dfa9558c8d0d77477c0ab973bf623da3' \
	'c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c' \
	'PASS A660 firmware-request-only open_invocations=1 open_errno=117 firmware_requests=2 success_markers=1 zap=absent ucode=0 power=0 hfi=0 scm=0 drm_fds=0 storage=0 mounts=0 failed_units=0 iommu=2 render=1' \
	'exact_reprobe=1 driver_override=unset-null-representation watchdog=disarmed' \
	'PASS compound A660 firmware-request-only gate open_errno=117 transition_watchdog=armed reboot=requested' \
	'PASS fallback health thermal_zones=70 thermal_max_mC=38500 pstore_records=0 project_modules=0' \
	'PASS privileged host cleanup NFS=0 exports=0 listeners=0 mounts=0 firewall-temp=0 nonlocal=0 services=restored etab_mode=600' \
	'V4 is consumed and must never be served or retried.' \
	'Nothing was flashed.'
do
	grep -Fq "$contract" "$report" ||
		fail "A660 request-only v4 live report omits: $contract"
done

for contract in \
	'format=rog5-a660-firmware-request-only-live-acceptance-v1' \
	'device=asus-rog-phone5-anakin' \
	'kernel_release=7.1.4-rog5-a660reg1' \
	'candidate_git_checkpoint=2cb3d85439b1bc72f96b8d401207c53d9d77cf1e' \
	'evidence_git_checkpoint=9c140753e1d188de141be90c253d5d42af21a3ce' \
	"live_report_sha256=$report_sha" \
	'temporary_boot_sha256=c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c' \
	'export_seal_sha256=2b615c6acb96b76384e741798e67e86322fce228cab1f78e01494227509f0dc8' \
	'msm_module_sha256=eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082' \
	'helper_sha256=d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae' \
	'sqe_firmware_sha256=d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76' \
	'gmu_firmware_sha256=8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7' \
	'zap=absent' \
	'acceptance_scope=A660_SQE_GMU_REQUEST_ONLY_EUCLEAN_PRE_UCODE_POWER_HFI_ZAP' \
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
	'open_invocations=1' \
	'open_errno=117' \
	'firmware_requests=2' \
	'success_markers=1' \
	'drm_fds=0' \
	'display_connectors=0' \
	'ucode=0' \
	'power=0' \
	'hfi=0' \
	'scm=0' \
	'storage=0' \
	'mounts=0' \
	'failed_units=0' \
	'settle_seconds=20' \
	'thermal_max_mC=38500' \
	'fallback=PASSED' \
	'fallback_pstore_records=0' \
	'fallback_project_modules=0' \
	'host_cleanup=PASSED' \
	'v4_reuse=FORBIDDEN' \
	'flash=NONE'
do
	[ "$(grep -Fxc "$contract" "$marker")" -eq 1 ] ||
		fail "A660 request-only v4 marker omits or duplicates: $contract"
done

if grep -Eqi \
	'serial(_number)?=|BEGIN .*PRIVATE KEY|ssh-ed25519|authorization:|bearer[[:space:]]' \
	"$marker"
then
	fail 'A660 request-only v4 acceptance marker contains private material'
fi

echo "PASS exact A660 request-only v4 live acceptance report=$report_sha marker=$marker_sha scope=two-firmware-euclean-pre-hardware consumed=yes flash=none"
