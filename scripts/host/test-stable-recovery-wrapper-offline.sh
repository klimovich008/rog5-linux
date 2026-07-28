#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
initramfs_a=${1:?usage: test-stable-recovery-wrapper-offline.sh INITRAMFS_A INITRAMFS_B OUTPUT_ROOT}
initramfs_b=${2:?missing second stable-recovery initramfs}
output_root=${3:?missing ignored output root}

source_volume=${SOURCE_VOLUME:-rog5-asus-v12a-source}
builder_image=${KERNEL_BUILDER_IMAGE:-localhost/rog5-kernel-builder:ubuntu-24.04}
reference_config=${REFERENCE_CONFIG:-$repo/../work/linux-server/kernel-33.0210.0210.200/config-5.4.210-qgki-perf}
template=${BOOT_TEMPLATE:-$repo/artifacts/recovery-stage-v18/boot-5.4.210-kexec-stage-builtin-recovery.raw.img}
mkbootimg_dir=${MKBOOTIMG_DIR:-$repo/../work/linux-server/mkbootimg}
avbtool=${AVBTOOL:-$repo/../work/linux-server/avb/avbtool.py}
jobs=${JOBS:-1}
partition_size=100663296

expected_source=3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8
expected_reference_config=e8605b42cd27d372cea195811c3ff064346390a235572a0018c9dc8d048b5da4
expected_template=292a14e212826a250de501d4d502dda6973097ed172cd9324d82cf88d82fd657
expected_mkbootimg=d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a
expected_unpack=7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef
expected_avbtool=6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff
expected_builder_id=34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941
expected_builder_digest=sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c

for command in awk cmp cp cut find git grep mkdir podman python3 realpath \
	sha256sum stat touch tr; do
	command -v "$command" >/dev/null ||
		fail "missing wrapper-test command: $command"
