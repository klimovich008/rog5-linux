#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
archive=${1:-$repo/artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor.tar.gz}
export_root=${2:-/var/lib/rog5-network-root-arch-successor-v1}
archive_name=artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor.tar.gz
expected_size=2006999039
expected_hash=88c2d671a26f577aef963212cda17bc61baa888d77d0c1aaf1ca25c6fb3ad62a
manifest=$repo/manifests/artifacts.tsv
verifier=$repo/scripts/host/verify-arch-successor-export.sh
seal_relative=etc/rog5/arch-successor-v1-export

[[ $EUID == 0 ]] ||
	fail 'run through PolicyKit; do not share a sudo password'
for command in awk btrfs bsdtar cut df find findmnt getfacl getfattr \
	install realpath sha256sum ssh-keygen stat xargs; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ -x $verifier ]] || fail 'missing successor export verifier'
[[ $export_root == /var/lib/rog5-network-root-arch-successor-v1 ]] ||
	fail 'successor export path is not exact'
[[ -f $archive && ! -L $archive ]] ||
	fail "missing regular successor archive: $archive"
archive=$(realpath -e "$archive")
case $archive in
	"$repo"/*) relative=${archive#"$repo"/} ;;
	*) fail 'successor archive must be inside the repository artifact store' ;;
esac
[[ $relative == "$archive_name" ]] || fail 'unexpected successor archive'

record=$(awk -F '\t' -v name="$archive_name" '$1 == name {
	count++
	size=$2
	hash=$3
} END {
	if (count == 1) print size "\t" hash
}' "$manifest")
[[ $record == "$expected_size"$'\t'"$expected_hash" ]] ||
	fail 'successor archive lacks one exact manifest identity'
[[ $(stat -c %s "$archive") == "$expected_size" ]] ||
	fail 'successor archive size does not match the manifest'
[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$expected_hash" ]] ||
	fail 'successor archive hash does not match the manifest'

[[ $(findmnt -n -o FSTYPE --target /var/lib) == btrfs ]] ||
	fail '/var/lib must be on Btrfs for a read-only protected export'
available_kib=$(df -Pk /var/lib | awk 'NR == 2 { print $4 }')
[[ $available_kib =~ ^[0-9]+$ && $available_kib -ge 12582912 ]] ||
	fail 'at least 12 GiB free under /var/lib is required'
[[ ! -e $export_root ]] || fail "refusing existing export root: $export_root"

recursive_tree_sha256() {
	local tree=$1
	(
		cd "$tree"
		LC_ALL=C find . -xdev -mindepth 1 \
			! -path "./$seal_relative" \
			-printf 'M|%P|%y|%m|%U|%G|%s|%T@|%l\n' |
			LC_ALL=C sort
		LC_ALL=C find . -xdev -type f \
			! -path "./$seal_relative" -print0 |
			LC_ALL=C sort -z |
			xargs -0 -r sha256sum
		LC_ALL=C find . -xdev -mindepth 1 \
			! -path "./$seal_relative" -print0 |
			LC_ALL=C sort -z |
			xargs -0 -r getfacl -spn -- 2>/dev/null
		LC_ALL=C find . -xdev -mindepth 1 \
			! -path "./$seal_relative" -print0 |
			LC_ALL=C sort -z |
			xargs -0 -r getfattr -h -d -m - -- 2>/dev/null
	) | sha256sum | cut -d ' ' -f 1
}

stage=$export_root.partial.$$
[[ ! -e $stage ]] || fail "refusing existing staging root: $stage"
succeeded=0
cleanup() {
	if [[ $succeeded != 1 && -e $stage ]]; then
		case $stage in
			/var/lib/rog5-network-root-arch-successor-v1.partial.*)
				if [[ $(btrfs property get -ts "$stage" ro 2>/dev/null) == \
					ro=true ]]; then
					btrfs property set -ts "$stage" ro false
				fi
				btrfs subvolume delete "$stage" >/dev/null
				;;
			*) echo "FAIL refusing unsafe partial cleanup: $stage" >&2 ;;
		esac
	fi
}
trap cleanup EXIT HUP INT TERM

btrfs subvolume create "$stage" >/dev/null
chmod 0700 "$stage"
bsdtar --acls --xattrs --fflags -xpf "$archive" -C "$stage"

install -Dm0644 "$repo/packaging/arch/10-rog5-sshd.conf" \
	"$stage/etc/ssh/sshd_config.d/10-rog5-server.conf"
[[ -z $(find "$stage/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit) ]] ||
	fail 'successor archive unexpectedly contains an SSH host key'
host_key=$stage/etc/ssh/ssh_host_ed25519_key
ssh-keygen -q -t ed25519 -N '' -C rog5-arch-successor-v1 -f "$host_key"
chown root:root "$host_key" "$host_key.pub"
chmod 0600 "$host_key"
chmod 0644 "$host_key.pub"

seal=$stage/$seal_relative
install -Dm0444 /dev/null "$seal"
tree_entries=$(find "$stage" -xdev -mindepth 1 \
	! -path "$seal" | wc -l)
tree_sha=$(recursive_tree_sha256 "$stage")
host_public_sha=$(sha256sum "$host_key.pub" | cut -d ' ' -f 1)
chmod 0644 "$seal"
{
	printf 'export_generation=arch-successor-v1\n'
	printf 'archive_name=%s\n' "$archive_name"
	printf 'archive_size=%s\n' "$expected_size"
	printf 'archive_sha256=%s\n' "$expected_hash"
	printf 'project_commit=22f5429fd5497ce1a37addb4ff9ab3cb9027af78\n'
	printf 'kernel_release=7.1.4-g7a5cef0db479\n'
	printf 'package_count=655\n'
	printf 'packages_sha256=83328a5ca9d4b516888439037762829c0aa388292352810bc375b61114716bc2\n'
	printf 'chromium_service_sha256=6e6cfd6a3ede945f67dc9dd42650153a1abfc63651175f54868e1e394cdac8cb\n'
	printf 'hotspot_service_sha256=4c29a2cb097a081b9dc4b18abc330d5f6401211cad4178de2b77eb73f0dd5525\n'
	printf 'offline_report_sha256=d88c3092289cb5994289ea3a293ed10d334804080059584631c1f31db1b4955c\n'
	printf 'staged_verifier_sha256=e8ab452b1994ffbffe0a0e1db32e3b2f66866d813e8f32b03713fb4f2545e87f\n'
	printf 'ssh_host_key_policy=DEDICATED_ED25519_GENERATED_ONCE\n'
	printf 'ssh_host_public_key_sha256=%s\n' "$host_public_sha"
	printf 'recursive_tree_entries=%s\n' "$tree_entries"
	printf 'recursive_tree_sha256=%s\n' "$tree_sha"
	printf 'promotion_state=UNBOOTED_HOLD\n'
} >"$seal"
chown root:root "$seal"
chmod 0444 "$seal"
chmod 0555 "$stage"
btrfs property set -ts "$stage" ro true

"$verifier" "$stage"
mv "$stage" "$export_root"
succeeded=1
echo "PASS prepared Arch successor protected export at $export_root"
