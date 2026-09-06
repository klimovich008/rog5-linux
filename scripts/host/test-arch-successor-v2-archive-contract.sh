#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
archive_name=artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor-v2.tar.gz
archive=$repo/$archive_name
manifest=$repo/manifests/artifacts.tsv
expected_commit=ed7fa5e12e888c90edfe6e89a45beb30a7b222f6

for command in awk bsdtar cmp cut grep gzip mktemp rm sed sha256sum \
	stat wc; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
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
	fail 'successor v2 archive lacks one exact manifest identity'
IFS=$'\t' read -r expected_size expected_hash role <<<"$record"
[[ $expected_size =~ ^[1-9][0-9]*$ ]]
[[ $expected_hash =~ ^[0-9a-f]{64}$ ]]
[[ $role == *'successor v2'* ]] ||
	fail 'successor v2 manifest role is not explicit'

if [[ ! -e $archive ]]; then
	echo 'PASS successor v2 archive contract is manifest-pinned; local artifact absent'
	exit 0
fi
[[ -f $archive && ! -L $archive ]] ||
	fail 'successor v2 archive is not a regular file'
[[ $(stat -c %s "$archive") == "$expected_size" ]] ||
	fail 'successor v2 archive size changed'
[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$expected_hash" ]] ||
	fail 'successor v2 archive hash changed'
gzip -t "$archive"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
listing=$work/listing
bsdtar -tzf "$archive" >"$listing"
[[ -s $listing ]] || fail 'successor v2 archive is empty'
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
' "$listing" || fail 'successor v2 archive contains an unsafe path'

for required in \
	./etc/rog5/build \
	./etc/rog5/packages.txt \
	./etc/machine-id \
	./usr/local/sbin/rog5-vpn-hotspot.sh \
	./etc/systemd/system/rog5-vpn-hotspot.service \
	./usr/lib/firmware/qcom/a660_sqe.fw \
	./usr/lib/firmware/qcom/a660_gmu.bin \
	./usr/lib/firmware/qcom/sm8350/a660_zap.mbn
do
	grep -Fqx "$required" "$listing" ||
		fail "successor v2 archive omits $required"
done
if grep -Eq \
	'^[.]/etc/ssh/ssh_host_|^[.]/etc/wireguard/wg0[.]conf$|^[.]/etc/NetworkManager/system-connections/.+|^[.]/home/rog5/[.]config/(krdpserverrc|kwallet)' \
	"$listing"
then
	fail 'successor v2 archive embeds first-boot or VPN credentials'
fi

bsdtar -xOf "$archive" ./etc/rog5/build >"$work/build"
bsdtar -xOf "$archive" ./etc/rog5/packages.txt >"$work/packages"
bsdtar -xOf "$archive" ./etc/machine-id >"$work/machine-id"
bsdtar -xOf "$archive" ./usr/local/sbin/rog5-vpn-hotspot.sh \
	>"$work/hotspot"
bsdtar -xOf "$archive" ./etc/systemd/system/rog5-vpn-hotspot.service \
	>"$work/hotspot.service"

project_commit=$(sed -n 's/^project_commit=//p' "$work/build")
[[ $project_commit =~ ^[0-9a-f]{40}$ ]] ||
	fail 'successor v2 build commit is malformed'
[[ $project_commit == "$expected_commit" ]] ||
	fail 'successor v2 archive build commit changed'
grep -qx 'rootfs_sha256=3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a' \
	"$work/build"
grep -qx 'modules_sha256=5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9' \
	"$work/build"
grep -qx 'kernel_release=7.1.4-g7a5cef0db479' "$work/build"
[[ ! -s $work/machine-id ]] || fail 'successor v2 machine ID is not empty'
[[ $(wc -l <"$work/packages") -ge 600 ]] ||
	fail 'successor v2 package database is unexpectedly small'
cmp "$work/hotspot" "$repo/scripts/device/vpn-hotspot-v2.sh"
cmp "$work/hotspot.service" \
	"$repo/packaging/arch/rog5-vpn-hotspot-v2.service"

echo "PASS successor v2 archive is manifest-pinned, path-safe, credential-clean, current, and contains exact fail-closed hotspot controls"
