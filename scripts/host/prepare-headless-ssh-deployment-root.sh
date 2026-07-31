#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD:-} == 1 ]] ||
	fail 'set ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD=1 for one private root build'
[[ ${ALLOW_PHONE_CREDENTIAL_USE:-} == 1 ]] ||
	fail 'set ALLOW_PHONE_CREDENTIAL_USE=1 before using the key-bound root'

source_archive=${1:?usage: prepare-headless-ssh-deployment-root.sh SOURCE_ARCHIVE OUTPUT_DIRECTORY}
output=${2:?missing output directory}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
command_manifest=$repo/packaging/arch/rog5-headless-command-manifest
tool=$repo/scripts/host/headless-network-root.py
root_tool=$repo/scripts/device/persistent-root-tool.py
builder_verifier=$repo/scripts/host/verify-steam-deck-builder.sh
publisher=$repo/scripts/host/a660-runtime-publish.py
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04
fixture_fingerprint=SHA256:ylv66wbMSxVEAMiOFvMQOztcvtSB5wSbVe9FXePMLN0
fixture_source=2abe8c533179da598c37939ff8ebb4667a243bd8140c2d497237e41fbea72e6a
fixture_sealed=60fed48c8714a3f3b2082f95a04e913f32dfc74ed4c262e5b3d6e924a39a9c3b
fixture_tree=6f8a8f11bfb581bb52ca7d590141ce465b8d48d8f9f4577a076b7a37604a2fd5
fixture_seal=f443a47c456b33d670e6efd4a2e20cff2bc72061e7661472694acfbba45c8d5a

for command in bsdtar cmp cut dirname find git grep id install mktemp \
	podman python3 realpath rm sed sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing deployment-root command: $command"
