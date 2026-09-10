#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# -eq 6 ]] || fail \
	'usage: prepare-post-wipe-restoration-bundle.sh OUTPUT ARCH_ARCHIVE ALPINE_BOOT_B STOCK_BOOT_B VERIFIED_BACKUP INVENTORY'

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output=$1
archive=$(realpath -e -- "$2")
alpine_boot=$(realpath -e -- "$3")
stock_boot=$(realpath -e -- "$4")
backup=$(realpath -e -- "$5")
inventory=$(realpath -e -- "$6")
parent=$(realpath -e -- "$(dirname -- "$output")")
output=$parent/${output##*/}

for command_name in cp cut date find git install ln mkdir mktemp mv python3 \
	realpath rm sha256sum stat sync; do
	command -v "$command_name" >/dev/null ||
		fail "missing bundle preparation command: $command_name"
done
[[ ! -e $output && ! -L $output ]] || fail 'refusing existing bundle output'
[[ -z $(git -C "$repo" status --porcelain=v1) ]] ||
	fail 'repository working tree is not clean'
head=$(git -C "$repo" rev-parse --verify HEAD)

check_exact() {
	path=$1
	size=$2
	hash=$3
	label=$4
	[[ -f $path && ! -L $path && -r $path ]] ||
		fail "missing, linked, or unreadable $label"
	[[ $(stat -c %s "$path") == "$size" ]] || fail "$label size changed"
	[[ $(sha256sum "$path" | cut -d ' ' -f 1) == "$hash" ]] ||
		fail "$label hash changed"
}

check_exact "$archive" 536746495 \
	4d120a4b3a10be098cea47ba8536969bbaa931b47b31cc37fc3474fea045b324 \
	'Arch source archive'
check_exact "$alpine_boot" 100663296 \
	0a67358df714570af18d4dd209785ab337d5e6a1ec9dd6532babc30bf83a95f1 \
	'pre-stock Alpine boot image'
check_exact "$stock_boot" 100663296 \
	3bd168d7959fcf8070b0b1e9029e635b796c3972ed913514fb64f151247699f1 \
	'exact stock slot-B boot image'
[[ -d $backup && ! -L $backup ]] || fail 'verified backup is unsafe'
[[ -f $inventory && ! -L $inventory ]] || fail 'storage inventory is unsafe'
[[ -z $(find "$backup" -type l -print -quit) ]] ||
	fail 'verified backup contains a symbolic link'
python3 "$repo/scripts/host/verify-readonly-storage-backup.py" \
	--inventory "$inventory" --backup "$backup" >/dev/null

umask 077
temporary=$(mktemp -d "$parent/.rog5-post-wipe-restoration.XXXXXX")
cleanup() {
	status=$?
	trap - EXIT HUP INT TERM
	if [[ -d $temporary ]]; then
		rm -rf --one-file-system -- "$temporary"
	fi
	exit "$status"
}
trap cleanup EXIT HUP INT TERM

install -d -m 0700 \
	"$temporary/inputs" "$temporary/metadata" "$temporary/device-backup" \
	"$temporary/source" "$temporary/source-tools/scripts/host" \
	"$temporary/source-tools/scripts/device"
ln -- "$archive" "$temporary/inputs/arch-headless-root.tar.gz"
ln -- "$alpine_boot" "$temporary/inputs/alpine-boot-b-pre-stock.img"
ln -- "$stock_boot" "$temporary/inputs/stock-boot-b-18.0840.2202.231.img"
cp -al -- "$backup"/. "$temporary/device-backup"/
install -m 0600 "$inventory" "$temporary/metadata/storage-inventory-v3.json"
install -m 0600 "$repo/configs/storage/rog5-native-root-v1.seal" \
	"$temporary/metadata/rog5-native-root-v1.seal"
install -m 0700 "$repo/scripts/host/verify-post-wipe-restoration-bundle.sh" \
	"$temporary/VERIFY.sh"
install -m 0600 "$repo/docs/post-wipe-restoration.md" "$temporary/README.md"
install -m 0600 "$repo/scripts/host/verify-readonly-storage-backup.py" \
	"$temporary/source-tools/scripts/host/verify-readonly-storage-backup.py"
install -m 0600 "$repo/scripts/host/backup-readonly-storage-inventory.py" \
	"$temporary/source-tools/scripts/host/backup-readonly-storage-inventory.py"
install -m 0600 "$repo/scripts/device/collect-readonly-storage-inventory.py" \
	"$temporary/source-tools/scripts/device/collect-readonly-storage-inventory.py"

git -C "$repo" bundle create "$temporary/source/rog5-linux.git.bundle" HEAD
git bundle verify "$temporary/source/rog5-linux.git.bundle" >/dev/null

created=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '%s\n' \
	'bundle_format=rog5-post-wipe-restoration-v1' \
	"created_utc=$created" \
	'device_serial=M5AIKN00F0353YH' \
	'product=lahaina' \
	"repository_head=$head" \
	'userdata_snapshot=absent' \
	'rollback_class=functional-rebuild-not-byte-exact' \
	>"$temporary/BUNDLE.env"

(cd "$temporary" && sha256sum \
	BUNDLE.env README.md VERIFY.sh \
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
	source-tools/scripts/device/collect-readonly-storage-inventory.py \
	>SHA256SUMS)

"$temporary/VERIFY.sh" >/dev/null
sync -f "$temporary"
mv -T -- "$temporary" "$output"
sync -f "$parent"
trap - EXIT HUP INT TERM
echo "PASS prepared private post-wipe restoration bundle: $output"
