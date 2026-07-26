#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
helper_source=$repo/tools/diagnostics/a660-firmware-request-only-open.c
helper_builder=$repo/scripts/device/build-a660-firmware-request-only-open-helper.sh
helper_verifier=$repo/scripts/device/verify-a660-firmware-request-only-open-helper.sh
helper_test=$repo/scripts/device/test-a660-firmware-request-only-open-helper.sh
baseline=$repo/scripts/device/check-network-root-a660-ucode-allocation-baseline.sh
probe=$repo/scripts/device/probe-network-root-a660-ucode-allocation.sh
runtime_verifier=$repo/scripts/device/verify-a660-ucode-allocation-runtime-sources.sh
probe_test=$repo/scripts/device/test-probe-network-root-a660-ucode-allocation.sh
gate=$repo/scripts/device/run-network-root-a660-ucode-allocation-gate.sh
gate_test=$repo/scripts/device/test-run-network-root-a660-ucode-allocation-gate.sh
prepare=$repo/scripts/host/prepare-a660-ucode-allocation-export.sh
verify_export=$repo/scripts/host/verify-a660-ucode-allocation-export.sh
export_test=$repo/scripts/host/test-a660-ucode-allocation-export.sh
live_runner=$repo/scripts/host/run-a660-ucode-allocation-live-gate.sh
live_runner_test=$repo/scripts/host/test-run-a660-ucode-allocation-live-gate.sh
live_window_test=$repo/scripts/host/test-serve-a660-ucode-allocation-live-window.sh
serve=$repo/scripts/host/serve-network-root.sh
build_test=$repo/scripts/device/test-mainline-a660-ucode-allocation-build-contract.sh
package_test=$repo/scripts/device/test-network-root-a660-registration-bundle.sh
report=$repo/test-results/2026-07-26-a660-ucode-allocation-v5-offline.md
hold_report=$repo/test-results/2026-07-26-a660-ucode-allocation-v5-prelive-hold.md
go_report=$repo/test-results/2026-07-26-a660-ucode-allocation-v5-prelive-go.md

[ -f "$helper_source" ] && [ ! -L "$helper_source" ] || {
	echo 'FAIL missing accepted A660 one-open helper source' >&2
	exit 1
}
for document in "$report" "$hold_report" "$go_report"; do
	[ -f "$document" ] && [ ! -L "$document" ] || {
		echo "FAIL missing A660 ucode-allocation v5 report: $document" >&2
		exit 1
	}
done

for input in "$baseline" "$probe" "$runtime_verifier" "$probe_test" "$gate" \
	"$gate_test" "$prepare" "$verify_export" "$export_test" "$helper_builder" \
	"$helper_verifier" "$helper_test" "$build_test" "$package_test" \
	"$live_runner" "$live_runner_test" "$live_window_test"
do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 ucode-allocation v5 tool: $input" >&2
		exit 1
	}
done

for input in "$baseline" "$probe" "$runtime_verifier" "$probe_test" "$gate" \
	"$gate_test" "$helper_builder" "$helper_verifier" "$helper_test" \
	"$build_test" "$package_test"
do
	sh -n "$input"
done
for input in "$prepare" "$verify_export" "$export_test" "$live_runner" \
	"$live_runner_test" "$live_window_test" "$serve"
do
	bash -n "$input"
done

for contract in \
	'/var/lib/rog5-network-root-a660-registration-v3' \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v5' \
	'manifests/acceptance/a660-registration-v3-live.accepted' \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f \
	2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79 \
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
	'/dev/dri/renderD128' \
	'OPEN_ERRNO=117' \
	'separate_gpu_kms=1' \
	'ucode_allocation_only=1' \
	'firmware_request_only=N' \
	'A660 ucode-allocation-only passed and rolled back; reject open' \
	'A660 ucode-allocation-only failed:' \
	'CONFIG_KPROBE_EVENTS=y' \
	'CONFIG_KALLSYMS_ALL=y' \
	'CONFIG_DEBUG_FS=y' \
	'set_event_pid' \
	'msm_gem_vma_map' \
	'msm_gem_vma_unmap' \
	'msm_gem_vma_close' \
	'msm_gem_free_object' \
	'msm_gem_get_vaddr' \
	'msm_gem_put_vaddr' \
	'request_firmware_direct' \
	'release_firmware' \
	'maps=3' \
	'unmaps=3' \
	'closes=3' \
	'gem_frees=3' \
	'cpu_vmaps=4' \
	'cpu_vunmaps=4' \
	'firmware_requests=2' \
	'firmware_releases=2' \
	'gem_snapshot=equal' \
	'drm_fds=0' \
	'power=0' \
	'hfi=0' \
	'scm=0' \
	'zap=absent' \
	'storage=0' \
	'watchdog=disarmed' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_GATE=1' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_REBOOT=1' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_LIVE_GATE=1' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_NFS' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'HostKeyAlias=rog5-network-root' \
	'StrictHostKeyChecking=yes' \
	'ConnectionAttempts=1' \
	'umask 077' \
	c6df42496b2fa6920187773bc7a97a8dc8bc5a7afb518f98ff1265a585580225 \
	d8e08191c50b6f5c925c82d03f837c9757e7e8aa0a9323fd63a8bb9871688cf7 \
	306474f71518ba1ff59373b9a13368b5a7f2a49753c6abba94feba3a05bbc3dc \
	0c5f1fb69ee377a42146be97a9c3f0a44338231fdc2c19b8383ccf170ad6f4c5 \
	'Decision: **HOLD.' \
	'Decision: **GO for exactly one attended RAM-only ucode-allocation cycle' \
	'The phone was not contacted.' \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c \
	'verify-a660-registration-v3-live-acceptance.sh' \
	'verify-mainline-a660-ucode-allocation-build.sh' \
	'credentials=preserved' \
	'root-owned mode 0555' \
	'v4_reuse=FORBIDDEN'
do
	if ! grep -Fq "$contract" "$helper_source" "$helper_builder" \
		"$helper_verifier" "$baseline" "$probe" "$runtime_verifier" \
		"$probe_test" "$gate" "$gate_test" "$prepare" "$verify_export" \
		"$export_test" "$live_runner" "$live_runner_test" \
		"$live_window_test" "$serve" "$build_test" "$package_test" \
		"$report" "$hold_report" "$go_report"
	then
		echo "FAIL A660 ucode-allocation v5 path omits: $contract" >&2
		exit 1
	fi
done

for document in README.md ROADMAP.md docs/current-state.md \
	docs/kernel-port.md docs/network-root.md docs/test-plan.md \
	docs/builds-and-artifacts.md docs/port-status.md
do
	grep -Fq 'ucode-allocation-v5-prelive-go.md' "$repo/$document" || {
		echo "FAIL project status omits ucode-allocation v5 GO: $document" >&2
		exit 1
	}
done

if grep -Eq \
	'fastboot[[:space:]]+(boot|flash)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$helper_builder" "$helper_verifier" "$baseline" "$probe" \
	"$runtime_verifier" "$gate" "$prepare" "$verify_export"
then
	echo 'FAIL A660 ucode-allocation v5 offline path controls the phone or storage' >&2
	exit 1
fi

"$helper_test"
"$probe_test"
"$gate_test"
"$live_runner_test"
"$live_window_test"
"$export_test"
"$build_test"
"$package_test"

echo 'PASS A660 ucode-allocation v5 contract is exact-root, trace-balanced, snapshot-clean, watchdog-guarded, storage-isolated, package-accepted, host-runner-tested, preflight-GO, explicit-window-only, and non-flashing'
