#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
authorized_key=${1:?usage: stage-arch-rootfs.sh AUTHORIZED_KEY [OUTPUT]}
output=${2:-}
rootfs=${ROOTFS:-$repo/artifacts/arch/ArchLinuxARM-aarch64-latest.tar.gz}
modules=${MODULES_ARCHIVE:-$repo/artifacts/network-root-v1/modules-7.1.4-network-root.tar.gz}
firmware=${FIRMWARE_DIRECTORY:-$repo/artifacts/firmware/linux-firmware-20260622}
builder_image=${BUILDER_IMAGE:-localhost/rog5-kernel-builder:ubuntu-24.04}
manifest=$repo/manifests/artifacts.tsv
generation=${ARCH_ROOTFS_GENERATION:-v2}
firmware_required=1
indicator_required=0
indicator=$repo/artifacts/headless-indicator-v1/rog5-key-indicatord

case $generation in
	v2)
		stage_runner=/workspace/repo/scripts/device/run-arch-rootfs-stage.sh
		device_stage=scripts/device/stage-arch-rootfs.sh
		rootfs_verifier=/workspace/repo/scripts/device/verify-staged-arch-rootfs-v2.sh
		default_output=$repo/artifacts/arch/rog5-arch-plasma-network-root-7.1.4.tar.gz
		;;
	v3)
		stage_runner=/workspace/repo/scripts/device/run-arch-rootfs-v3-stage.sh
		device_stage=scripts/device/stage-arch-rootfs-v3.sh
		rootfs_verifier=/workspace/repo/scripts/device/verify-staged-arch-rootfs-v3.sh
		default_output=$repo/artifacts/arch/rog5-arch-plasma-network-root-v3-7.1.4.tar.gz
		;;
	headless-v1)
		stage_runner=/workspace/repo/scripts/device/run-arch-rootfs-stage.sh
		device_stage=scripts/device/stage-arch-headless-rootfs.sh
		rootfs_verifier=/workspace/repo/scripts/device/verify-staged-arch-headless-rootfs.sh
		default_output=$repo/artifacts/arch/rog5-arch-headless-ssh-7.1.4.tar.gz
		firmware_required=0
		;;
	headless-v2)
		stage_runner=/workspace/repo/scripts/device/run-arch-rootfs-stage.sh
		device_stage=scripts/device/stage-arch-headless-core-rootfs.sh
		rootfs_verifier=/workspace/repo/scripts/device/verify-staged-arch-headless-core-rootfs.sh
		default_output=$repo/artifacts/arch/rog5-arch-headless-core-7.1.4.tar.gz
		firmware_required=0
		indicator_required=1
		;;
	*)
		echo "FAIL unsupported Arch rootfs generation: $generation" >&2
		exit 1
		;;
esac
output=${output:-$default_output}

for command in bash bsdtar file git podman readelf realpath sha256sum \
	ssh-keygen stat strings tar; do
	command -v "$command" >/dev/null
done
for path in "$authorized_key" "$rootfs" "$modules"; do
	[[ -f $path ]]
done
[[ -r $manifest ]]
if [[ $firmware_required == 1 ]]; then
	[[ -d $firmware ]]
fi
if [[ $indicator_required == 1 ]]; then
	[[ -f $indicator && ! -L $indicator && -x $indicator ]]
fi

authorized_key=$(realpath "$authorized_key")
rootfs=$(realpath "$rootfs")
modules=$(realpath "$modules")
firmware_mount=()
if [[ $firmware_required == 1 ]]; then
	firmware=$(realpath "$firmware")
	firmware_mount=(
		--mount
		"type=bind,source=$firmware,target=/stage/input/firmware,readonly"
	)
fi
indicator_mount=()
if [[ $indicator_required == 1 ]]; then
	indicator=$(realpath "$indicator")
	indicator_mount=(
		--mount
		"type=bind,source=$indicator,target=/stage/input/rog5-key-indicatord,readonly"
	)
fi
mkdir -p "$(dirname "$output")"
output=$(realpath -m "$output")
[[ ! -e $output ]] || {
	echo "FAIL refusing to overwrite $output" >&2
	exit 1
}

