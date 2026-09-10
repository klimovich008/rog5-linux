#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
baseline=$repo/scripts/device/check-network-root-a660-firmware-request-only-baseline.sh
probe=$repo/scripts/device/probe-network-root-a660-firmware-request-only.sh
verifier=$repo/scripts/device/verify-a660-firmware-request-only-runtime-sources.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing request-only runtime-source verifier' >&2
	exit 1
}
"$verifier" "$baseline" "$probe" >/dev/null

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM

expect_rejected() {
	name=$1
	mutated_baseline=$2
	mutated_probe=$3
	if ALLOW_UNPINNED_A660_FIRMWARE_RUNTIME=1 \
		"$verifier" "$mutated_baseline" "$mutated_probe" \
		>"$work/$name.log" 2>&1
	then
		echo "FAIL request-only runtime mutation passed: $name" >&2
		exit 1
	fi
}

sed 's/firmware_request_only=1/firmware_request_only=0/' "$probe" \
	>"$work/unarmed-msm.sh"
expect_rejected unarmed-msm "$baseline" "$work/unarmed-msm.sh"

sed '/helper_output=$(.*"$helper"/a\
helper_output=$("$helper" 2>\&1)' "$probe" >"$work/second-open.sh"
expect_rejected second-open "$baseline" "$work/second-open.sh"

sed 's/\[ "$helper_status" -eq 117 \]/[ "$helper_status" -eq 0 ]/' \
	"$probe" >"$work/wrong-errno.sh"
expect_rejected wrong-errno "$baseline" "$work/wrong-errno.sh"

sed 's/a660_zap\[.\]mbn|qcom_scm/qcom_scm/' "$probe" \
	>"$work/no-zap-boundary.sh"
expect_rejected no-zap-boundary "$baseline" "$work/no-zap-boundary.sh"

sed 's/d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76/0222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76/' \
	"$baseline" >"$work/wrong-sqe.sh"
expect_rejected wrong-sqe "$work/wrong-sqe.sh" "$probe"

sed 's/check_no_drm_fds ||/true ||/g' "$probe" \
	>"$work/no-fd-boundary.sh"
expect_rejected no-fd-boundary "$baseline" "$work/no-fd-boundary.sh"

{
	printf 'systemctl reboot\n'
	cat "$probe"
} >"$work/reboot-bypass.sh"
expect_rejected reboot-bypass "$baseline" "$work/reboot-bypass.sh"

echo 'PASS request-only runtime rejects unarmed MSM, second open, wrong errno, missing ZAP/FD boundary, wrong firmware, and reboot bypass'
