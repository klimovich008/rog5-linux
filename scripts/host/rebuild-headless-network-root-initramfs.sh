#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
base=${1:-$repo/artifacts/network-root-v3/rog5-network-root-initramfs.cpio.gz}
mode=${3:-normal}
base_size=5840728
base_sha=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
legacy_verifier_size=326920
legacy_verifier_sha=bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58
verifier_size=
verifier_sha=
reporter_size=67288
reporter_sha=6a87ffa7bcbef1dcef9353d2ada3b34888f6bcb881fe38d417c3ae97e6767d01
profile=$repo/configs/kernel-builder/steam-deck-recovery-arm64-v1.json
profile_sha=780d564013d30c278b709939db6402347243eb2866065c6cbbe1788a946b842f
builder_verifier=$repo/scripts/host/verify-steam-deck-recovery-builders.sh
runner=$repo/scripts/host/run-private-arm64-binfmt.sh
builder_image=localhost/rog5-persistent-root-verifier:alpine-3.24-deck-v1
builder_image_id=a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e
builder_image_digest=sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa
builder=$repo/scripts/device/build-network-root-initramfs.sh
archive_verifier=$repo/scripts/device/verify-network-root-initramfs.sh
reporter_builder=$repo/scripts/device/build-early-target-diag.sh
reporter_source=$repo/tools/early_target_diag/rog5-early-target-diag.c
publisher=$repo/scripts/host/publish-noreplace.py
cpio_path=$repo/scripts/host/qualified-cpio-path
active_builder=$builder
active_archive_verifier=$archive_verifier
verifier_workspace=$repo
case $mode in
	normal)
		verifier_size=$legacy_verifier_size
		verifier_sha=$legacy_verifier_sha
		output_root=${2:-$repo/artifacts/headless-network-root-v1}
		output_name=rog5-headless-network-root-initramfs.cpio.gz
		output_size=5978369
		output_sha=819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5
		report_name=headless-network-root-initramfs-rebuild.txt
		report_schema=rog5-headless-network-root-initramfs-rebuild-v1
		report_state=exact-historical-bytes-reproduced
		reproducibility=twin-verifier-and-twin-initramfs-builds
		legacy_source_commit=27a270f2955c57f61e2cb8aeae0be23b31223499
		legacy_source_tree=56668d6b44907ffb3644c04d6d9ff3a7c1f49b95
		;;
	diagnostic)
		verifier_size=327968
		verifier_sha=2bcead5ca06751d2744cdf0199802ba7ea089257ff383301d1c371f1ef60e28f
		output_root=${2:-$repo/artifacts/early-target-diagnostic-v7}
		output_name=rog5-early-target-diagnostic-initramfs.cpio.gz
		output_size=6014751
		output_sha=635e641c62f894d4bc150cd3fec9ae965f0f9a769ff7b856ad5ca2432530ed2b
		report_name=early-target-diagnostic-initramfs-rebuild.txt
		report_schema=rog5-early-target-diagnostic-initramfs-rebuild-v7
		report_state=exact-pinned-bytes-reproduced
		reproducibility=twin-verifier-reporter-and-twin-initramfs-builds
		;;
	*) fail 'mode must be normal or diagnostic' ;;
esac

for command_name in chmod cmp cut dirname find grep gzip install mkdir \
	mktemp podman readelf realpath sha256sum stat; do
	command -v "$command_name" >/dev/null ||
		fail "missing headless initramfs rebuild command: $command_name"
done
if [[ $mode == normal ]]; then
	for command_name in git tar; do
		command -v "$command_name" >/dev/null ||
			fail "missing historical initramfs command: $command_name"
	done
