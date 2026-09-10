#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source_name=artifacts/arch/rog5-arch-headless-core-7.1.4.tar.gz
output_name=artifacts/arch/rog5-arch-headless-core-network-source-7.1.4.tar.gz
source_archive=${1:-$repo/$source_name}
output_archive=${2:-$repo/$output_name}
manifest=$repo/manifests/artifacts.tsv
comparator=$repo/scripts/host/compare-root-archives.py
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04
expected_builder_id=c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec
expected_builder_digest=sha256:8513960144bb1ca77878a1364c03fb100c8b87fffb8440fd37a6cc4fc0043b41
indicator_sha256=3792745382a390ebeef37a081e532884aae07bbcd73fd9f0da1c94e67bdabbc8
kernel_release=7.1.4-g7a5cef0db479
source_date_epoch=1681862400

for command in awk cmp cut install ln mktemp podman realpath rm \
	sha256sum stat unlink; do
	command -v "$command" >/dev/null ||
		fail "missing archive-normalization command: $command"
done
for path in "$source_archive" "$manifest" "$comparator"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing fixed archive-normalization input: $path"
done

source_archive=$(realpath -e "$source_archive")
output_archive=$(realpath -m "$output_archive")
[[ $source_archive == "$repo/$source_name" ]] ||
	fail 'unexpected headless-core source archive'
[[ $output_archive == "$repo/$output_name" ]] ||
	fail 'unexpected normalized headless-core output path'
[[ ! -e $output_archive && ! -L $output_archive ]] ||
	fail 'refusing existing normalized headless-core archive'

record=$(awk -F $'\t' -v name="$source_name" '$1 == name {
	count++
	size=$2
	hash=$3
} END {
	if (count == 1) print size "\t" hash
}' "$manifest")
[[ -n $record ]] || fail 'missing unique headless-core manifest row'
IFS=$'\t' read -r expected_size expected_hash <<<"$record"
[[ $(stat -c %s "$source_archive") == "$expected_size" ]] ||
	fail 'headless-core source archive size changed'
[[ $(sha256sum "$source_archive" | cut -d ' ' -f 1) == "$expected_hash" ]] ||
	fail 'headless-core source archive hash changed'

podman image exists "$builder_image" ||
	fail 'accepted snapshot builder is unavailable'
[[ $(podman image inspect "$builder_image" --format '{{.Id}}') == \
	"$expected_builder_id" ]] ||
	fail 'accepted snapshot builder ID changed'
[[ $(podman image inspect "$builder_image" --format '{{.Digest}}') == \
	"$expected_builder_digest" ]] ||
	fail 'accepted snapshot builder digest changed'

work=$(mktemp -d)
stage_volume=rog5-headless-core-normalize-stage-$$
verify_volume=rog5-headless-core-normalize-verify-$$
stage=
succeeded=0
cleanup() {
	if [[ $succeeded == 1 ]]; then
		podman volume rm "$stage_volume" "$verify_volume" >/dev/null
		rm -rf -- "$work"
	else
		echo "INFO retained failed normalization work: $work" >&2
		echo "INFO retained failed Podman volumes: $stage_volume $verify_volume" >&2
		[[ -z $stage || ! -e $stage ]] ||
			echo "INFO retained failed output stage: $stage" >&2
	fi
}
trap cleanup EXIT HUP INT TERM

for volume in "$stage_volume" "$verify_volume"; do
	! podman volume exists "$volume" ||
		fail "refusing existing Podman volume: $volume"
	podman volume create "$volume" >/dev/null
done

podman run --rm --network none \
	--mount "type=volume,source=$stage_volume,target=/stage" \
	--mount "type=bind,source=$source_archive,target=/input/root.tar.gz,readonly" \
	"$builder_image" \
	bsdtar --acls --xattrs --fflags -xpf /input/root.tar.gz -C /stage

