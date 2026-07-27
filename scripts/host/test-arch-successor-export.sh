#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
prepare=$repo/scripts/host/prepare-arch-successor-export.sh
verify=$repo/scripts/host/verify-arch-successor-export.sh
serve=$repo/scripts/host/serve-network-root.sh
manifest=$repo/manifests/artifacts.tsv
archive_name=artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor.tar.gz
archive=$repo/$archive_name
expected_size=2006999039
expected_hash=88c2d671a26f577aef963212cda17bc61baa888d77d0c1aaf1ca25c6fb3ad62a

for script in "$prepare" "$verify" "$serve"; do
	[[ -x $script ]] || {
		echo "FAIL missing executable Arch successor export tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done

record=$(awk -F '\t' -v name="$archive_name" '$1 == name {
	count++
	size=$2
	hash=$3
} END {
	if (count == 1) print size "\t" hash
}' "$manifest")
[[ $record == "$expected_size"$'\t'"$expected_hash" ]] || {
	echo 'FAIL successor archive lacks one exact manifest identity' >&2
	exit 1
}

if [[ -e $archive ]]; then
	[[ -f $archive && ! -L $archive ]]
	[[ $(stat -c %s "$archive") == "$expected_size" ]]
	[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$expected_hash" ]]
fi

for contract in \
	"$archive_name" \
	'/var/lib/rog5-network-root-arch-successor-v1' \
	"$expected_size" \
	"$expected_hash" \
	'22f5429fd5497ce1a37addb4ff9ab3cb9027af78' \
	'7.1.4-g7a5cef0db479' \
	'655' \
	'83328a5ca9d4b516888439037762829c0aa388292352810bc375b61114716bc2' \
	'6e6cfd6a3ede945f67dc9dd42650153a1abfc63651175f54868e1e394cdac8cb' \
	'4c29a2cb097a081b9dc4b18abc330d5f6401211cad4178de2b77eb73f0dd5525' \
	'd88c3092289cb5994289ea3a293ed10d334804080059584631c1f31db1b4955c' \
	'btrfs subvolume create' \
	'btrfs property set -ts "$stage" ro true' \
	'btrfs property get -ts "$root" ro' \
	'recursive_tree_sha256' \
	'ssh-keygen -q -t ed25519 -N' \
	'ssh_host_key_policy=DEDICATED_ED25519_GENERATED_ONCE' \
	'promotion_state=UNBOOTED_HOLD' \
	'root-owned read-only Btrfs mode 0555'
do
	grep -Fq "$contract" "$prepare" "$verify" || {
		echo "FAIL Arch successor export contract omits: $contract" >&2
		exit 1
	}
done

if grep -Fq '/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10' \
	"$prepare" "$verify"; then
	echo 'FAIL successor export path references the sealed v10 root' >&2
	exit 1
fi
if grep -Fq '/var/lib/rog5-network-root-arch-successor-v1)' "$serve"; then
	echo 'FAIL unbooted successor is already NFS-allowlisted' >&2
	exit 1
fi
if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$prepare" "$verify"
then
	echo 'FAIL successor offline export path controls the phone or storage' >&2
	exit 1
fi

if [[ -n ${CANDIDATE_ROOT:-} ]]; then
	[[ $EUID == 0 ]] || {
		echo 'FAIL candidate mutation test requires PolicyKit root' >&2
		exit 1
	}
	"$verify" "$CANDIDATE_ROOT"

	mutation_parent=/var/tmp/rog5-arch-successor-export-mutation.$$
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
			echo "FAIL successor verifier accepts mutated $label" >&2
			exit 1
		fi
		btrfs property set -ts "$mutation_root" ro false
		btrfs subvolume delete "$mutation_root" >/dev/null
	}

	reject_mutation seal etc/rog5/arch-successor-v1-export
	reject_mutation hotspot etc/systemd/system/rog5-vpn-hotspot.service
	reject_mutation agent etc/passwd
fi

echo 'PASS Arch successor export is manifest-pinned, recursively sealed, read-only Btrfs, mutation-tested, v10-independent, unbooted, non-NFS, and non-flashing'
