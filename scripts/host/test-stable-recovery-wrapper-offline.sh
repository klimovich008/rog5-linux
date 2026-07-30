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

cache_profile=$repo/configs/recovery-wrapper-cache/asus-5.4-stable-recovery-v1.json
cache_tool=$repo/scripts/host/stable-recovery-wrapper-cache.py
source_tree_tool=$repo/scripts/host/kernel-source-seal.py
build_script=
repack_script=$repo/scripts/device/repack-android-boot-v3.sh
builder_verifier=$repo/scripts/host/verify-steam-deck-builder.sh
source_volume=${SOURCE_VOLUME:-rog5-asus-v12a-source}
builder_image=${KERNEL_BUILDER_IMAGE:-localhost/rog5-kernel-builder:ubuntu-24.04}
builder_profile=${ROG5_WRAPPER_BUILDER_PROFILE:-historical-2026-07-29}
reference_config=${REFERENCE_CONFIG:-}
template=${BOOT_TEMPLATE:-}
mkbootimg_dir=${MKBOOTIMG_DIR:-$repo/artifacts/android-boot-tools-v1}
avbtool=${AVBTOOL:-$mkbootimg_dir/avbtool.py}
cache_root=${STABLE_RECOVERY_WRAPPER_CACHE_ROOT:-$repo/build/stable-recovery-wrapper-cache}
jobs=${JOBS:-1}
partition_size=100663296

expected_source=3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8
expected_reference_config=
expected_template=
expected_mkbootimg=d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a
expected_unpack=7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef
expected_avbtool=6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff
expected_builder_id=c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec
expected_builder_digest=sha256:8513960144bb1ca77878a1364c03fb100c8b87fffb8440fd37a6cc4fc0043b41
expected_wrapper_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
expected_compiler='Ubuntu clang version 18.1.3 (1ubuntu1)'
cache_enabled=
builder_report=
reference_config_profile=

case $builder_profile in
historical-2026-07-29)
	cache_enabled=1
	build_script=$repo/scripts/device/build-asus-kexec-stage.sh
	reference_config_profile=historical-running-config-v1
	reference_config=${reference_config:-$repo/../work/linux-server/kernel-33.0210.0210.200/config-5.4.210-qgki-perf}
	template=${template:-$repo/artifacts/recovery-stage-v18/boot-5.4.210-kexec-stage-builtin-recovery.raw.img}
	expected_reference_config=e8605b42cd27d372cea195811c3ff064346390a235572a0018c9dc8d048b5da4
	expected_template=292a14e212826a250de501d4d502dda6973097ed172cd9324d82cf88d82fd657
	;;
steam-deck-asus-5.4-v1)
	cache_enabled=0
	build_script=$repo/scripts/device/build-asus-kexec-stage-successor.sh
	reference_config_profile=accepted-wrapper-v18-v1
	reference_config=${reference_config:-$repo/artifacts/recovery-stage-v18/config-5.4.210-kexec-stage-builtin-recovery}
	template=${template:-$repo/artifacts/recovery-wrapper-inputs-v1/rog5-canonical-boot-v3-template.raw.img}
	expected_reference_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
	expected_template=95be17d48ec61d00a4e8c92be754c8a8345f93685ce05d412a6d3a6aceba6e02
	;;
*)
	fail "unsupported wrapper builder profile: $builder_profile"
	;;
