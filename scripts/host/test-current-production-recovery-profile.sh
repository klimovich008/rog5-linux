#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
gate=$repo/scripts/host/run-stable-recovery-live-gate.sh
claim_consumer=$repo/scripts/host/consume-exact-boot-claim.py
boot_policy=$repo/manifests/temporary-boot-images.tsv
profile=headless-diagnostic-host-rendezvous-v3-live-v10
tmp=$(mktemp -d)
build_tmp=
cleanup_build_tmp() {
	local path=$build_tmp
	[[ -n $path ]] || return 0
	if [[ -d $path ]]; then
		# cp -al preserves the sealed bundle's read-only directory mode. Only
		# directories are chmodded: regular files remain hard links to retained
		# evidence and must not have their modes changed.
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

[[ $(awk -v profile="$profile" '
	/^# Historical profiles retain/ { contracts = 1 }
	!contracts && index($0, "\t" profile ")") == 1 { count++ }
	END { print count + 0 }
' "$gate") -eq 1 ]] ||
	fail 'current production live profile case is not unique'
case_source=$(awk -v profile="$profile" '
	index($0, "\t" profile ")") == 1 { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
[[ -n $case_source ]] || fail 'current production live profile is absent'
case_unindented=$(sed 's/^[[:space:]]*//' <<<"$case_source")
for assignment in \
	expected_boot_image=build/host-rendezvous-v10-observer-production-20260811-r1/wrapper/repack/stable-recovery-a.avb.img \
	expected_kernel=2e5d6e1766aab790dd1d1718125244886d376ffb73aa6b761571b12820b3061c \
	expected_raw=067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff \
	expected_initramfs=d9a3fba43abf0c3e456feb2e7f9da5e043df1e7cdef2e33112e0313358ae98d8 \
	expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31 \
	expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800 \
	expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef \
	expected_target_id=headless-netroot-early-diag-v2 \
	expected_bundle=headless-netroot-early-diag-v2 \
	expected_bundle_profile=diagnostic-initramfs-v1 \
	expected_generation_record=13821062e2d3d83100b125d853197e56cbe2240d34881917c234f151524038ed \
	expected_avb_salt=983545d63d606b6cf2965127139a4f43944fd8161f3667895d0544d49ee96af3 \
	expected_avb_digest=da72637ff12a53fcd6bc2db9963e94506cd1f68f002bd30e6e51afe97145ab97 \
	recovery_init=\$repo/initramfs/recovery-init
do
	grep -Fxq "$assignment" <<<"$case_unindented" ||
		fail "current production live profile omits $assignment"
done

contract_source=$(awk -v profile="$profile" '
	/^# Historical profiles retain/ { contracts = 1 }
	contracts && index($0, "\t" profile " |") == 1 { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
contract_unindented=$(sed 's/^[[:space:]]*//' <<<"$contract_source")
[[ -n $contract_source ]] ||
	fail 'current production profile lacks an initramfs contract'
grep -Fxq 'initramfs_contract=exact-a600000-v1' <<<"$contract_unindented" ||
	fail 'current profile does not select the exact initramfs contract'
grep -Fxq 'initramfs_verifier_expected=-' <<<"$contract_unindented" ||
	fail 'current exact initramfs contract does not reject an external identity'
historical_contract=$(awk '
	/^# Historical profiles retain/ { contracts = 1 }
	contracts && /^\thistorical-2026-07-29 / { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
grep -Fq $'\tinitramfs_contract=historical-pinned-v1' \
	<<<"$historical_contract" ||
	fail 'historical profiles no longer select their pinned contract'
grep -Fq $'\tinitramfs_verifier_expected=$expected_initramfs' \
	<<<"$historical_contract" ||
	fail 'historical initramfs contracts no longer pass their pinned identity'
grep -Fq \
	'"$source_initramfs" "$recovery_init" "$control" "$fetcher" "$verifier" \' \
	"$gate" || fail 'live gate does not pass the repository-owned recovery init'
[[ $(grep -Fc 'check_hash "$source_initramfs" "$expected_initramfs"' \
	"$gate") -eq 1 ]] ||
	fail 'current archive identity check is not unique'
[[ $(grep -Fc 'verify-stable-recovery-initramfs.sh' "$gate") -eq 1 ]] ||
	fail 'stable-recovery initramfs verifier call is not unique'
hash_line=$(grep -n 'check_hash "$source_initramfs" "$expected_initramfs"' \
	"$gate" | cut -d: -f1)
verify_line=$(grep -n 'verify-stable-recovery-initramfs.sh' "$gate" | cut -d: -f1)
[[ $hash_line =~ ^[0-9]+$ && $verify_line =~ ^[0-9]+$ &&
	$hash_line -lt $verify_line ]] ||
	fail 'current archive identity is not checked before exact init verification'

run_policy() {
	local recovery=$1 trust=$2 manifest=$3 host_verifier=$4 bundle=$5
	env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE="$profile" \
		BUNDLE="$bundle" \
		RECOVERY_SHA256="$recovery" \
		TRUST_KEY_SHA256="$trust" \
		MANIFEST_SHA256="$manifest" \
		HOST_VERIFIER_SHA256="$host_verifier" \
		bash "$gate" policy-preflight
}

exact=(
	fb5fce1a8cd7849b70ea52052caf8dc524708f94eb2d5756b29abb2074523452
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc
	03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0
	headless-netroot-early-diag-v2
)
fields=(recovery trust manifest host-verifier bundle)
errors=(
	'retention-observed successor recovery image is not pinned'
	'retention-observed successor trust key is not pinned'
	'retention-observed successor runtime manifest is not pinned'
	'retention-observed successor host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v2'
)

policy=$(run_policy "${exact[@]}")
grep -Fxq "recovery_profile=$profile" <<<"$policy"
grep -Fxq "recovery_sha256=${exact[0]}" <<<"$policy"
grep -Fxq 'authority=none' <<<"$policy"
grep -Fxq 'result=PASS' <<<"$policy"

for index in "${!fields[@]}"; do
	mutation=("${exact[@]}")
	if ((index == 4)); then
		mutation[$index]=wrong-current-bundle
	else
		mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
	fi
	if run_policy "${mutation[@]}" >"$tmp/out" 2>"$tmp/err"; then
		fail "current production policy accepted wrong ${fields[$index]}"
	fi
	grep -Fq "${errors[$index]}" "$tmp/err" ||
		fail "wrong ${fields[$index]} returned an unexpected rejection"
done

[[ $(awk -F '\t' '$2 == "allow" { count++ } END { print count + 0 }' \
	"$boot_policy") == 2 ]] || fail 'current temporary-boot policy is not exact'
grep -Fq "\"$profile\":" "$claim_consumer" ||
	fail 'current production live profile lacks an exact claim registration'
[[ $(awk -F '\t' -v name="build/host-rendezvous-v10-observer-production-20260811-r1/wrapper/repack/stable-recovery-a.avb.img" \
	'$1 == name && $2 == "allow" { count++ } END { print count + 0 }' \
	"$boot_policy") == 1 ]] ||
	fail 'current production live image is not uniquely admitted'

production_root=$repo/build/host-rendezvous-v10-observer-production-20260811-r1
if [[ -d $production_root ]]; then
	artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE="$profile" \
			LIVE_BUILD_ROOT="$production_root/wrapper" \
			RECOVERY_COMPONENT_ROOT="$production_root/recovery" \
			TRUST_KEY="$production_root/recovery/ephemeral-public.raw" \
			BUNDLE_ROOT="$production_root/bundle-a" \
			BUNDLE="${exact[4]}" \
			RECOVERY_SHA256="${exact[0]}" \
			TRUST_KEY_SHA256="${exact[1]}" \
			MANIFEST_SHA256="${exact[2]}" \
			HOST_VERIFIER_SHA256="${exact[3]}" \
			bash "$gate" artifact-preflight
	)
	grep -Fxq \
		"PASS stable-recovery artifact preflight profile=$profile image_sha256=${exact[0]}" \
		<<<"$artifact" || fail 'current production artifact preflight did not pass'

	build_tmp=$(mktemp -d "$repo/build/current-production-profile-test.XXXXXX")
	cp -al -- "$production_root"/. "$build_tmp"/
	for relative in \
		wrapper/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz \
		wrapper/wrapper-b/rog5-kexec-stage-initramfs.cpio.gz \
		recovery/initramfs-a/rog5-stable-recovery.cpio.gz \
		recovery/initramfs-b/rog5-stable-recovery.cpio.gz
	do
		cp --reflink=never -- "$build_tmp/$relative" "$build_tmp/$relative.mutated"
		printf X >>"$build_tmp/$relative.mutated"
		chmod --reference="$build_tmp/$relative" "$build_tmp/$relative.mutated"
		mv -f -- "$build_tmp/$relative.mutated" "$build_tmp/$relative"
	done
	if env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE="$profile" \
		LIVE_BUILD_ROOT="$build_tmp/wrapper" \
		RECOVERY_COMPONENT_ROOT="$build_tmp/recovery" \
		TRUST_KEY="$build_tmp/recovery/ephemeral-public.raw" \
		BUNDLE_ROOT="$build_tmp/bundle-a" \
		BUNDLE="${exact[4]}" \
		RECOVERY_SHA256="${exact[0]}" \
		TRUST_KEY_SHA256="${exact[1]}" \
		MANIFEST_SHA256="${exact[2]}" \
		HOST_VERIFIER_SHA256="${exact[3]}" \
		bash "$gate" artifact-preflight >"$tmp/out" 2>"$tmp/err"
	then
		fail 'current production artifact preflight accepted a changed initramfs'
	fi
	[[ ! -s $tmp/out && $(wc -l <"$tmp/err") -eq 1 &&
		$(cat "$tmp/err") == \
		"FAIL identity mismatch: $build_tmp/recovery/initramfs-a/rog5-stable-recovery.cpio.gz" ]] ||
		fail 'changed initramfs did not fail first at its independent hash'
	finished_build_tmp=$build_tmp
	cleanup_build_tmp
	[[ ! -e $finished_build_tmp ]] ||
		fail 'current production profile test left its private build copy behind'
else
	[[ ${REQUIRE_CURRENT_PRODUCTION_ARTIFACT:-0} != 1 ]] ||
		fail 'required current production artifact output is absent'
	echo 'SKIP current production artifact preflight: ignored clean-twin output absent' >&2
fi

echo 'PASS current production recovery profile is exact, one-use, and artifact-verified'
