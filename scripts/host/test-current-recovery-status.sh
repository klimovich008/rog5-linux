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
	'Active slot: B, running V11 boot' \
	'1-1.2' \
	'V49' \
	'no DT, wrapper, GPT, or boot-partition'
do
	grep -Fq "$contract" "$active" || {
		echo "FAIL active context omits current contract: $contract" >&2
		exit 1
	}
done

for contract in \
	'M5AIKN00F0353YH' \
	'33.0210.0210.200' \
	'Persistent release v11 boots successfully' \
	'SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ' \
	'P24 (`arch_root_a`)' \
	'72.816 seconds' \
	'Do not rebuild or reflash `super`' \
	'test-results/2026-08-29-persistent-ncm-two-hour-pass.md' \
	'test-results/2026-08-30-persistent-tailscale-v11-live.md'
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

grep -Fq 'test-results/2026-08-30-persistent-tailscale-v11-live.md' "$current" || {
	echo 'FAIL current state omits the persistent v11 live evidence' >&2
	exit 1
}

[ "$(wc -l < "$current")" -le 150 ] || {
	echo 'FAIL current state exceeded its compact 150-line budget' >&2
	exit 1
}
[ "$(wc -l < "$active")" -le 100 ] || {
	echo 'FAIL active context exceeded its compact 100-line budget' >&2
	exit 1
}

echo 'PASS compact current status records WW33 rescue, V11 firewall/reboot pass, and peer SSH gate'
