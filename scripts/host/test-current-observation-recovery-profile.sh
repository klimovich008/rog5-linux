#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
gate=$repo/scripts/host/run-observation-recovery-live-gate.sh
claim_consumer=$repo/scripts/host/consume-exact-boot-claim.py
boot_policy=$repo/manifests/temporary-boot-images.tsv
profile=observation-host-rendezvous-v3-haven-production-hold-v1
expected_avb=3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b
tmp=$(mktemp -d)
build_tmp=
cleanup_build_tmp() {
	local path=$build_tmp
	[[ -n $path ]] || return 0
	if [[ -d $path ]]; then
		find "$path" -type d -exec chmod u+rwx -- {} +
		rm -rf -- "$path"
	fi
	build_tmp=
}
cleanup() {
	cleanup_build_tmp
	rm -rf -- "$tmp"
}
trap cleanup EXIT HUP INT TERM

[[ -x $gate ]] || fail 'current observation-recovery HOLD gate is absent'
bash -n "$gate"
! grep -Fq fastboot "$gate" ||
	fail 'observation-recovery HOLD gate contains a fastboot surface'
! grep -Fq consume-exact-boot-claim.py "$gate" ||
	fail 'observation-recovery HOLD gate can consume a boot claim'
grep -Fq 'c3c75dd55167e898edd92a04e4afd2aae1c3d4cf826cd1011ac32c6e9f8214c2' "$gate" ||
	fail 'observation-recovery HOLD gate does not pin its repository verifier'

verifier_function=$(
	awk '
		/^verify_repository_verifier\(\) \{/ { copy=1 }
		copy { print }
		copy && /^}/ { exit }
	' "$gate"
)
[[ $verifier_function == verify_repository_verifier* ]] ||
	fail 'observation verifier identity check is not extractable'
run_verifier_fixture() {
	local path=$1
	(
		fail() { exit 1; }
		eval "$verifier_function"
		verify_repository_verifier "$path"
	)
}
verifier=$repo/scripts/host/verify-observation-recovery-wrapper.py
run_verifier_fixture "$verifier"
cp -- "$verifier" "$tmp/changed-verifier.py"
printf X >>"$tmp/changed-verifier.py"
chmod 0755 "$tmp/changed-verifier.py"
if run_verifier_fixture "$tmp/changed-verifier.py"; then
	fail 'observer gate accepted a changed repository verifier'
fi
ln -s -- "$verifier" "$tmp/verifier-link.py"
if run_verifier_fixture "$tmp/verifier-link.py"; then
	fail 'observer gate accepted a symlinked repository verifier'
fi

run_policy() {
	local identity=$1
	env -i PATH="$PATH" HOME="$HOME" \
		ROG5_OBSERVATION_RECOVERY_PROFILE="$profile" \
		OBSERVER_RECOVERY_SHA256="$identity" \
		bash "$gate" policy-preflight
}

policy=$(run_policy "$expected_avb")
grep -Fxq "recovery_profile=$profile" <<<"$policy"
grep -Fxq "recovery_sha256=$expected_avb" <<<"$policy"
grep -Fxq 'authority=none' <<<"$policy"
grep -Fxq 'boot_authority=none' <<<"$policy"
grep -Fxq 'boot_result_protocol=rog5-retention-boot-result-v1' <<<"$policy"
grep -Fxq 'boot_result_live_producer=none' <<<"$policy"
grep -Fxq 'result=PASS' <<<"$policy"

if run_policy aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
	>"$tmp/out" 2>"$tmp/err"
then
	fail 'observer policy accepted a wrong recovery identity'
fi
[[ ! -s $tmp/out && $(wc -l <"$tmp/err") -eq 1 &&
	$(cat "$tmp/err") == \
	'FAIL current observation recovery image is not pinned' ]] ||
	fail 'wrong observer identity returned an unexpected rejection'

for action in preflight boot; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
		ROG5_OBSERVATION_RECOVERY_PROFILE="$profile" \
		OBSERVER_BUILD_ROOT="$repo/build/unused-observer-root" \
		OBSERVER_RECOVERY_SHA256="$expected_avb" \
		bash "$gate" "$action" >"$tmp/out" 2>"$tmp/err"
	then
		fail "current observation HOLD profile reached $action"
	fi
	[[ ! -s $tmp/out && $(wc -l <"$tmp/err") -eq 1 &&
		$(cat "$tmp/err") == \
		'FAIL current observation HOLD profile is offline-only and not boot-authorized' ]] ||
		fail "current observation $action emitted output before its rejection"
