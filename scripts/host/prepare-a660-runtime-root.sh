#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
tools=${1:-$repo/artifacts/a660-runtime-tools-v1}
expected_tools=$repo/artifacts/a660-runtime-tools-v1
base=/var/lib/rog5-network-root-arch-successor-v3
output=/var/lib/rog5-network-root-a660-acceptance-v1
stage=$output.partial.$$
stage_root=$stage/root
base_snapshot=$stage/base
stage_identity=$stage/identity
root=$output/root
identity=$output/identity
base_verifier=$repo/scripts/host/verify-arch-successor-v3-export.sh
runtime_tool=$repo/scripts/host/a660-runtime-root.py
runtime_verifier=$repo/scripts/host/verify-a660-runtime-root.sh
publisher=$repo/scripts/host/a660-runtime-publish.py
base_seal_sha256=26b4fcd8f21c5974d281d4b39386f82965265a31728c3a54877ab6717e98f2a7
base_verifier_sha256=ee301696a22565bb338781b455e5510dbb7102b1e11e1653baba9538a3282e1e
base_archive_size=2007033670
base_archive_sha256=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7
kernel_release=7.1.4-g7a5cef0db479
tools_manifest_sha256=356ec71e4f8fff5cdc0c371c49225df1f387f4157f8f850a5eeed9ecc8c51e4f

[[ $EUID == 0 ]] ||
	fail 'run through PolicyKit; do not share the sudo password'
for command in btrfs cut mkdir python3 realpath rmdir sha256sum stat sync \
	unlink; do
	command -v "$command" >/dev/null ||
		fail "missing A660 runtime-root preparation command: $command"
done
for path in "$base_verifier" "$runtime_tool" "$runtime_verifier" \
	"$publisher"; do
	[[ -x $path && -f $path && ! -L $path ]] ||
		fail "A660 runtime-root dependency is absent or linked: $path"
done
[[ -d $base && ! -L $base ]] ||
	fail 'protected successor-v3 base root is absent or linked'
[[ -d $tools && ! -L $tools ]] ||
	fail 'A660 runtime-tools directory is absent or linked'
tools=$(realpath -e "$tools")
[[ $tools == "$expected_tools" ]] ||
	fail 'A660 runtime-tools path is not the fixed artifact path'
[[ $(sha256sum "$tools/manifest" | cut -d ' ' -f 1) == \
	"$tools_manifest_sha256" ]] ||
	fail 'A660 runtime-tools manifest is not the approved build'
for path in "$output" "$stage"; do
	[[ ! -e $path && ! -L $path ]] ||
		fail "A660 runtime-root publication path already exists: $path"
done
[[ $(sha256sum "$base/etc/rog5/arch-successor-v3-export" |
	cut -d ' ' -f 1) == "$base_seal_sha256" ]] ||
	fail 'successor-v3 base export seal changed'

"$base_verifier" "$base" >/dev/null ||
	fail 'protected successor-v3 base verification failed'

succeeded=0
remove_publication() {
	local container=$1
	local candidate_root=$container/root
	local candidate_base=$container/base
	local candidate_identity=$container/identity

	case $container in
		/var/lib/rog5-network-root-a660-acceptance-v1|\
		/var/lib/rog5-network-root-a660-acceptance-v1.partial.*) ;;
		*) echo "FAIL refusing unsafe A660 cleanup: $container" >&2
			return ;;
	esac
	if [[ -e $candidate_base ]]; then
		btrfs subvolume delete "$candidate_base" >/dev/null
	fi
	if [[ -e $candidate_root ]]; then
		if [[ $(btrfs property get -ts "$candidate_root" ro 2>/dev/null) == \
			ro=true ]]; then
			btrfs property set -ts "$candidate_root" ro false
		fi
		btrfs subvolume delete "$candidate_root" >/dev/null
	fi
	if [[ -e $candidate_identity || -L $candidate_identity ]]; then
		[[ -f $candidate_identity && ! -L $candidate_identity ]] ||
			fail 'refusing unsafe A660 identity cleanup'
		unlink "$candidate_identity"
	fi
	[[ ! -e $container ]] || rmdir "$container"
}
cleanup() {
	if [[ $succeeded == 1 ]]; then
		return
	fi
	if [[ -e $stage ]]; then
		remove_publication "$stage"
	fi
}
trap cleanup EXIT HUP INT TERM

mkdir -m 0700 "$stage"
btrfs subvolume snapshot "$base" "$stage_root" >/dev/null ||
	fail 'cannot create the A660 runtime-root snapshot'
btrfs subvolume snapshot -r "$stage_root" "$base_snapshot" >/dev/null ||
	fail 'cannot preserve the pre-integration base snapshot'
python3 "$runtime_tool" prepare \
	--root "$stage_root" \
	--base-root "$base_snapshot" \
	--tools "$tools" \
	--identity "$stage_identity" \
	--base-generation arch-successor-v3 \
	--base-seal-sha256 "$base_seal_sha256" \
	--base-verifier-sha256 "$base_verifier_sha256" \
	--base-archive-size "$base_archive_size" \
	--base-archive-sha256 "$base_archive_sha256" \
	--kernel-release "$kernel_release" \
	--approved-tools-manifest-sha256 "$tools_manifest_sha256" ||
	fail 'A660 runtime-root transaction failed'
sync -f "$stage_root"
btrfs property set -ts "$stage_root" ro true ||
	fail 'cannot seal the A660 runtime-root subvolume read-only'
"$runtime_verifier" "$stage_root" "$stage_identity" >/dev/null ||
	fail 'new A660 runtime root failed independent verification'
btrfs subvolume delete "$base_snapshot" >/dev/null ||
	fail 'cannot remove the private base snapshot'
sync -f "$stage"
if ! python3 "$publisher" --stage "$stage" --output "$output" >/dev/null; then
	fail 'A660 runtime-root atomic publication failed'
fi
[[ ! -e $stage && -d $root && -f $identity ]] ||
	fail 'A660 runtime-root publication identity is ambiguous'
"$runtime_verifier" "$root" "$identity" >/dev/null ||
	fail 'published A660 runtime root failed final verification'
succeeded=1

printf 'format=rog5-a660-runtime-root-publication-v2\n'
printf 'publication=%s\n' "$output"
printf 'root=%s\n' "$root"
printf 'identity=%s\n' "$identity"
grep -E \
	'^(base_tree_entries|base_tree_sha256|command_manifest_sha256|root_tree_entries|root_tree_sha256|root_seal_sha256)=' \
	"$identity"
