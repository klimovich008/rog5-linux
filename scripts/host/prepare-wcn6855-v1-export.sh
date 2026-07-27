#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
overlay=${1:-$repo/build/wifi-bundle/one/rog5-wifi-root-overlay.tar.gz}
base_root=${2:-/var/lib/rog5-network-root-arch-successor-v3}
export_root=${3:-/var/lib/rog5-network-root-wcn6855-v1}
base_archive=$repo/artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor-v3.tar.gz
wifi_modules=$repo/build/wifi-bundle/one/modules-7.1.4-network-root.tar.gz
base_verifier=$repo/scripts/host/verify-arch-successor-v3-export.sh
overlay_verifier=$repo/scripts/device/verify-wifi-root-overlay.sh
candidate_verifier=$repo/scripts/host/verify-wcn6855-v1-export.sh
release=7.1.4-g7a5cef0db479
base_seal_sha=26b4fcd8f21c5974d281d4b39386f82965265a31728c3a54877ab6717e98f2a7
base_verifier_sha=ee301696a22565bb338781b455e5510dbb7102b1e11e1653baba9538a3282e1e
base_archive_sha=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7
overlay_sha=4e2de54fad3476c950cfc1a97ad30d38a8d03810e66665747adc85762faa6025
modules_sha=e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d
bundle_manifest_sha=9bc99cf80a85388aff7732a0101771c7fcdd18479ba287c62a8dc9b22bd523cd
package_commit=eb99cc751cf8ea03a5220bcc18b691769fcd1a33
seal_relative=etc/rog5/wcn6855-v1-export

[[ $EUID == 0 ]] || fail 'run through PolicyKit; do not share a sudo password'
for command in awk btrfs bsdtar chmod chown cmp cp cut df find findmnt \
	getfacl getfattr install mktemp mv realpath rm sha256sum ssh-keygen \
	stat xargs; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
for tool in "$base_verifier" "$overlay_verifier" "$candidate_verifier"; do
	[[ -x $tool ]] || fail "missing executable verifier: $tool"
done
[[ $base_root == /var/lib/rog5-network-root-arch-successor-v3 ]] ||
	fail 'successor-v3 base path is not exact'
[[ $export_root == /var/lib/rog5-network-root-wcn6855-v1 ]] ||
	fail 'WCN6855 v1 export path is not exact'
[[ -d $base_root && ! -L $base_root ]] ||
	fail 'successor-v3 protected base is absent'
[[ ! -e $export_root ]] || fail 'WCN6855 v1 export already exists'

check_hash() {
	local file=$1 expected=$2 label=$3
	[[ -f $file && ! -L $file ]] || fail "$label is absent or linked"
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "$label hash mismatch"
}

overlay=$(realpath -e "$overlay")
[[ $overlay == "$repo/build/wifi-bundle/one/rog5-wifi-root-overlay.tar.gz" ]] ||
	fail 'unexpected WCN6855 root overlay path'
check_hash "$base_verifier" "$base_verifier_sha" 'successor-v3 verifier'
check_hash "$base_root/etc/rog5/arch-successor-v3-export" \
	"$base_seal_sha" 'successor-v3 seal'
check_hash "$base_archive" "$base_archive_sha" 'successor-v3 archive'
check_hash "$overlay" "$overlay_sha" 'WCN6855 root overlay'
check_hash "$wifi_modules" "$modules_sha" 'WCN6855 module archive'
check_hash "$repo/build/wifi-bundle/one/SHA256SUMS" \
	"$bundle_manifest_sha" 'WCN6855 bundle manifest'
"$base_verifier" "$base_root" >/dev/null
"$overlay_verifier" "$base_archive" "$wifi_modules" "$overlay" >/dev/null

[[ $(findmnt -n -o FSTYPE --target /var/lib) == btrfs ]] ||
	fail '/var/lib must be on Btrfs'
available_kib=$(df -Pk /var/lib | awk 'NR == 2 { print $4 }')
[[ $available_kib =~ ^[0-9]+$ && $available_kib -ge 4194304 ]] ||
	fail 'at least 4 GiB free under /var/lib is required'

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
work=$(mktemp -d /var/tmp/rog5-wcn6855-v1-export.XXXXXX)
succeeded=0
cleanup() {
	rm -rf -- "$work"
	if [[ $succeeded != 1 && -e $stage ]]; then
		case $stage in
			/var/lib/rog5-network-root-wcn6855-v1.partial.*)
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

