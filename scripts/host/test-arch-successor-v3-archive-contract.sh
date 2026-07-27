#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
archive_name=artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor-v3.tar.gz
archive=$repo/$archive_name
manifest=$repo/manifests/artifacts.tsv
expected_size=2007033670
expected_hash=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7
expected_commit=b8b80013d0acd912530ce42af7bc0adf7f9fd6ea

for command in awk bsdtar cmp cut grep gzip mktemp readlink sed \
	sha256sum stat wc; do
	command -v "$command" >/dev/null ||
		fail "missing host command: $command"
done

record=$(awk -F '\t' -v name="$archive_name" '$1 == name {
	count++
	size=$2
	hash=$3
	role=$4
} END {
	if (count == 1) print size "\t" hash "\t" role
}' "$manifest")
[[ -n $record ]] ||
	fail 'successor v3 archive lacks one exact manifest identity'
IFS=$'\t' read -r size hash role <<<"$record"
[[ $size == "$expected_size" && $hash == "$expected_hash" ]] ||
	fail 'successor v3 manifest identity changed'
[[ $role == *'successor v3'* && $role == *'power-button'* ]] ||
	fail 'successor v3 manifest role is not explicit'

if [[ ! -e $archive ]]; then
	echo 'PASS successor v3 archive contract is manifest-pinned; local artifact absent'
	exit 0
fi
[[ -f $archive && ! -L $archive ]] ||
	fail 'successor v3 archive is not a regular file'
[[ $(stat -c %s "$archive") == "$expected_size" ]] ||
	fail 'successor v3 archive size changed'
[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$expected_hash" ]] ||
	fail 'successor v3 archive hash changed'
gzip -t "$archive"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
listing=$work/listing
bsdtar -tzf "$archive" >"$listing"
[[ -s $listing ]] || fail 'successor v3 archive is empty'
awk '
	/^\// { bad=1 }
	{
		path=$0
		sub(/^[.]\//, "", path)
		count=split(path, part, "/")
		for (field=1; field <= count; field++)
			if (part[field] == "..") bad=1
	}
	END { exit bad ? 1 : 0 }
' "$listing" || fail 'successor v3 archive contains an unsafe path'

for required in \
	./etc/rog5/build \
	./etc/rog5/packages.txt \
	./etc/machine-id \
	./usr/local/libexec/rog5-power-buttond \
	./etc/systemd/system/rog5-power-button.service \
	./etc/systemd/system/multi-user.target.wants/rog5-power-button.service \
	./usr/local/sbin/rog5-vpn-hotspot.sh \
	./etc/systemd/system/rog5-vpn-hotspot.service
do
	grep -Fqx "$required" "$listing" ||
		fail "successor v3 archive omits $required"
done
if grep -Eq \
	'^[.]/etc/ssh/ssh_host_|^[.]/etc/wireguard/wg0[.]conf$|^[.]/etc/NetworkManager/system-connections/.+|^[.]/home/rog5/[.]config/krdpserverrc$|^[.]/home/rog5/[.]local/share/kwalletd/.+|^[.]/var/lib/rog5-agent/private/.+' \
	"$listing"
then
	fail 'successor v3 archive embeds first-boot, VPN, desktop, or agent credentials'
fi

selected=$work/selected
mkdir "$selected"
bsdtar -xzf "$archive" -C "$selected" \
	./etc/rog5/build \
	./etc/rog5/packages.txt \
	./etc/machine-id \
	./usr/local/libexec/rog5-power-buttond \
	./etc/systemd/system/rog5-power-button.service \
	./etc/systemd/system/multi-user.target.wants/rog5-power-button.service \
	./usr/local/sbin/rog5-vpn-hotspot.sh \
	./etc/systemd/system/rog5-vpn-hotspot.service

build=$selected/etc/rog5/build
packages=$selected/etc/rog5/packages.txt
machine_id=$selected/etc/machine-id
power_button=$selected/usr/local/libexec/rog5-power-buttond
power_service=$selected/etc/systemd/system/rog5-power-button.service
power_link=$selected/etc/systemd/system/multi-user.target.wants/rog5-power-button.service
hotspot=$selected/usr/local/sbin/rog5-vpn-hotspot.sh
hotspot_service=$selected/etc/systemd/system/rog5-vpn-hotspot.service

grep -qx "project_commit=$expected_commit" "$build"
grep -qx 'rootfs_sha256=3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a' \
	"$build"
grep -qx 'modules_sha256=5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9' \
	"$build"
grep -qx 'kernel_release=7.1.4-g7a5cef0db479' "$build"
[[ ! -s $machine_id ]] ||
	fail 'successor v3 machine ID is not empty'
[[ $(wc -l <"$packages") == 655 ]] ||
	fail 'successor v3 package count changed'
cmp "$power_button" "$repo/scripts/device/power-buttond.py"
cmp "$power_service" \
	"$repo/packaging/arch/rog5-power-button.service"
cmp "$hotspot" "$repo/scripts/device/vpn-hotspot-v2.sh"
cmp "$hotspot_service" \
	"$repo/packaging/arch/rog5-vpn-hotspot-v2.service"
[[ $(readlink "$power_link") == \
	/etc/systemd/system/rog5-power-button.service ]]

echo 'PASS successor v3 archive is manifest-pinned, path-safe, credential-clean, v2-preserving, and power-button-enabled'