done

[[ $(awk -F '\t' '$2 == "allow" { count++ } END { print count + 0 }' \
	"$boot_policy") == 0 ]] || fail 'current temporary-boot policy is not empty'
! grep -Fq "$profile" "$claim_consumer" ||
	fail 'current observation HOLD profile has a consumable claim'

artifact_files=(
	builder-profile.txt
	builder-qualification.txt
	cache-publication.txt
	observation-wrapper-evidence.txt
	source-seal-after.txt
	source-seal-before.txt
	inspection/avb-info.txt
	inspection/boot-args.lines
	inspection/unpacked/kernel
	inspection/unpacked/ramdisk
	repack/stable-recovery-a.avb.img
	repack/stable-recovery-a.raw.img
	repack/stable-recovery-b.avb.img
	repack/stable-recovery-b.raw.img
	wrapper-a/asus-kexec-stage/.config
	wrapper-a/asus-kexec-stage/arch/arm64/boot/Image
	wrapper-a/asus-kexec-stage/build-meta.txt
	wrapper-a/rog5-kexec-stage-initramfs.cpio.gz
	wrapper-b/asus-kexec-stage/.config
	wrapper-b/asus-kexec-stage/arch/arm64/boot/Image
	wrapper-b/asus-kexec-stage/build-meta.txt
	wrapper-b/rog5-kexec-stage-initramfs.cpio.gz
)

run_artifact() {
	local root=$1
	env -i PATH="$PATH" HOME="$HOME" \
		ROG5_OBSERVATION_RECOVERY_PROFILE="$profile" \
		OBSERVER_BUILD_ROOT="$root" \
		OBSERVER_RECOVERY_SHA256="$expected_avb" \
		bash "$gate" artifact-preflight
}

materialize_fixture() {
	local source=$1 relative destination
	build_tmp=$(mktemp -d "$repo/build/current-observation-profile-test.XXXXXX")
	chmod 0700 "$build_tmp"
	for relative in "${artifact_files[@]}"; do
		destination=$build_tmp/$relative
		mkdir -p -- "$(dirname -- "$destination")"
		cp --reflink=auto -- "$source/$relative" "$destination"
	done
}

production_root=$repo/build/observation-recovery-haven-offline-20260810-r1
if [[ -d $production_root ]]; then
	materialize_fixture "$production_root"
	fixture_report=$(run_artifact "$build_tmp")
	grep -Fxq \
		"PASS observation-recovery artifact preflight profile=$profile image_sha256=$expected_avb" \
		<<<"$fixture_report" || fail 'sparse observer artifact fixture did not pass'

	ln -- "$build_tmp/builder-profile.txt" "$build_tmp/hardlink-peer"
	if run_artifact "$build_tmp" >"$tmp/out" 2>"$tmp/err"; then
		fail 'current observation preflight accepted a hard-linked artifact'
	fi
	[[ ! -s $tmp/out && $(wc -l <"$tmp/err") -eq 1 &&
		$(cat "$tmp/err") == \
		'FAIL unsafe observation artifact: builder-profile.txt' ]] ||
		fail 'hard-linked observer artifact returned an unexpected rejection'
	unlink -- "$build_tmp/hardlink-peer"

	for relative in \
		wrapper-a/rog5-kexec-stage-initramfs.cpio.gz \
		wrapper-b/rog5-kexec-stage-initramfs.cpio.gz
	do
		printf X >>"$build_tmp/$relative"
	done
	if run_artifact "$build_tmp" >"$tmp/out" 2>"$tmp/err"; then
		fail 'current observation preflight accepted a changed initramfs'
	fi
	[[ ! -s $tmp/out && $(wc -l <"$tmp/err") -eq 1 &&
		$(cat "$tmp/err") == \
		'FAIL observer initramfs identity mismatch' ]] ||
		fail 'changed observer initramfs did not fail at its independent hash'
	finished_build_tmp=$build_tmp
	cleanup_build_tmp
	[[ ! -e $finished_build_tmp ]] ||
		fail 'current observation profile test left its private build copy behind'
else
	[[ ${REQUIRE_CURRENT_OBSERVATION_ARTIFACT:-0} != 1 ]] ||
		fail 'required current observation artifact output is absent'
	echo 'SKIP current observation artifact preflight: ignored clean-twin output absent' >&2
fi

echo 'PASS current observation recovery profile is exact, authority-free, and offline-only'