overlay_root=$work/overlay
install -d -m 0700 "$overlay_root"
bsdtar --acls --xattrs --fflags -xpf "$overlay" -C "$overlay_root"

btrfs subvolume snapshot "$base_root" "$stage" >/dev/null
[[ $(btrfs property get -ts "$stage" ro) == ro=false ]]
chmod 0700 "$stage"

module_root=$stage/usr/lib/modules/$release
[[ -d $module_root && ! -L $module_root ]] ||
	fail 'successor-v3 module root is absent or linked'
rm -rf -- "$module_root"
cp -a --reflink=auto "$overlay_root/usr/lib/modules/$release" "$module_root"

rm -f -- "$stage/etc/rog5/arch-successor-v3-export" \
	"$stage/etc/ssh/ssh_host_ed25519_key" \
	"$stage/etc/ssh/ssh_host_ed25519_key.pub"
install -Dm0644 \
	"$overlay_root/etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf" \
	"$stage/etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf"
install -Dm0644 \
	"$overlay_root/etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf" \
	"$stage/etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf"
install -Dm0755 \
	"$overlay_root/usr/local/sbin/rog5-wifi-enumeration-probe" \
	"$stage/usr/local/sbin/rog5-wifi-enumeration-probe"
install -Dm0444 "$overlay_root/etc/rog5/wifi-enumeration-v1" \
	"$stage/etc/rog5/wifi-enumeration-v1"

host_key=$stage/etc/ssh/ssh_host_ed25519_key
ssh-keygen -q -t ed25519 -N '' -C rog5-wcn6855-v1 -f "$host_key"
chown root:root "$host_key" "$host_key.pub"
chmod 0600 "$host_key"
chmod 0644 "$host_key.pub"
! cmp -s "$host_key.pub" \
	"$base_root/etc/ssh/ssh_host_ed25519_key.pub" ||
	fail 'WCN6855 v1 reused the successor-v3 SSH host identity'

seal=$stage/$seal_relative
install -Dm0444 /dev/null "$seal"
tree_entries=$(find "$stage" -xdev -mindepth 1 ! -path "$seal" | wc -l)
tree_sha=$(recursive_tree_sha256 "$stage")
host_public_sha=$(sha256sum "$host_key.pub" | cut -d ' ' -f 1)
chmod 0644 "$seal"
{
	printf 'export_generation=wcn6855-enumeration-v1\n'
	printf 'base_export=rog5-network-root-arch-successor-v3\n'
	printf 'base_export_seal_sha256=%s\n' "$base_seal_sha"
	printf 'base_archive_sha256=%s\n' "$base_archive_sha"
	printf 'runtime_package_commit=%s\n' "$package_commit"
	printf 'bundle_manifest_sha256=%s\n' "$bundle_manifest_sha"
	printf 'root_overlay_sha256=%s\n' "$overlay_sha"
	printf 'wifi_modules_sha256=%s\n' "$modules_sha"
	printf 'wifi_image_sha256=a4edaee34dca66534cf886fd0daa6068273d4fd722b63960d517ef17699af43e\n'
	printf 'wifi_dtb_sha256=15acdcd6fad910f105047ef53de08b47cafadbbf94827e123931408d92310d89\n'
	printf 'kernel_release=%s\n' "$release"
	printf 'probe_sha256=699039d117cb3ba23a4b5e3a5897777c6a661afc1ece95c230f67c98166854cb\n'
	printf 'blacklist_sha256=46b4d41a08d5d16041bafec2e239cff229d13ed48504a0c04470d74a098ddf3e\n'
	printf 'unmanaged_sha256=13b96d77b5f51b41b5a60eaf460ba6b59c563b2d38c5fa09b916c625b8ed172d\n'
	printf 'ssh_host_key_policy=DEDICATED_ED25519_GENERATED_ONCE\n'
	printf 'ssh_host_public_key_sha256=%s\n' "$host_public_sha"
	printf 'recursive_tree_entries=%s\n' "$tree_entries"
	printf 'recursive_tree_sha256=%s\n' "$tree_sha"
	printf 'probe_scope=ENUMERATION_ONLY_NO_SCAN_NO_ASSOCIATION_NO_AP\n'
	printf 'promotion_state=UNBOOTED_HOLD\n'
} >"$seal"
chown root:root "$seal"
chmod 0444 "$seal"
chmod 0555 "$stage"
btrfs property set -ts "$stage" ro true

"$candidate_verifier" "$stage" "$base_root" "$overlay"
mv "$stage" "$export_root"
succeeded=1
echo "PASS prepared WCN6855 v1 protected export at $export_root"
