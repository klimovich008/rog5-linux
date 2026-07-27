#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-arch-successor-export.sh ROOT}
archive_name=artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor.tar.gz
archive=$repo/$archive_name
expected_size=2006999039
expected_hash=88c2d671a26f577aef963212cda17bc61baa888d77d0c1aaf1ca25c6fb3ad62a
project_commit=22f5429fd5497ce1a37addb4ff9ab3cb9027af78
kernel_release=7.1.4-g7a5cef0db479
package_count=655
packages_hash=83328a5ca9d4b516888439037762829c0aa388292352810bc375b61114716bc2
chromium_hash=6e6cfd6a3ede945f67dc9dd42650153a1abfc63651175f54868e1e394cdac8cb
hotspot_hash=4c29a2cb097a081b9dc4b18abc330d5f6401211cad4178de2b77eb73f0dd5525
report_hash=d88c3092289cb5994289ea3a293ed10d334804080059584631c1f31db1b4955c
staged_verifier_hash=e8ab452b1994ffbffe0a0e1db32e3b2f66866d813e8f32b03713fb4f2545e87f
rootfs_hash=3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a
modules_hash=5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9
manifest=$repo/manifests/artifacts.tsv
seal_relative=etc/rog5/arch-successor-v1-export

for command in awk btrfs cmp cut file find findmnt getfacl getfattr grep \
	mktemp readlink realpath sha256sum ssh-keygen stat xargs; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ -d $root && ! -L $root ]] ||
	fail 'successor export root must be a real directory'
root=$(realpath -e "$root")
[[ $root != / ]] || fail 'refusing the host root filesystem'
[[ $(findmnt -n -o FSTYPE --target "$root") == btrfs ]] ||
	fail 'successor export is not on Btrfs'
btrfs subvolume show "$root" >/dev/null 2>&1 ||
	fail 'successor export is not a Btrfs subvolume'
[[ $(btrfs property get -ts "$root" ro) == ro=true ]] ||
	fail 'successor export Btrfs subvolume is writable'
[[ $(stat -c '%u:%g:%a' "$root") == 0:0:555 ]] ||
	fail 'successor export root is not root-owned mode 0555'

check_hash() {
	local file=$1 expected=$2 label=$3
	[[ -f $file && ! -L $file ]] || fail "$label is absent or linked"
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "$label hash mismatch"
}

record=$(awk -F '\t' -v name="$archive_name" '$1 == name {
	count++
	size=$2
	hash=$3
} END {
	if (count == 1) print size "\t" hash
}' "$manifest")
[[ $record == "$expected_size"$'\t'"$expected_hash" ]] ||
	fail 'successor archive lacks one exact manifest identity'
[[ -f $archive && ! -L $archive ]] ||
	fail 'manifest-pinned successor archive is absent'
[[ $(stat -c %s "$archive") == "$expected_size" ]] ||
	fail 'successor archive size changed'
check_hash "$archive" "$expected_hash" 'successor archive'
check_hash "$repo/packaging/arch/packages.txt" "$packages_hash" \
	'requested package list'
check_hash "$repo/packaging/arch/rog5-chromium-headless.service" \
	"$chromium_hash" 'isolated Chromium service'
check_hash "$repo/packaging/arch/rog5-vpn-hotspot.service" \
	"$hotspot_hash" 'VPN hotspot service'
check_hash "$repo/test-results/2026-07-27-arch-successor-rootfs-offline.md" \
	"$report_hash" 'offline successor report'
check_hash "$repo/scripts/device/verify-staged-arch-rootfs.sh" \
	"$staged_verifier_hash" 'complete staged-root verifier'

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

seal=$root/$seal_relative
[[ -f $seal && ! -L $seal ]] || fail 'successor export seal is absent or linked'
[[ $(stat -c '%u:%g:%a' "$seal") == 0:0:444 ]] ||
	fail 'successor export seal metadata changed'
