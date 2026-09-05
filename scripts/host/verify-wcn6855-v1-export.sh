#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-wcn6855-v1-export.sh ROOT [BASE_ROOT] [OVERLAY]}
base_root=${2:-/var/lib/rog5-network-root-arch-successor-v3}
overlay=${3:-$repo/build/wifi-bundle/one/rog5-wifi-root-overlay.tar.gz}
base_archive=$repo/artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor-v3.tar.gz
wifi_modules=$repo/build/wifi-bundle/one/modules-7.1.4-network-root.tar.gz
base_verifier=$repo/scripts/host/verify-arch-successor-v3-export.sh
overlay_verifier=$repo/scripts/device/verify-wifi-root-overlay.sh
release=7.1.4-g7a5cef0db479
base_seal_sha=26b4fcd8f21c5974d281d4b39386f82965265a31728c3a54877ab6717e98f2a7
base_verifier_sha=ee301696a22565bb338781b455e5510dbb7102b1e11e1653baba9538a3282e1e
base_archive_sha=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7
overlay_sha=4e2de54fad3476c950cfc1a97ad30d38a8d03810e66665747adc85762faa6025
modules_sha=e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d
bundle_manifest_sha=9bc99cf80a85388aff7732a0101771c7fcdd18479ba287c62a8dc9b22bd523cd
package_commit=eb99cc751cf8ea03a5220bcc18b691769fcd1a33
seal_relative=etc/rog5/wcn6855-v1-export

for command in awk btrfs bsdtar cmp cut diff file find findmnt getfacl \
	getfattr grep mktemp modinfo readlink realpath rm sha256sum ssh-keygen \
	stat xargs; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
for tool in "$base_verifier" "$overlay_verifier"; do
	[[ -x $tool ]] || fail "missing executable verifier: $tool"
done
[[ $base_root == /var/lib/rog5-network-root-arch-successor-v3 ]] ||
	fail 'successor-v3 base path is not exact'
[[ -d $base_root && ! -L $base_root ]] ||
	fail 'successor-v3 protected base is absent'
[[ -d $root && ! -L $root ]] || fail 'WCN6855 v1 root is not a directory'
root=$(realpath -e "$root")
base_root=$(realpath -e "$base_root")
overlay=$(realpath -e "$overlay")
[[ $base_root == /var/lib/rog5-network-root-arch-successor-v3 ]] ||
	fail 'successor-v3 base resolves unexpectedly'
[[ $overlay == "$repo/build/wifi-bundle/one/rog5-wifi-root-overlay.tar.gz" ]] ||
	fail 'unexpected WCN6855 root overlay path'
[[ $root != / && $root != "$base_root" ]] || fail 'unsafe or aliased root'
[[ $(findmnt -n -o FSTYPE --target "$root") == btrfs ]] ||
	fail 'WCN6855 v1 export is not on Btrfs'
btrfs subvolume show "$root" >/dev/null 2>&1 ||
	fail 'WCN6855 v1 export is not a Btrfs subvolume'
[[ $(btrfs property get -ts "$root" ro) == ro=true ]] ||
	fail 'WCN6855 v1 export Btrfs subvolume is writable'
[[ $(stat -c '%u:%g:%a' "$root") == 0:0:555 ]] ||
	fail 'WCN6855 v1 export root is not root-owned mode 0555'

check_hash() {
	local file=$1 expected=$2 label=$3
	[[ -f $file && ! -L $file ]] || fail "$label is absent or linked"
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "$label hash mismatch"
}

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

[[ ! -e $root/etc/rog5/arch-successor-v3-export ]] ||
	fail 'candidate retained the predecessor export seal'
inner_seal=$root/etc/rog5/wifi-enumeration-v1
check_hash "$inner_seal" \
	897608e6a4cf1725512ed22fc1332af680de103cf6947fd9f05dc64e20e8e9eb \
	'WCN6855 enumeration seal'
[[ $(stat -c '%u:%g:%a' "$inner_seal") == 0:0:444 ]]
grep -qx 'promotion_state=UNBOOTED_HOLD' "$inner_seal"

blacklist=$root/etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf
unmanaged=$root/etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf
probe=$root/usr/local/sbin/rog5-wifi-enumeration-probe
check_hash "$blacklist" \
	46b4d41a08d5d16041bafec2e239cff229d13ed48504a0c04470d74a098ddf3e \
	'WCN6855 module blacklist'
check_hash "$unmanaged" \
	13b96d77b5f51b41b5a60eaf460ba6b59c563b2d38c5fa09b916c625b8ed172d \
	'WCN6855 NetworkManager hold'
check_hash "$probe" \
	699039d117cb3ba23a4b5e3a5897777c6a661afc1ece95c230f67c98166854cb \
	'WCN6855 enumeration probe'
[[ $(stat -c '%u:%g:%a' "$blacklist") == 0:0:644 ]]
[[ $(stat -c '%u:%g:%a' "$unmanaged") == 0:0:644 ]]
[[ $(stat -c '%u:%g:%a' "$probe") == 0:0:755 ]]

for module in phy_qcom_qmp_pcie pwrseq_qcom_wcn pci_pwrctrl_pwrseq \
	mhi mhi_pci_generic ath11k ath11k_pci; do
	grep -Fqx "blacklist $module" "$blacklist" ||
		fail "automatic module hold omits $module"
done
grep -Fqx '[keyfile]' "$unmanaged"
grep -Fqx 'unmanaged-devices=interface-name:wlan0' "$unmanaged"

