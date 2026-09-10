#!/usr/bin/bash
set -euo pipefail
umask 077

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# == 3 ]] || fail 'usage: build-local-arch-image.sh ARCHIVE ROOT_TOOL OUTPUT'
archive=$(realpath -e -- "$1")
root_tool=$(realpath -e -- "$2")
output=$(realpath -m -- "$3")
output_parent=$(dirname -- "$output")

[[ $(id -u) == 0 ]] || fail 'local image build requires root'
[[ -d $output_parent && ! -L $output_parent ]] || fail 'output parent is unsafe'
[[ ! -e $output && ! -L $output && ! -e $output.gz && ! -L $output.gz ]] ||
	fail 'output already exists'

expected_archive_size=536746495
expected_archive_sha256=4d120a4b3a10be098cea47ba8536969bbaa931b47b31cc37fc3474fea045b324
expected_root_tool_sha256=0b2a3a9a8ad330dd427427ac8deb79ca18cb2f8575d46cdc9b354594dce27057
expected_source_seal_sha256=42ef8388bb771fbd0dd8141939b042a89037ea1cf1bec9288f7a3ae51455210a
expected_source_tree_sha256=f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087
expected_local_seal_sha256=02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876
expected_local_tree_sha256=4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167
image_bytes=17179869184
image_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4
image_label=ROG5_ARCH_A

[[ $(stat -c %s "$archive") == $expected_archive_size &&
	$(sha256sum "$archive" | cut -d ' ' -f 1) == $expected_archive_sha256 ]] ||
	fail 'Arch archive identity changed'
[[ $(sha256sum "$root_tool" | cut -d ' ' -f 1) == $expected_root_tool_sha256 ]] ||
	fail 'root tool identity changed'

partial=$output.partial
compressed=$output.gz
compressed_tmp=$compressed.partial
mountpoint=$(mktemp -d /run/rog5-local-image-build.XXXXXX)
loop=
mounted=0
cleanup() {
	status=$?
	trap - EXIT HUP INT TERM
	if [[ $mounted == 1 ]]; then
		umount "$mountpoint" || status=1
	fi
	if [[ -n $loop ]]; then
		losetup -d "$loop" || status=1
	fi
	rmdir "$mountpoint" 2>/dev/null || true
	exit "$status"
}
trap cleanup EXIT HUP INT TERM

truncate -s "$image_bytes" "$partial"
mkfs.ext4 -q -F -m 1 -L "$image_label" -U "$image_uuid" \
	-E "hash_seed=$image_uuid,lazy_itable_init=0,lazy_journal_init=0" "$partial"
loop=$(losetup --find --show "$partial")
mount -t ext4 -o rw,nodev,nosuid,noatime "$loop" "$mountpoint"
mounted=1
rmdir "$mountpoint/lost+found"
bsdtar --numeric-owner --same-permissions --safe-writes --acls --xattrs \
	--fflags --strip-components 1 -xpf "$archive" -C "$mountpoint"

[[ $(sha256sum "$mountpoint/.rog5-persistent-seal" | cut -d ' ' -f 1) == \
	$expected_source_seal_sha256 ]] || fail 'source seal changed'
grep -Fqx "tree_sha256=$expected_source_tree_sha256" \
	"$mountpoint/.rog5-persistent-seal" || fail 'source tree changed'
mv "$mountpoint/.rog5-persistent-seal" "$mountpoint/.rog5-source-seal"
: >"$mountpoint/.rog5-persistent-seal"
chown 0:0 "$mountpoint" "$mountpoint/.rog5-persistent-seal"
chmod 0755 "$mountpoint"
touch -d @1681862400 "$mountpoint"

tree_report=$(python3 "$root_tool" seal "$mountpoint") || fail 'root sealing failed'
for field in \
	'tree_entries=37736' \
	'tree_regular_files=27604' \
	'tree_directories=1902' \
	'tree_symlinks=8230' \
	'tree_bytes=1625282905' \
	'tree_xattrs=3' \
	"tree_sha256=$expected_local_tree_sha256"; do
	grep -Fqx "$field" <<<"$tree_report" || fail "root seal changed: $field"
done
{
	printf '%s\n' \
		'seal_format=rog5-persistent-root-v1' \
		'generation=arch-a' \
		"source_archive_size=$expected_archive_size" \
		"source_archive_sha256=$expected_archive_sha256" \
		'promotion_state=UNBOOTED'
	printf '%s\n' "$tree_report"
} >"$mountpoint/.rog5-persistent-seal"
chmod 0444 "$mountpoint/.rog5-persistent-seal"
[[ $(sha256sum "$mountpoint/.rog5-persistent-seal" | cut -d ' ' -f 1) == \
	$expected_local_seal_sha256 ]] || fail 'local seal changed'
python3 "$root_tool" verify "$mountpoint" \
	"$mountpoint/.rog5-persistent-seal" >/dev/null

sync -f "$mountpoint"
umount "$mountpoint"
mounted=0
losetup -d "$loop"
loop=
e2fsck -fn "$partial" >/dev/null
image_sha256=$(sha256sum "$partial" | cut -d ' ' -f 1)
mv -T -- "$partial" "$output"
gzip -n -1 -c "$output" >"$compressed_tmp"
mv -T -- "$compressed_tmp" "$compressed"

owner_uid=${SUDO_UID:-0}
owner_gid=${SUDO_GID:-0}
chown "$owner_uid:$owner_gid" "$output" "$compressed"
chmod 0600 "$output" "$compressed"
trap - EXIT HUP INT TERM
rmdir "$mountpoint"

printf 'image_size=%s\nimage_sha256=%s\ncompressed_size=%s\ncompressed_sha256=%s\nresult=PASS\n' \
	"$(stat -c %s "$output")" "$image_sha256" \
	"$(stat -c %s "$compressed")" \
	"$(sha256sum "$compressed" | cut -d ' ' -f 1)"
