#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
tools=${1:-$repo/artifacts/a660-runtime-tools-v1}
expected_tools=$repo/artifacts/a660-runtime-tools-v1
base=/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10
predecessor=/var/lib/rog5-network-root-a660-gmu-resume-entry-v9
output=/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10-runtime-v1
stage=$output.partial.$$
stage_root=$stage/root
base_snapshot=$stage/base
stage_identity=$stage/identity
root=$output/root
identity=$output/identity
base_verifier=$repo/scripts/host/verify-a660-gmu-cx-runtime-pm-v10-export.sh
runtime_tool=$repo/scripts/host/a660-runtime-root.py
runtime_verifier=$repo/scripts/host/verify-a660-runtime-root.sh
publisher=$repo/scripts/host/a660-runtime-publish.py
base_seal_sha256=eaa44f2a7cef85e14d1b9dd0359b47d3cf10a5d5b05dafee77c085ce12a45cb4
base_verifier_sha256=f26d67a3267f34153fb672b30bcc9cede8bc4b5bef4f011fa2a3028473601743
base_archive_size=2007186653
base_archive_sha256=8711b34cf454a3f3eef04f12650ef0622ee575d80942e418e1c61f45679aa717
kernel_release=7.1.4-rog5-a660reg1
msm_sha256=c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d
msm_relative=usr/lib/modules/$kernel_release/kernel/drivers/gpu/drm/msm/msm.ko
tools_manifest_sha256=356ec71e4f8fff5cdc0c371c49225df1f387f4157f8f850a5eeed9ecc8c51e4f

[[ $EUID == 0 ]] ||
	fail 'run through PolicyKit; do not share the sudo password'
for command in btrfs chmod chown cp cut mkdir python3 realpath rmdir \
	sha256sum stat sync touch unlink; do
	command -v "$command" >/dev/null ||
		fail "missing v10 runtime-root preparation command: $command"
done
for path in "$base_verifier" "$runtime_tool" "$runtime_verifier" \
	"$publisher"; do
	[[ -x $path && -f $path && ! -L $path ]] ||
		fail "v10 runtime-root dependency is absent or linked: $path"
done
for path in "$base" "$predecessor" "$tools"; do
	[[ -d $path && ! -L $path ]] ||
		fail "v10 runtime-root input is absent or linked: $path"
done
tools=$(realpath -e "$tools")
[[ $tools == "$expected_tools" ]] ||
	fail 'A660 runtime-tools path is not the fixed artifact path'
[[ $(sha256sum "$tools/manifest" | cut -d ' ' -f 1) == \
	"$tools_manifest_sha256" ]] ||
	fail 'A660 runtime-tools manifest is not the approved build'
for path in "$output" "$stage"; do
	[[ ! -e $path && ! -L $path ]] ||
		fail "v10 runtime-root publication path already exists: $path"
done
[[ $(sha256sum \
	"$base/etc/rog5/a660-gmu-cx-runtime-pm-v10-export" |
	cut -d ' ' -f 1) == "$base_seal_sha256" ]] ||
	fail 'accepted v10 export seal changed'

"$base_verifier" "$base" "$predecessor" >/dev/null ||
	fail 'accepted v10 protected export verification failed'

succeeded=0
remove_publication() {
	local container=$1
	local candidate_root=$container/root
	local candidate_base=$container/base
	local candidate_identity=$container/identity

	case $container in
		/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10-runtime-v1|\
		/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10-runtime-v1.partial.*) ;;
		*) echo "FAIL refusing unsafe v10 cleanup: $container" >&2
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
			fail 'refusing unsafe v10 identity cleanup'
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
btrfs subvolume create "$stage_root" >/dev/null ||
	fail 'cannot create the v10 runtime-root staging subvolume'
cp -a --reflink=always --one-file-system "$base/." "$stage_root/" ||
	fail 'cannot clone the accepted v10 root into the runtime subvolume'
chown --reference="$base" "$stage_root"
chmod --reference="$base" "$stage_root"
touch --reference="$base" "$stage_root"
"$base_verifier" "$stage_root" "$predecessor" >/dev/null ||
	fail 'cloned v10 root differs before runtime integration'
btrfs subvolume snapshot -r "$stage_root" "$base_snapshot" >/dev/null ||
	fail 'cannot preserve the verified v10 base snapshot'

python3 "$runtime_tool" prepare \
	--root "$stage_root" \
	--base-root "$base_snapshot" \
	--tools "$tools" \
	--identity "$stage_identity" \
	--base-generation a660-gmu-cx-runtime-pm-v10 \
	--base-seal-sha256 "$base_seal_sha256" \
	--base-verifier-sha256 "$base_verifier_sha256" \
	--base-archive-size "$base_archive_size" \
	--base-archive-sha256 "$base_archive_sha256" \
	--kernel-release "$kernel_release" \
	--approved-tools-manifest-sha256 "$tools_manifest_sha256" ||
	fail 'v10 runtime-root transaction failed'
[[ $(sha256sum "$stage_root/$msm_relative" | cut -d ' ' -f 1) == \
	"$msm_sha256" ]] ||
	fail 'v10 runtime integration changed the accepted msm.ko'
sync -f "$stage_root"
btrfs property set -ts "$stage_root" ro true ||
	fail 'cannot seal the v10 runtime root read-only'
"$runtime_verifier" "$stage_root" "$stage_identity" >/dev/null ||
	fail 'v10 runtime root failed independent verification'
btrfs subvolume delete "$base_snapshot" >/dev/null ||
	fail 'cannot remove the private v10 base snapshot'
sync -f "$stage"
if ! python3 "$publisher" --stage "$stage" --output "$output" >/dev/null; then
	fail 'v10 runtime-root atomic publication failed'
fi
[[ ! -e $stage && -d $root && -f $identity ]] ||
	fail 'v10 runtime-root publication identity is ambiguous'
"$runtime_verifier" "$root" "$identity" >/dev/null ||
	fail 'published v10 runtime root failed final verification'
succeeded=1

printf 'format=rog5-a660-v10-runtime-root-publication-v2\n'
printf 'publication=%s\n' "$output"
printf 'root=%s\n' "$root"
printf 'identity=%s\n' "$identity"
grep -E \
	'^(base_export_verifier_sha256|base_tree_entries|base_tree_sha256|command_manifest_sha256|root_tree_entries|root_tree_sha256|root_seal_sha256)=' \
	"$identity"