verify_root() {
	local volume=$1
	podman run --rm --network none \
		--mount "type=volume,source=$volume,target=/stage,readonly" \
		--mount "type=bind,source=$repo,target=/stage/workspace/repo,readonly" \
		--mount type=bind,source=/dev,target=/stage/dev \
		--mount type=bind,source=/proc,target=/stage/proc \
		--mount type=bind,source=/sys,target=/stage/sys \
		--tmpfs /stage/run \
		--tmpfs /stage/tmp \
		--tmpfs /stage/var/tmp \
		--env "TARGET_KERNEL_RELEASE=$kernel_release" \
		--env "INDICATOR_SHA256=$indicator_sha256" \
		"$builder_image" chroot /stage /bin/bash \
		/workspace/repo/scripts/device/verify-staged-arch-headless-core-rootfs.sh
}

canonicalize_root_mtime() {
	local volume=$1
	podman run --rm --network none \
		--mount "type=volume,source=$volume,target=/stage" \
		"$builder_image" \
		touch -d "@$source_date_epoch" /stage
}

canonicalize_root_mtime "$stage_volume"
podman run --rm --network none \
	--mount "type=volume,source=$stage_volume,target=/stage,readonly" \
	--mount "type=bind,source=$repo,target=/workspace/repo,readonly" \
	"$builder_image" \
	python3 /workspace/repo/scripts/device/persistent-root-tool.py \
	seal /stage >"$work/source.tree"

for suffix in a b; do
	podman run --rm --network none \
		--mount "type=volume,source=$stage_volume,target=/stage,readonly" \
		--mount "type=bind,source=$work,target=/output" \
		"$builder_image" \
		sh -ceu '
			suffix=$1
			cd /stage
			find . -xdev -print0 |
				LC_ALL=C sort -z >"/output/files-$suffix"
			bsdtar --null --no-recursion --format pax \
				--acls --xattrs --fflags --no-read-sparse \
				-cpf "/output/root-$suffix.tar" \
				-T "/output/files-$suffix"
			gzip -n -6 "/output/root-$suffix.tar"
		' sh "$suffix"
done
cmp "$work/root-a.tar.gz" "$work/root-b.tar.gz" ||
	fail 'normalized headless-core archive is not reproducible'
podman run --rm --network none \
	--mount "type=bind,source=$repo,target=/workspace/repo,readonly" \
	--mount "type=bind,source=$source_archive,target=/input/source.tar.gz,readonly" \
	--mount "type=bind,source=$work/root-a.tar.gz,target=/input/normalized.tar.gz,readonly" \
	"$builder_image" \
	python3 /workspace/repo/scripts/host/compare-root-archives.py \
	/input/source.tar.gz /input/normalized.tar.gz
podman run --rm --network none \
	--mount "type=bind,source=$repo,target=/workspace/repo,readonly" \
	--mount "type=bind,source=$work/root-a.tar.gz,target=/input/root.tar.gz,readonly" \
	"$builder_image" \
	python3 /workspace/repo/scripts/device/persistent-root-tool.py \
	archive /input/root.tar.gz >/dev/null
verify_root "$stage_volume"

podman run --rm --network none \
	--mount "type=volume,source=$verify_volume,target=/stage" \
	--mount "type=bind,source=$work/root-a.tar.gz,target=/input/root.tar.gz,readonly" \
	"$builder_image" \
	bsdtar --acls --xattrs --fflags -xpf /input/root.tar.gz -C /stage
canonicalize_root_mtime "$verify_volume"
podman run --rm --network none \
	--mount "type=volume,source=$verify_volume,target=/stage,readonly" \
	--mount "type=bind,source=$repo,target=/workspace/repo,readonly" \
	"$builder_image" \
	python3 /workspace/repo/scripts/device/persistent-root-tool.py \
	seal /stage >"$work/normalized.tree"
cmp "$work/source.tree" "$work/normalized.tree" ||
	fail 'archive normalization changed the extracted root tree'
verify_root "$verify_volume"

stage=$(mktemp \
	--tmpdir="$(dirname "$output_archive")" \
	".$(basename "$output_archive").partial.XXXXXXXX")
install -m 0444 "$work/root-a.tar.gz" "$stage"
ln -- "$stage" "$output_archive" ||
	fail 'normalized archive appeared during publication'
unlink "$stage"
stage=
printf 'PASS normalized headless-core archive size=%s sha256=%s\n' \
	"$(stat -c %s "$output_archive")" \
	"$(sha256sum "$output_archive" | cut -d ' ' -f 1)"
succeeded=1