esac
build_script_relative=${build_script#"$repo"/}
[[ $build_script_relative != "$build_script" &&
	$build_script_relative != /* ]] ||
	fail 'wrapper build script is outside the repository'

for command in awk cmp cp cut find git grep mkdir podman python3 realpath \
	sha256sum stat tee touch tr; do
	command -v "$command" >/dev/null ||
		fail "missing wrapper-test command: $command"
done
[[ $jobs =~ ^[1-9][0-9]*$ ]] || fail 'JOBS must be a positive integer'
[[ $source_volume =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] ||
	fail 'invalid source-volume name'
[[ $builder_image != -* ]] || fail 'invalid kernel-builder image name'
grep -Fqx 'set -f' "$repack_script" ||
	fail 'boot repacker does not disable pathname expansion'

for input in "$initramfs_a" "$initramfs_b" "$reference_config" "$template" \
	"$mkbootimg_dir/mkbootimg.py" "$mkbootimg_dir/unpack_bootimg.py" "$avbtool" \
	"$source_tree_tool" "$build_script" "$repack_script"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing regular nonsymlink input: $input"
done
if [[ $cache_enabled == 1 ]]; then
	for input in "$cache_profile" "$cache_tool"; do
		[[ -f $input && ! -L $input ]] ||
			fail "missing regular nonsymlink cache input: $input"
	done
else
	[[ -f $builder_verifier && ! -L $builder_verifier &&
		-x $builder_verifier ]] ||
		fail 'missing qualified Steam Deck builder verifier'
fi
initramfs_a=$(realpath "$initramfs_a")
initramfs_b=$(realpath "$initramfs_b")
reference_config=$(realpath "$reference_config")
template=$(realpath "$template")
mkbootimg_dir=$(realpath "$mkbootimg_dir")
avbtool=$(realpath "$avbtool")
output_root=$(realpath -m "$output_root")
cache_root=$(realpath -m "$cache_root")
case $output_root in
	"$repo"/build/*) ;;
	*) fail 'output root must be below the ignored repository build directory' ;;
esac
git -C "$repo" check-ignore -q "$output_root" ||
	fail 'output root is not ignored by Git'
if [[ $cache_enabled == 1 ]]; then
	case $cache_root in
		"$repo"/build/*) ;;
		*) fail 'wrapper cache must be below the ignored repository build directory' ;;
	esac
	git -C "$repo" check-ignore -q "$cache_root" ||
		fail 'wrapper cache is not ignored by Git'
	case $output_root in
		"$cache_root"|"$cache_root"/*) fail 'wrapper output overlaps its cache' ;;
	esac
	case $cache_root in
		"$output_root"|"$output_root"/*) fail 'wrapper cache overlaps its output' ;;
	esac
fi
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
if [[ $builder_profile == historical-2026-07-29 ]]; then
	[[ $(podman image inspect "$builder_image" --format '{{.Id}}') == \
		"$expected_builder_id" ]] ||
		fail 'unexpected historical kernel-builder image ID'
	[[ $(podman image inspect "$builder_image" --format '{{.Digest}}') == \
		"$expected_builder_digest" ]] ||
		fail 'unexpected historical kernel-builder image digest'
else
	builder_report=$("$builder_verifier" "$builder_image")
	grep -Fxq 'PASS qualified Steam Deck ASUS 5.4 kernel builder' \
		<<<"$builder_report" ||
		fail 'Steam Deck builder verifier did not return its success marker'
fi
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
printf 'builder_profile=%s\n' "$builder_profile" \
	>"$output_root/builder-profile.txt"
printf 'reference_config_profile=%s\n' "$reference_config_profile" \
	>>"$output_root/builder-profile.txt"
if [[ -n $builder_report ]]; then
	printf '%s\n' "$builder_report" \
		>"$output_root/builder-qualification.txt"
fi

seal_source() {
	podman run --rm --network=none --security-opt label=disable \
		-v "$source_volume:/root/src:ro" \
		-v "$repo:/workspace:ro" \
		"$builder_image" \
		python3 /workspace/scripts/host/kernel-source-seal.py \
		/root/src/msm-5.4
}

source_seal_before=$output_root/source-seal-before.txt
source_seal_after=$output_root/source-seal-after.txt
seal_source >"$source_seal_before"
if [[ $cache_enabled == 1 ]]; then
	cache_input_args=(
		--profile "$cache_profile"
		--source-seal "$source_seal_before"
		--source-tree-tool "$source_tree_tool"
		--reference-config "$reference_config"
		--initramfs "$initramfs_a"
		--build-script "$build_script"
		--repack-script "$repack_script"
		--boot-template "$template"
		--mkbootimg "$mkbootimg_dir/mkbootimg.py"
		--unpack-bootimg "$mkbootimg_dir/unpack_bootimg.py"
		--avbtool "$avbtool"
	)
	python3 "$cache_tool" input-key "${cache_input_args[@]}" \
		>"$output_root/cache-input.txt"
fi

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
		-e REFERENCE_CONFIG_PROFILE="$reference_config_profile" \
		-e INITRAMFS_SOURCE=/inputs/rog5-stable-recovery.cpio.gz \
		-e INITRAMFS_SHA256="$initramfs_sha256" \
		-e JOBS="$jobs" \
		"$builder_image" \
		"/workspace/$build_script_relative"
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
	"$repack_script" \
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
	"$repack_script" \
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
wrapper_config_sha256=$(
	sha256sum "$output_root/wrapper-a/asus-kexec-stage/.config" |
		cut -d ' ' -f 1
)
[[ $wrapper_config_sha256 == "$expected_wrapper_config" ]] ||
	fail 'wrapper output config identity changed'
wrapper_image_sha256=$(
	sha256sum \
		"$output_root/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image" |
		cut -d ' ' -f 1
)
{
	printf 'source_sha256=%s\n' "$expected_source"
	if [[ $builder_profile == steam-deck-asus-5.4-v1 ]]; then
		printf 'reference_config_profile=%s\n' "$reference_config_profile"
	fi
	printf 'kexec_file=0\n'
	printf 'initramfs_sha256=%s\n' "$initramfs_sha256"
	printf 'compiler=%s\n' "$expected_compiler"
	printf '%s  /root/build/asus-kexec-stage/.config\n' \
		"$wrapper_config_sha256"
	printf '%s  /root/build/asus-kexec-stage/arch/arm64/boot/Image\n' \
		"$wrapper_image_sha256"
} >"$output_root/inspection/expected-build-meta.txt"
cmp "$output_root/inspection/expected-build-meta.txt" \
	"$output_root/wrapper-a/asus-kexec-stage/build-meta.txt" ||
	fail 'wrapper build metadata changed'
seal_source >"$source_seal_after"
cmp "$source_seal_before" "$source_seal_after" ||
	fail 'ASUS source tree changed across the clean wrapper builds'
if [[ $cache_enabled == 1 ]]; then
	python3 "$cache_tool" publish \
		"${cache_input_args[@]}" \
		--source-seal-after "$source_seal_after" \
		--cache-root "$cache_root" \
		--build-a "$output_root/wrapper-a" \
		--build-b "$output_root/wrapper-b" \
		--raw-a "$output_root/repack/stable-recovery-a.raw.img" \
		--raw-b "$output_root/repack/stable-recovery-b.raw.img" \
		--avb-a "$output_root/repack/stable-recovery-a.avb.img" \
		--avb-b "$output_root/repack/stable-recovery-b.avb.img" |
		tee "$output_root/cache-publication.txt"
else
	echo 'cache_publication=disabled-for-qualified-steam-deck-twin-build' \
		>"$output_root/cache-publication.txt"
fi
printf 'builder_profile=%s\n' "$builder_profile"
printf 'cache_publication=%s\n' \
	"$([[ $cache_enabled == 1 ]] && echo content-addressed || echo disabled)"
echo 'PASS two clean stable-recovery wrapper/raw/AVB builds are byte-identical; test-only and not boot-authorized'