fi
for input in "$profile" "$builder_verifier" "$runner" "$publisher" \
	"$cpio_path/cpio"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing or linked headless initramfs input: ${input#"$repo"/}"
done
for executable in "$builder_verifier" "$runner" "$publisher" \
	"$cpio_path/cpio"; do
	[[ -x $executable ]] ||
		fail "headless initramfs input lost executable mode: ${executable#"$repo"/}"
done
if [[ $mode == diagnostic ]]; then
	for input in "$builder" "$archive_verifier" "$reporter_builder" \
		"$reporter_source"; do
		[[ -f $input && ! -L $input ]] ||
			fail "missing or linked diagnostic initramfs input: ${input#"$repo"/}"
	done
	for executable in "$builder" "$archive_verifier" "$reporter_builder"; do
		[[ -x $executable ]] ||
			fail "diagnostic initramfs input lost executable mode: ${executable#"$repo"/}"
	done
fi
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
if [[ $mode == diagnostic ]]; then
	mkdir "$work/reporter-a" "$work/reporter-b"
else
	resolved_commit=$(git -C "$repo" rev-parse --verify \
		"$legacy_source_commit^{commit}")
	resolved_tree=$(git -C "$repo" rev-parse --verify \
		"$legacy_source_commit^{tree}")
	[[ $resolved_commit == "$legacy_source_commit" &&
		$resolved_tree == "$legacy_source_tree" ]] ||
		fail 'historical normal-initramfs source identity changed'
	mkdir "$work/legacy-source"
	git -C "$repo" archive --format=tar "$legacy_source_commit" -- \
		initramfs/network-root-init \
		initramfs/network-root-shutdown \
		scripts/device/build-network-root-initramfs.sh \
		scripts/device/build-persistent-root-verifier-static.sh \
		scripts/device/verify-network-root-initramfs.sh \
		tools/persistent-root-verify.c |
		tar -x -C "$work/legacy-source"
	active_builder=$work/legacy-source/scripts/device/build-network-root-initramfs.sh
	active_archive_verifier=$work/legacy-source/scripts/device/verify-network-root-initramfs.sh
	verifier_workspace=$work/legacy-source
	[[ -x $active_builder && -x $active_archive_verifier ]] ||
		fail 'historical normal-initramfs source lost executable mode'
fi

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
	local destination=$1
	"$runner" podman run --rm --pull=never --network=none \
		--platform linux/arm64 --security-opt label=disable \
		-v "$verifier_workspace:/workspace:ro" \
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

reporter_a=
reporter_b=
if [[ $mode == diagnostic ]]; then
	build_reporter() {
		local destination=$1
		"$runner" podman run --rm --pull=never --network=none \
			--platform linux/arm64 --security-opt label=disable \
			-v "$repo:/workspace:ro" \
			-v "$destination:/output" \
			--workdir /workspace \
			"$builder_image" \
			/workspace/scripts/device/build-early-target-diag.sh \
			/workspace/tools/early_target_diag/rog5-early-target-diag.c \
			/output/rog5-early-target-diag
	}

	build_reporter "$work/reporter-a" >"$work/reporter-a.txt"
	build_reporter "$work/reporter-b" >"$work/reporter-b.txt"
	reporter_a=$work/reporter-a/rog5-early-target-diag
	reporter_b=$work/reporter-b/rog5-early-target-diag
	cmp "$reporter_a" "$reporter_b" ||
		fail 'two qualified early-target reporter builds differ'
	for reporter in "$reporter_a" "$reporter_b"; do
		[[ -f $reporter && ! -L $reporter && -x $reporter &&
			$(stat -c %s "$reporter") == "$reporter_size" &&
			$(sha256sum "$reporter" | cut -d ' ' -f 1) == \
				"$reporter_sha" ]] ||
			fail 'qualified early-target reporter identity changed'
		readelf -h "$reporter" | grep -q 'Machine:.*AArch64' ||
			fail 'qualified early-target reporter is not AArch64'
		if readelf -l "$reporter" |
			grep -q 'Requesting program interpreter'; then
			fail 'qualified early-target reporter is dynamically linked'
		fi
	done
fi

build_archive() {
	local verifier=$1
	local reporter=$2
	local output=$3
	if [[ $mode == diagnostic ]]; then
		PATH="$cpio_path:/usr/bin:/bin:/usr/sbin:/sbin" \
		NETWORK_ROOT_VERIFIER="$verifier" \
		NETWORK_ROOT_DIAGNOSTIC_REPORTER="$reporter" \
			"$active_builder" "$base" "$output"
	else
		PATH="$cpio_path:/usr/bin:/bin:/usr/sbin:/sbin" \
		NETWORK_ROOT_VERIFIER="$verifier" \
			"$active_builder" "$base" "$output"
	fi
}

archive_a=$work/initramfs-a/$output_name
archive_b=$work/initramfs-b/$output_name
build_archive "$verifier_a" "$reporter_a" "$archive_a" \
	>"$work/initramfs-a.txt"
build_archive "$verifier_b" "$reporter_b" "$archive_b" \
	>"$work/initramfs-b.txt"
cmp "$archive_a" "$archive_b" ||
	fail 'two qualified headless initramfs builds differ'
observed_output_size=$(stat -c %s "$archive_a")
observed_output_sha=$(sha256sum "$archive_a" | cut -d ' ' -f 1)
[[ $observed_output_size == "$output_size" &&
	$observed_output_sha == "$output_sha" ]] ||
	fail "network-root initramfs identity changed: size=$observed_output_size sha256=$observed_output_sha"
if [[ $mode == diagnostic ]]; then
	PATH="$cpio_path:/usr/bin:/bin:/usr/sbin:/sbin" \
	NETWORK_ROOT_VERIFIER="$verifier_a" \
	NETWORK_ROOT_DIAGNOSTIC_REPORTER="$reporter_a" \
		"$active_archive_verifier" "$archive_a" \
		>"$work/archive-verification.txt"
else
	PATH="$cpio_path:/usr/bin:/bin:/usr/sbin:/sbin" \
	NETWORK_ROOT_VERIFIER="$verifier_a" \
		"$active_archive_verifier" "$archive_a" \
		>"$work/archive-verification.txt"
fi
grep -Fqx \
	'PASS credential-free network-root initramfs, static AArch64 root verifier, retained exitrd source, and required BusyBox applets' \
	"$work/archive-verification.txt" ||
	fail 'headless initramfs verifier did not return its success marker'

builder_report_sha=$(
	sha256sum "$work/builder-qualification.txt" | cut -d ' ' -f 1
)
install -m 0644 "$archive_a" "$publish/$output_name"
if [[ $mode == diagnostic ]]; then
	install -m 0755 "$reporter_a" "$publish/rog5-early-target-diag"
fi
{
	printf '%s\n' \
		"schema=$report_schema" \
		"state=$report_state" \
		'boot_authority=none' \
		"base_size=$base_size" \
		"base_sha256=$base_sha" \
		"builder_profile_sha256=$profile_sha" \
		"builder_image_id=$builder_image_id" \
		"builder_image_digest=$builder_image_digest" \
		"builder_qualification_sha256=$builder_report_sha" \
		"persistent_root_verifier_size=$verifier_size" \
		"persistent_root_verifier_sha256=$verifier_sha"
	if [[ $mode == diagnostic ]]; then
		printf '%s\n' \
			"early_target_reporter_size=$reporter_size" \
			"early_target_reporter_sha256=$reporter_sha"
	else
		printf '%s\n' \
			"historical_source_commit=$legacy_source_commit" \
			"historical_source_tree=$legacy_source_tree"
	fi
	printf '%s\n' \
		"archive_size=$output_size" \
		"archive_sha256=$output_sha" \
		"reproducibility=$reproducibility"
} >"$publish/$report_name"
chmod 0644 "$publish/$report_name"

"$publisher" "$publish" "$output_root" ||
	fail 'headless initramfs output publication collided'
publish=
trap - EXIT HUP INT TERM
find "$work" -depth -delete

sha256sum "$output_root/$output_name"
if [[ $mode == diagnostic ]]; then
	echo 'PASS reproduced exact early-target diagnostic initramfs with qualified rootless ARM64 builders'
else
	echo 'PASS reproduced exact headless network-root initramfs with qualified rootless ARM64 builders'
fi