verify_manifest_artifact() {
	local name=$1
	local path=$2
	local records expected_size expected_hash
	records=$(awk -F '\t' -v name="$name" '$1 == name {
		count++
		size=$2
		hash=$3
	} END {
		if (count == 1) print size "\t" hash
	}' "$manifest")
	[[ -n $records ]] || {
		echo "FAIL missing unique manifest entry: $name" >&2
		exit 1
	}
	IFS=$'\t' read -r expected_size expected_hash <<<"$records"
	[[ $(stat -c %s "$path") == "$expected_size" ]]
	[[ $(sha256sum "$path" | cut -d ' ' -f 1) == "$expected_hash" ]]
	printf '%s\n' "$expected_hash"
}

rootfs_hash=$(verify_manifest_artifact \
	artifacts/arch/ArchLinuxARM-aarch64-latest.tar.gz "$rootfs")
modules_hash=$(verify_manifest_artifact \
	artifacts/network-root-v1/modules-7.1.4-network-root.tar.gz "$modules")
indicator_hash=
if [[ $indicator_required == 1 ]]; then
	indicator_hash=$(verify_manifest_artifact \
		artifacts/headless-indicator-v1/rog5-key-indicatord "$indicator")
	[[ $(stat -c %s "$indicator") == 67520 ]]
	file "$indicator" |
		grep -q 'ELF 64-bit LSB pie executable, ARM aarch64.*static-pie linked'
	readelf -h "$indicator" | grep -q 'Machine:.*AArch64'
	! readelf -l "$indicator" | grep -q 'INTERP'
	! strings "$indicator" | grep -q -- '--fixture'
fi
if [[ $firmware_required == 1 ]]; then
	for relative in qcom/a660_sqe.fw qcom/a660_gmu.bin \
		qcom/sm8350/a660_zap.mbn; do
		verify_manifest_artifact \
			"artifacts/firmware/linux-firmware-20260622/$relative" \
			"$firmware/$relative" >/dev/null
	done
fi

[[ $(awk 'NF { count++ } END { print count + 0 }' "$authorized_key") == 1 ]]
grep -Eq '^ssh-(ed25519|rsa|ecdsa-[^ ]+) [A-Za-z0-9+/=]+([[:space:]].*)?$' \
	"$authorized_key"
ssh-keygen -l -f "$authorized_key" >/dev/null
if grep -q 'BEGIN .*PRIVATE KEY' "$authorized_key"; then
	echo 'FAIL authorized-key input contains private-key material' >&2
	exit 1
fi

project_commit=$(git -C "$repo" rev-parse HEAD)
[[ -z $(git -C "$repo" status --porcelain --untracked-files=normal) ]] || {
	echo 'FAIL commit or remove repository changes before rootfs staging' >&2
	exit 1
}
if [[ ! -r /proc/sys/fs/binfmt_misc/qemu-aarch64 ]] ||
	! grep -qx enabled /proc/sys/fs/binfmt_misc/qemu-aarch64; then
	echo 'FAIL enabled qemu-aarch64 binfmt registration is required' >&2
	exit 1
fi

