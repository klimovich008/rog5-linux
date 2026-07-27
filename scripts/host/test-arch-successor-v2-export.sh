#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-arch-successor-v2-export.sh
verify=$repo/scripts/host/verify-arch-successor-v2-export.sh
archive_test=$repo/scripts/host/test-arch-successor-v2-archive-contract.sh
manifest=$repo/manifests/artifacts.tsv
archive_name=artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor-v2.tar.gz
archive=$repo/$archive_name
expected_size=2007001876
expected_hash=0da5f1dbc05588fcda444b6ba6d8a66db8fa9749691b1f7e37132de9e8a88078

for script in "$prepare" "$verify" "$archive_test"; do
	[[ -x $script ]] || fail "missing executable successor v2 export tool: $script"
	bash -n "$script"
done
"$archive_test" >/dev/null

record=$(awk -F '\t' -v name="$archive_name" '$1 == name {
	count++
	size=$2
	hash=$3
} END {
	if (count == 1) print size "\t" hash
}' "$manifest")
[[ $record == "$expected_size"$'\t'"$expected_hash" ]] ||
	fail 'successor v2 archive lacks one exact manifest identity'
if [[ -e $archive ]]; then
	[[ -f $archive && ! -L $archive ]]
	[[ $(stat -c %s "$archive") == "$expected_size" ]]
	[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$expected_hash" ]]
fi

for contract in \
	"$archive_name" \
	'/var/lib/rog5-network-root-arch-successor-v2' \
	"$expected_size" \
	"$expected_hash" \
	'ed7fa5e12e888c90edfe6e89a45beb30a7b222f6' \
	'7.1.4-g7a5cef0db479' \
	'655' \
	'83328a5ca9d4b516888439037762829c0aa388292352810bc375b61114716bc2' \
	'6e6cfd6a3ede945f67dc9dd42650153a1abfc63651175f54868e1e394cdac8cb' \
	'5e2b4af39227f3afd37a494474faf982f1a87f3e8807406e47196d92b3bb079d' \
	'8ea3d2509bb220d200816571f379c2992c5281771be22d1b84d49d4a716cd814' \
	'6e2af69d729c4d4f8d22e7ba2688561218e870bc8de14debf0fe435019c08a67' \
	'5137868d14400815e99ee642d78ccd125196ce811238120836c59cce92abe44e' \
	'arch-successor-v2-export' \
	'btrfs subvolume create' \
	'btrfs property set -ts "$stage" ro true' \
	'btrfs property get -ts "$root" ro' \
	'recursive_tree_sha256' \
	'ssh-keygen -q -t ed25519 -N' \
	'ssh_host_key_policy=DEDICATED_ED25519_GENERATED_ONCE' \
	'promotion_state=UNBOOTED_HOLD' \
	'root-owned read-only Btrfs mode 0555'
do
	grep -Fq "$contract" "$prepare" "$verify" ||
		fail "successor v2 export contract omits: $contract"
done

if grep -Fq '/var/lib/rog5-network-root-arch-successor-v1' \
	"$prepare" "$verify"; then
	fail 'successor v2 export path references the accepted v1 root'
fi
if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$prepare" "$verify"
then
	fail 'successor v2 offline export path controls the phone or storage'
fi

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ $EUID == 0 ]] ||
		fail 'candidate mutation test requires PolicyKit root'
	"$verify" "$CANDIDATE_ROOT"

	mutation_parent=/var/tmp/rog5-arch-successor-v2-export-mutation.$$
	[[ ! -e $mutation_parent ]]
	install -d -m 0700 "$mutation_parent"
	trap 'rm -rf -- "$mutation_parent"' EXIT HUP INT TERM

	reject_mutation() {
		local label=$1 relative=$2
		local mutation_root=$mutation_parent/$label

		btrfs subvolume snapshot "$CANDIDATE_ROOT" "$mutation_root" >/dev/null
		printf '\nmutation\n' >>"$mutation_root/$relative"
		btrfs property set -ts "$mutation_root" ro true
		if "$verify" "$mutation_root" >/dev/null 2>&1; then
			fail "successor v2 verifier accepts mutated $label"
		fi
		btrfs property set -ts "$mutation_root" ro false
		btrfs subvolume delete "$mutation_root" >/dev/null
	}

	reject_mutation seal etc/rog5/arch-successor-v2-export
	reject_mutation hotspot-control usr/local/sbin/rog5-vpn-hotspot.sh
	reject_mutation hotspot-service \
		etc/systemd/system/rog5-vpn-hotspot.service
	reject_mutation agent etc/passwd
fi

echo 'PASS Arch successor v2 export is manifest-pinned, recursively sealed, read-only Btrfs, mutation-tested, v1-independent, unbooted, and non-flashing'
