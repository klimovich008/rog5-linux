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
profile=headless-diagnostic-host-rendezvous-v3-haven-production-hold-v1
tmp=$(mktemp -d)
build_tmp=
cleanup() {
	[[ -z $build_tmp ]] || rm -rf -- "$build_tmp"
	rm -rf -- "$tmp"
}
trap cleanup EXIT HUP INT TERM

[[ $(awk -v profile="$profile" '
	/^# Historical profiles retain/ { contracts = 1 }
	!contracts && $0 == "\t" profile ")" { count++ }
	END { print count + 0 }
' "$gate") -eq 1 ]] ||
	fail 'current production HOLD profile case is not unique'
case_source=$(awk -v profile="$profile" '
	index($0, "\t" profile ")") == 1 { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
[[ -n $case_source ]] || fail 'current production HOLD profile is absent'
case_unindented=$(sed 's/^[[:space:]]*//' <<<"$case_source")
for assignment in \
	expected_kernel=8a600acfc6f7e01f9eb932e0a04174079d6ee68142c44fad819fe96bbd34325d \
	expected_raw=ea9e90fdbf1bfdbe75816462ae79897e6cf7749d9e87607be2b033b7cfb06517 \
	expected_initramfs=ab0a3ee219684c994af386cb60e5280dcc4269457b196f96ca3928acce691f0b \
	expected_control=68142abd8daafed2f1d017bd0ae07407be9dcac17e57d2294a162d2b58bf2840 \
	expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800 \
	expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef \
	expected_target_id=headless-netroot-early-diag-v2 \
	expected_bundle=headless-netroot-early-diag-v2 \
	expected_bundle_profile=diagnostic-initramfs-v1 \
	expected_avb_salt=ea9e90fdbf1bfdbe75816462ae79897e6cf7749d9e87607be2b033b7cfb06517 \
	expected_avb_digest=9647a92d83bc1d3a71a59742d8aacd8d05b9e5105ac729c792e6577ef9af52eb \
	recovery_init=\$repo/initramfs/recovery-init
do
	grep -Fxq "$assignment" <<<"$case_unindented" ||
		fail "current production HOLD profile omits $assignment"
done

grep -Fq \
	"fail 'current production HOLD profile is offline-only and not boot-authorized'" \
	<<<"$case_source" ||
	fail 'current production HOLD profile does not reject connected actions'
contract_source=$(awk -v profile="$profile" '
	/^# Historical profiles retain/ { contracts = 1 }
	contracts && index($0, "\t" profile ")") == 1 { capture = 1 }
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
	cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc
	03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0
	headless-netroot-early-diag-v2
)
fields=(recovery trust manifest host-verifier bundle)
errors=(
	'current production recovery image is not pinned'
	'current production trust key is not pinned'
	'current production runtime manifest is not pinned'
	'current production host verifier is not pinned'
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

for action in preflight boot; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
		ROG5_STABLE_RECOVERY_PROFILE="$profile" \
		LIVE_BUILD_ROOT="$repo/build/unused-current-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-current-component-root" \
		TRUST_KEY="$repo/build/unused-current-trust-key" \
		BUNDLE_ROOT="$repo/build/unused-current-bundle-root" \
		BUNDLE="${exact[4]}" \
		RECOVERY_SHA256="${exact[0]}" \
		TRUST_KEY_SHA256="${exact[1]}" \
		MANIFEST_SHA256="${exact[2]}" \
		HOST_VERIFIER_SHA256="${exact[3]}" \
		bash "$gate" "$action" >"$tmp/out" 2>"$tmp/err"
	then
		fail "current production HOLD profile reached $action"
	fi
	grep -Fq \
		'current production HOLD profile is offline-only and not boot-authorized' \
		"$tmp/err" || fail "current production $action returned a wrong rejection"
	[[ ! -s $tmp/out && $(wc -l <"$tmp/err") -eq 1 &&
		$(cat "$tmp/err") == \
		'FAIL current production HOLD profile is offline-only and not boot-authorized' ]] ||
		fail "current production $action emitted output before its rejection"
done

[[ $(awk -F '\t' '$2 == "allow" { count++ } END { print count + 0 }' \
	"$boot_policy") == 0 ]] || fail 'current temporary-boot policy is not empty'
! grep -Fq "$profile" "$claim_consumer" ||
	fail 'current production HOLD profile has a consumable claim'

production_root=$repo/build/host-rendezvous-v3-haven-production-20260810-r2
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
else
	[[ ${REQUIRE_CURRENT_PRODUCTION_ARTIFACT:-0} != 1 ]] ||
		fail 'required current production artifact output is absent'
	echo 'SKIP current production artifact preflight: ignored clean-twin output absent' >&2
fi

echo 'PASS current production recovery profile is exact, authority-free, and offline-only'
