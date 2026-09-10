#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
archive=${1:-$repo/artifacts/arch/rog5-arch-plasma-network-root-7.1.4.tar.gz}
export_root=${2:-/var/lib/rog5-network-root-v1}
archive_name=artifacts/arch/rog5-arch-plasma-network-root-7.1.4.tar.gz
manifest=$repo/manifests/artifacts.tsv

[[ $EUID == 0 ]] || fail 'run with sudo; do not share the sudo password'
for command in awk bsdtar df install realpath sha256sum ssh-keygen stat; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ $export_root == /var/lib/rog5-network-root-v1 ]] ||
	fail 'export root must be /var/lib/rog5-network-root-v1'
[[ -f $archive ]] || fail "missing rootfs archive: $archive"
archive=$(realpath -e "$archive")
case $archive in
	"$repo"/*) relative=${archive#"$repo"/} ;;
	*) fail 'rootfs archive must be inside the repository artifact store' ;;
esac
[[ $relative == "$archive_name" ]] || fail 'unexpected rootfs archive'

record=$(awk -F '\t' -v name="$archive_name" '$1 == name {
	count++
	size=$2
	hash=$3
} END {
	if (count == 1) print size "\t" hash
}' "$manifest")
[[ -n $record ]] || fail 'missing unique rootfs manifest row'
IFS=$'\t' read -r expected_size expected_hash <<<"$record"
[[ $(stat -c %s "$archive") == "$expected_size" ]] ||
	fail 'rootfs archive size does not match manifest'
[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$expected_hash" ]] ||
	fail 'rootfs archive hash does not match manifest'

available_kib=$(df -Pk /var/lib | awk 'NR == 2 { print $4 }')
[[ $available_kib =~ ^[0-9]+$ && $available_kib -ge 8388608 ]] ||
	fail 'at least 8 GiB free under /var/lib is required'
[[ ! -e $export_root ]] || fail "refusing existing export root: $export_root"
stage=$export_root.partial.$$
[[ ! -e $stage ]] || fail "refusing existing staging root: $stage"

succeeded=0
report_retained_stage() {
	if [[ $succeeded != 1 && -e $stage ]]; then
		echo "INFO retained failed export stage for inspection: $stage" >&2
	fi
}
trap report_retained_stage EXIT

install -d -m 0755 "$stage"
bsdtar --acls --xattrs --fflags -xpf "$archive" -C "$stage"
install -d -m 0755 "$stage/etc/rog5"
{
	printf 'archive_name=%s\n' "$archive_name"
	printf 'archive_size=%s\n' "$expected_size"
	printf 'archive_sha256=%s\n' "$expected_hash"
} >"$stage/etc/rog5/network-root-export"
chmod 0444 "$stage/etc/rog5/network-root-export"

install -Dm0644 "$repo/packaging/arch/10-rog5-sshd.conf" \
	"$stage/etc/ssh/sshd_config.d/10-rog5-server.conf"
host_key=$stage/etc/ssh/ssh_host_ed25519_key
[[ ! -e $host_key && ! -e $host_key.pub ]]
ssh-keygen -q -t ed25519 -N '' -C rog5-network-root -f "$host_key"
chown root:root "$host_key" "$host_key.pub"
chmod 0600 "$host_key"
chmod 0644 "$host_key.pub"

"$repo/scripts/host/verify-network-root-export.sh" "$stage"
mv "$stage" "$export_root"
succeeded=1
echo "PASS prepared read-only NFS source at $export_root"
