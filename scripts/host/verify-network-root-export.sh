#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-network-root-export.sh ROOT}
manifest=$repo/manifests/artifacts.tsv
kernel_release=7.1.4-g7a5cef0db479
archive_name=artifacts/arch/rog5-arch-plasma-network-root-7.1.4.tar.gz
modules_name=artifacts/network-root-v1/modules-7.1.4-network-root.tar.gz
source_commit=8c35d4e72382fab6217d510e17108fca60d3bd6f

for command in awk cmp file find getfattr grep readelf realpath readlink \
	sha256sum ssh-keygen stat; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ -d $root && ! -L $root ]] || fail 'export root must be a real directory'
root=$(realpath -e "$root")
[[ $root != / ]] || fail 'refusing the host root filesystem'

manifest_record() {
	local name=$1
	awk -F '\t' -v name="$name" '$1 == name {
		count++
		size=$2
		hash=$3
	} END {
		if (count == 1) print size "\t" hash
	}' "$manifest"
}

archive_record=$(manifest_record "$archive_name")
modules_record=$(manifest_record "$modules_name")
[[ -n $archive_record && -n $modules_record ]] ||
	fail 'missing unique artifact identity'
IFS=$'\t' read -r archive_size archive_hash <<<"$archive_record"
IFS=$'\t' read -r _ modules_hash <<<"$modules_record"

seal=$root/etc/rog5/network-root-export
[[ -r $seal ]] || fail 'missing prepared-export seal'
grep -qx "archive_name=$archive_name" "$seal"
grep -qx "archive_size=$archive_size" "$seal"
grep -qx "archive_sha256=$archive_hash" "$seal"

build=$root/etc/rog5/build
[[ -r $build ]] || fail 'missing rootfs build provenance'
grep -qx "project_commit=$source_commit" "$build"
grep -qx 'rootfs_sha256=3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a' \
	"$build"
grep -qx "modules_sha256=$modules_hash" "$build"
grep -qx "kernel_release=$kernel_release" "$build"

file -b "$root/usr/lib/systemd/systemd" |
	grep -Eq 'ELF 64-bit.*ARM aarch64'
init_link=$(readlink "$root/sbin/init")
[[ $init_link == ../lib/systemd/systemd ||
	$init_link == /usr/lib/systemd/systemd ]]
[[ -x $root/usr/lib/systemd/systemd ]]
cmp "$root/etc/rog5/packages.requested.txt" \
	"$repo/packaging/arch/packages.txt"

mapfile -t module_dirs < <(
	find "$root/lib/modules" -mindepth 1 -maxdepth 1 -type d -printf '%f\n'
)
[[ ${#module_dirs[@]} == 1 && ${module_dirs[0]} == "$kernel_release" ]]
[[ -s $root/lib/modules/$kernel_release/modules.dep ]]
sh "$repo/scripts/device/verify-a660-firmware.sh" "$root/usr/lib/firmware"

for account in root rog5; do
	awk -F: -v account="$account" \
		'$1 == account {
			found=1
			locked=(substr($2,1,1) == "!")
			exit
		}
		END { exit !(found && locked) }' "$root/etc/shadow"
done
[[ $(stat -c %u:%g "$root/root/.ssh/authorized_keys") == 0:0 ]]
[[ $(stat -c %a "$root/root/.ssh/authorized_keys") == 600 ]]
[[ $(stat -c %u:%g "$root/home/rog5/.ssh/authorized_keys") == 1000:1000 ]]
[[ $(stat -c %a "$root/home/rog5/.ssh/authorized_keys") == 600 ]]
cmp "$root/root/.ssh/authorized_keys" \
	"$root/home/rog5/.ssh/authorized_keys"
[[ $(awk 'NF { count++ } END { print count + 0 }' \
	"$root/root/.ssh/authorized_keys") == 1 ]]
grep -Eq '^ssh-(ed25519|rsa|ecdsa-[^ ]+) [A-Za-z0-9+/=]+([[:space:]].*)?$' \
	"$root/root/.ssh/authorized_keys"
! grep -q 'BEGIN .*PRIVATE KEY' "$root/root/.ssh/authorized_keys"

grep -qx 'PasswordAuthentication no' \
	"$root/etc/ssh/sshd_config.d/10-rog5-server.conf"
grep -qx 'PermitRootLogin prohibit-password' \
	"$root/etc/ssh/sshd_config.d/10-rog5-server.conf"
cmp "$root/etc/ssh/sshd_config.d/10-rog5-server.conf" \
	"$repo/packaging/arch/10-rog5-sshd.conf"
host_key=$root/etc/ssh/ssh_host_ed25519_key
host_public_key=$host_key.pub
[[ -f $host_key && ! -L $host_key && -s $host_key ]]
[[ -f $host_public_key && ! -L $host_public_key && -s $host_public_key ]]
[[ $(stat -c %u:%g:%a "$host_key") == 0:0:600 ]]
[[ $(stat -c %u:%g:%a "$host_public_key") == 0:0:644 ]]
[[ $(find "$root/etc/ssh" -maxdepth 1 -type f -name 'ssh_host_*' |
	wc -l) == 2 ]]
cmp \
	<(ssh-keygen -y -f "$host_key" | awk '{ print $1, $2 }') \
	<(awk '{ print $1, $2 }' "$host_public_key")
grep -qx 'unmanaged-devices=interface-name:usb0' \
	"$root/etc/NetworkManager/conf.d/10-rog5-usb-unmanaged.conf"
[[ $(readlink "$root/etc/systemd/system/default.target") == \
	/usr/lib/systemd/system/multi-user.target ]]
for unit in NetworkManager.service rog5-server-inhibit.service sshd.service; do
	[[ -L $root/etc/systemd/system/multi-user.target.wants/$unit ]]
done

[[ ! -s $root/etc/machine-id ]]
[[ -z $(find "$root/etc/NetworkManager/system-connections" \
	-type f -print -quit) ]]
[[ ! -e $root/etc/wireguard/wg0.conf ]]
[[ ! -e $root/home/rog5/.config/krdpserverrc ]]
if [[ -r $root/etc/fstab ]]; then
	! awk '$1 !~ /^#/ && ($1 ~ /^\/dev\// || $1 ~ /^(UUID|PARTUUID)=/) {
		exit 1
	}' "$root/etc/fstab"
fi
[[ $(getfattr --only-values -n user.rog5 \
	"$root/etc/rog5/xattr-probe" 2>/dev/null) == preserved ]]
[[ -z $(find "$root/etc/pacman.d/gnupg" -type s -print -quit) ]]
for empty_mount in dev proc run sys; do
	if [[ -e $root/$empty_mount ]]; then
		[[ -d $root/$empty_mount ]]
		[[ -z $(find "$root/$empty_mount" -mindepth 1 -print -quit) ]]
	fi
done

if command -v selinuxenabled >/dev/null && selinuxenabled; then
	command -v getsebool >/dev/null || fail 'missing getsebool'
	getsebool nfs_export_all_ro | grep -q -- '--> on' ||
		fail 'SELinux nfs_export_all_ro is disabled'
fi

echo "PASS prepared network-root export kernel=$kernel_release"