done
[[ $jobs =~ ^[1-9][0-9]*$ ]] || fail 'JOBS must be a positive integer'
[[ $source_volume =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] ||
	fail 'invalid source-volume name'
[[ $builder_image != -* ]] || fail 'invalid kernel-builder image name'
grep -Fqx 'set -f' "$repo/scripts/device/repack-android-boot-v3.sh" ||
	fail 'boot repacker does not disable pathname expansion'

for input in "$initramfs_a" "$initramfs_b" "$reference_config" "$template" \
	"$mkbootimg_dir/mkbootimg.py" "$mkbootimg_dir/unpack_bootimg.py" "$avbtool"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing regular nonsymlink input: $input"
done
initramfs_a=$(realpath "$initramfs_a")
initramfs_b=$(realpath "$initramfs_b")
reference_config=$(realpath "$reference_config")
template=$(realpath "$template")
mkbootimg_dir=$(realpath "$mkbootimg_dir")
avbtool=$(realpath "$avbtool")
output_root=$(realpath -m "$output_root")
case $output_root in
	"$repo"/build/*) ;;
	*) fail 'output root must be below the ignored repository build directory' ;;
esac
git -C "$repo" check-ignore -q "$output_root" ||
	fail 'output root is not ignored by Git'
[[ ! -d $output_root ||
	-z $(find "$output_root" -mindepth 1 -maxdepth 1 -print -quit) ]] ||
	fail 'refusing nonempty output root'

check_hash() {
	input=$1
	expected=$2
	actual=$(sha256sum "$input" | cut -d ' ' -f 1)
	[[ $actual == "$expected" ]] ||
		fail "input hash mismatch: $input"
}

check_hash "$reference_config" "$expected_reference_config"
check_hash "$template" "$expected_template"
check_hash "$mkbootimg_dir/mkbootimg.py" "$expected_mkbootimg"
check_hash "$mkbootimg_dir/unpack_bootimg.py" "$expected_unpack"
check_hash "$avbtool" "$expected_avbtool"
cmp "$initramfs_a" "$initramfs_b" ||
	fail 'stable-recovery initramfs inputs are not byte-identical'
initramfs_sha256=$(sha256sum "$initramfs_a" | cut -d ' ' -f 1)

podman image exists "$builder_image" ||
	fail "missing pinned kernel builder: $builder_image"
[[ $(podman image inspect "$builder_image" --format '{{.Id}}') == \
	"$expected_builder_id" ]] ||
	fail 'unexpected kernel-builder image ID'
[[ $(podman image inspect "$builder_image" --format '{{.Digest}}') == \
	"$expected_builder_digest" ]] ||
	fail 'unexpected kernel-builder image digest'
podman volume exists "$source_volume" ||
	fail "missing ASUS source volume: $source_volume"
source_sha256=$(
	podman run --rm --network=none --security-opt label=disable \
		-v "$source_volume:/root/src:ro" \
		"$builder_image" /bin/sh -eu -c \
		"sed -n 's/^source_sha256=//p' /root/src/msm-5.4/.rog5-kexec-source"
)
[[ $source_sha256 == "$expected_source" ]] ||
	fail 'unexpected ASUS source-volume identity'

mkdir -p "$output_root/wrapper-a" "$output_root/wrapper-b" \
	"$output_root/repack" "$output_root/inspection" \
	"$output_root/glob-cwd"

build_wrapper() {
	suffix=$1
	initramfs=$2
	wrapper_root=$output_root/wrapper-$suffix
	podman run --rm --network=none --security-opt label=disable \
		-v "$source_volume:/root/src:ro" \
		-v "$repo:/workspace:ro" \
		-v "$initramfs:/inputs/rog5-stable-recovery.cpio.gz:ro" \
		-v "$wrapper_root:/root/build" \
		-v "$reference_config:/reference.config:ro" \
		-e SOURCE_DIR=/root/src/msm-5.4 \
		-e OUTPUT_DIR=/root/build/asus-kexec-stage \
		-e REFERENCE_CONFIG=/reference.config \
		-e INITRAMFS_SOURCE=/inputs/rog5-stable-recovery.cpio.gz \
		-e INITRAMFS_SHA256="$initramfs_sha256" \
		-e JOBS="$jobs" \
		"$builder_image" \
		/workspace/scripts/device/build-asus-kexec-stage.sh
}

build_wrapper a "$initramfs_a"
build_wrapper b "$initramfs_b"
"$repo/scripts/device/compare-asus-kexec-stage-builds.sh" \
	"$output_root/wrapper-a" "$output_root/wrapper-b" asus-kexec-stage
cmp "$output_root/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz" \
	"$initramfs_a"
cmp "$output_root/wrapper-b/rog5-kexec-stage-initramfs.cpio.gz" \
	"$initramfs_b"

repack_wrapper() {
	suffix=$1
	wrapper_root=$output_root/wrapper-$suffix
	"$repo/scripts/device/repack-android-boot-v3.sh" \
		"$template" \
		"$wrapper_root/asus-kexec-stage/arch/arm64/boot/Image" \
		"$wrapper_root/rog5-kexec-stage-initramfs.cpio.gz" \
		"$mkbootimg_dir" "$avbtool" \
		"$output_root/repack/stable-recovery-$suffix.raw.img" \
		"$output_root/repack/stable-recovery-$suffix.avb.img" \
		"$partition_size" '' 'rog5.recovery_cidr'
}

repack_wrapper a
repack_wrapper b
cmp "$output_root/repack/stable-recovery-a.raw.img" \
	"$output_root/repack/stable-recovery-b.raw.img"
cmp "$output_root/repack/stable-recovery-a.avb.img" \
	"$output_root/repack/stable-recovery-b.avb.img"
[[ $(stat -c %s "$output_root/repack/stable-recovery-a.avb.img") == \
	"$partition_size" ]]

python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$output_root/repack/stable-recovery-a.raw.img" \
	--out "$output_root/inspection/unpacked" \
	>"$output_root/inspection/boot-info.txt"
grep -qx 'boot image header version: 3' \
	"$output_root/inspection/boot-info.txt"
cmp "$output_root/inspection/unpacked/kernel" \
	"$output_root/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image"
cmp "$output_root/inspection/unpacked/ramdisk" \
	"$output_root/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz"
if grep -q '^CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=' \
	"$output_root/wrapper-a/asus-kexec-stage/.config"
then
	fail 'ASUS wrapper falsely claims target-only UFS discovery mode'
fi

python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$output_root/repack/stable-recovery-a.raw.img" \
	--out "$output_root/inspection/args" \
	--format=mkbootimg --null >"$output_root/inspection/boot-args.nul"
tr '\000' '\n' <"$output_root/inspection/boot-args.nul" \
	>"$output_root/inspection/boot-args.lines"
command_line=$(
	awk '$0 == "--cmdline" { getline; print; exit }' \
		"$output_root/inspection/boot-args.lines"
)
for token in \
	init=/init \
	selinux=0 \
	rog5linux.test=1 \
	rog5.recovery_timeout=180
do
	count=$(
		printf '%s\n' "$command_line" |
			tr ' ' '\n' |
			grep -Fxc "$token" || true
	)
	[[ $count == 1 ]] || fail "missing or duplicate boot token: $token"
done
cidr_count=$(
	printf '%s\n' "$command_line" |
		tr ' ' '\n' |
		grep -Ec '^rog5\.recovery_cidr=' || true
)
[[ $cidr_count == 0 ]] || fail 'legacy recovery address survived repack'
if printf '%s\n' "$command_line" |
	tr ' ' '\n' |
	grep -Eq '^rog5\.ufs_discovery='
then
	fail 'target-only UFS discovery token reached the ASUS wrapper'
fi

touch "$output_root/glob-cwd/rog5.glob=alpha" \
	"$output_root/glob-cwd/rog5.glob=beta"
(
	cd "$output_root/glob-cwd"
	"$repo/scripts/device/repack-android-boot-v3.sh" \
		"$template" \
		"$output_root/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image" \
		"$output_root/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz" \
		"$mkbootimg_dir" "$avbtool" \
		"$output_root/repack/glob.raw.img" \
		"$output_root/repack/glob.avb.img" \
		"$partition_size" 'rog5.glob=[ab]*' 'rog5.recovery_cidr'
)
python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$output_root/repack/glob.raw.img" \
	--out "$output_root/inspection/glob-args" \
	--format=mkbootimg --null >"$output_root/inspection/glob-args.nul"
tr '\000' '\n' <"$output_root/inspection/glob-args.nul" \
	>"$output_root/inspection/glob-args.lines"
glob_command_line=$(
	awk '$0 == "--cmdline" { getline; print; exit }' \
		"$output_root/inspection/glob-args.lines"
)
glob_count=$(
	printf '%s\n' "$glob_command_line" |
		tr ' ' '\n' |
		grep -Fxc 'rog5.glob=[ab]*' || true
)
[[ $glob_count == 1 ]] ||
	fail 'pathname expansion changed the literal boot override'
glob_cidr_count=$(
	printf '%s\n' "$glob_command_line" |
		tr ' ' '\n' |
		grep -Ec '^rog5\.recovery_cidr=' || true
)
[[ $glob_cidr_count == 0 ]] ||
	fail 'legacy recovery address survived adversarial glob repack'

cp "$output_root/repack/stable-recovery-a.avb.img" \
	"$output_root/inspection/boot.img"
python3 "$avbtool" verify_image \
	--image "$output_root/inspection/boot.img"
python3 "$avbtool" info_image \
	--image "$output_root/inspection/boot.img" \
	>"$output_root/inspection/avb-info.txt"
grep -q '^Algorithm:[[:space:]]*NONE$' \
	"$output_root/inspection/avb-info.txt"
grep -q '^      Partition Name:[[:space:]]*boot$' \
	"$output_root/inspection/avb-info.txt"

sha256sum \
	"$output_root/wrapper-a/asus-kexec-stage/.config" \
	"$output_root/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image" \
	"$output_root/repack/stable-recovery-a.raw.img" \
	"$output_root/repack/stable-recovery-a.avb.img"
echo 'PASS two clean stable-recovery wrapper/raw/AVB builds are byte-identical; test-only and not boot-authorized'
