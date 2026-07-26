#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-a660-firmware-request-only-v4-live-acceptance.sh
report=$repo/test-results/2026-07-26-a660-firmware-request-only-v4-live-accepted.md
marker=$repo/manifests/acceptance/a660-firmware-request-only-v4-live.accepted
serve=$repo/scripts/host/serve-network-root.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing A660 firmware-request-only v4 live-acceptance verifier' >&2
	exit 1
}
[ -f "$report" ] && [ ! -L "$report" ] || {
	echo 'FAIL missing exact A660 firmware-request-only v4 live report' >&2
	exit 1
}
[ -f "$marker" ] && [ ! -L "$marker" ] || {
	echo 'FAIL missing exact A660 firmware-request-only v4 acceptance marker' >&2
	exit 1
}

if grep -Fq \
	'/var/lib/rog5-network-root-a660-firmware-request-only-v4)' "$serve"
then
	echo 'FAIL consumed A660 firmware-request-only v4 root remains runnable' >&2
	exit 1
fi

for contract in \
	'firmware_requests=2' \
	'open_errno=117' \
	'drm_fds=0' \
	'ucode=0' \
	'power=0' \
	'hfi=0' \
	'scm=0' \
	'fallback=PASSED' \
	'host_cleanup=PASSED' \
	'v4_reuse=FORBIDDEN' \
	'flash=NONE'
do
	grep -Fq "$contract" "$verifier" "$marker" || {
		echo "FAIL A660 request-only live acceptance omits: $contract" >&2
		exit 1
	}
done

"$verifier" "$report" "$marker" >/dev/null

echo 'PASS A660 firmware-request-only v4 live acceptance is exact-report pinned, consumed, two-firmware, failed-open, storage-free, and non-flashing'
