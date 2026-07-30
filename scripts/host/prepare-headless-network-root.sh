#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
build_profile=${HEADLESS_NETWORK_ROOT_PROFILE:-headless-ssh-v1}
case $build_profile in
	headless-ssh-v1)
		archive_name=artifacts/arch/rog5-arch-headless-ssh-7.1.4.tar.gz
		default_output=$repo/artifacts/arch/rog5-arch-headless-network-root-7.1.4
		package_contract=$repo/configs/network-roots/headless-network-root-v1.package
		;;
	headless-core-v2)
		archive_name=artifacts/arch/rog5-arch-headless-core-network-source-7.1.4.tar.gz
		default_output=$repo/artifacts/arch/rog5-arch-headless-core-network-root-7.1.4
		package_contract=$repo/configs/network-roots/headless-core-network-root-v2.package
		;;
	headless-ssh-v2)
		archive_name=artifacts/arch/rog5-arch-headless-ssh-v2-7.1.4.tar.gz
		default_output=$repo/artifacts/arch/rog5-arch-headless-ssh-v2-network-root-7.1.4
		package_contract=$repo/configs/network-roots/headless-ssh-network-root-v3.package
		;;
	*) fail 'unsupported headless network-root build profile' ;;
esac
archive=${1:-$repo/$archive_name}
output=${2:-$default_output}
manifest=$repo/manifests/artifacts.tsv
command_manifest=$repo/packaging/arch/rog5-headless-command-manifest
tool=$repo/scripts/host/headless-network-root.py
builder_image=${BUILDER_IMAGE:-localhost/rog5-kernel-builder:ubuntu-24.04}

for command in awk bsdtar install podman python3 realpath sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing headless network-root command: $command"
done
for path in "$archive" "$command_manifest" "$package_contract" "$tool"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing fixed headless network-root input: $path"
done
[[ -x $tool ]] || fail 'headless network-root tool is not executable'
archive=$(realpath -e "$archive")
output=$(realpath -m "$output")
case $archive in
	"$repo"/*) relative=${archive#"$repo"/} ;;
	*) fail 'headless source archive is outside the repository' ;;
esac
[[ $relative == "$archive_name" ]] ||
	fail 'unexpected headless source archive'
[[ ! -e $output && ! -L $output ]] ||
	fail "refusing existing output: $output"

record=$(awk -F $'\t' -v name="$archive_name" '$1 == name {
	count++
	size=$2
	hash=$3
} END {
	if (count == 1) print size "\t" hash
}' "$manifest")
[[ -n $record ]] || fail 'missing unique headless archive manifest row'
IFS=$'\t' read -r expected_size expected_hash <<<"$record"
[[ $(stat -c %s "$archive") == "$expected_size" ]] ||
	fail 'headless source archive size changed'
[[ $(sha256sum "$archive" | awk '{ print $1 }') == "$expected_hash" ]] ||
	fail 'headless source archive hash changed'
python3 "$repo/scripts/device/persistent-root-tool.py" archive "$archive" \
	>/dev/null || fail 'headless source archive contract failed'
podman image exists "$builder_image" ||
	fail "missing rootless builder image: $builder_image"

work=$(mktemp -d)
stage_volume=rog5-headless-network-stage-$$
verify_volume=rog5-headless-network-verify-$$
stage=${output}.partial.$$
succeeded=0
cleanup() {
	if [[ $succeeded == 1 ]]; then
		podman volume rm "$stage_volume" "$verify_volume" >/dev/null
		rm -rf -- "$work"
	else
		echo "INFO retained failed package work: $work" >&2
		echo "INFO retained failed Podman volumes: $stage_volume $verify_volume" >&2
		if [[ -d $stage ]]; then
			echo "INFO retained failed package stage: $stage" >&2
		fi
	fi
}
trap cleanup EXIT

for volume in "$stage_volume" "$verify_volume"; do
	! podman volume exists "$volume" ||
		fail "refusing existing Podman volume: $volume"
	podman volume create "$volume" >/dev/null
done

podman run --rm --network none \
	--mount "type=volume,source=$stage_volume,target=/stage" \
	--mount "type=bind,source=$archive,target=/input/root.tar.gz,readonly" \
	"$builder_image" \
	sh -c \
	'install -d -m 0755 /stage/root && bsdtar --acls --xattrs --fflags -xpf /input/root.tar.gz -C /stage/root'

podman run --rm --network none \
	--mount "type=volume,source=$stage_volume,target=/stage" \
	--mount "type=bind,source=$repo,target=/workspace/repo,readonly" \
	--mount "type=bind,source=$work,target=/output" \
	"$builder_image" \
	python3 /workspace/repo/scripts/host/headless-network-root.py prepare \
	/stage/root "$expected_size" "$expected_hash" \
	/workspace/repo/packaging/arch/rog5-headless-command-manifest \
	/output/root.identity --build-profile "$build_profile"

if [[ $build_profile == headless-ssh-v2 ]]; then
	podman run --rm --network none \
		--mount "type=volume,source=$stage_volume,target=/stage,readonly" \
		--mount "type=bind,source=$work,target=/output" \
		"$builder_image" sh -ceu '
			cd /stage
			find root -xdev -print0 |
				LC_ALL=C sort -z >/tmp/root-files
			bsdtar --null --no-recursion --format paxr \
				--acls --xattrs --fflags \
				-cpf /output/root.tar -T /tmp/root-files
			gzip -n -6 /output/root.tar
		'
else
	podman run --rm --network none \
		--mount "type=volume,source=$stage_volume,target=/stage,readonly" \
		--mount "type=bind,source=$work,target=/output" \
		"$builder_image" \
		sh -c \
		'cd /stage && bsdtar --format paxr --acls --xattrs --fflags -cpf /output/root.tar root && gzip -n -6 /output/root.tar'
fi

python3 "$tool" package \
	"$work/root.identity" "$work/root.tar.gz" "$work/manifest"
cmp "$work/manifest" "$package_contract" ||
	fail 'headless network-root package is not reproducible'

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
	fail "refusing existing package stage: $stage"
install -d -m 0700 "$stage"
install -m 0400 "$work/root.tar.gz" "$stage/root.tar.gz"
install -m 0400 "$work/manifest" "$stage/manifest"
mv -T -- "$stage" "$output"
succeeded=1
echo "PASS headless network-root package prepared at $output"
