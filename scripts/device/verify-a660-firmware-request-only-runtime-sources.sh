#!/bin/sh
# shellcheck disable=SC2016
set -eu

baseline=${1:?usage: verify-a660-firmware-request-only-runtime-sources.sh BASELINE PROBE}
probe=${2:?missing probe}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
accepted_baseline=$repo/scripts/device/check-network-root-a660-firmware-request-only-baseline.sh
accepted_probe=$repo/scripts/device/probe-network-root-a660-firmware-request-only.sh
baseline_hash=88db9503be4c4ee58639bc1afdfdf2958a419c4c2a7d5d6db966a255264026ff
probe_hash=17a8d45e6dec02f1977800eab8562c12f7ef3841a92d7797b0ffc4d86313c25e

fail() {
	echo "FAIL $*" >&2
	exit 1
}

line_once() {
	file=$1
	needle=$2
	label=$3
	stats=$(awk -v needle="$needle" '
		index($0, needle) { count++; line = NR }
		END { print count + 0 ":" line + 0 }
	' "$file")
	count=${stats%%:*}
	line=${stats#*:}
	[ "$count" -eq 1 ] ||
		fail "$label count is $count, expected 1"
	printf '%s\n' "$line"
}

for command in awk cut grep sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done
for input in "$baseline" "$probe"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "runtime source is missing, linked, or unreadable: $input"
	sh -n "$input"
done

if [ "${ALLOW_UNPINNED_A660_FIRMWARE_RUNTIME:-0}" != 1 ]; then
	[ "$baseline" = "$accepted_baseline" ] ||
		fail 'baseline path is not accepted'
	[ "$probe" = "$accepted_probe" ] ||
		fail 'probe path is not accepted'
	[ "$(sha256sum "$baseline" | cut -d ' ' -f 1)" = \
		"$baseline_hash" ] ||
		fail 'baseline hash mismatch'
	[ "$(sha256sum "$probe" | cut -d ' ' -f 1)" = "$probe_hash" ] ||
		fail 'probe hash mismatch'
fi

for contract in \
	'7.1.4-rog5-a660reg1' \
	'/.rog5/root-ro' \
	'a660-registration-v3-live.accepted' \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f \
	2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79 \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082 \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	'a660_zap.mbn' \
	'/dev/dri/renderD128' \
	'firmware_request_only=1' \
	'separate_gpu_kms=1' \
	'A660 firmware-only passed; reject open' \
	'A660 firmware-only failed:' \
	'OPEN_ERRNO=117' \
	'helper_status' \
	'forbidden_open=' \
	'check_no_drm_fds' \
	'firmware_requests=2' \
	'zap=absent' \
	'ucode=0 power=0 hfi=0 scm=0' \
	'storage=0 mounts=0'
do
	if ! grep -Fq "$contract" "$baseline" "$probe"; then
		fail "runtime sources omit: $contract"
	fi
done
for exact_input in "$baseline" "$probe"; do
	for exact_contract in \
		d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
		eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082 \
		d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
		8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
		'a660_zap.mbn' \
		'drm_fds=0' \
		'storage=0'
	do
		grep -Fq "$exact_contract" "$exact_input" ||
			fail "runtime source omits exact boundary: $exact_input: $exact_contract"
	done
done

msm_line=$(line_once "$probe" \
	'insmod "$msm_module" separate_gpu_kms=1 firmware_request_only=1' \
	'exact request-only MSM load')
helper_line=$(line_once "$probe" 'helper_output=$("$helper" 2>&1)' \
	'one-open helper invocation')
status_line=$(line_once "$probe" '[ "$helper_status" -eq 117 ]' \
	'EUCLEAN status check')
output_line=$(line_once "$probe" '[ "$helper_output" = OPEN_ERRNO=117 ]' \
	'EUCLEAN output check')
open_log_line=$(line_once "$probe" \
	'open_log=$(dmesg | tail -n +"$open_dmesg_start")' \
	'open-scoped kernel log')
forbidden_line=$(line_once "$probe" \
	"forbidden_open='a660_zap[.]mbn|qcom_scm|pas_auth|zap.shader|HFI|ucode|a6xx_gmu_start|GMU firmware|GPU hardware init'" \
	'pre-power forbidden marker set')
settle_line=$(line_once "$probe" 'sleep "$settle_seconds"' \
	'post-open settle')
[ "$msm_line" -lt "$helper_line" ] &&
	[ "$helper_line" -lt "$status_line" ] &&
	[ "$status_line" -lt "$output_line" ] &&
	[ "$output_line" -lt "$open_log_line" ] &&
	[ "$open_log_line" -lt "$forbidden_line" ] &&
	[ "$forbidden_line" -lt "$settle_line" ] ||
	fail 'request-only module/open/evidence/settle order changed'

[ "$(grep -Fc '"$helper"' "$probe")" -eq 2 ] ||
	fail 'helper path use count changed'
[ "$(grep -Fc 'grep -Fc "$success_marker"' "$probe")" -eq 2 ] ||
	fail 'success marker is not checked before and after settling'
[ "$(grep -Fc 'grep -Fc "$failure_marker"' "$probe")" -eq 2 ] ||
	fail 'failure marker is not checked before and after settling'
[ "$(grep -Fc 'check_no_drm_fds ||' "$probe")" -ge 4 ] ||
	fail 'DRM descriptor boundary is not repeatedly checked'
[ "$(grep -Fc 'runtime_status' "$probe")" -ge 4 ] ||
	fail 'runtime-suspend boundary is not checked'

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|systemctl[[:space:]]+poweroff|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$baseline" "$probe"
then
	fail 'runtime source can control transport or write phone storage'
fi
if grep -Fq 'systemctl reboot' "$baseline" "$probe"; then
	fail 'baseline or probe can bypass the compound reboot gate'
fi

echo 'PASS request-only runtime sources pin accepted registration, exact two firmware files, one EUCLEAN open, pre-power evidence, watchdog, and storage isolation'
