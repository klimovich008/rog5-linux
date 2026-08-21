#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
design=$repo/docs/reusable-recovery-claim-model.md

[ -f "$design" ] && [ ! -L "$design" ]
for invariant in \
	'Status: design checkpoint; not yet a live-authority change.' \
	'PRECOMMIT_CLEAN' \
	'COMMITTING' \
	'written and fsynced before the host sends any COMMIT byte' \
	'Absence of pstore is not' \
	'A partial write, timeout, process crash, USB loss, unknown reply' \
	'No target retry after COMMIT or an ambiguous outcome.' \
	'current conservative' \
	'one-recovery-boot/one-target claim remains authoritative'
do
	grep -Fq "$invariant" "$design"
done

echo 'PASS split claim design permits only proven pre-COMMIT recovery reuse and permanently consumes every COMMIT or ambiguous target attempt'