mapfile -t releases < <(
	tar -tzf "$modules" |
		sed -n 's|^lib/modules/\([^/]*\)/.*|\1|p' |
		LC_ALL=C sort -u
)
[[ ${#releases[@]} == 1 ]]
kernel_release=${releases[0]}

stage_volume=rog5-arch-stage-$$
verify_volume=rog5-arch-verify-$$
cache_volume=rog5-arch-pacman-cache
for volume in "$stage_volume" "$verify_volume"; do
	! podman volume exists "$volume" || {
		echo "FAIL refusing existing volume $volume" >&2
		exit 1
	}
done
for volume in "$stage_volume" "$verify_volume"; do
	podman volume create "$volume" >/dev/null
done
podman volume exists "$cache_volume" ||
	podman volume create "$cache_volume" >/dev/null

succeeded=0
cleanup() {
	if [[ $succeeded == 1 ]]; then
		podman volume rm "$stage_volume" "$verify_volume" >/dev/null
	else
		printf 'Retained failed staging volumes: %s %s\n' \
			"$stage_volume" "$verify_volume" >&2
	fi
}
trap cleanup EXIT

podman run --rm --network none \
	--mount "type=volume,source=$stage_volume,target=/stage" \
	--mount "type=bind,source=$rootfs,target=/input/rootfs.tar.gz,readonly" \
	"$builder_image" \
	bsdtar --acls --xattrs --fflags -xpf /input/rootfs.tar.gz -C /stage

podman run --rm --network none \
	--mount "type=volume,source=$stage_volume,target=/stage" \
	--mount type=bind,source=/dev,target=/stage/dev \
	--mount type=bind,source=/proc,target=/stage/proc \
	--mount type=bind,source=/sys,target=/stage/sys \
	--tmpfs /stage/run \
	"$builder_image" chroot /stage /bin/uname -m |
	grep -qx aarch64

podman run --rm \
	--mount "type=volume,source=$stage_volume,target=/stage" \
	--mount "type=bind,source=$repo,target=/stage/workspace/repo,readonly" \
	--mount "type=bind,source=$modules,target=/stage/input/modules.tar.gz,readonly" \
	"${firmware_mount[@]}" \
	"${indicator_mount[@]}" \
	--mount "type=bind,source=$authorized_key,target=/stage/input/authorized_key,readonly" \
	--mount "type=volume,source=$cache_volume,target=/stage/var/cache/pacman/pkg" \
	--mount type=bind,source=/dev,target=/stage/dev \
	--mount type=bind,source=/proc,target=/stage/proc \
	--mount type=bind,source=/sys,target=/stage/sys \
	--tmpfs /stage/run \
	--env "ROOTFS_SHA256=$rootfs_hash" \
	--env "MODULES_SHA256=$modules_hash" \
	--env "TARGET_KERNEL_RELEASE=$kernel_release" \
	--env "PROJECT_COMMIT=$project_commit" \
	--env "INDICATOR_SHA256=$indicator_hash" \
	--env "ARCH_DEVICE_STAGE=$device_stage" \
	"$builder_image" \
	/bin/bash "/stage$stage_runner"

output_dir=$(dirname "$output")
output_name=$(basename "$output")
tar_part=$output_dir/$output_name.tar.part
gzip_part=$output.part
[[ ! -e $tar_part && ! -e $gzip_part ]]

podman run --rm --network none \
	--mount "type=volume,source=$stage_volume,target=/stage,readonly" \
	--mount "type=bind,source=$output_dir,target=/output" \
	"$builder_image" \
	bsdtar --acls --xattrs --fflags \
	-cpf "/output/$(basename "$tar_part")" \
	-C /stage --exclude ./workspace --exclude ./input \
	--exclude './dev/*' --exclude './proc/*' --exclude './sys/*' \
	--exclude './run/*' .
podman run --rm --network none \
	--mount "type=bind,source=$output_dir,target=/output" \
	"$builder_image" sh -c \
	"gzip -n -c '/output/$(basename "$tar_part")' >'/output/$(basename "$gzip_part")'"
unlink "$tar_part"

podman run --rm --network none \
	--mount "type=volume,source=$verify_volume,target=/stage" \
	--mount "type=bind,source=$gzip_part,target=/input/rootfs.tar.gz,readonly" \
	"$builder_image" \
	bsdtar --acls --xattrs --fflags -xpf /input/rootfs.tar.gz -C /stage
podman run --rm --network none \
	--mount "type=volume,source=$verify_volume,target=/stage" \
	--mount "type=bind,source=$repo,target=/stage/workspace/repo,readonly" \
	--mount type=bind,source=/dev,target=/stage/dev \
	--mount type=bind,source=/proc,target=/stage/proc \
	--mount type=bind,source=/sys,target=/stage/sys \
	--tmpfs /stage/run \
	--env "TARGET_KERNEL_RELEASE=$kernel_release" \
	--env "INDICATOR_SHA256=$indicator_hash" \
	"$builder_image" chroot /stage /bin/bash \
	"$rootfs_verifier"

mv "$gzip_part" "$output"
succeeded=1
size=$(stat -c %s "$output")
hash=$(sha256sum "$output" | cut -d ' ' -f 1)
printf 'PASS staged Arch rootfs kernel=%s size=%s sha256=%s\n' \
	"$kernel_release" "$size" "$hash"