host_key=$root/etc/ssh/ssh_host_ed25519_key
host_public_key=$host_key.pub
[[ -f $host_key && ! -L $host_key && -s $host_key ]]
[[ -f $host_public_key && ! -L $host_public_key && -s $host_public_key ]]
[[ $(stat -c '%u:%g:%a' "$host_key") == 0:0:600 ]]
[[ $(stat -c '%u:%g:%a' "$host_public_key") == 0:0:644 ]]
[[ $(find "$root/etc/ssh" -maxdepth 1 -type f -name 'ssh_host_*' |
	wc -l) == 2 ]]
cmp \
	<(ssh-keygen -y -f "$host_key" | awk '{ print $1, $2 }') \
	<(awk '{ print $1, $2 }' "$host_public_key")

tree_entries=$(find "$root" -xdev -mindepth 1 \
	! -path "$seal" | wc -l)
tree_sha=$(recursive_tree_sha256 "$root")
host_public_sha=$(sha256sum "$host_public_key" | cut -d ' ' -f 1)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
expected_seal=$work/expected-seal
{
	printf 'export_generation=arch-successor-v1\n'
	printf 'archive_name=%s\n' "$archive_name"
	printf 'archive_size=%s\n' "$expected_size"
	printf 'archive_sha256=%s\n' "$expected_hash"
	printf 'project_commit=%s\n' "$project_commit"
	printf 'kernel_release=%s\n' "$kernel_release"
	printf 'package_count=%s\n' "$package_count"
	printf 'packages_sha256=%s\n' "$packages_hash"
	printf 'chromium_service_sha256=%s\n' "$chromium_hash"
	printf 'hotspot_service_sha256=%s\n' "$hotspot_hash"
	printf 'offline_report_sha256=%s\n' "$report_hash"
	printf 'staged_verifier_sha256=%s\n' "$staged_verifier_hash"
	printf 'ssh_host_key_policy=DEDICATED_ED25519_GENERATED_ONCE\n'
	printf 'ssh_host_public_key_sha256=%s\n' "$host_public_sha"
	printf 'recursive_tree_entries=%s\n' "$tree_entries"
	printf 'recursive_tree_sha256=%s\n' "$tree_sha"
	printf 'promotion_state=UNBOOTED_HOLD\n'
} >"$expected_seal"
cmp "$expected_seal" "$seal" ||
	fail 'successor export seal is not byte-exact'

build=$root/etc/rog5/build
[[ -f $build && ! -L $build ]] || fail 'missing rootfs build provenance'
grep -qx "project_commit=$project_commit" "$build"
grep -qx "rootfs_sha256=$rootfs_hash" "$build"
grep -qx "modules_sha256=$modules_hash" "$build"
grep -qx "kernel_release=$kernel_release" "$build"
cmp "$root/etc/rog5/packages.requested.txt" \
	"$repo/packaging/arch/packages.txt"
[[ $(find "$root/var/lib/pacman/local" -mindepth 1 -maxdepth 1 \
	-type d | wc -l) == "$package_count" ]]

file -b "$root/usr/lib/systemd/systemd" |
	grep -Eq 'ELF 64-bit.*ARM aarch64'
init_link=$(readlink "$root/sbin/init")
[[ $init_link == ../lib/systemd/systemd ||
	$init_link == /usr/lib/systemd/systemd ]]
