#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
helper_source=$repo/tools/diagnostics/a660-firmware-request-only-open.c
helper_builder=$repo/scripts/device/build-a660-firmware-request-only-open-helper.sh
helper_verifier=$repo/scripts/device/verify-a660-firmware-request-only-open-helper.sh
baseline=$repo/scripts/device/check-network-root-a660-firmware-request-only-baseline.sh
probe=$repo/scripts/device/probe-network-root-a660-firmware-request-only.sh
gate=$repo/scripts/device/run-network-root-a660-firmware-request-only-gate.sh
prepare=$repo/scripts/host/prepare-a660-firmware-request-only-export.sh
verify_export=$repo/scripts/host/verify-a660-firmware-request-only-export.sh
run_live=$repo/scripts/host/run-a660-firmware-request-only-live-gate.sh
serve=$repo/scripts/host/serve-network-root.sh

[ -f "$helper_source" ] && [ ! -L "$helper_source" ] || {
	echo 'FAIL missing A660 firmware-request-only open-helper source' >&2
	exit 1
}
for input in "$helper_builder" "$helper_verifier" "$baseline" "$probe" \
	"$gate" "$prepare" "$verify_export" "$run_live"
do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 firmware-request-only v4 tool: $input" >&2
		exit 1
	}
done

for input in "$helper_builder" "$helper_verifier" "$baseline" "$probe" \
	"$gate"
do
	sh -n "$input"
done
for input in "$prepare" "$verify_export" "$run_live" "$serve"; do
	bash -n "$input"
done

for contract in \
	'/var/lib/rog5-network-root-a660-registration-v3' \
	'/var/lib/rog5-network-root-a660-firmware-request-only-v4' \
	'manifests/acceptance/a660-registration-v3-live.accepted' \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f \
	2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79 \
	04149f41648f12925a6f04261eed96bfecdd6174a10462c82c36213fef0d1bc9 \
	eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082 \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d \
	'usr/lib/firmware/qcom/a660_sqe.fw' \
	'usr/lib/firmware/qcom/a660_gmu.bin' \
	'usr/lib/firmware/qcom/sm8350/a660_zap.mbn' \
	'rog5-a660-firmware-request-only-open' \
	'/dev/dri/renderD128' \
	'OPEN_ERRNO=117' \
	'firmware_request_only=1' \
	'separate_gpu_kms=1' \
	'A660 firmware-only passed; reject open' \
	'A660 firmware-only failed:' \
	'ALLOW_MAINLINE_A660_FIRMWARE_REQUEST_ONLY_GATE=1' \
	'ALLOW_MAINLINE_A660_FIRMWARE_REQUEST_ONLY_REBOOT=1' \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c \
	'verify-a660-registration-v3-live-acceptance.sh' \
	'verify-a660-firmware-request-only-open-helper.sh' \
	'verify-a660-firmware-request-only-export.sh' \
	'credentials=preserved' \
	'zap=absent' \
	'storage=0' \
	'drm_fds=0' \
	'watchdog=disarmed'
do
	if ! grep -Fq "$contract" "$helper_source" "$helper_builder" \
		"$helper_verifier" "$baseline" "$probe" "$gate" "$prepare" \
		"$verify_export" "$run_live" "$serve"
	then
		echo "FAIL A660 firmware-request-only v4 path omits: $contract" >&2
		exit 1
	fi
done

if grep -Eq \
	'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$helper_builder" "$helper_verifier" "$baseline" "$probe" "$gate" \
	"$prepare" "$verify_export" "$run_live"
then
	echo 'FAIL A660 firmware-request-only v4 path can write phone storage' >&2
	exit 1
fi

echo 'PASS A660 firmware-request-only v4 contract is exact-root, SQE/GMU-only, one-open, watchdog-guarded, storage-isolated, and non-flashing'
