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
sh -n "$verifier"

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

for contract in \
	f5e1226923f82528e8cc2ad2727d38834c64761d7691559e295da43fafcfbd8c \
	912846d98ef6ee9fb3c0fa9f0b455c49d47a2f43ff72e2ba1d14c1c284cbfe32 \
	2cb3d85439b1bc72f96b8d401207c53d9d77cf1e \
	9c140753e1d188de141be90c253d5d42af21a3ce \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c \
	'acceptance_scope=A660_SQE_GMU_REQUEST_ONLY_EUCLEAN_PRE_UCODE_POWER_HFI_ZAP' \
	'exact_reprobe=1' \
	'driver_override=unset-null-representation' \
	'open_invocations=1' \
	'success_markers=1' \
	'display_connectors=0' \
	'fallback_pstore_records=0'
do
	grep -Fq "$contract" "$verifier" "$marker" || {
		echo "FAIL A660 request-only live pin omits: $contract" >&2
		exit 1
	}
done

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
cp "$report" "$stage/report"
cp "$marker" "$stage/marker"

printf '\nmutation\n' >>"$stage/report"
if "$verifier" "$stage/report" "$marker" >/dev/null 2>&1; then
	echo 'FAIL A660 request-only verifier accepted a modified live report' >&2
	exit 1
fi

cp "$report" "$stage/report"
printf 'firmware_requests=3\n' >>"$stage/marker"
if "$verifier" "$report" "$stage/marker" >/dev/null 2>&1; then
	echo 'FAIL A660 request-only verifier accepted a modified marker' >&2
	exit 1
fi

rm "$stage/marker"
ln -s "$marker" "$stage/marker"
if "$verifier" "$report" "$stage/marker" >/dev/null 2>&1; then
	echo 'FAIL A660 request-only verifier accepted a linked marker' >&2
	exit 1
fi

echo 'PASS A660 firmware-request-only v4 live acceptance is exact-report pinned, mutation-tested, consumed, two-firmware, failed-open, storage-free, and non-flashing'
