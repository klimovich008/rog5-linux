#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
base=${1:-$repo/artifacts/network-root-v3/rog5-network-root-initramfs.cpio.gz}
output_root=${2:-$repo/artifacts/headless-network-root-v1}
base_size=5840728
base_sha=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
verifier_size=326920
verifier_sha=bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58
output_name=rog5-headless-network-root-initramfs.cpio.gz
output_size=5978369
output_sha=819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5
profile=$repo/configs/kernel-builder/steam-deck-recovery-arm64-v1.json
profile_sha=18fc6f392d4a84cf15eab867de89b7a8760c54568793d5fe07f5a50725402278
builder_verifier=$repo/scripts/host/verify-steam-deck-recovery-builders.sh
runner=$repo/scripts/host/run-private-arm64-binfmt.sh
builder_image=localhost/rog5-persistent-root-verifier:alpine-3.24-deck-v1
builder_image_id=a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e
builder_image_digest=sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa
builder=$repo/scripts/device/build-network-root-initramfs.sh
archive_verifier=$repo/scripts/device/verify-network-root-initramfs.sh
cpio_path=$repo/scripts/host/qualified-cpio-path
report_name=headless-network-root-initramfs-rebuild.txt

for command_name in chmod cmp cut dirname find grep gzip install mkdir \
	mktemp mv podman readelf realpath sha256sum stat; do
	command -v "$command_name" >/dev/null ||
		fail "missing headless initramfs rebuild command: $command_name"
