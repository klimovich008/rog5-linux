#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
current=$repo/docs/current-state.md
active=$repo/docs/active-context.md
charging=$repo/docs/asus-charging-recovery.md

for document in "$current" "$active" "$charging"; do
	[ -f "$document" ] && [ ! -L "$document" ] || {
		echo "FAIL current status source is missing or linked: $document" >&2
		exit 1
	}
done

for contract in \
	'M5AIKN00F0353YH' \
	'Active slot: A' \
	'33.0210.0210.200' \
	'headless-power-usb-observer-v1' \
	'a600000.dwc3' \
	'a600000.usb' \
	'Do not rebuild or reflash `super`' \
	'Never reuse a consumed or ambiguous candidate.'
do
	grep -Fq "$contract" "$active" || {
		echo "FAIL active context omits current contract: $contract" >&2
		exit 1
	}
done

for contract in \
	'281d5f6bc48972a1d428db5a268a2a6078d05fbceb0008d4996ceae1f4e0f549' \
	'48cc851a31e80492d60b3d1895e6be8605f4ef5d9d7c940c8582215fd80ac005' \
	'f3df0e5865a55a2d5260270db628b61358e2c1287491e35f79b73c38e9ade4d9' \
	'92.25 GiB' \
	'Full UCSI'
do
	grep -Fq "$contract" "$current" || {
		echo "FAIL current state omits current evidence: $contract" >&2
		exit 1
	}
done

grep -Fq 'Status: completed' "$charging" || {
	echo 'FAIL charging runbook does not mark the repair complete' >&2
	exit 1
}
grep -Fq 'Do not rebuild or reflash `super`.' "$charging" || {
	echo 'FAIL completed charging runbook permits repeating the repair' >&2
	exit 1
}

echo 'PASS current status records the verified WW33 rescue baseline and active power/USB successor'
