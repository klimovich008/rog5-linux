#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

usage() {
	fail 'usage: run-observation-recovery-live-gate.sh {policy-preflight|artifact-preflight|preflight|boot}'
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
action=${1:-policy-preflight}
profile=${ROG5_OBSERVATION_RECOVERY_PROFILE:-}
expected_profile=observation-host-rendezvous-v3-haven-production-hold-v1
expected_recovery=3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b

case $action in
	policy-preflight | artifact-preflight | preflight | boot) ;;
	*) usage ;;
esac

[[ $profile == "$expected_profile" ]] ||
	fail 'current observation recovery profile is not pinned'

recovery_identity=${OBSERVER_RECOVERY_SHA256:-}
[[ $recovery_identity =~ ^[0-9a-f]{64}$ &&
	$recovery_identity == "$expected_recovery" ]] ||
	fail 'current observation recovery image is not pinned'

case $action in
	preflight | boot)
		fail 'current observation HOLD profile is offline-only and not boot-authorized'
		;;
	policy-preflight)
		printf '%s\n' \
			"recovery_profile=$profile" \
			"recovery_sha256=$recovery_identity" \
			'authority=none' \
			'boot_authority=none' \
			'boot_result_protocol=rog5-retention-boot-result-v1' \
			'boot_result_live_producer=none' \
			'result=PASS'
		exit 0
		;;
esac

for command_name in realpath stat sha256sum python3; do
	command -v "$command_name" >/dev/null 2>&1 ||
		fail "required command is unavailable: $command_name"
done

build_root=$(realpath -e -- "$repo/build") ||
	fail 'repository build root is unavailable'
requested_root=${OBSERVER_BUILD_ROOT:-}
[[ -n $requested_root && ! -L $requested_root ]] ||
	fail 'observation build root is missing or unsafe'
observation_root=$(realpath -e -- "$requested_root") ||
	fail 'observation build root is missing or unsafe'
[[ -d $observation_root && $observation_root == "$build_root/"* ]] ||
	fail 'observation build root is outside the repository build directory'

root_metadata=$(stat -c '%u:%g:%a:%d:%i' -- "$observation_root") ||
	fail 'cannot inspect observation build root'
IFS=: read -r root_uid root_gid root_mode _ <<<"$root_metadata"
[[ $root_uid == "$(id -u)" && $root_gid == "$(id -g)" &&
	$root_mode == 700 ]] ||
	fail 'observation build root owner or mode is unsafe'

artifact_records=(
	'2f0a29db13dd5e9b64b60bc20a20e3a4458609df8425c3366c1a34e3c267836e|88|builder-profile.txt|observer artifact identity mismatch: builder-profile.txt'
	'b3032dd2c946df30f487fba84772b40ac902ca5b0ef2f5c3b06f9912840494f6|753|builder-qualification.txt|observer artifact identity mismatch: builder-qualification.txt'
	'01b33d9305cd0884aab19e55d886563a75182b8c877559af21d0ff16ca767c90|63|cache-publication.txt|observer artifact identity mismatch: cache-publication.txt'
	'116d21a57514b25fa7c43137b925bce94d9d83e9bbb7287bcceb2a0a50fd8b11|823|observation-wrapper-evidence.txt|observer evidence identity mismatch'
	'4c4958385b9d0f270c368642c484c84e4c60ea23d18f68c00e37ca67a8637344|221|source-seal-after.txt|observer artifact identity mismatch: source-seal-after.txt'
	'4c4958385b9d0f270c368642c484c84e4c60ea23d18f68c00e37ca67a8637344|221|source-seal-before.txt|observer artifact identity mismatch: source-seal-before.txt'
	'fa111672ebfb511b154c8a6aba19b4af18d2615f856aab0ff49b9848154bb5d6|847|inspection/avb-info.txt|observer artifact identity mismatch: inspection/avb-info.txt'
	'6fc200de779ef1e626bee166acc2eaf6a0d1f65c597c7660fa20a2b0b4153fb1|612|inspection/boot-args.lines|observer artifact identity mismatch: inspection/boot-args.lines'
	'eedb7deb64aa42de582245b121f4ea581d0b1e21e9eb49f3591e98df8f63ef59|48400896|inspection/unpacked/kernel|observer Image identity mismatch'
	'b2440d8ccc2f22b9c9072a2404569d2a5843f7dab186a2ccac307a929a4941ad|5374739|inspection/unpacked/ramdisk|observer initramfs identity mismatch'
	'3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b|100663296|repack/stable-recovery-a.avb.img|observer AVB identity mismatch'
	'5daf0919d38c9f7b1ffde85a8c5e9aabdbba526bcafa1a528bd8c31e27dda171|53784576|repack/stable-recovery-a.raw.img|observer raw image identity mismatch'
	'3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b|100663296|repack/stable-recovery-b.avb.img|observer AVB identity mismatch'
	'5daf0919d38c9f7b1ffde85a8c5e9aabdbba526bcafa1a528bd8c31e27dda171|53784576|repack/stable-recovery-b.raw.img|observer raw image identity mismatch'
	'df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f|185763|wrapper-a/asus-kexec-stage/.config|observer config identity mismatch'
	'eedb7deb64aa42de582245b121f4ea581d0b1e21e9eb49f3591e98df8f63ef59|48400896|wrapper-a/asus-kexec-stage/arch/arm64/boot/Image|observer Image identity mismatch'
	'c9556a8640716b59fd57885440eb1f95512361c2ea163c71f69b0573704ab3fd|491|wrapper-a/asus-kexec-stage/build-meta.txt|observer metadata identity mismatch'
	'b2440d8ccc2f22b9c9072a2404569d2a5843f7dab186a2ccac307a929a4941ad|5374739|wrapper-a/rog5-kexec-stage-initramfs.cpio.gz|observer initramfs identity mismatch'
	'df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f|185763|wrapper-b/asus-kexec-stage/.config|observer config identity mismatch'
	'eedb7deb64aa42de582245b121f4ea581d0b1e21e9eb49f3591e98df8f63ef59|48400896|wrapper-b/asus-kexec-stage/arch/arm64/boot/Image|observer Image identity mismatch'
	'c9556a8640716b59fd57885440eb1f95512361c2ea163c71f69b0573704ab3fd|491|wrapper-b/asus-kexec-stage/build-meta.txt|observer metadata identity mismatch'
	'b2440d8ccc2f22b9c9072a2404569d2a5843f7dab186a2ccac307a929a4941ad|5374739|wrapper-b/rog5-kexec-stage-initramfs.cpio.gz|observer initramfs identity mismatch'
)