done
for input in "$profile" "$builder_verifier" "$runner" "$builder" \
	"$archive_verifier" "$cpio_path/cpio"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing or linked headless initramfs input: ${input#"$repo"/}"
done
for executable in "$builder_verifier" "$runner" "$builder" \
	"$archive_verifier" "$cpio_path/cpio"; do
	[[ -x $executable ]] ||
		fail "headless initramfs input lost executable mode: ${executable#"$repo"/}"
done
[[ $(sha256sum "$profile" | cut -d ' ' -f 1) == "$profile_sha" ]] ||
	fail 'qualified recovery-builder profile changed'
[[ -f $base && ! -L $base && -r $base ]] ||
	fail 'accepted network-root-v3 base is absent, linked, or unreadable'
[[ $(stat -c %s "$base") == "$base_size" ]] ||
	fail 'accepted network-root-v3 base size changed'
[[ $(sha256sum "$base" | cut -d ' ' -f 1) == "$base_sha" ]] ||
	fail 'accepted network-root-v3 base hash changed'
gzip -t "$base" ||
	fail 'accepted network-root-v3 base is not a valid gzip stream'

base=$(realpath -e "$base")
case $output_root in
	''|/|/dev|/dev/*|/proc|/proc/*|/sys|/sys/*|/run|/run/*)
		fail 'unsafe headless initramfs output root'
		;;
esac
output_parent=$(dirname "$output_root")
mkdir -p "$output_parent"
output_parent=$(realpath -e "$output_parent")
output_root=$output_parent/$(basename "$output_root")
[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'refusing existing headless initramfs output root'

work=$(mktemp -d)
publish=$(mktemp -d "$output_parent/.headless-network-root-v1.XXXXXX")
cleanup() {
	find "$work" -depth -delete 2>/dev/null || true
	if [[ -n ${publish:-} && -e $publish ]]; then
		find "$publish" -depth -delete 2>/dev/null || true
	fi
}
trap cleanup EXIT HUP INT TERM
mkdir "$work/verifier-a" "$work/verifier-b" \
	"$work/initramfs-a" "$work/initramfs-b"

"$builder_verifier" >"$work/builder-qualification.txt"
grep -Fqx 'PASS qualified rootless Steam Deck ARM64 recovery builders' \
	"$work/builder-qualification.txt" ||
	fail 'recovery-builder qualification did not return its success marker'
[[ $(podman image inspect "$builder_image" --format '{{.Id}}') == \
	"$builder_image_id" ]] ||
	fail 'persistent-root verifier builder image ID changed after qualification'
[[ $(podman image inspect "$builder_image" --format '{{.Digest}}') == \
	"$builder_image_digest" ]] ||
	fail 'persistent-root verifier builder image digest changed after qualification'

build_verifier() {
	destination=$1
	"$runner" podman run --rm --pull=never --network=none \
		--platform linux/arm64 --security-opt label=disable \
		-v "$repo:/workspace:ro" \
		-v "$destination:/output" \
		--workdir /workspace --env CC=gcc \
		"$builder_image" \
		/workspace/scripts/device/build-persistent-root-verifier-static.sh \
		/output/persistent-root-verify
}

build_verifier "$work/verifier-a" >"$work/verifier-a.txt"
build_verifier "$work/verifier-b" >"$work/verifier-b.txt"
verifier_a=$work/verifier-a/persistent-root-verify
verifier_b=$work/verifier-b/persistent-root-verify
cmp "$verifier_a" "$verifier_b" ||
	fail 'two qualified persistent-root verifier builds differ'
for verifier in "$verifier_a" "$verifier_b"; do
	[[ -f $verifier && ! -L $verifier && -x $verifier &&
		$(stat -c %s "$verifier") == "$verifier_size" &&
		$(sha256sum "$verifier" | cut -d ' ' -f 1) == \
			"$verifier_sha" ]] ||
		fail 'qualified persistent-root verifier identity changed'
	readelf -h "$verifier" | grep -q 'Machine:.*AArch64' ||
		fail 'qualified persistent-root verifier is not AArch64'
	if readelf -l "$verifier" |
		grep -q 'Requesting program interpreter'; then
		fail 'qualified persistent-root verifier is dynamically linked'
	fi
done

build_archive() {
	verifier=$1
	output=$2
	PATH="$cpio_path:/usr/bin:/bin:/usr/sbin:/sbin" \
	NETWORK_ROOT_VERIFIER="$verifier" \
		"$builder" "$base" "$output"
}

archive_a=$work/initramfs-a/$output_name
archive_b=$work/initramfs-b/$output_name
build_archive "$verifier_a" "$archive_a" >"$work/initramfs-a.txt"
build_archive "$verifier_b" "$archive_b" >"$work/initramfs-b.txt"
cmp "$archive_a" "$archive_b" ||
	fail 'two qualified headless initramfs builds differ'
[[ $(stat -c %s "$archive_a") == "$output_size" &&
	$(sha256sum "$archive_a" | cut -d ' ' -f 1) == "$output_sha" ]] ||
	fail 'headless network-root initramfs identity changed'
PATH="$cpio_path:/usr/bin:/bin:/usr/sbin:/sbin" \
NETWORK_ROOT_VERIFIER="$verifier_a" \
	"$archive_verifier" "$archive_a" >"$work/archive-verification.txt"
grep -Fqx \
	'PASS credential-free network-root initramfs, static AArch64 root verifier, retained exitrd source, and required BusyBox applets' \
	"$work/archive-verification.txt" ||
	fail 'headless initramfs verifier did not return its success marker'

builder_report_sha=$(
	sha256sum "$work/builder-qualification.txt" | cut -d ' ' -f 1
)
install -m 0644 "$archive_a" "$publish/$output_name"
{
	printf '%s\n' \
		'schema=rog5-headless-network-root-initramfs-rebuild-v1' \
		'state=exact-historical-bytes-reproduced' \
		'boot_authority=none' \
		"base_size=$base_size" \
		"base_sha256=$base_sha" \
		"builder_profile_sha256=$profile_sha" \
		"builder_image_id=$builder_image_id" \
		"builder_image_digest=$builder_image_digest" \
		"builder_qualification_sha256=$builder_report_sha" \
		"persistent_root_verifier_size=$verifier_size" \
		"persistent_root_verifier_sha256=$verifier_sha" \
		"archive_size=$output_size" \
		"archive_sha256=$output_sha" \
		'reproducibility=twin-verifier-and-twin-initramfs-builds'
} >"$publish/$report_name"
chmod 0644 "$publish/$report_name"

mv -T -- "$publish" "$output_root"
publish=
trap - EXIT HUP INT TERM
find "$work" -depth -delete

sha256sum "$output_root/$output_name"
echo 'PASS reproduced exact headless network-root initramfs with qualified rootless ARM64 builders'