if [[ -n $(find "$root/etc/NetworkManager/system-connections" \
	-type f -print -quit 2>/dev/null) ]]; then
	fail 'NetworkManager credential exists in WCN6855 v1 root'
fi
[[ ! -e $root/etc/wireguard/wg0.conf ]] ||
	fail 'provider WireGuard credential exists in WCN6855 v1 root'

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
overlay_root=$work/overlay
mkdir -p "$overlay_root"
bsdtar --acls --xattrs --fflags -xpf "$overlay" -C "$overlay_root"
diff --no-dereference -qr \
	"$overlay_root/usr/lib/modules/$release" \
	"$root/usr/lib/modules/$release" >/dev/null ||
	fail 'installed WCN6855 module tree differs from the accepted overlay'

qmp=$root/usr/lib/modules/$release/kernel/drivers/phy/qualcomm/phy-qcom-qmp-pcie.ko
pwrctrl=$root/usr/lib/modules/$release/kernel/drivers/pci/pwrctrl/pci-pwrctrl-pwrseq.ko
pwrseq=$root/usr/lib/modules/$release/kernel/drivers/power/sequencing/pwrseq-qcom-wcn.ko
ath11k_pci=$root/usr/lib/modules/$release/kernel/drivers/net/wireless/ath/ath11k/ath11k_pci.ko
[[ $(modinfo -F name "$qmp") == phy_qcom_qmp_pcie ]]
modinfo -F alias "$pwrctrl" | grep -Fq 'of:N*T*Cpci17cb,1103'
modinfo -F alias "$pwrseq" | grep -Fq 'of:N*T*Cqcom,wcn6855-pmu'
modinfo -F alias "$ath11k_pci" | grep -Fq 'pci:v000017CBd00001103'

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
! cmp -s "$host_public_key" \
	"$base_root/etc/ssh/ssh_host_ed25519_key.pub" ||
	fail 'WCN6855 v1 reused the successor-v3 SSH host identity'
for relative in root/.ssh/authorized_keys home/rog5/.ssh/authorized_keys; do
	cmp "$root/$relative" "$base_root/$relative"
	[[ $(stat -c '%u:%g:%a' "$root/$relative") == \
		"$(stat -c '%u:%g:%a' "$base_root/$relative")" ]]
done

unchanged_metadata() {
	local tree=$1
	find "$tree" -xdev -mindepth 1 \
		! -path "$tree/usr/lib/modules" \
		! -path "$tree/usr/lib/modules/*" \
		! -path "$tree/etc/rog5" \
		! -path "$tree/etc/rog5/arch-successor-v3-export" \
		! -path "$tree/etc/rog5/wifi-enumeration-v1" \
		! -path "$tree/etc/rog5/wcn6855-v1-export" \
		! -path "$tree/etc/ssh" \
		! -path "$tree/etc/ssh/ssh_host_ed25519_key" \
		! -path "$tree/etc/ssh/ssh_host_ed25519_key.pub" \
		! -path "$tree/etc/modprobe.d" \
		! -path "$tree/etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf" \
		! -path "$tree/etc/NetworkManager/conf.d" \
		! -path "$tree/etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf" \
		! -path "$tree/usr/local/sbin" \
		! -path "$tree/usr/local/sbin/rog5-wifi-enumeration-probe" \
		-printf '%P|%y|%m|%U|%G|%s|%l\n' | LC_ALL=C sort
}
unchanged_hashes() {
	local tree=$1
	(
		cd "$tree"
		find . -xdev -type f \
			! -path './usr/lib/modules/*' \
			! -path './etc/rog5/arch-successor-v3-export' \
			! -path './etc/rog5/wifi-enumeration-v1' \
			! -path './etc/rog5/wcn6855-v1-export' \
			! -path './etc/ssh/ssh_host_ed25519_key' \
			! -path './etc/ssh/ssh_host_ed25519_key.pub' \
			! -path './etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf' \
			! -path './etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf' \
			! -path './usr/local/sbin/rog5-wifi-enumeration-probe' \
			-print0 | LC_ALL=C sort -z | xargs -0 -r sha256sum
	)
}
unchanged_metadata "$base_root" >"$work/base.metadata"
unchanged_metadata "$root" >"$work/candidate.metadata"
cmp "$work/base.metadata" "$work/candidate.metadata" ||
	fail 'non-Wi-Fi tree metadata differs from successor-v3'
unchanged_hashes "$base_root" >"$work/base.sha256"
unchanged_hashes "$root" >"$work/candidate.sha256"
cmp "$work/base.sha256" "$work/candidate.sha256" ||
	fail 'non-Wi-Fi tree content differs from successor-v3'

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
[[ -f $seal && ! -L $seal ]] || fail 'WCN6855 v1 seal is absent or linked'
[[ $(stat -c '%u:%g:%a' "$seal") == 0:0:444 ]] ||
	fail 'WCN6855 v1 seal metadata changed'
tree_entries=$(find "$root" -xdev -mindepth 1 ! -path "$seal" | wc -l)
tree_sha=$(recursive_tree_sha256 "$root")
host_public_sha=$(sha256sum "$host_public_key" | cut -d ' ' -f 1)
expected_seal=$work/expected-seal
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
} >"$expected_seal"
cmp "$expected_seal" "$seal" || fail 'WCN6855 v1 seal is not byte-exact'

echo 'PASS WCN6855 v1 export modules=exact firmware=predecessor-pinned probe=enumeration-only credentials=absent dedicated-host-key root-owned read-only Btrfs mode 0555 promotion=UNBOOTED_HOLD'