[[ -x $root/usr/lib/systemd/systemd ]]
mapfile -t module_dirs < <(
	find "$root/lib/modules" -mindepth 1 -maxdepth 1 -type d -printf '%f\n'
)
[[ ${#module_dirs[@]} == 1 && ${module_dirs[0]} == "$kernel_release" ]]
[[ -s $root/lib/modules/$kernel_release/modules.dep ]]
sh "$repo/scripts/device/verify-a660-firmware.sh" \
	"$root/usr/lib/firmware" >/dev/null

for account in root rog5 rog5-agent; do
	awk -F: -v account="$account" \
		'$1 == account {
			found=1
			locked=(substr($2,1,1) == "!")
			exit
		}
		END { exit !(found && locked) }' "$root/etc/shadow"
done
grep -qx 'rog5:x:1000:1000::/home/rog5:/bin/bash' "$root/etc/passwd"
grep -qx 'rog5-agent:x:961:961::/var/lib/rog5-agent:/usr/bin/nologin' \
	"$root/etc/passwd"
grep -qx 'rog5-agent:x:961:' "$root/etc/group"
[[ $(stat -c '%u:%g:%a' "$root/var/lib/rog5-agent") == 961:961:700 ]]
[[ $(stat -c '%u:%g:%a' "$root/var/lib/rog5-agent/private") == \
	961:961:700 ]]
[[ ! -e $root/var/lib/rog5-agent/.ssh ]]
[[ -z $(find "$root/var/lib/rog5-agent" -mindepth 1 \
	! -path "$root/var/lib/rog5-agent/private" -print -quit) ]]

[[ $(stat -c '%u:%g:%a' "$root/root/.ssh/authorized_keys") == 0:0:600 ]]
[[ $(stat -c '%u:%g:%a' "$root/home/rog5/.ssh/authorized_keys") == \
	1000:1000:600 ]]
cmp "$root/root/.ssh/authorized_keys" \
	"$root/home/rog5/.ssh/authorized_keys"
[[ $(awk 'NF { count++ } END { print count + 0 }' \
	"$root/root/.ssh/authorized_keys") == 1 ]]
grep -Eq '^ssh-(ed25519|rsa|ecdsa-[^ ]+) [A-Za-z0-9+/=]+([[:space:]].*)?$' \
	"$root/root/.ssh/authorized_keys"
if grep -q 'BEGIN .*PRIVATE KEY' "$root/root/.ssh/authorized_keys"; then
	fail 'authorized key file contains private-key material'
fi

cmp "$root/etc/ssh/sshd_config.d/10-rog5-server.conf" \
	"$repo/packaging/arch/10-rog5-sshd.conf"
cmp "$root/etc/systemd/system/rog5-chromium-headless.service" \
	"$repo/packaging/arch/rog5-chromium-headless.service"
cmp "$root/etc/systemd/system/rog5-vpn-hotspot.service" \
	"$repo/packaging/arch/rog5-vpn-hotspot.service"
grep -qx 'User=rog5-agent' \
	"$root/etc/systemd/system/rog5-chromium-headless.service"
grep -qx 'PrivateDevices=yes' \
	"$root/etc/systemd/system/rog5-chromium-headless.service"
grep -qx 'ProtectSystem=strict' \
	"$root/etc/systemd/system/rog5-chromium-headless.service"
grep -qx 'HandlePowerKey=ignore' \
	"$root/etc/systemd/logind.conf.d/10-rog5-server.conf"
grep -qx 'unmanaged-devices=interface-name:usb0' \
	"$root/etc/NetworkManager/conf.d/10-rog5-usb-unmanaged.conf"
[[ $(readlink "$root/etc/systemd/system/default.target") == \
	/usr/lib/systemd/system/multi-user.target ]]
for unit in NetworkManager.service rog5-server-inhibit.service sshd.service; do
	[[ -L $root/etc/systemd/system/multi-user.target.wants/$unit ]]
done
for unit in rog5-chromium-headless.service rog5-ttyd.service \
	rog5-vpn-hotspot.service; do
	[[ ! -e $root/etc/systemd/system/multi-user.target.wants/$unit ]]
done

[[ ! -s $root/etc/machine-id ]]
[[ -z $(find "$root/etc/NetworkManager/system-connections" \
	-type f -print -quit) ]]
[[ ! -e $root/etc/wireguard/wg0.conf ]]
[[ ! -e $root/home/rog5/.config/krdpserverrc ]]
[[ ! -e $root/home/rog5/.local/share/kwalletd ]]
if [[ -r $root/etc/fstab ]]; then
	if awk '$1 !~ /^#/ &&
		($1 ~ /^\/dev\// || $1 ~ /^(UUID|PARTUUID)=/) {
			found=1
		}
		END { exit !found }' "$root/etc/fstab"
	then
		fail 'fstab contains a block-device mount'
	fi
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

echo 'PASS Arch successor export package=655 agent=isolated services=exact secrets=absent root-owned read-only Btrfs mode 0555 promotion=UNBOOTED_HOLD'
