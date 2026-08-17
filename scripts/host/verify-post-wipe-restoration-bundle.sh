#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)

for command_name in awk cut git grep python3 sha256sum stat; do
	command -v "$command_name" >/dev/null ||
		fail "missing bundle verification command: $command_name"
done

[[ $(stat -c '%a:%u:%g' "$root") == 700:$(id -u):$(id -g) ]] ||
	fail 'bundle root is not private and caller-owned'
for path in \
	BUNDLE.env SHA256SUMS README.md \
	inputs/arch-headless-root.tar.gz \
	inputs/alpine-boot-b-pre-stock.img \
	inputs/stock-boot-b-18.0840.2202.231.img \
	metadata/storage-inventory-v3.json \
	metadata/rog5-native-root-v1.seal \
	device-backup/SHA256SUMS.tsv \
	device-backup/GPT-SHA256SUMS.tsv \
	source/rog5-linux.git.bundle \
	source-tools/scripts/host/verify-readonly-storage-backup.py \
	source-tools/scripts/host/backup-readonly-storage-inventory.py \
	source-tools/scripts/device/collect-readonly-storage-inventory.py; do
	[[ -f $root/$path && ! -L $root/$path ]] ||
		fail "missing, linked, or non-regular bundle member: $path"
done

(cd "$root" && sha256sum -c SHA256SUMS)

grep -Fxq 'bundle_format=rog5-post-wipe-restoration-v1' "$root/BUNDLE.env" ||
	fail 'bundle format changed'
grep -Fxq 'device_serial=M5AIKN00F0353YH' "$root/BUNDLE.env" ||
	fail 'device serial changed'
grep -Fxq 'product=lahaina' "$root/BUNDLE.env" ||
	fail 'device product changed'
grep -Fxq 'userdata_snapshot=absent' "$root/BUNDLE.env" ||
	fail 'bundle incorrectly claims a userdata snapshot'

[[ $(stat -c %s "$root/inputs/arch-headless-root.tar.gz") == 536746495 ]] ||
	fail 'Arch archive size changed'
[[ $(sha256sum "$root/inputs/arch-headless-root.tar.gz" | cut -d ' ' -f 1) == \
	4d120a4b3a10be098cea47ba8536969bbaa931b47b31cc37fc3474fea045b324 ]] ||
	fail 'Arch archive hash changed'
[[ $(stat -c %s "$root/inputs/alpine-boot-b-pre-stock.img") == 100663296 ]] ||
	fail 'Alpine boot image size changed'
[[ $(sha256sum "$root/inputs/alpine-boot-b-pre-stock.img" | cut -d ' ' -f 1) == \
	0a67358df714570af18d4dd209785ab337d5e6a1ec9dd6532babc30bf83a95f1 ]] ||
	fail 'Alpine boot image hash changed'
[[ $(stat -c %s "$root/inputs/stock-boot-b-18.0840.2202.231.img") == 100663296 ]] ||
	fail 'stock boot image size changed'
[[ $(sha256sum "$root/inputs/stock-boot-b-18.0840.2202.231.img" | cut -d ' ' -f 1) == \
	3bd168d7959fcf8070b0b1e9029e635b796c3972ed913514fb64f151247699f1 ]] ||
	fail 'stock boot image hash changed'

expected_head=$(awk -F= '$1 == "repository_head" { print $2 }' "$root/BUNDLE.env")
case $expected_head in
	[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]* ) ;;
	*) fail 'repository head is invalid' ;;
esac
[[ ${#expected_head} -eq 40 ]] || fail 'repository head length changed'
git bundle verify "$root/source/rog5-linux.git.bundle" >/dev/null
git bundle list-heads "$root/source/rog5-linux.git.bundle" |
	awk -v expected="$expected_head" '$1 == expected { found++ } END { exit found != 1 }' ||
	fail 'source bundle does not contain the recorded exact head'

python3 "$root/source-tools/scripts/host/verify-readonly-storage-backup.py" \
	--inventory "$root/metadata/storage-inventory-v3.json" \
	--backup "$root/device-backup"

echo "PASS post-wipe restoration bundle verified at repository head $expected_head"