done
for path in \
	"$command_manifest" \
	"$tool" \
	"$root_tool" \
	"$builder_verifier" \
	"$publisher"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing fixed deployment-root input: ${path#"$repo"/}"
done
[[ -x $tool && -x $root_tool && -x $builder_verifier &&
	-x $publisher ]] ||
	fail 'deployment-root verifier is not executable'

[[ -z $(git -C "$repo" status --porcelain --untracked-files=all) ]] ||
	fail 'repository must be clean before a deployment-root build'
branch=$(git -C "$repo" branch --show-current)
[[ -n $branch ]] || fail 'repository is not on a branch'
upstream=$(git -C "$repo" rev-parse \
	--abbrev-ref --symbolic-full-name '@{u}')
[[ $upstream == "origin/$branch" ]] ||
	fail 'deployment-root branch does not track its origin peer'
[[ $(git -C "$repo" rev-parse HEAD) == \
	$(git -C "$repo" rev-parse "$upstream") ]] ||
	fail 'deployment-root checkpoint differs from its origin peer'

source_archive=$(realpath -e "$source_archive")
output=$(realpath -m "$output")
for path in "$source_archive" "$output"; do
	case $path in
	"$repo"|"$repo"/*)
		fail 'deployment-root private paths must remain outside the repository'
		;;
	esac
done
source_parent=$(dirname "$source_archive")
output_parent=$(dirname "$output")
for parent in "$source_parent" "$output_parent"; do
	[[ -d $parent && ! -L $parent &&
		$(stat -Lc '%u:%g:%a:%F' "$parent") == \
		"$(id -u):$(id -g):700:directory" ]] ||
		fail 'deployment-root parent metadata is unsafe'
done
[[ -f $source_archive && ! -L $source_archive &&
	$(stat -Lc '%u:%g:%h:%a:%F' "$source_archive") == \
	"$(id -u):$(id -g):1:444:regular file" ]] ||
	fail 'deployment source archive metadata is unsafe'
[[ ! -e $output && ! -L $output ]] ||
	fail 'deployment-root output already exists'

source_size=$(stat -c %s "$source_archive")
source_sha256=$(sha256sum "$source_archive" | cut -d ' ' -f 1)
[[ $source_size =~ ^[1-9][0-9]*$ &&
	$source_sha256 =~ ^[0-9a-f]{64}$ &&
	$source_sha256 != "$fixture_source" ]] ||
	fail 'deployment source archive identity is invalid or fixture-bound'
python3 "$root_tool" archive "$source_archive" >/dev/null ||
	fail 'deployment source archive contract failed'
podman image exists "$builder_image" ||
	fail 'qualified rootless builder image is absent'
"$builder_verifier" "$builder_image" >/dev/null ||
	fail 'rootless builder qualification failed'

work=$(mktemp -d)
stage_volume=rog5-deployment-root-stage-$$
verify_volume=rog5-deployment-root-verify-$$
stage=${output}.partial.$$
succeeded=0
cleanup() {
	if [[ $succeeded == 1 ]]; then
		podman volume rm "$stage_volume" "$verify_volume" >/dev/null
		rm -rf -- "$work"
	else
		echo "INFO retained failed deployment-root work: $work" >&2
		echo "INFO retained failed deployment-root volumes: $stage_volume $verify_volume" >&2
		if [[ -d $stage ]]; then
			echo "INFO retained failed deployment-root stage: $stage" >&2
		fi
	fi
}
trap cleanup EXIT

for volume in "$stage_volume" "$verify_volume"; do
	! podman volume exists "$volume" ||
		fail "refusing existing deployment-root volume: $volume"
	podman volume create "$volume" >/dev/null
done

podman run --rm --network none \
	--mount "type=volume,source=$stage_volume,target=/stage" \
	--mount "type=bind,source=$source_archive,target=/input/root.tar.gz,readonly" \
	"$builder_image" \
	sh -c \
	'install -d -m 0755 /stage/root && bsdtar --acls --xattrs --fflags -xpf /input/root.tar.gz -C /stage/root'

podman run --rm --network none \
	--mount "type=volume,source=$stage_volume,target=/stage" \
	--mount "type=bind,source=$repo,target=/workspace/repo,readonly" \
	--mount "type=bind,source=$work,target=/output" \
	"$builder_image" \
	python3 /workspace/repo/scripts/host/headless-network-root.py prepare \
	/stage/root "$source_size" "$source_sha256" \
	/workspace/repo/packaging/arch/rog5-headless-command-manifest \
	/output/root.identity --build-profile headless-ssh-v2

podman run --rm --network none \
	--mount "type=volume,source=$stage_volume,target=/stage,readonly" \
	--mount "type=bind,source=$work,target=/output" \
	"$builder_image" sh -ceu '
		cd /stage
		find root -xdev -print0 >/tmp/root-files.unsorted
		LC_ALL=C sort -z /tmp/root-files.unsorted >/tmp/root-files
		bsdtar --null --no-recursion --format paxr \
			--acls --xattrs --fflags \
			-cpf /output/root.tar -T /tmp/root-files
		gzip -n -6 /output/root.tar
	'

python3 "$tool" package \
	"$work/root.identity" "$work/root.tar.gz" "$work/manifest"
for fixture in \
	"$fixture_fingerprint" \
	"$fixture_source" \
	"$fixture_sealed" \
	"$fixture_tree" \
	"$fixture_seal"; do
	! grep -Fq "$fixture" "$work/manifest" ||
		fail 'deployment package retained a fixture identity'
done

podman run --rm --network none \
	--mount "type=volume,source=$verify_volume,target=/stage" \
	--mount "type=bind,source=$work/root.tar.gz,target=/input/root.tar.gz,readonly" \
	"$builder_image" \
	bsdtar --acls --xattrs --fflags -xpf /input/root.tar.gz -C /stage
podman run --rm --network none \
	--mount "type=volume,source=$verify_volume,target=/stage,readonly" \
	--mount "type=bind,source=$repo,target=/workspace/repo,readonly" \
	--mount "type=bind,source=$work,target=/output,readonly" \
	"$builder_image" \
	python3 /workspace/repo/scripts/host/headless-network-root.py verify \
	/stage/root /output/root.tar.gz /output/manifest \
	/workspace/repo/packaging/arch/rog5-headless-command-manifest

[[ ! -e $stage && ! -L $stage ]] ||
	fail 'deployment-root partial output already exists'
install -d -m 0700 "$stage"
install -m 0400 "$work/root.tar.gz" "$stage/root.tar.gz"
install -m 0444 "$work/manifest" "$stage/manifest"
python3 "$publisher" --stage "$stage" --output "$output" \
	>"$work/publication.txt"
succeeded=1

printf 'format=rog5-headless-ssh-deployment-root-v1\n'
printf 'source_archive_size=%s\n' "$source_size"
printf 'source_archive_sha256=%s\n' "$source_sha256"
sed -n \
	-e '/^authorized_key_fingerprint=/p' \
	-e '/^sealed_archive_size=/p' \
	-e '/^sealed_archive_sha256=/p' \
	-e '/^root_tree_entries=/p' \
	-e '/^root_tree_sha256=/p' \
	-e '/^root_seal_sha256=/p' \
	"$output/manifest"
printf 'output=%s\n' "$output"
printf 'authority=none\n'
echo 'PASS non-fixture SSH-only deployment root prepared and verified'
