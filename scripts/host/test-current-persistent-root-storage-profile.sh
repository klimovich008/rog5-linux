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
inventory=$repo/manifests/artifacts.tsv
profile=persistent-root-storage-read-v3-live-v1
image_name=build/persistent-root-storage-read-v3-generation24-20260812-r1/repack/stable-recovery-a.avb.img
basis='one exact precheck-USB-observable read-only UFS persistent Arch recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
role='unbooted precheck-USB-observable read-only UFS persistent Arch recovery; clean-twin signed bundle and byte-distinct Generation 24 AVB wrapper; one RAM-only use only; never flash'
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM

case_source=$(awk -v profile="$profile" '
	/^# Historical profiles retain/ { contracts = 1 }
	!contracts && index($0, "\t" profile ")") == 1 { capture = 1; count++ }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
	END { if (count != 1) exit 1 }
' "$gate") || fail 'persistent-root live profile case is not unique'
case_unindented=$(sed 's/^[[:space:]]*//' <<<"$case_source")
for assignment in \
	expected_boot_image=$image_name \
	expected_kernel=2e5d6e1766aab790dd1d1718125244886d376ffb73aa6b761571b12820b3061c \
	expected_raw=067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff \
	expected_initramfs=d9a3fba43abf0c3e456feb2e7f9da5e043df1e7cdef2e33112e0313358ae98d8 \
	expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31 \
	expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800 \
	expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef \
	expected_target_id=persistent-root-storage-read-v3 \
	expected_bundle=persistent-root-storage-read-v3 \
	expected_bundle_profile=persistent-root-ro-v1 \
	expected_target_release=7.1.4-gcfd385a1c754 \
	expected_avb_salt=ee656e98fa1e7345f8684aa9553a9ce5f008ed7e7b0c4d42a33dde6bc288d4bd \
	expected_avb_digest=e6820b4f03ad6a422c255093019be6b2df09f2b135d07d16e3bbc290df566c10 \
	expected_generation_record=ed213bacc14e6c2c88a380595c0b4a9b6aa8b6cea31b0119fd87043a152fb46d \
	recovery_init=\$repo/initramfs/recovery-init
do
	grep -Fxq "$assignment" <<<"$case_unindented" ||
		fail "persistent-root live profile omits $assignment"
done

contract_source=$(awk -v profile="$profile" '
	/^# Historical profiles retain/ { contracts = 1 }
	contracts && index($0, "\t" profile) == 1 { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
grep -Fq $'\tinitramfs_contract=exact-a600000-v1' <<<"$contract_source" ||
	fail 'persistent-root profile lacks the exact recovery-init contract'
grep -Fq 'grep -Fxq "target_release=$expected_target_release"' "$gate" ||
	fail 'stable gate does not verify the profile-specific target release'

exact=(
	6850d79af138717190ab58e171a6f7f1d9874510026c9f10bf57d35a3e9f6bca
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	3bc4b40f7e230945249db08be19b5791c176e08aeb8b5cfca059f48db5b8ed73
	03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0
	persistent-root-storage-read-v3
)
run_policy() {
	env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE="$profile" \
		RECOVERY_SHA256="$1" TRUST_KEY_SHA256="$2" \
		MANIFEST_SHA256="$3" HOST_VERIFIER_SHA256="$4" BUNDLE="$5" \
		bash "$gate" policy-preflight
}
policy=$(run_policy "${exact[@]}")
grep -Fxq "recovery_profile=$profile" <<<"$policy"
grep -Fxq 'target_id=persistent-root-storage-read-v3' <<<"$policy"
grep -Fxq 'authority=none' <<<"$policy"
grep -Fxq 'result=PASS' <<<"$policy"

fields=(recovery trust manifest host-verifier bundle)
errors=(
	'persistent-root recovery image is not pinned'
	'persistent-root trust key is not pinned'
	'persistent-root runtime manifest is not pinned'
	'persistent-root host verifier is not pinned'
	'profile requires bundle=persistent-root-storage-read-v3'
)
for index in "${!fields[@]}"; do
	mutation=("${exact[@]}")
	if ((index == 4)); then
		mutation[$index]=wrong-persistent-bundle
	else
		mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
	fi
	if run_policy "${mutation[@]}" >"$tmp/out" 2>"$tmp/err"; then
		fail "persistent-root policy accepted wrong ${fields[$index]}"
	fi
	grep -Fq "${errors[$index]}" "$tmp/err" ||
		fail "wrong ${fields[$index]} returned an unexpected rejection"
done

awk -F '\t' -v name="$image_name" -v basis="$basis" '
	$1 == name && $2 == "allow" && $3 == basis && NF == 3 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$boot_policy" || fail 'persistent-root image is not uniquely admitted'
awk -F '\t' -v name="$image_name" -v role="$role" '
	$1 == name && $2 == "100663296" &&
	$3 == "6850d79af138717190ab58e171a6f7f1d9874510026c9f10bf57d35a3e9f6bca" &&
	$4 == role && $5 == "no" && NF == 5 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$inventory" || fail 'persistent-root artifact inventory is not exact'
grep -Fq "\"$profile\":" "$claim_consumer" ||
	fail 'persistent-root profile lacks an exact-record claim'
grep -Fq 'PERSISTENT_TARGET_PRODUCT = "ROG5 persistent root"' \
	"$repo/scripts/host/pin-minimal-headless-host-key.py" ||
	fail 'host-key pinning does not accept the exact persistent-root gadget'

production_root=$repo/build/persistent-root-storage-read-v3-production-20260812-r1
generation_root=$repo/build/persistent-root-storage-read-v3-generation24-20260812-r1
recovery_root=$repo/build/headless-core-v21-production-20260812-r1/recovery
if [[ -d $production_root/bundle-a && -d $generation_root && -d $recovery_root ]]; then
	artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE="$profile" \
			LIVE_BUILD_ROOT="$generation_root" \
			RECOVERY_COMPONENT_ROOT="$recovery_root" \
			TRUST_KEY="$recovery_root/ephemeral-public.raw" \
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
		<<<"$artifact" || fail 'persistent-root artifact preflight did not pass'
else
	[[ ${REQUIRE_CURRENT_PERSISTENT_ARTIFACT:-0} != 1 ]] ||
		fail 'required persistent-root clean-twin output is absent'
	echo 'SKIP persistent-root artifact preflight: ignored clean-twin output absent' >&2
fi

echo 'PASS Generation 24 precheck-USB-observable read-only UFS persistent-root profile, exact claim, and admission are pinned'
