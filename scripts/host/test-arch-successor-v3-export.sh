#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-arch-successor-v3-export.sh
verify=$repo/scripts/host/verify-arch-successor-v3-export.sh
archive_test=$repo/scripts/host/test-arch-successor-v3-archive-contract.sh
manifest=$repo/manifests/artifacts.tsv
archive_name=artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor-v3.tar.gz
archive=$repo/$archive_name
expected_size=2007033670
expected_hash=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7

for script in "$prepare" "$verify" "$archive_test"; do
	[[ -x $script ]] || fail "missing executable successor v3 export tool: $script"
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
	fail 'successor v3 archive lacks one exact manifest identity'
if [[ -e $archive ]]; then
	[[ -f $archive && ! -L $archive ]]
	[[ $(stat -c %s "$archive") == "$expected_size" ]]
	[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$expected_hash" ]]
fi

for contract in \
	"$archive_name" \
	'/var/lib/rog5-network-root-arch-successor-v3' \
	"$expected_size" \
	"$expected_hash" \
	'b8b80013d0acd912530ce42af7bc0adf7f9fd6ea' \
	'7.1.4-g7a5cef0db479' \
	'655' \
	'83328a5ca9d4b516888439037762829c0aa388292352810bc375b61114716bc2' \
	'6e6cfd6a3ede945f67dc9dd42650153a1abfc63651175f54868e1e394cdac8cb' \
	'5e2b4af39227f3afd37a494474faf982f1a87f3e8807406e47196d92b3bb079d' \
	'8ea3d2509bb220d200816571f379c2992c5281771be22d1b84d49d4a716cd814' \
	'8185962d42cdf4f77f052a39f7b8eeb2e4d107d62c184f05a84dcb9c0450bd80' \
	'734283f0a465011682f8cca625614f4e67ec4554d3b3163e9bad326d78f3551d' \
	'66b3a8bfc32434e450d10ea707e21481b991e6fc728cd7afa618664331b4298a' \
	'c617188753e17482328f69abc55c3d2b6da62dd543ecb3a14f551c4f17fb72c7' \
	'arch-successor-v3-export' \
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
		fail "successor v3 export contract omits: $contract"
done

if grep -Eq \
	'/var/lib/rog5-network-root-arch-successor-v[12]([^0-9]|$)' \
	"$prepare" "$verify"
then
	fail 'successor v3 export path references an earlier protected root'
fi
if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$prepare" "$verify"
then
	fail 'successor v3 offline export path controls the phone or storage'
fi

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ $EUID == 0 ]] ||
		fail 'candidate mutation test requires PolicyKit root'
	"$verify" "$CANDIDATE_ROOT"

	mutation_parent=/var/tmp/rog5-arch-successor-v3-export-mutation.$$
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
			fail "successor v3 verifier accepts mutated $label"
		fi
		btrfs property set -ts "$mutation_root" ro false
		btrfs subvolume delete "$mutation_root" >/dev/null
	}

	reject_mutation seal etc/rog5/arch-successor-v3-export
	reject_mutation power-handler usr/local/libexec/rog5-power-buttond
	reject_mutation power-service \
		etc/systemd/system/rog5-power-button.service
	reject_mutation agent etc/passwd
fi

echo 'PASS Arch successor v3 export is manifest-pinned, recursively sealed, read-only Btrfs, power-button-pinned, mutation-tested, predecessor-independent, unbooted, and non-flashing'
