#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-wcn6855-v1-export.sh
verify=$repo/scripts/host/verify-wcn6855-v1-export.sh

for script in "$prepare" "$verify"; do
	[[ -x $script ]] || fail "missing executable WCN6855 v1 export tool: $script"
	bash -n "$script"
done

for contract in \
	'/var/lib/rog5-network-root-arch-successor-v3' \
	'/var/lib/rog5-network-root-wcn6855-v1' \
	'build/wifi-bundle/one/rog5-wifi-root-overlay.tar.gz' \
	'a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7' \
	'4e2de54fad3476c950cfc1a97ad30d38a8d03810e66665747adc85762faa6025' \
	'e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d' \
	'26b4fcd8f21c5974d281d4b39386f82965265a31728c3a54877ab6717e98f2a7' \
	'ee301696a22565bb338781b455e5510dbb7102b1e11e1653baba9538a3282e1e' \
	'verify-arch-successor-v3-export.sh' \
	'verify-wifi-root-overlay.sh' \
	'btrfs subvolume snapshot' \
	'btrfs property set -ts "$stage" ro true' \
	'btrfs property get -ts "$root" ro' \
	'recursive_tree_sha256' \
	'ssh-keygen -q -t ed25519 -N' \
	'ssh_host_key_policy=DEDICATED_ED25519_GENERATED_ONCE' \
	'export_generation=wcn6855-enumeration-v1' \
	'probe_scope=ENUMERATION_ONLY_NO_SCAN_NO_ASSOCIATION_NO_AP' \
	'promotion_state=UNBOOTED_HOLD' \
	'root-owned read-only Btrfs mode 0555'
do
	grep -Fq "$contract" "$prepare" "$verify" ||
		fail "WCN6855 v1 export contract omits: $contract"
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp|nmcli|hostapd|wpa_supplicant)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$prepare" "$verify"
then
	fail 'WCN6855 v1 export controls the phone, radio, or host storage'
fi

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ $EUID == 0 ]] || fail 'candidate mutation test requires PolicyKit root'
	"$verify" "$CANDIDATE_ROOT"

	mutation_parent=/var/tmp/rog5-wcn6855-v1-export-mutation.$$
	[[ ! -e $mutation_parent ]]
	install -d -m 0700 "$mutation_parent"
	trap 'rm -rf -- "$mutation_parent"' EXIT HUP INT TERM

	reject_file_mutation() {
		local label=$1 relative=$2
		local mutation_root=$mutation_parent/$label

		btrfs subvolume snapshot "$CANDIDATE_ROOT" "$mutation_root" >/dev/null
		printf '\nmutation\n' >>"$mutation_root/$relative"
		btrfs property set -ts "$mutation_root" ro true
		if "$verify" "$mutation_root" >/dev/null 2>&1; then
			fail "WCN6855 v1 verifier accepts mutated $label"
		fi
		btrfs property set -ts "$mutation_root" ro false
		btrfs subvolume delete "$mutation_root" >/dev/null
	}

	reject_file_mutation seal etc/rog5/wcn6855-v1-export
	reject_file_mutation probe usr/local/sbin/rog5-wifi-enumeration-probe
	reject_file_mutation blacklist \
		etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf
	reject_file_mutation module \
		usr/lib/modules/7.1.4-g7a5cef0db479/kernel/drivers/phy/qualcomm/phy-qcom-qmp-pcie.ko

	mutation_root=$mutation_parent/credential
	btrfs subvolume snapshot "$CANDIDATE_ROOT" "$mutation_root" >/dev/null
	install -Dm0600 /dev/null \
		"$mutation_root/etc/NetworkManager/system-connections/forbidden.nmconnection"
	btrfs property set -ts "$mutation_root" ro true
	if "$verify" "$mutation_root" >/dev/null 2>&1; then
		fail 'WCN6855 v1 verifier accepts an injected credential'
	fi
	btrfs property set -ts "$mutation_root" ro false
	btrfs subvolume delete "$mutation_root" >/dev/null
fi

echo 'PASS WCN6855 v1 export is exact-overlay, recursively sealed, read-only Btrfs, dedicated-key, mutation-tested, unbooted, and non-flashing'