declare -A initial_state

artifact_state() {
	local relative=$1 path resolved metadata uid gid mode links
	path=$observation_root/$relative
	[[ -f $path && ! -L $path ]] ||
		fail "unsafe observation artifact: $relative"
	resolved=$(realpath -e -- "$path") ||
		fail "unsafe observation artifact: $relative"
	[[ $resolved == "$path" ]] ||
		fail "unsafe observation artifact: $relative"
	metadata=$(stat -c '%u:%g:%a:%h:%d:%i:%s:%Y:%Z' -- "$path") ||
		fail "unsafe observation artifact: $relative"
	IFS=: read -r uid gid mode links _ <<<"$metadata"
	[[ $uid == "$(id -u)" && $gid == "$(id -g)" && $links == 1 ]] ||
		fail "unsafe observation artifact: $relative"
	(( (8#$mode & 8#022) == 0 )) ||
		fail "unsafe observation artifact: $relative"
	printf '%s\n' "$metadata"
}

verify_artifact_identity() {
	local expected_digest=$1 expected_size=$2 relative=$3 message=$4
	local path actual_digest actual_size
	path=$observation_root/$relative
	actual_size=$(stat -c %s -- "$path") || fail "$message"
	[[ $actual_size == "$expected_size" ]] || fail "$message"
	actual_digest=$(sha256sum -- "$path") || fail "$message"
	actual_digest=${actual_digest%% *}
	[[ $actual_digest == "$expected_digest" ]] || fail "$message"
}

verify_repository_verifier() {
	local path=$1 metadata uid gid mode links size digest
	[[ -f $path && ! -L $path ]] ||
		fail 'observation recovery verifier is missing or unsafe'
	metadata=$(stat -c '%u:%g:%a:%h:%s' -- "$path") ||
		fail 'cannot inspect observation recovery verifier'
	IFS=: read -r uid gid mode links size <<<"$metadata"
	[[ $uid == "$(id -u)" && $gid == "$(id -g)" && $mode == 755 &&
		$links == 1 && $size == 19876 ]] ||
		fail 'observation recovery verifier identity is not exact'
	digest=$(sha256sum -- "$path") ||
		fail 'cannot hash observation recovery verifier'
	digest=${digest%% *}
	[[ $digest == c3c75dd55167e898edd92a04e4afd2aae1c3d4cf826cd1011ac32c6e9f8214c2 ]] ||
		fail 'observation recovery verifier identity is not exact'
}

for record in "${artifact_records[@]}"; do
	IFS='|' read -r expected_digest expected_size relative message <<<"$record"
	initial_state[$relative]=$(artifact_state "$relative")
	verify_artifact_identity "$expected_digest" "$expected_size" "$relative" "$message"
done

verifier=$repo/scripts/host/verify-observation-recovery-wrapper.py
verify_repository_verifier "$verifier"
if report=$(
	python3 "$verifier" \
		"$observation_root/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz" \
		"$observation_root/wrapper-b/rog5-kexec-stage-initramfs.cpio.gz" \
		"$observation_root"
); then
	:
else
	status=$?
	exit "$status"
fi

retained_report=$(<"$observation_root/observation-wrapper-evidence.txt")
[[ $report == "$retained_report" ]] ||
	fail 'observer verifier report differs from retained evidence'
grep -Fxq "unsigned_avb_sha256=$expected_recovery" <<<"$report" ||
	fail 'observer verifier did not attest the pinned AVB image'
grep -Fxq 'authority=none' <<<"$report" ||
	fail 'observer verifier did not preserve authority-free state'
grep -Fxq 'candidate=none' <<<"$report" ||
	fail 'observer verifier unexpectedly described a candidate'
grep -Fxq 'boot_authority=none' <<<"$report" ||
	fail 'observer verifier unexpectedly described boot authority'

for record in "${artifact_records[@]}"; do
	IFS='|' read -r expected_digest expected_size relative message <<<"$record"
	[[ $(artifact_state "$relative") == "${initial_state[$relative]}" ]] ||
		fail "observation artifact changed during verification: $relative"
	verify_artifact_identity "$expected_digest" "$expected_size" "$relative" "$message"
done

final_root_metadata=$(stat -c '%u:%g:%a:%d:%i' -- "$observation_root") ||
	fail 'cannot revalidate observation build root'
[[ $final_root_metadata == "$root_metadata" ]] ||
	fail 'observation build root changed during verification'

printf '%s\n' \
	"PASS observation-recovery artifact preflight profile=$profile image_sha256=$recovery_identity"
