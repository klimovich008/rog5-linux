#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
preparer=$repo/scripts/host/prepare-post-wipe-restoration-bundle.sh
verifier=$repo/scripts/host/verify-post-wipe-restoration-bundle.sh
runbook=$repo/docs/post-wipe-restoration.md

for path in "$preparer" "$verifier"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable bundle contract: ${path#"$repo"/}"
	bash -n "$path"
done
[[ -f $runbook && ! -L $runbook ]] || fail 'missing restoration runbook'

for token in \
	4d120a4b3a10be098cea47ba8536969bbaa931b47b31cc37fc3474fea045b324 \
	0a67358df714570af18d4dd209785ab337d5e6a1ec9dd6532babc30bf83a95f1 \
	3bd168d7959fcf8070b0b1e9029e635b796c3972ed913514fb64f151247699f1 \
	'userdata_snapshot=absent' \
	'git -C "$repo" bundle create' \
	'verify-readonly-storage-backup.py' \
	'cp -al -- "$backup"/.' \
	'refusing existing bundle output'; do
	grep -Fq -- "$token" "$preparer" ||
		fail "bundle preparer omits contract token: $token"
done

for token in \
	'bundle_format=rog5-post-wipe-restoration-v1' \
	'device_serial=M5AIKN00F0353YH' \
	'userdata_snapshot=absent' \
	'git bundle verify' \
	'git bundle list-heads' \
	'--inventory "$root/metadata/storage-inventory-v3.json"'; do
	grep -Fq -- "$token" "$verifier" ||
		fail "bundle verifier omits contract token: $token"
done

if grep -Eq '\b(fastboot|adb|sudo|pkexec)\b|/dev/(sd|nvme|ufs)' \
	"$preparer" "$verifier"; then
	fail 'host-only restoration preparation contains device or privilege commands'
fi

grep -Fq 'full `userdata` snapshot' "$runbook" ||
	fail 'runbook omits the non-byte-exact rollback limit'
grep -Fq 'Do not flash the Alpine boot image by itself' "$runbook" ||
	fail 'runbook omits the root-dependent Alpine boot warning'

echo 'PASS post-wipe restoration bundle is host-only, exact-input-bound, and explicit about rollback limits'
